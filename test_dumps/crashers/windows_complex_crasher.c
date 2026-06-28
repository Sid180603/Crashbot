/*
 * windows_complex_crasher.c
 *
 * Generates extremely hard-to-parse Windows crash dumps for testing
 * crash analysis tools (Crashbot). Each mode produces a different
 * pathological crash scenario.
 *
 * BUILD (MSVC x64 Native Tools Command Prompt):
 *   cl /Zi /Od /W4 /Fe:windows_complex_crasher.exe windows_complex_crasher.c ^
 *      /link /DEBUG:FULL dbghelp.lib kernel32.lib user32.lib advapi32.lib
 *
 * USAGE:
 *   windows_complex_crasher.exe <mode> [dump_path]
 *
 *   Modes:
 *     1  Multi-threaded race condition crash (heap corruption)
 *     2  Deep recursion with mixed calling conventions
 *     3  Exception chain (__try/__except nesting)
 *     4  Corrupted stack frame (broken EBP/RBP)
 *     5  DLL callback crash (dynamically loaded function)
 *     6  VEH chain (vectored exception handlers modify context)
 *     0  Run ALL modes sequentially (each writes its own dump)
 *
 *   dump_path: Optional directory for .dmp files (default: current dir)
 *
 * NOTES:
 *   - Target: x64 (AMD64). Works on x86 with minor changes.
 *   - Uses MiniDumpWriteDump to capture dump before fatal crash.
 *   - MSVC-compatible C; avoids C99/C11 features MSVC handles poorly.
 *   - #ifdef _WIN32 guards allow compilation (as no-op) on other platforms.
 */

#ifdef _WIN32

/* Must define before including windows.h to get full API */
#define WIN32_LEAN_AND_MEAN
#define _CRT_SECURE_NO_WARNINGS

#include <windows.h>
#include <dbghelp.h>
#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#pragma comment(lib, "dbghelp.lib")

/* =========================================================================
 * Forward declarations
 * ========================================================================= */

static void write_minidump(const char *filename, EXCEPTION_POINTERS *ep);
static void crash_mode_1_race_condition(const char *dump_dir);
static void crash_mode_2_mixed_calling(const char *dump_dir);
static void crash_mode_3_exception_chain(const char *dump_dir);
static void crash_mode_4_corrupted_frame(const char *dump_dir);
static void crash_mode_5_dll_callback(const char *dump_dir);
static void crash_mode_6_veh_chain(const char *dump_dir);

/* =========================================================================
 * Globals (intentionally messy to make dump analysis harder)
 * ========================================================================= */

/* Shared state for race-condition mode */
static volatile LONG g_race_counter = 0;
static volatile LONG g_race_ready = 0;
static volatile LONG g_race_go = 0;
static char *g_shared_heap_block = NULL;
static CRITICAL_SECTION g_cs_fake; /* intentionally misused */

/* For VEH chain */
static volatile LONG g_veh_handler_count = 0;
static PVOID g_veh_handles[8];
static volatile int g_veh_crash_now = 0;

/* Dump directory passed through global for exception filter access */
static char g_dump_dir[MAX_PATH];

/* =========================================================================
 * Utility: MiniDump writer
 * ========================================================================= */

static void write_minidump(const char *filename, EXCEPTION_POINTERS *ep)
{
    HANDLE hFile;
    MINIDUMP_EXCEPTION_INFORMATION mei;
    MINIDUMP_TYPE dump_type;
    char full_path[MAX_PATH * 2];

    _snprintf(full_path, sizeof(full_path) - 1, "%s", filename);
    full_path[sizeof(full_path) - 1] = '\0';

    hFile = CreateFileA(
        full_path,
        GENERIC_WRITE,
        0,
        NULL,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        NULL
    );

    if (hFile == INVALID_HANDLE_VALUE) {
        fprintf(stderr, "[!] Failed to create dump file: %s (error %lu)\n",
                full_path, GetLastError());
        return;
    }

    /* Use a comprehensive dump type to make the dump large and realistic */
    dump_type = (MINIDUMP_TYPE)(
        MiniDumpWithFullMemory |
        MiniDumpWithFullMemoryInfo |
        MiniDumpWithHandleData |
        MiniDumpWithThreadInfo |
        MiniDumpWithUnloadedModules |
        MiniDumpWithProcessThreadData |
        MiniDumpWithFullAuxiliaryState |
        MiniDumpWithIndirectlyReferencedMemory
    );

    if (ep != NULL) {
        mei.ThreadId = GetCurrentThreadId();
        mei.ExceptionPointers = ep;
        mei.ClientPointers = FALSE;

        MiniDumpWriteDump(
            GetCurrentProcess(),
            GetCurrentProcessId(),
            hFile,
            dump_type,
            &mei,
            NULL,
            NULL
        );
    } else {
        MiniDumpWriteDump(
            GetCurrentProcess(),
            GetCurrentProcessId(),
            hFile,
            dump_type,
            NULL,
            NULL,
            NULL
        );
    }

    CloseHandle(hFile);
    printf("[+] Dump written: %s\n", full_path);
}

static void build_dump_path(char *out, size_t out_size,
                            const char *dump_dir, const char *mode_name)
{
    time_t now;
    struct tm *t;
    time(&now);
    t = localtime(&now);
    _snprintf(out, out_size - 1,
              "%s\\crash_%s_%04d%02d%02d_%02d%02d%02d.dmp",
              dump_dir, mode_name,
              t->tm_year + 1900, t->tm_mon + 1, t->tm_mday,
              t->tm_hour, t->tm_min, t->tm_sec);
    out[out_size - 1] = '\0';
}

/* =========================================================================
 * MODE 1: Multi-threaded race condition crash
 *
 * Multiple threads hammer a shared heap block with no synchronization.
 * One thread frees the block while others are writing. This causes
 * heap corruption that produces extremely confusing dump state:
 * - Multiple threads in the same address range
 * - Freed memory being written to
 * - Corrupted heap metadata
 * ========================================================================= */

#define RACE_THREAD_COUNT 8
#define RACE_BLOCK_SIZE   4096
#define RACE_ITERATIONS   500000

/* Padding struct to create interesting local variables in each thread */
typedef struct {
    int thread_id;
    char local_buffer[256];
    double computation_results[32];
    void *pointer_chain[16];
    DWORD start_tick;
    DWORD iteration_count;
    volatile int *shared_flag;
} RaceThreadContext;

static unsigned __stdcall race_worker_thread(void *param)
{
    RaceThreadContext ctx;
    int i, j;
    char *local_heap;
    volatile char dummy;

    /* Fill context with identifiable data */
    memset(&ctx, 0, sizeof(ctx));
    ctx.thread_id = (int)(INT_PTR)param;
    ctx.start_tick = GetTickCount();
    ctx.shared_flag = (volatile int *)&g_race_go;

    /* Each thread makes its own allocation to fragment the heap */
    local_heap = (char *)HeapAlloc(GetProcessHeap(), 0, 1024 + ctx.thread_id * 64);
    if (local_heap) {
        memset(local_heap, 0xCC + ctx.thread_id, 1024 + ctx.thread_id * 64);
    }

    /* Build a fake pointer chain (will appear in dump memory) */
    for (i = 0; i < 16; i++) {
        ctx.pointer_chain[i] = (void *)(ULONG_PTR)(0xDEAD0000 + ctx.thread_id * 0x1000 + i);
    }

    _snprintf(ctx.local_buffer, sizeof(ctx.local_buffer),
              "RaceThread-%d-PID-%lu", ctx.thread_id, GetCurrentProcessId());

    /* Signal ready and spin-wait for go */
    InterlockedIncrement(&g_race_ready);
    while (!g_race_go) {
        YieldProcessor();
    }

    /* Hammer the shared block */
    for (i = 0; i < RACE_ITERATIONS; i++) {
        ctx.iteration_count++;

        /* Computation to fill locals with interesting values */
        for (j = 0; j < 32; j++) {
            ctx.computation_results[j] = (double)(i * ctx.thread_id + j) / 3.14159;
        }

        if (g_shared_heap_block != NULL) {
            /* Intentional race: read and write without locking */
            volatile int offset = (i + ctx.thread_id * 37) % RACE_BLOCK_SIZE;
            g_shared_heap_block[offset] = (char)(ctx.thread_id ^ i);
            dummy = g_shared_heap_block[(offset + 1) % RACE_BLOCK_SIZE];
            (void)dummy;

            /* Thread 0 periodically frees and re-allocates the block */
            if (ctx.thread_id == 0 && (i % 1000) == 999) {
                char *old = g_shared_heap_block;
                g_shared_heap_block = NULL;
                HeapFree(GetProcessHeap(), 0, old);
                Sleep(0); /* yield to maximize race window */
                g_shared_heap_block = (char *)HeapAlloc(
                    GetProcessHeap(), 0, RACE_BLOCK_SIZE);
                if (g_shared_heap_block) {
                    memset(g_shared_heap_block, 0xAA, RACE_BLOCK_SIZE);
                }
            }

            /* Thread 3 does double-free after many iterations */
            if (ctx.thread_id == 3 && i == RACE_ITERATIONS - 100) {
                HeapFree(GetProcessHeap(), 0, g_shared_heap_block);
                /* Don't NULL it -- other threads will use-after-free */
            }

            /* Thread 5 corrupts heap metadata by writing before the block */
            if (ctx.thread_id == 5 && i > RACE_ITERATIONS / 2) {
                if (g_shared_heap_block) {
                    /* Write before allocation start -- heap metadata corruption */
                    char *bad_ptr = g_shared_heap_block - 16;
                    *bad_ptr = (char)0xFF;
                }
            }
        }

        InterlockedIncrement(&g_race_counter);
    }

    if (local_heap) {
        HeapFree(GetProcessHeap(), 0, local_heap);
    }

    return 0;
}

static LONG WINAPI race_exception_filter(EXCEPTION_POINTERS *ep)
{
    char path[MAX_PATH * 2];
    build_dump_path(path, sizeof(path), g_dump_dir, "race_condition");
    printf("[!] Race condition crash caught! Exception code: 0x%08lX\n",
           ep->ExceptionRecord->ExceptionCode);
    write_minidump(path, ep);
    return EXCEPTION_EXECUTE_HANDLER;
}

static void crash_mode_1_race_condition(const char *dump_dir)
{
    HANDLE threads[RACE_THREAD_COUNT];
    int i;

    printf("\n=== MODE 1: Multi-threaded race condition crash ===\n");

    strncpy(g_dump_dir, dump_dir, MAX_PATH - 1);
    g_dump_dir[MAX_PATH - 1] = '\0';

    g_race_counter = 0;
    g_race_ready = 0;
    g_race_go = 0;

    InitializeCriticalSection(&g_cs_fake);

    g_shared_heap_block = (char *)HeapAlloc(GetProcessHeap(), 0, RACE_BLOCK_SIZE);
    if (!g_shared_heap_block) {
        fprintf(stderr, "[!] HeapAlloc failed\n");
        return;
    }
    memset(g_shared_heap_block, 0xBB, RACE_BLOCK_SIZE);

    /* Spawn worker threads */
    for (i = 0; i < RACE_THREAD_COUNT; i++) {
        threads[i] = (HANDLE)_beginthreadex(
            NULL, 0, race_worker_thread, (void *)(INT_PTR)i, 0, NULL);
    }

    /* Wait for all threads to be ready */
    while (g_race_ready < RACE_THREAD_COUNT) {
        Sleep(1);
    }

    printf("[*] All %d threads ready, releasing...\n", RACE_THREAD_COUNT);

    /* Set the unhandled exception filter to capture dump */
    SetUnhandledExceptionFilter(race_exception_filter);

    /* Go! */
    InterlockedExchange(&g_race_go, 1);

    /* Wait for threads -- crash is expected during execution */
    WaitForMultipleObjects(RACE_THREAD_COUNT, threads, TRUE, 30000);

    /* If we get here without crashing, force a heap corruption crash */
    printf("[*] Threads completed without crash, forcing heap corruption...\n");
    {
        char dump_path[MAX_PATH * 2];
        build_dump_path(dump_path, sizeof(dump_path), dump_dir, "race_condition");

        __try {
            /* Force heap corruption by double-freeing */
            if (g_shared_heap_block) {
                HeapFree(GetProcessHeap(), 0, g_shared_heap_block);
                HeapFree(GetProcessHeap(), 0, g_shared_heap_block);
            }
            /* If double-free didn't crash, corrupt more aggressively */
            {
                char *p = (char *)HeapAlloc(GetProcessHeap(), 0, 64);
                if (p) {
                    /* Overwrite heap metadata */
                    memset(p - 32, 0xFF, 96);
                    HeapFree(GetProcessHeap(), 0, p);
                }
            }
        } __except(
            write_minidump(dump_path, GetExceptionInformation()),
            EXCEPTION_EXECUTE_HANDLER
        ) {
            printf("[+] Heap corruption crash captured in dump.\n");
        }
    }

    for (i = 0; i < RACE_THREAD_COUNT; i++) {
        CloseHandle(threads[i]);
    }

    DeleteCriticalSection(&g_cs_fake);
}

/* =========================================================================
 * MODE 2: Deep recursion with mixed calling conventions
 *
 * __cdecl and __stdcall functions call each other in a deep recursive
 * chain. Different parameter counts and local variable sizes at each
 * level create a confusing stack trace where the unwinder cannot easily
 * determine frame boundaries.
 * ========================================================================= */

#define MIXED_RECURSION_DEPTH 150

/* Large struct to make stack frames big and variable-sized */
typedef struct {
    char label[64];
    int depth;
    double values[16];
    void *prev_frame;
    DWORD thread_id;
    LARGE_INTEGER timestamp;
    char padding[128];
} MixedCallFrame;

/* Forward declarations for mutual recursion */
static int __cdecl  mixed_cdecl_func(int depth, int mode, void *prev);
static int __stdcall mixed_stdcall_func(int depth, int mode, void *prev);
static void __cdecl  mixed_leaf_crash(int depth, void *frame_ptr);

/* __cdecl path: variable number of args, caller cleans stack */
static int __cdecl mixed_cdecl_func(int depth, int mode, void *prev)
{
    MixedCallFrame frame;
    volatile int local_array[32];
    volatile double fp_accumulator;
    int i;

    memset(&frame, 0, sizeof(frame));
    frame.depth = depth;
    frame.prev_frame = prev;
    frame.thread_id = GetCurrentThreadId();
    QueryPerformanceCounter((LARGE_INTEGER *)&frame.timestamp);
    _snprintf(frame.label, sizeof(frame.label), "cdecl_frame_%d_mode_%d", depth, mode);

    /* Fill local array with depth-dependent pattern */
    for (i = 0; i < 32; i++) {
        local_array[i] = depth * 1000 + i * 7 + mode;
    }

    /* Floating-point computation to dirty FP registers */
    fp_accumulator = 0.0;
    for (i = 0; i < 16; i++) {
        frame.values[i] = (double)(depth * i) / 2.71828;
        fp_accumulator += frame.values[i];
    }

    if (depth <= 0) {
        mixed_leaf_crash(depth, &frame);
        return -1; /* unreachable */
    }

    /* Alternate between calling conventions based on depth parity */
    if (depth % 3 == 0) {
        return mixed_stdcall_func(depth - 1, mode ^ 1, &frame);
    } else if (depth % 3 == 1) {
        /* Double recursion: call self then stdcall */
        i = mixed_cdecl_func(depth - 2, mode + 1, &frame);
        return mixed_stdcall_func(depth - 1, i, &frame);
    } else {
        return mixed_cdecl_func(depth - 1, (int)(fp_accumulator) % 5, &frame);
    }
}

/* __stdcall path: callee cleans stack, different ABI */
static int __stdcall mixed_stdcall_func(int depth, int mode, void *prev)
{
    MixedCallFrame frame;
    volatile char big_local[512]; /* extra large frame */
    volatile DWORD canary_before;
    volatile DWORD canary_after;
    int result;

    canary_before = 0xCAFEBABE;
    canary_after = 0xDEADBEEF;

    memset(&frame, 0, sizeof(frame));
    memset((void *)big_local, (char)(depth & 0xFF), sizeof(big_local));

    frame.depth = depth;
    frame.prev_frame = prev;
    frame.thread_id = GetCurrentThreadId();
    QueryPerformanceCounter((LARGE_INTEGER *)&frame.timestamp);
    _snprintf(frame.label, sizeof(frame.label), "stdcall_frame_%d_mode_%d", depth, mode);

    if (depth <= 0) {
        mixed_leaf_crash(depth, &frame);
        return -1;
    }

    /* Verify canaries (they'll be corrupted in mode 4) */
    if (canary_before != 0xCAFEBABE || canary_after != 0xDEADBEEF) {
        printf("[!] Stack corruption detected at depth %d!\n", depth);
    }

    if (depth % 2 == 0) {
        result = mixed_cdecl_func(depth - 1, mode ^ depth, &frame);
    } else {
        result = mixed_stdcall_func(depth - 1, mode + depth, &frame);
    }

    return result + (int)canary_before;
}

/* Leaf function: writes the dump and crashes */
static void __cdecl mixed_leaf_crash(int depth, void *frame_ptr)
{
    char path[MAX_PATH * 2];
    volatile int *null_ptr;

    printf("[*] Reached recursion leaf at depth %d, crashing...\n", depth);
    build_dump_path(path, sizeof(path), g_dump_dir, "mixed_calling");

    __try {
        null_ptr = NULL;
        *null_ptr = 0x41414141;
    } __except(
        write_minidump(path, GetExceptionInformation()),
        EXCEPTION_EXECUTE_HANDLER
    ) {
        printf("[+] Mixed calling convention crash captured.\n");
    }
}

static void crash_mode_2_mixed_calling(const char *dump_dir)
{
    printf("\n=== MODE 2: Deep recursion with mixed calling conventions ===\n");
    strncpy(g_dump_dir, dump_dir, MAX_PATH - 1);
    mixed_cdecl_func(MIXED_RECURSION_DEPTH, 42, NULL);
}

/* =========================================================================
 * MODE 3: Exception chain
 *
 * Nested __try/__except blocks where inner handlers re-raise or trigger
 * new exceptions. The resulting exception record chain is deeply nested
 * and contains multiple exception codes, making analysis very difficult.
 * ========================================================================= */

#define EXCEPTION_CHAIN_DEPTH 12

typedef struct ExceptionChainContext {
    int level;
    DWORD exception_code;
    char description[128];
    void *next;
    volatile int touched;
    CONTEXT saved_context;
} ExceptionChainContext;

static int chain_exception_level(int level, ExceptionChainContext *ctx_chain);

static int chain_inner_handler(int level, EXCEPTION_POINTERS *ep,
                               ExceptionChainContext *ctx)
{
    printf("  [handler] Level %d caught exception 0x%08lX\n",
           level, ep->ExceptionRecord->ExceptionCode);

    ctx->exception_code = ep->ExceptionRecord->ExceptionCode;
    ctx->touched = 1;

    /* Save the CPU context at this exception point */
    memcpy(&ctx->saved_context, ep->ContextRecord, sizeof(CONTEXT));

    /* Odd levels re-raise by returning CONTINUE_SEARCH */
    if (level % 3 == 0) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    return EXCEPTION_EXECUTE_HANDLER;
}

static int chain_exception_level(int level, ExceptionChainContext *ctx_chain)
{
    ExceptionChainContext local_ctx;
    volatile int *bad_ptr;
    volatile int trigger;
    int result = 0;

    memset(&local_ctx, 0, sizeof(local_ctx));
    local_ctx.level = level;
    local_ctx.next = ctx_chain;
    _snprintf(local_ctx.description, sizeof(local_ctx.description),
              "ExceptionChain-Level%d-TID%lu", level, GetCurrentThreadId());

    if (level <= 0) {
        /* Bottom of chain: trigger the initial exception */
        printf("  [chain] Bottom reached, triggering access violation...\n");

        __try {
            bad_ptr = NULL;
            trigger = *bad_ptr; /* ACCESS_VIOLATION */
            (void)trigger;
        } __except(chain_inner_handler(level, GetExceptionInformation(), &local_ctx)) {
            printf("  [chain] Level %d handled AV\n", level);
            /* Now trigger a different exception */
            __try {
                RaiseException(0xE0000001, 0, 0, NULL); /* custom exception */
            } __except(chain_inner_handler(level + 100, GetExceptionInformation(), &local_ctx)) {
                printf("  [chain] Level %d handled custom exception\n", level);
            }
        }
        return 1;
    }

    /* Recurse deeper, catching whatever bubbles up */
    __try {
        __try {
            result = chain_exception_level(level - 1, &local_ctx);

            /* After inner returns, raise our own exception */
            if (level % 2 == 0) {
                RaiseException(
                    0xE0000000 + level,
                    EXCEPTION_NONCONTINUABLE,
                    0,
                    NULL
                );
            } else {
                /* Integer divide by zero */
                __try {
                    volatile int zero = 0;
                    trigger = 1 / zero;
                    (void)trigger;
                } __except(chain_inner_handler(level + 200, GetExceptionInformation(), &local_ctx)) {
                    printf("  [chain] Level %d handled div-by-zero\n", level);
                    /* Re-raise as custom */
                    RaiseException(0xE0000000 + level * 10, 0, 0, NULL);
                }
            }
        } __except(chain_inner_handler(level, GetExceptionInformation(), &local_ctx)) {
            printf("  [chain] Level %d outer handler caught 0x%08lX\n",
                   level, local_ctx.exception_code);
            /* Sometimes re-raise to outer layers */
            if (level > EXCEPTION_CHAIN_DEPTH / 2) {
                RaiseException(local_ctx.exception_code, 0, 0, NULL);
            }
        }
    } __except(
        (level == EXCEPTION_CHAIN_DEPTH) ?
            EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH
    ) {
        printf("  [chain] Top-level handler at level %d\n", level);
    }

    return result;
}

static void crash_mode_3_exception_chain(const char *dump_dir)
{
    char path[MAX_PATH * 2];
    ExceptionChainContext root_ctx;

    printf("\n=== MODE 3: Exception chain ===\n");
    strncpy(g_dump_dir, dump_dir, MAX_PATH - 1);

    memset(&root_ctx, 0, sizeof(root_ctx));
    _snprintf(root_ctx.description, sizeof(root_ctx.description), "ROOT");

    build_dump_path(path, sizeof(path), dump_dir, "exception_chain");

    __try {
        chain_exception_level(EXCEPTION_CHAIN_DEPTH, &root_ctx);
    } __except(
        write_minidump(path, GetExceptionInformation()),
        EXCEPTION_EXECUTE_HANDLER
    ) {
        printf("[+] Exception chain crash captured.\n");
    }
}

/* =========================================================================
 * MODE 4: Corrupted stack frame
 *
 * Deliberately corrupt the frame pointer (RBP on x64) and other
 * stack-walking metadata before crashing. This makes debugger stack
 * unwinding produce garbage or truncated traces.
 * ========================================================================= */

/* Nested functions with large frames to make corruption more impactful */
static volatile int g_stack_corruption_depth = 0;

typedef struct {
    char function_name[64];
    void *return_address_fake;
    void *frame_pointer_fake;
    DWORD_PTR stack_values[64];
    char marker[32];
} StackCorruptionFrame;

/* This function is called at the bottom; it corrupts its own stack frame */
#pragma optimize("", off) /* prevent compiler from optimizing away our corruption */

static void __cdecl corrupt_stack_and_crash(int depth)
{
    StackCorruptionFrame frame;
    volatile char *stack_ptr;
    volatile DWORD_PTR *frame_ptr;
    char path[MAX_PATH * 2];
    int i;

    memset(&frame, 0, sizeof(frame));
    _snprintf(frame.function_name, sizeof(frame.function_name),
              "corrupt_stack_depth_%d", depth);
    memcpy(frame.marker, "STACK_CORRUPTION_MARKER!", 24);

    /* Fill frame with recognizable pattern */
    for (i = 0; i < 64; i++) {
        frame.stack_values[i] = (DWORD_PTR)0xDEADC0DE00000000ULL + i;
    }

    /* Create fake return addresses and frame pointers */
    frame.return_address_fake = (void *)0x00007FF700001234ULL;
    frame.frame_pointer_fake = (void *)0x00007FF700005678ULL;

    build_dump_path(path, sizeof(path), g_dump_dir, "corrupted_stack");

    /* Now corrupt the stack: write garbage over the saved RBP and return addr.
     * On x64, RBP is at [RSP+offset] depending on frame size.
     * We use inline asm or pointer arithmetic to find and corrupt it. */

    /* Strategy: get current RSP, then write garbage above our frame */
#if defined(_M_X64) || defined(_M_AMD64)
    {
        /* On x64, corrupt memory around our frame pointer area */
        volatile char *base;
        volatile DWORD_PTR *qword_ptr;

        /* Get approximate stack pointer location */
        base = (volatile char *)&frame;

        /* Write corrupt frame pointers above and below our frame.
         * This will confuse the stack unwinder which relies on
         * the RBP chain to walk frames. */
        for (i = 0; i < 8; i++) {
            /* Write fake return addresses into the stack area above us */
            qword_ptr = (volatile DWORD_PTR *)(base + sizeof(frame) + i * 8);

            __try {
                *qword_ptr = 0x00007FF700000000ULL + (i * 0x1000);
            } __except(EXCEPTION_EXECUTE_HANDLER) {
                /* Guard page or invalid -- skip */
            }
        }

        /* Corrupt our own saved frame pointer if we can find it.
         * Write several QWORD values below our locals that will
         * land on saved RBP / return addr from the caller. */
        for (i = 1; i <= 16; i++) {
            qword_ptr = (volatile DWORD_PTR *)(base - i * 8);
            __try {
                /* Mix of plausible-looking and garbage addresses */
                if (i % 2 == 0) {
                    *qword_ptr = 0x00007FF7DEADBEEFULL;
                } else {
                    *qword_ptr = 0xCCCCCCCCCCCCCCCCULL;
                }
            } __except(EXCEPTION_EXECUTE_HANDLER) {
                break; /* hit guard page */
            }
        }
    }
#elif defined(_M_IX86)
    {
        /* On x86, corrupt EBP chain directly */
        volatile DWORD *ebp_ptr;
        __asm {
            mov eax, ebp
            mov ebp_ptr, eax
        }
        /* Corrupt saved EBP and return address */
        __try {
            ebp_ptr[0] = 0xDEADBEEF; /* saved EBP */
            ebp_ptr[1] = 0x41414141; /* return address */
        } __except(EXCEPTION_EXECUTE_HANDLER) {
            /* ignore */
        }
    }
#endif

    printf("[*] Stack corrupted, triggering crash...\n");

    /* Now crash -- the stack is corrupted so the dump's stack trace
     * will be garbled or truncated */
    __try {
        /* Access violation with corrupted stack */
        *(volatile int *)0 = 0xDEADDEAD;
    } __except(
        write_minidump(path, GetExceptionInformation()),
        EXCEPTION_EXECUTE_HANDLER
    ) {
        printf("[+] Corrupted stack frame crash captured.\n");
    }
}

#pragma optimize("", on)

/* Build up a deep stack before corrupting it */
static void __cdecl stack_buildup(int depth)
{
    StackCorruptionFrame frame;
    int i;

    memset(&frame, 0, sizeof(frame));
    _snprintf(frame.function_name, sizeof(frame.function_name),
              "stack_buildup_%d", depth);

    for (i = 0; i < 64; i++) {
        frame.stack_values[i] = (DWORD_PTR)(depth * 100 + i);
    }

    g_stack_corruption_depth = depth;

    if (depth > 0) {
        stack_buildup(depth - 1);
    } else {
        corrupt_stack_and_crash(depth);
    }
}

static void crash_mode_4_corrupted_frame(const char *dump_dir)
{
    printf("\n=== MODE 4: Corrupted stack frame ===\n");
    strncpy(g_dump_dir, dump_dir, MAX_PATH - 1);
    stack_buildup(30); /* 30 frames of buildup before corruption */
}

/* =========================================================================
 * MODE 5: DLL callback crash
 *
 * Dynamically loads system DLLs, obtains function pointers, and crashes
 * inside a callback invoked by a dynamically-resolved function. This
 * creates a stack trace that traverses multiple modules with no
 * static linkage, making symbol resolution very difficult.
 * ========================================================================= */

/* Callback functions that will be called from dynamically loaded code */
typedef BOOL (CALLBACK *ENUM_WINDOWS_PROC)(HWND, LPARAM);
typedef VOID (WINAPI *FIBER_START_ROUTINE)(PVOID);
typedef DWORD (WINAPI *THREAD_START_ROUTINE)(PVOID);
typedef void (WINAPI *PTP_WORK_CALLBACK)(PTP_CALLBACK_INSTANCE, PVOID, PTP_WORK);

/* Dynamic function types */
typedef BOOL (WINAPI *PFN_EnumWindows)(ENUM_WINDOWS_PROC, LPARAM);
typedef HANDLE (WINAPI *PFN_CreateThread)(
    LPSECURITY_ATTRIBUTES, SIZE_T, LPTHREAD_START_ROUTINE,
    LPVOID, DWORD, LPDWORD);
typedef LPVOID (WINAPI *PFN_ConvertThreadToFiber)(LPVOID);
typedef LPVOID (WINAPI *PFN_CreateFiber)(SIZE_T, LPFIBER_START_ROUTINE, LPVOID);
typedef void (WINAPI *PFN_SwitchToFiber)(LPVOID);

/* Struct to pass context through callback chains */
typedef struct {
    int callback_depth;
    char trace_info[256];
    HMODULE loaded_modules[8];
    int module_count;
    void *fiber_main;
    void *fiber_crash;
    const char *dump_dir;
    volatile int windows_enumerated;
} DllCallbackContext;

static DllCallbackContext g_dll_ctx;

/* Deeply nested helper called from the callback */
static void dll_callback_inner(int depth, DllCallbackContext *ctx)
{
    volatile char local_data[256];
    int i;

    memset((void *)local_data, (char)(depth & 0xFF), sizeof(local_data));

    for (i = 0; i < 256; i++) {
        local_data[i] = (char)(depth * 17 + i);
    }

    if (depth > 0) {
        dll_callback_inner(depth - 1, ctx);
    } else {
        /* Crash inside the deeply nested callback */
        char path[MAX_PATH * 2];
        build_dump_path(path, sizeof(path), ctx->dump_dir, "dll_callback");

        printf("[*] Crashing inside DLL callback chain (depth=%d)...\n",
               ctx->callback_depth);

        __try {
            /* Call through a function pointer that points to NULL */
            void (*func_ptr)(void) = NULL;
            func_ptr();
        } __except(
            write_minidump(path, GetExceptionInformation()),
            EXCEPTION_EXECUTE_HANDLER
        ) {
            printf("[+] DLL callback crash captured.\n");
        }
    }
}

/* EnumWindows callback -- called from user32.dll */
static BOOL CALLBACK enum_windows_callback(HWND hwnd, LPARAM lParam)
{
    DllCallbackContext *ctx = (DllCallbackContext *)lParam;
    char window_title[256];

    ctx->windows_enumerated++;
    GetWindowTextA(hwnd, window_title, sizeof(window_title));

    /* After enumerating a few windows, crash inside the callback */
    if (ctx->windows_enumerated >= 5) {
        ctx->callback_depth = ctx->windows_enumerated;
        dll_callback_inner(10, ctx);
        return FALSE; /* stop enumeration */
    }

    return TRUE; /* continue */
}

/* Fiber that crashes */
static void CALLBACK crash_fiber_proc(PVOID param)
{
    DllCallbackContext *ctx = (DllCallbackContext *)param;
    volatile char fiber_local[1024];
    int i;

    /* Fill fiber stack with identifiable data */
    for (i = 0; i < 1024; i++) {
        fiber_local[i] = (char)(0xFB ^ (i & 0xFF));
    }

    printf("[*] Inside crash fiber, depth=%d\n", ctx->callback_depth);
    ctx->callback_depth = 99;
    dll_callback_inner(15, ctx);

    /* Switch back (if we didn't crash) */
    if (ctx->fiber_main) {
        SwitchToFiber(ctx->fiber_main);
    }
}

static void crash_mode_5_dll_callback(const char *dump_dir)
{
    HMODULE hUser32, hKernel32, hNtdll;
    PFN_EnumWindows pfnEnumWindows;
    PFN_ConvertThreadToFiber pfnConvertThreadToFiber;
    PFN_CreateFiber pfnCreateFiber;
    PFN_SwitchToFiber pfnSwitchToFiber;

    printf("\n=== MODE 5: DLL callback crash ===\n");

    memset(&g_dll_ctx, 0, sizeof(g_dll_ctx));
    g_dll_ctx.dump_dir = dump_dir;

    /* Dynamically load system DLLs (even though they're usually loaded) */
    hUser32 = LoadLibraryA("user32.dll");
    hKernel32 = LoadLibraryA("kernel32.dll");
    hNtdll = LoadLibraryA("ntdll.dll");

    if (hUser32) g_dll_ctx.loaded_modules[g_dll_ctx.module_count++] = hUser32;
    if (hKernel32) g_dll_ctx.loaded_modules[g_dll_ctx.module_count++] = hKernel32;
    if (hNtdll) g_dll_ctx.loaded_modules[g_dll_ctx.module_count++] = hNtdll;

    /* Also load some less common DLLs to add noise */
    {
        HMODULE hExtra;
        const char *extra_dlls[] = {
            "version.dll", "winmm.dll", "crypt32.dll",
            "wintrust.dll", "imagehlp.dll"
        };
        int i;
        for (i = 0; i < 5 && g_dll_ctx.module_count < 8; i++) {
            hExtra = LoadLibraryA(extra_dlls[i]);
            if (hExtra) {
                g_dll_ctx.loaded_modules[g_dll_ctx.module_count++] = hExtra;
            }
        }
    }

    printf("[*] Loaded %d dynamic modules\n", g_dll_ctx.module_count);

    /* Strategy 1: Crash inside an EnumWindows callback */
    pfnEnumWindows = (PFN_EnumWindows)GetProcAddress(hUser32, "EnumWindows");
    if (pfnEnumWindows) {
        printf("[*] Attempting crash via EnumWindows callback...\n");
        pfnEnumWindows(enum_windows_callback, (LPARAM)&g_dll_ctx);
    }

    /* Strategy 2: If EnumWindows didn't trigger crash, try fiber-based crash */
    if (g_dll_ctx.callback_depth < 99) {
        printf("[*] Attempting crash via fiber...\n");
        pfnConvertThreadToFiber = (PFN_ConvertThreadToFiber)
            GetProcAddress(hKernel32, "ConvertThreadToFiber");
        pfnCreateFiber = (PFN_CreateFiber)
            GetProcAddress(hKernel32, "CreateFiber");
        pfnSwitchToFiber = (PFN_SwitchToFiber)
            GetProcAddress(hKernel32, "SwitchToFiber");

        if (pfnConvertThreadToFiber && pfnCreateFiber && pfnSwitchToFiber) {
            g_dll_ctx.fiber_main = pfnConvertThreadToFiber(NULL);
            if (g_dll_ctx.fiber_main) {
                g_dll_ctx.fiber_crash = pfnCreateFiber(
                    0, crash_fiber_proc, &g_dll_ctx);
                if (g_dll_ctx.fiber_crash) {
                    pfnSwitchToFiber(g_dll_ctx.fiber_crash);
                }
            }
        }
    }

    /* Cleanup loaded modules */
    {
        int i;
        for (i = 0; i < g_dll_ctx.module_count; i++) {
            FreeLibrary(g_dll_ctx.loaded_modules[i]);
        }
    }
}

/* =========================================================================
 * MODE 6: VEH (Vectored Exception Handler) chain
 *
 * Install multiple vectored exception handlers that modify the CPU context
 * (registers, instruction pointer) before passing the exception to the
 * next handler. By the time the exception reaches the final handler,
 * the context is completely different from the original crash state.
 * ========================================================================= */

/* Each VEH handler modifies different registers */
static LONG WINAPI veh_handler_0(EXCEPTION_POINTERS *ep)
{
    InterlockedIncrement(&g_veh_handler_count);
    printf("  [VEH-0] Handling exception 0x%08lX (handler count: %ld)\n",
           ep->ExceptionRecord->ExceptionCode, g_veh_handler_count);

    /* Modify general-purpose registers to confuse analysis */
#if defined(_M_X64) || defined(_M_AMD64)
    ep->ContextRecord->Rax = 0xAAAAAAAAAAAAAAAAULL;
    ep->ContextRecord->Rbx = 0xBBBBBBBBBBBBBBBBULL;
    ep->ContextRecord->R8  = 0x0000000800000008ULL;
    ep->ContextRecord->R9  = 0x0000000900000009ULL;
#elif defined(_M_IX86)
    ep->ContextRecord->Eax = 0xAAAAAAAA;
    ep->ContextRecord->Ebx = 0xBBBBBBBB;
#endif

    return EXCEPTION_CONTINUE_SEARCH; /* pass to next handler */
}

static LONG WINAPI veh_handler_1(EXCEPTION_POINTERS *ep)
{
    InterlockedIncrement(&g_veh_handler_count);
    printf("  [VEH-1] Handling exception 0x%08lX (handler count: %ld)\n",
           ep->ExceptionRecord->ExceptionCode, g_veh_handler_count);

    /* Modify more registers and the flags */
#if defined(_M_X64) || defined(_M_AMD64)
    ep->ContextRecord->Rcx = 0xCCCCCCCCCCCCCCCCULL;
    ep->ContextRecord->Rdx = 0xDDDDDDDDDDDDDDDDULL;
    ep->ContextRecord->R10 = 0x1010101010101010ULL;
    ep->ContextRecord->R11 = 0x1111111111111111ULL;
    /* Modify segment selectors (will appear in dump context) */
    ep->ContextRecord->EFlags ^= 0x00000800; /* toggle overflow flag */
#elif defined(_M_IX86)
    ep->ContextRecord->Ecx = 0xCCCCCCCC;
    ep->ContextRecord->Edx = 0xDDDDDDDD;
#endif

    return EXCEPTION_CONTINUE_SEARCH;
}

static LONG WINAPI veh_handler_2(EXCEPTION_POINTERS *ep)
{
    InterlockedIncrement(&g_veh_handler_count);
    printf("  [VEH-2] Handling exception 0x%08lX (handler count: %ld)\n",
           ep->ExceptionRecord->ExceptionCode, g_veh_handler_count);

    /* Modify floating-point and SSE state */
#if defined(_M_X64) || defined(_M_AMD64)
    ep->ContextRecord->R12 = 0x1212121212121212ULL;
    ep->ContextRecord->R13 = 0x1313131313131313ULL;
    ep->ContextRecord->R14 = 0x1414141414141414ULL;
    ep->ContextRecord->R15 = 0x1515151515151515ULL;

    /* Corrupt the XMM registers if XSTATE is available */
    if (ep->ContextRecord->ContextFlags & CONTEXT_FLOATING_POINT) {
        int i;
        for (i = 0; i < 16; i++) {
            ep->ContextRecord->FltSave.XmmRegisters[i].Low = 0xBADBADBADBADBAD0ULL + i;
            ep->ContextRecord->FltSave.XmmRegisters[i].High = 0xFEEDFEEDFEEDFE00ULL + i;
        }
    }
#endif

    return EXCEPTION_CONTINUE_SEARCH;
}

static LONG WINAPI veh_handler_3(EXCEPTION_POINTERS *ep)
{
    InterlockedIncrement(&g_veh_handler_count);
    printf("  [VEH-3] Handling exception 0x%08lX (handler count: %ld)\n",
           ep->ExceptionRecord->ExceptionCode, g_veh_handler_count);

    /* Modify the stack pointer to point somewhere else (dangerous but
     * the dump has already been written by an earlier handler if needed) */
#if defined(_M_X64) || defined(_M_AMD64)
    /* Don't actually change RSP -- just change RBP to break frame chain */
    ep->ContextRecord->Rbp = 0xDEADFACEDEADFACEULL;

    /* Also modify RSI/RDI which are used in some calling conventions */
    ep->ContextRecord->Rsi = 0x5151515151515151ULL;
    ep->ContextRecord->Rdi = 0xD1D1D1D1D1D1D1D1ULL;
#elif defined(_M_IX86)
    ep->ContextRecord->Ebp = 0xDEADFACE;
#endif

    return EXCEPTION_CONTINUE_SEARCH;
}

/* Final VEH handler: writes the dump (with all the corrupted context) */
static LONG WINAPI veh_handler_final(EXCEPTION_POINTERS *ep)
{
    char path[MAX_PATH * 2];

    InterlockedIncrement(&g_veh_handler_count);
    printf("  [VEH-FINAL] Writing dump with modified context (handler count: %ld)\n",
           g_veh_handler_count);

    build_dump_path(path, sizeof(path), g_dump_dir, "veh_chain");
    write_minidump(path, ep);

    return EXCEPTION_CONTINUE_SEARCH; /* let default handler terminate */
}

static void crash_mode_6_veh_chain(const char *dump_dir)
{
    volatile int *null_ptr;
    int i;

    printf("\n=== MODE 6: VEH chain ===\n");
    strncpy(g_dump_dir, dump_dir, MAX_PATH - 1);

    g_veh_handler_count = 0;

    /* Install VEH handlers. They execute in order: first added = first called.
     * The final handler (added first with AddFirst=1) writes the dump with
     * all the context modifications from the earlier handlers. Wait, actually:
     * AddVectoredExceptionHandler(1, ...) adds to the FRONT of the list,
     * so we add the final handler first, then prepend the others. */

    /* Add final handler to back of list */
    g_veh_handles[4] = AddVectoredExceptionHandler(0, veh_handler_final);

    /* Add modifying handlers to front (they'll run before final) */
    g_veh_handles[3] = AddVectoredExceptionHandler(1, veh_handler_3);
    g_veh_handles[2] = AddVectoredExceptionHandler(1, veh_handler_2);
    g_veh_handles[1] = AddVectoredExceptionHandler(1, veh_handler_1);
    g_veh_handles[0] = AddVectoredExceptionHandler(1, veh_handler_0);

    printf("[*] Installed 5 VEH handlers, triggering exception...\n");

    /* Create some interesting stack context before crashing */
    {
        volatile char veh_local_data[512];
        volatile DWORD_PTR interesting_values[8];
        int j;

        for (j = 0; j < 512; j++) {
            veh_local_data[j] = (char)(j ^ 0xAB);
        }
        interesting_values[0] = (DWORD_PTR)GetModuleHandleA(NULL);
        interesting_values[1] = (DWORD_PTR)GetCurrentThreadId();
        interesting_values[2] = (DWORD_PTR)GetTickCount64();
        interesting_values[3] = 0xCAFEBABEDEADBEEFULL;
        interesting_values[4] = (DWORD_PTR)&g_veh_handles;
        interesting_values[5] = (DWORD_PTR)veh_handler_0;
        interesting_values[6] = (DWORD_PTR)veh_handler_final;
        interesting_values[7] = 0x0BADF00D0BADF00DULL;

        /* Trigger the crash -- all VEH handlers will fire */
        __try {
            null_ptr = NULL;
            *null_ptr = 0x42424242;
        } __except(EXCEPTION_EXECUTE_HANDLER) {
            /* The VEH handlers already wrote the dump with corrupted context.
             * The SEH handler here just prevents process termination. */
            printf("[+] VEH chain crash captured (handlers invoked: %ld).\n",
                   g_veh_handler_count);
        }
    }

    /* Remove VEH handlers */
    for (i = 0; i < 5; i++) {
        if (g_veh_handles[i]) {
            RemoveVectoredExceptionHandler(g_veh_handles[i]);
        }
    }
}

/* =========================================================================
 * Main entry point
 * ========================================================================= */

int main(int argc, char *argv[])
{
    int mode;
    char dump_dir[MAX_PATH];
    DWORD attrs;

    printf("=== Crashbot Complex Crasher ===\n");
    printf("PID: %lu  TID: %lu\n\n", GetCurrentProcessId(), GetCurrentThreadId());

    if (argc < 2) {
        printf("Usage: %s <mode> [dump_directory]\n", argv[0]);
        printf("\nModes:\n");
        printf("  1  Multi-threaded race condition crash\n");
        printf("  2  Deep recursion with mixed calling conventions\n");
        printf("  3  Exception chain (nested __try/__except)\n");
        printf("  4  Corrupted stack frame\n");
        printf("  5  DLL callback crash\n");
        printf("  6  VEH chain\n");
        printf("  0  Run ALL modes\n");
        return 1;
    }

    mode = atoi(argv[1]);

    /* Set dump directory */
    if (argc >= 3) {
        strncpy(dump_dir, argv[2], MAX_PATH - 1);
        dump_dir[MAX_PATH - 1] = '\0';
    } else {
        GetCurrentDirectoryA(MAX_PATH, dump_dir);
    }

    /* Verify dump directory exists */
    attrs = GetFileAttributesA(dump_dir);
    if (attrs == INVALID_FILE_ATTRIBUTES || !(attrs & FILE_ATTRIBUTE_DIRECTORY)) {
        fprintf(stderr, "[!] Dump directory does not exist: %s\n", dump_dir);
        fprintf(stderr, "    Creating it...\n");
        CreateDirectoryA(dump_dir, NULL);
    }

    printf("[*] Dump directory: %s\n", dump_dir);

    switch (mode) {
    case 0:
        printf("\n*** Running ALL crash modes ***\n");
        crash_mode_1_race_condition(dump_dir);
        crash_mode_2_mixed_calling(dump_dir);
        crash_mode_3_exception_chain(dump_dir);
        crash_mode_4_corrupted_frame(dump_dir);
        crash_mode_5_dll_callback(dump_dir);
        crash_mode_6_veh_chain(dump_dir);
        printf("\n*** All modes completed ***\n");
        break;
    case 1:
        crash_mode_1_race_condition(dump_dir);
        break;
    case 2:
        crash_mode_2_mixed_calling(dump_dir);
        break;
    case 3:
        crash_mode_3_exception_chain(dump_dir);
        break;
    case 4:
        crash_mode_4_corrupted_frame(dump_dir);
        break;
    case 5:
        crash_mode_5_dll_callback(dump_dir);
        break;
    case 6:
        crash_mode_6_veh_chain(dump_dir);
        break;
    default:
        fprintf(stderr, "[!] Unknown mode: %d\n", mode);
        return 1;
    }

    printf("\n[*] Crasher finished.\n");
    return 0;
}

#else /* !_WIN32 */

/*
 * Non-Windows stub: compiles but does nothing.
 * The crash scenarios above rely on Windows-specific APIs
 * (__try/__except, VEH, MiniDumpWriteDump, Windows heap, etc.)
 */

#include <stdio.h>

int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;
    printf("windows_complex_crasher: This program only runs on Windows.\n");
    printf("Compile with MSVC (cl.exe) on a Windows system.\n");
    return 0;
}

#endif /* _WIN32 */
