/*
 * linux_complex_crasher.c
 *
 * A program that generates extremely hard-to-parse Linux core dumps for
 * testing the Crashbot crash dump analysis tool. Each crash mode exercises
 * a different pattern that is notoriously difficult for debuggers like GDB
 * to present clearly.
 *
 * BUILD:
 *   gcc -g -O0 -o linux_complex_crasher linux_complex_crasher.c -lpthread
 *
 * USAGE:
 *   ulimit -c unlimited          # ensure core dumps are generated
 *   ./linux_complex_crasher <mode>
 *
 *   Modes:
 *     1  - Multi-threaded deadlock + crash (8 threads, mutex deadlock, SIGSEGV)
 *     2  - Signal handler crash (double fault: SIGSEGV handler itself crashes)
 *     3  - Heap corruption with delayed crash (use-after-free + reallocation)
 *     4  - Deep recursion through function pointers (200+ frames, 20+ functions)
 *     5  - Fork + shared memory corruption + crash
 *     6  - Stack buffer overflow (corrupts return address & frame pointer)
 *     7  - Thread-local storage crash (crash during TLS access)
 *     8  - SIGABRT from assert in atexit destructor chain
 *     0  - Run ALL modes sequentially (forks each, collects cores)
 *
 * NOTES:
 *   - Core dump location depends on /proc/sys/kernel/core_pattern
 *   - Compile with -O0 to preserve all debug info and local variables
 *   - The program prints its PID for easy core file identification
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <pthread.h>
#include <assert.h>
#include <errno.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <fcntl.h>
#include <stdint.h>
#include <time.h>

/* --------------------------------------------------------------------------
 * Shared types and helpers used across multiple crash modes
 * -------------------------------------------------------------------------- */

/* Large struct to make core dumps more realistic and harder to parse */
typedef struct {
    char name[64];
    int id;
    double values[16];
    void *pointers[8];
    uint64_t flags;
    struct {
        int x, y, z;
        char label[32];
    } nested;
} complex_record_t;

/* Another struct for stack/heap noise */
typedef struct node {
    int key;
    char data[128];
    struct node *next;
    struct node *prev;
    complex_record_t record;
} linked_node_t;

/* Fill a complex_record with recognizable but varied data */
static void fill_record(complex_record_t *rec, int seed) {
    snprintf(rec->name, sizeof(rec->name), "record_%d_pid_%d", seed, getpid());
    rec->id = seed;
    for (int i = 0; i < 16; i++)
        rec->values[i] = (double)seed * 1.1 + i * 0.7;
    for (int i = 0; i < 8; i++)
        rec->pointers[i] = (void *)(uintptr_t)(0xDEAD0000 + seed * 0x100 + i);
    rec->flags = 0xCAFEBABE00000000ULL | (uint64_t)seed;
    rec->nested.x = seed;
    rec->nested.y = seed * 2;
    rec->nested.z = seed * 3;
    snprintf(rec->nested.label, sizeof(rec->nested.label), "nested_%d", seed);
}

/* Create some stack noise: local variables that will appear in the core */
static void create_stack_noise(int depth) {
    complex_record_t local_rec;
    char local_buf[256];
    int local_array[32];
    volatile int sentinel = 0xBAADF00D;

    fill_record(&local_rec, depth);
    snprintf(local_buf, sizeof(local_buf),
             "stack_noise_depth_%d_pid_%d", depth, getpid());
    for (int i = 0; i < 32; i++)
        local_array[i] = depth * 100 + i;

    (void)sentinel;
    (void)local_buf;
    (void)local_array;
}

/* =========================================================================
 * MODE 1: Multi-threaded deadlock + crash
 *
 * Creates 8+ threads. Some deadlock on mutexes (A-B / B-A ordering), while
 * another thread crashes with SIGSEGV. GDB will show threads in RUNNING,
 * BLOCKED (on mutex), and crashed states simultaneously.
 * ========================================================================= */

#define NUM_DEADLOCK_THREADS 8
#define NUM_MUTEXES 4

static pthread_mutex_t deadlock_mutexes[NUM_MUTEXES];
static volatile int deadlock_ready = 0;

typedef struct {
    int thread_id;
    int first_mutex;
    int second_mutex;
    int should_crash;
    complex_record_t thread_data;
    linked_node_t local_nodes[4];
} deadlock_thread_arg_t;

static void *deadlock_thread_func(void *arg) {
    deadlock_thread_arg_t *targ = (deadlock_thread_arg_t *)arg;
    complex_record_t local_rec;
    char thread_name[64];
    int local_counters[16];
    void *local_pointers[8];

    /* Fill local variables to make per-thread state visible in core */
    fill_record(&local_rec, targ->thread_id * 1000);
    snprintf(thread_name, sizeof(thread_name), "deadlock_thread_%d", targ->thread_id);
    for (int i = 0; i < 16; i++)
        local_counters[i] = targ->thread_id * 100 + i;
    for (int i = 0; i < 8; i++)
        local_pointers[i] = (void *)(uintptr_t)(0xFEED0000 + targ->thread_id * 0x10 + i);

    /* Initialize per-thread node data */
    for (int i = 0; i < 4; i++) {
        targ->local_nodes[i].key = targ->thread_id * 10 + i;
        snprintf(targ->local_nodes[i].data, sizeof(targ->local_nodes[i].data),
                 "node_%d_thread_%d", i, targ->thread_id);
        fill_record(&targ->local_nodes[i].record, targ->thread_id * 10 + i);
    }

    create_stack_noise(targ->thread_id);

    /* Wait for all threads to be ready */
    __sync_fetch_and_add(&deadlock_ready, 1);
    while (deadlock_ready < NUM_DEADLOCK_THREADS)
        usleep(1000);

    if (targ->should_crash) {
        /* This thread will crash: let the deadlocks form first */
        usleep(100000); /* 100ms */
        fprintf(stderr, "[Thread %d] About to crash via SIGSEGV\n", targ->thread_id);
        volatile int *null_ptr = NULL;
        *null_ptr = 0x42;  /* SIGSEGV */
    } else {
        /* Acquire mutexes in potentially deadlocking order */
        fprintf(stderr, "[Thread %d] Locking mutex %d then %d\n",
                targ->thread_id, targ->first_mutex, targ->second_mutex);
        pthread_mutex_lock(&deadlock_mutexes[targ->first_mutex]);
        usleep(50000); /* Give other threads time to grab their first mutex */
        pthread_mutex_lock(&deadlock_mutexes[targ->second_mutex]);

        /* Should never reach here if deadlocked */
        pthread_mutex_unlock(&deadlock_mutexes[targ->second_mutex]);
        pthread_mutex_unlock(&deadlock_mutexes[targ->first_mutex]);
    }

    (void)local_rec;
    (void)thread_name;
    (void)local_counters;
    (void)local_pointers;
    return NULL;
}

static void mode_deadlock_crash(void) {
    pthread_t threads[NUM_DEADLOCK_THREADS];
    deadlock_thread_arg_t args[NUM_DEADLOCK_THREADS];

    for (int i = 0; i < NUM_MUTEXES; i++)
        pthread_mutex_init(&deadlock_mutexes[i], NULL);

    /*
     * Thread layout:
     *   Threads 0-1: lock mutex 0 then 1 (forward order)
     *   Threads 2-3: lock mutex 1 then 0 (reverse order -> deadlock with 0-1)
     *   Threads 4-5: lock mutex 2 then 3
     *   Threads 6:   lock mutex 3 then 2 (reverse -> deadlock with 4-5)
     *   Thread 7:    crashes with SIGSEGV
     */
    int mutex_pairs[][2] = {
        {0, 1}, {0, 1},   /* threads 0-1 */
        {1, 0}, {1, 0},   /* threads 2-3: reverse order */
        {2, 3}, {2, 3},   /* threads 4-5 */
        {3, 2},           /* thread 6: reverse order */
        {0, 0},           /* thread 7: doesn't matter, will crash */
    };

    for (int i = 0; i < NUM_DEADLOCK_THREADS; i++) {
        args[i].thread_id = i;
        args[i].first_mutex = mutex_pairs[i][0];
        args[i].second_mutex = mutex_pairs[i][1];
        args[i].should_crash = (i == 7);
        fill_record(&args[i].thread_data, i);
        pthread_create(&threads[i], NULL, deadlock_thread_func, &args[i]);
    }

    for (int i = 0; i < NUM_DEADLOCK_THREADS; i++)
        pthread_join(threads[i], NULL);
}

/* =========================================================================
 * MODE 2: Signal handler crash (double fault)
 *
 * Installs a custom SIGSEGV handler that itself dereferences a bad pointer,
 * causing a second SIGSEGV. The kernel delivers the second signal with
 * SA_RESETHAND semantics (or we get a SIGBUS/SIGABRT), producing confusing
 * signal info and nested signal frames in the core dump.
 * ========================================================================= */

static volatile int signal_handler_depth = 0;

/* Lots of state in the signal handler to confuse debuggers */
typedef struct {
    int handler_invocation;
    void *fault_address;
    int signal_number;
    char context_description[128];
    complex_record_t handler_record;
} signal_handler_state_t;

static signal_handler_state_t g_handler_states[4];

static void crashing_signal_handler(int sig, siginfo_t *info, void *ucontext) {
    int depth = __sync_fetch_and_add(&signal_handler_depth, 1);
    complex_record_t handler_local;
    char msg_buf[256];
    volatile int handler_locals[32];

    /* Fill handler-local data */
    fill_record(&handler_local, 9000 + depth);
    snprintf(msg_buf, sizeof(msg_buf),
             "Signal handler invoked: sig=%d depth=%d fault_addr=%p",
             sig, depth, info ? info->si_addr : NULL);

    for (int i = 0; i < 32; i++)
        handler_locals[i] = 0xDEAD0000 + depth * 0x100 + i;

    /* Save state for forensics */
    if (depth < 4) {
        g_handler_states[depth].handler_invocation = depth;
        g_handler_states[depth].fault_address = info ? info->si_addr : NULL;
        g_handler_states[depth].signal_number = sig;
        snprintf(g_handler_states[depth].context_description,
                 sizeof(g_handler_states[depth].context_description),
                 "depth_%d_sig_%d", depth, sig);
        fill_record(&g_handler_states[depth].handler_record, 8000 + depth);
    }

    /*
     * The double fault: dereference a bad pointer inside the signal handler.
     * On the first invocation, SA_NODEFER lets us re-enter.
     * On the second invocation, the default handler runs (core dump).
     */
    fprintf(stderr, "[Signal handler depth %d] Deliberately crashing again...\n", depth);

    if (depth == 0) {
        /* First fault: re-enter the handler */
        volatile int *bad = (volatile int *)(uintptr_t)0x00000042;
        *bad = 0xFF;
    } else {
        /* Second fault: use an even worse address to ensure core */
        volatile int *worse = (volatile int *)(uintptr_t)0xFFFFFFFFDEADBEEFULL;
        *worse = 0xAB;
    }

    (void)handler_local;
    (void)msg_buf;
    (void)handler_locals;
    (void)ucontext;
}

static void mode_signal_handler_crash(void) {
    struct sigaction sa;
    complex_record_t pre_signal_state;
    char setup_info[256];

    fill_record(&pre_signal_state, 7777);
    snprintf(setup_info, sizeof(setup_info),
             "Setting up double-fault signal handler pid=%d", getpid());

    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = crashing_signal_handler;
    sa.sa_flags = SA_SIGINFO | SA_NODEFER; /* SA_NODEFER: don't block SIGSEGV in handler */
    sigemptyset(&sa.sa_mask);

    if (sigaction(SIGSEGV, &sa, NULL) < 0) {
        perror("sigaction");
        exit(1);
    }

    create_stack_noise(42);

    fprintf(stderr, "[Mode 2] Triggering initial SIGSEGV for double-fault...\n");
    volatile int *trigger = NULL;
    *trigger = 0xDEAD;

    (void)pre_signal_state;
    (void)setup_info;
}

/* =========================================================================
 * MODE 3: Heap corruption with delayed crash (use-after-free)
 *
 * Allocates memory, frees it, triggers reallocation that reuses the freed
 * block, partially overwrites it, then accesses through the stale pointer.
 * The crash location (stale pointer dereference) is far from the root cause
 * (the earlier free + overwrite). This is the classic "impossible" crash.
 * ========================================================================= */

typedef struct {
    int magic;
    char name[64];
    void (*callback)(void *);
    void *callback_arg;
    complex_record_t payload;
    struct {
        int refcount;
        void *owner;
        char tag[32];
    } metadata;
} heap_object_t;

static void dummy_callback(void *arg) {
    fprintf(stderr, "dummy_callback called with %p\n", arg);
}

static void mode_heap_corruption(void) {
    complex_record_t stack_context;
    char breadcrumb[128];
    linked_node_t *node_list[16];
    int step_tracker[32];

    fill_record(&stack_context, 3000);
    snprintf(breadcrumb, sizeof(breadcrumb), "heap_corruption_start_pid_%d", getpid());
    memset(step_tracker, 0, sizeof(step_tracker));

    /* Step 1: Allocate the victim object */
    heap_object_t *victim = (heap_object_t *)malloc(sizeof(heap_object_t));
    victim->magic = 0x600D0001;
    snprintf(victim->name, sizeof(victim->name), "victim_object");
    victim->callback = dummy_callback;
    victim->callback_arg = victim;
    fill_record(&victim->payload, 3001);
    victim->metadata.refcount = 1;
    victim->metadata.owner = (void *)victim;
    snprintf(victim->metadata.tag, sizeof(victim->metadata.tag), "original_alloc");
    step_tracker[0] = 1;

    /* Save the pointer (this becomes the stale pointer after free) */
    heap_object_t *stale_ptr = victim;

    /* Step 2: Allocate a bunch of other objects to push allocator state */
    for (int i = 0; i < 16; i++) {
        node_list[i] = (linked_node_t *)malloc(sizeof(linked_node_t));
        node_list[i]->key = 3000 + i;
        snprintf(node_list[i]->data, sizeof(node_list[i]->data),
                 "padding_node_%d", i);
        fill_record(&node_list[i]->record, 3100 + i);
        step_tracker[1 + i] = 1;
    }

    /* Step 3: Free the victim */
    fprintf(stderr, "[Mode 3] Freeing victim at %p (stale_ptr still holds this address)\n",
            (void *)victim);
    free(victim);
    victim = NULL; /* Good practice, but stale_ptr still points to freed memory */
    step_tracker[17] = 1;

    /* Step 4: Allocate new objects that will likely reuse the freed memory */
    heap_object_t *reuser1 = (heap_object_t *)malloc(sizeof(heap_object_t));
    heap_object_t *reuser2 = (heap_object_t *)malloc(sizeof(heap_object_t));
    heap_object_t *reuser3 = (heap_object_t *)malloc(sizeof(heap_object_t));

    /* Overwrite what used to be victim's data */
    reuser1->magic = 0xBAD0BAD0;
    snprintf(reuser1->name, sizeof(reuser1->name), "reuser_overwrote_victim");
    reuser1->callback = (void (*)(void *))0x4141414141414141ULL;
    reuser1->callback_arg = (void *)0x4242424242424242ULL;
    fill_record(&reuser1->payload, 6666);

    reuser2->magic = 0xDEADBEEF;
    reuser3->magic = 0xCAFEF00D;
    step_tracker[18] = 1;

    /* Free some padding to create more heap confusion */
    for (int i = 0; i < 16; i += 2)
        free(node_list[i]);
    step_tracker[19] = 1;

    /* Step 5: Use the stale pointer -- this is the DELAYED CRASH.
     * The memory has been freed and likely reused/overwritten.
     * The callback pointer is now 0x4141414141414141.
     * Calling it will SIGSEGV at an address that makes no sense
     * unless you trace back to the use-after-free. */
    fprintf(stderr, "[Mode 3] Using stale pointer %p -- crash incoming!\n",
            (void *)stale_ptr);
    fprintf(stderr, "[Mode 3] stale_ptr->callback = %p\n",
            (void *)(uintptr_t)stale_ptr->callback);

    create_stack_noise(99);

    /* The crash: calling a function pointer that was overwritten */
    stale_ptr->callback(stale_ptr->callback_arg);

    /* Cleanup that will never execute */
    free(reuser1);
    free(reuser2);
    free(reuser3);

    (void)stack_context;
    (void)breadcrumb;
}

/* =========================================================================
 * MODE 4: Deep recursion through function pointers
 *
 * A dispatch table of 24 functions that call each other through function
 * pointers. Creates 200+ deep stack traces with varying function names
 * at each level, making stack unwinding and pattern recognition difficult.
 * ========================================================================= */

#define NUM_DISPATCH_FUNCS 24
#define MAX_RECURSION_DEPTH 250

typedef void (*dispatch_func_t)(int depth, int path, void *context);

/* Forward declarations for all dispatch functions */
static void dispatch_alpha(int depth, int path, void *context);
static void dispatch_bravo(int depth, int path, void *context);
static void dispatch_charlie(int depth, int path, void *context);
static void dispatch_delta(int depth, int path, void *context);
static void dispatch_echo(int depth, int path, void *context);
static void dispatch_foxtrot(int depth, int path, void *context);
static void dispatch_golf(int depth, int path, void *context);
static void dispatch_hotel(int depth, int path, void *context);
static void dispatch_india(int depth, int path, void *context);
static void dispatch_juliet(int depth, int path, void *context);
static void dispatch_kilo(int depth, int path, void *context);
static void dispatch_lima(int depth, int path, void *context);
static void dispatch_mike(int depth, int path, void *context);
static void dispatch_november(int depth, int path, void *context);
static void dispatch_oscar(int depth, int path, void *context);
static void dispatch_papa(int depth, int path, void *context);
static void dispatch_quebec(int depth, int path, void *context);
static void dispatch_romeo(int depth, int path, void *context);
static void dispatch_sierra(int depth, int path, void *context);
static void dispatch_tango(int depth, int path, void *context);
static void dispatch_uniform(int depth, int path, void *context);
static void dispatch_victor(int depth, int path, void *context);
static void dispatch_whiskey(int depth, int path, void *context);
static void dispatch_xray(int depth, int path, void *context);

static dispatch_func_t dispatch_table[NUM_DISPATCH_FUNCS] = {
    dispatch_alpha,    dispatch_bravo,    dispatch_charlie,  dispatch_delta,
    dispatch_echo,     dispatch_foxtrot,  dispatch_golf,     dispatch_hotel,
    dispatch_india,    dispatch_juliet,   dispatch_kilo,     dispatch_lima,
    dispatch_mike,     dispatch_november, dispatch_oscar,    dispatch_papa,
    dispatch_quebec,   dispatch_romeo,    dispatch_sierra,   dispatch_tango,
    dispatch_uniform,  dispatch_victor,   dispatch_whiskey,  dispatch_xray,
};

static const char *dispatch_names[NUM_DISPATCH_FUNCS] = {
    "alpha",  "bravo",    "charlie", "delta",   "echo",    "foxtrot",
    "golf",   "hotel",    "india",   "juliet",  "kilo",    "lima",
    "mike",   "november", "oscar",   "papa",    "quebec",  "romeo",
    "sierra", "tango",    "uniform", "victor",  "whiskey", "xray",
};

typedef struct {
    int call_history[MAX_RECURSION_DEPTH];
    int current_depth;
    complex_record_t records[8];
    char trace_buffer[512];
} dispatch_context_t;

/* Core dispatch logic shared by all functions */
static void dispatch_common(int func_index, int depth, int path, void *context) {
    dispatch_context_t *ctx = (dispatch_context_t *)context;
    complex_record_t local_rec;
    char local_name[64];
    int local_data[16];
    volatile void *func_addr;

    fill_record(&local_rec, func_index * 1000 + depth);
    snprintf(local_name, sizeof(local_name), "%s_depth_%d",
             dispatch_names[func_index], depth);
    for (int i = 0; i < 16; i++)
        local_data[i] = func_index * 100 + depth * 10 + i;

    ctx->call_history[depth % MAX_RECURSION_DEPTH] = func_index;
    ctx->current_depth = depth;

    if (depth >= MAX_RECURSION_DEPTH) {
        /* Crash at maximum depth */
        fprintf(stderr, "[Mode 4] Reached depth %d, crashing via SIGSEGV\n", depth);
        snprintf(ctx->trace_buffer, sizeof(ctx->trace_buffer),
                 "CRASH at depth %d, last func: %s", depth, dispatch_names[func_index]);
        volatile int *crash = (volatile int *)(uintptr_t)(0xDEAD0000 + depth);
        *crash = depth;
    }

    /* Select next function based on depth and path for pseudo-random traversal */
    int next = (func_index + depth * 7 + path * 3 + 1) % NUM_DISPATCH_FUNCS;
    func_addr = (void *)dispatch_table[next];

    dispatch_table[next](depth + 1, path ^ (depth * 13), context);

    (void)local_rec;
    (void)local_name;
    (void)local_data;
    (void)func_addr;
}

/* All 24 dispatch functions: each adds its own frame with unique local variables */
#define DEFINE_DISPATCH_FUNC(name, index)                                      \
    static void name(int depth, int path, void *context) {                     \
        volatile int marker_##name = 0xD1500000 + index;                       \
        complex_record_t name##_rec;                                           \
        char name##_tag[32];                                                   \
        fill_record(&name##_rec, index * 100 + depth);                         \
        snprintf(name##_tag, sizeof(name##_tag), #name "_%d", depth);          \
        dispatch_common(index, depth, path, context);                          \
        (void)marker_##name;                                                   \
        (void)name##_rec;                                                      \
        (void)name##_tag;                                                      \
    }

DEFINE_DISPATCH_FUNC(dispatch_alpha,    0)
DEFINE_DISPATCH_FUNC(dispatch_bravo,    1)
DEFINE_DISPATCH_FUNC(dispatch_charlie,  2)
DEFINE_DISPATCH_FUNC(dispatch_delta,    3)
DEFINE_DISPATCH_FUNC(dispatch_echo,     4)
DEFINE_DISPATCH_FUNC(dispatch_foxtrot,  5)
DEFINE_DISPATCH_FUNC(dispatch_golf,     6)
DEFINE_DISPATCH_FUNC(dispatch_hotel,    7)
DEFINE_DISPATCH_FUNC(dispatch_india,    8)
DEFINE_DISPATCH_FUNC(dispatch_juliet,   9)
DEFINE_DISPATCH_FUNC(dispatch_kilo,     10)
DEFINE_DISPATCH_FUNC(dispatch_lima,     11)
DEFINE_DISPATCH_FUNC(dispatch_mike,     12)
DEFINE_DISPATCH_FUNC(dispatch_november, 13)
DEFINE_DISPATCH_FUNC(dispatch_oscar,    14)
DEFINE_DISPATCH_FUNC(dispatch_papa,     15)
DEFINE_DISPATCH_FUNC(dispatch_quebec,   16)
DEFINE_DISPATCH_FUNC(dispatch_romeo,    17)
DEFINE_DISPATCH_FUNC(dispatch_sierra,   18)
DEFINE_DISPATCH_FUNC(dispatch_tango,    19)
DEFINE_DISPATCH_FUNC(dispatch_uniform,  20)
DEFINE_DISPATCH_FUNC(dispatch_victor,   21)
DEFINE_DISPATCH_FUNC(dispatch_whiskey,  22)
DEFINE_DISPATCH_FUNC(dispatch_xray,     23)

static void mode_deep_recursion(void) {
    dispatch_context_t ctx;
    complex_record_t entry_state;

    memset(&ctx, 0, sizeof(ctx));
    fill_record(&entry_state, 4000);
    for (int i = 0; i < 8; i++)
        fill_record(&ctx.records[i], 4100 + i);

    fprintf(stderr, "[Mode 4] Starting deep recursion through %d functions...\n",
            NUM_DISPATCH_FUNCS);

    /* Start the chain */
    dispatch_table[0](0, 0x12345678, &ctx);

    (void)entry_state;
}

/* =========================================================================
 * MODE 5: Fork + shared memory corruption + crash
 *
 * Forks a child, both map shared memory. The child corrupts the shared
 * region then crashes. The core dump has confusing memory mappings
 * (shared pages, forked address space), and the corruption is visible
 * in the shared mapping.
 * ========================================================================= */

#define SHM_SIZE (4096 * 4)  /* 16KB shared region */

typedef struct {
    int magic;
    pid_t writer_pid;
    int corruption_count;
    char message[256];
    complex_record_t records[4];
    uint8_t data_region[4096];
    volatile int sync_flag;
} shared_region_t;

static void mode_fork_crash(void) {
    complex_record_t parent_state;
    char parent_info[128];

    fill_record(&parent_state, 5000);
    snprintf(parent_info, sizeof(parent_info),
             "fork_crash_parent_pid_%d", getpid());

    /* Create shared memory via mmap */
    shared_region_t *shm = (shared_region_t *)mmap(
        NULL, sizeof(shared_region_t),
        PROT_READ | PROT_WRITE,
        MAP_SHARED | MAP_ANONYMOUS,
        -1, 0);

    if (shm == MAP_FAILED) {
        perror("mmap");
        exit(1);
    }

    /* Initialize shared region */
    shm->magic = 0x5448524D; /* "SHRM" */
    shm->writer_pid = getpid();
    shm->corruption_count = 0;
    snprintf(shm->message, sizeof(shm->message), "initialized_by_parent_%d", getpid());
    for (int i = 0; i < 4; i++)
        fill_record(&shm->records[i], 5100 + i);
    memset(shm->data_region, 0xCC, sizeof(shm->data_region));
    shm->sync_flag = 0;

    pid_t child = fork();

    if (child < 0) {
        perror("fork");
        exit(1);
    }

    if (child == 0) {
        /* ---- CHILD PROCESS ---- */
        complex_record_t child_state;
        linked_node_t child_nodes[4];
        char child_info[128];

        fill_record(&child_state, 5500);
        snprintf(child_info, sizeof(child_info), "child_pid_%d_parent_%d",
                 getpid(), getppid());
        for (int i = 0; i < 4; i++) {
            child_nodes[i].key = 5500 + i;
            fill_record(&child_nodes[i].record, 5600 + i);
        }

        fprintf(stderr, "[Mode 5] Child %d corrupting shared memory...\n", getpid());

        /* Corrupt the shared region */
        shm->magic = 0xDEADDEAD;
        shm->writer_pid = getpid();
        shm->corruption_count = 999;
        snprintf(shm->message, sizeof(shm->message),
                 "CORRUPTED_BY_CHILD_%d", getpid());

        /* Write garbage patterns */
        for (int i = 0; i < (int)sizeof(shm->data_region); i++)
            shm->data_region[i] = (uint8_t)(i * 7 + 0x41);

        /* Corrupt record pointers with bad values */
        for (int i = 0; i < 4; i++) {
            for (int j = 0; j < 8; j++)
                shm->records[i].pointers[j] = (void *)(uintptr_t)(0xBAD00000 + i * 0x100 + j);
        }

        /* Also mmap an additional private region to confuse mappings */
        void *extra_map = mmap(NULL, 4096 * 8, PROT_READ | PROT_WRITE,
                               MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (extra_map != MAP_FAILED) {
            memset(extra_map, 0xAA, 4096 * 8);
            /* Don't unmap -- leave it in the core */
        }

        /* Signal parent, then crash */
        shm->sync_flag = 1;
        create_stack_noise(55);

        fprintf(stderr, "[Mode 5] Child %d crashing via SIGSEGV...\n", getpid());
        volatile int *crash = (volatile int *)(uintptr_t)0x0000DEAD;
        *crash = getpid();

        (void)child_state;
        (void)child_info;
        _exit(1); /* Should not reach */
    } else {
        /* ---- PARENT PROCESS ---- */
        fprintf(stderr, "[Mode 5] Parent %d waiting for child %d...\n",
                getpid(), child);

        /* Wait for child to corrupt and crash */
        int status;
        waitpid(child, &status, 0);

        if (WIFSIGNALED(status)) {
            fprintf(stderr, "[Mode 5] Child %d killed by signal %d\n",
                    child, WTERMSIG(status));
        }

        /* Now parent examines the corrupted shared memory and crashes too */
        fprintf(stderr, "[Mode 5] Parent examining corrupted shared memory...\n");
        fprintf(stderr, "[Mode 5] shm->magic = 0x%X (expected 0x5448524D)\n", shm->magic);

        /* Try to use a corrupted pointer from shared memory */
        void *bad_ptr = shm->records[0].pointers[0];
        fprintf(stderr, "[Mode 5] Parent dereferencing corrupted pointer %p\n", bad_ptr);
        volatile int *crash_via_shm = (volatile int *)bad_ptr;
        *crash_via_shm = 0xDEAD;

        munmap(shm, sizeof(shared_region_t));
    }

    (void)parent_state;
    (void)parent_info;
}

/* =========================================================================
 * MODE 6: Stack buffer overflow
 *
 * Carefully overflows a stack buffer to corrupt the return address and
 * frame pointer. GDB will show garbage frames when trying to unwind
 * the stack, mixing real and corrupted frame data.
 * ========================================================================= */

/* Use a separate noinline function so the overflow corrupts its caller's frame */
static void __attribute__((noinline)) vulnerable_function(const char *input, int repeat) {
    char small_buffer[64];
    int canary_before = 0xCAFECAFE;
    complex_record_t vuln_record;
    int canary_after = 0xFACEFACE;

    fill_record(&vuln_record, 6000);

    fprintf(stderr, "[Mode 6] vulnerable_function: buffer at %p, size 64\n",
            (void *)small_buffer);
    fprintf(stderr, "[Mode 6] Will write %d * %zu = %zu bytes\n",
            repeat, strlen(input), repeat * strlen(input));

    /*
     * Deliberately overflow: write 'repeat' copies of 'input' into small_buffer.
     * This will overwrite canary_after, vuln_record, saved frame pointer,
     * and return address on the stack.
     */
    char *write_ptr = small_buffer;
    for (int i = 0; i < repeat; i++) {
        /* No bounds checking -- intentional overflow */
        size_t len = strlen(input);
        memcpy(write_ptr, input, len);
        write_ptr += len;
    }
    *write_ptr = '\0';

    fprintf(stderr, "[Mode 6] canary_before=0x%X canary_after=0x%X\n",
            canary_before, canary_after);

    /* When this function returns, the corrupted return address causes a crash.
     * GDB will show the crash at an invalid instruction address, and the
     * backtrace will contain garbage frames from the corrupted frame pointer. */

    (void)canary_before;
    (void)vuln_record;
}

static void __attribute__((noinline)) stack_overflow_wrapper_3(void) {
    complex_record_t wrapper3_rec;
    int wrapper3_data[16];
    fill_record(&wrapper3_rec, 6300);
    for (int i = 0; i < 16; i++) wrapper3_data[i] = 6300 + i;

    /* Overflow pattern: "AAAABBBB" repeated many times overwrites saved RBP and return addr */
    vulnerable_function("AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH", 16);

    (void)wrapper3_rec;
    (void)wrapper3_data;
}

static void __attribute__((noinline)) stack_overflow_wrapper_2(void) {
    complex_record_t wrapper2_rec;
    char wrapper2_tag[64] = "wrapper_2_frame";
    fill_record(&wrapper2_rec, 6200);

    stack_overflow_wrapper_3();

    (void)wrapper2_rec;
    (void)wrapper2_tag;
}

static void __attribute__((noinline)) stack_overflow_wrapper_1(void) {
    complex_record_t wrapper1_rec;
    linked_node_t wrapper1_node;
    fill_record(&wrapper1_rec, 6100);
    wrapper1_node.key = 6100;
    fill_record(&wrapper1_node.record, 6101);

    stack_overflow_wrapper_2();

    (void)wrapper1_rec;
    (void)wrapper1_node;
}

static void mode_stack_overflow(void) {
    complex_record_t entry_rec;
    fill_record(&entry_rec, 6000);

    fprintf(stderr, "[Mode 6] Starting stack buffer overflow...\n");

    /* Disable stack protector warning -- compile with -fno-stack-protector
     * for best results, but the code works without it too (just might get
     * __stack_chk_fail instead of the corrupted return) */
    stack_overflow_wrapper_1();

    (void)entry_rec;
}

/* =========================================================================
 * MODE 7: Thread-local storage crash
 *
 * Uses __thread variables extensively across multiple threads, then crashes
 * during TLS access. Each thread has different TLS state, making the core
 * dump confusing when examining per-thread variables.
 * ========================================================================= */

#define NUM_TLS_THREADS 6

/* Thread-local storage variables */
static __thread int tls_thread_id = -1;
static __thread int tls_iteration = 0;
static __thread char tls_name[64] = {0};
static __thread complex_record_t tls_record;
static __thread void *tls_pointers[8] = {0};
static __thread int tls_array[32] = {0};
static __thread volatile int tls_sentinel = 0;

typedef struct {
    int thread_id;
    int should_crash;
    int crash_delay_us;
    complex_record_t arg_record;
} tls_thread_arg_t;

static volatile int tls_threads_ready = 0;

static void __attribute__((noinline)) tls_worker_inner(int iteration) {
    /* Access and modify TLS from an inner function */
    tls_iteration = iteration;
    tls_array[iteration % 32] = tls_thread_id * 1000 + iteration;
    tls_pointers[iteration % 8] = (void *)(uintptr_t)(0x71500000UL + iteration);

    /* Update the TLS record */
    tls_record.values[iteration % 16] = (double)iteration * tls_thread_id;
    tls_record.nested.x = iteration;
    tls_record.nested.y = tls_thread_id;
}

static void *tls_thread_func(void *arg) {
    tls_thread_arg_t *targ = (tls_thread_arg_t *)arg;
    complex_record_t local_rec;
    char local_tag[64];

    /* Initialize TLS for this thread */
    tls_thread_id = targ->thread_id;
    snprintf(tls_name, sizeof(tls_name), "tls_thread_%d", targ->thread_id);
    fill_record(&tls_record, 7000 + targ->thread_id);
    tls_sentinel = 0xBEEF0000 + targ->thread_id;

    for (int i = 0; i < 8; i++)
        tls_pointers[i] = (void *)(uintptr_t)(0x77000000 + targ->thread_id * 0x100 + i);
    for (int i = 0; i < 32; i++)
        tls_array[i] = targ->thread_id * 100 + i;

    fill_record(&local_rec, 7100 + targ->thread_id);
    snprintf(local_tag, sizeof(local_tag), "tls_local_%d", targ->thread_id);

    __sync_fetch_and_add(&tls_threads_ready, 1);
    while (tls_threads_ready < NUM_TLS_THREADS)
        usleep(1000);

    /* Do some work touching TLS */
    for (int i = 0; i < 100; i++) {
        tls_worker_inner(i);
        usleep(1000);

        if (targ->should_crash && i == 50) {
            fprintf(stderr, "[Mode 7] Thread %d crashing during TLS access...\n",
                    targ->thread_id);

            /* Crash while actively using TLS: dereference a TLS pointer
             * that was set to a bad address */
            tls_pointers[0] = (void *)(uintptr_t)0x0000000000001337ULL;
            volatile int *tls_crash = (volatile int *)tls_pointers[0];
            tls_sentinel = *tls_crash; /* SIGSEGV during TLS read */
        }
    }

    (void)local_rec;
    (void)local_tag;
    return NULL;
}

static void mode_tls_crash(void) {
    pthread_t threads[NUM_TLS_THREADS];
    tls_thread_arg_t args[NUM_TLS_THREADS];
    complex_record_t main_rec;

    fill_record(&main_rec, 7777);

    for (int i = 0; i < NUM_TLS_THREADS; i++) {
        args[i].thread_id = i;
        args[i].should_crash = (i == NUM_TLS_THREADS - 1); /* Last thread crashes */
        args[i].crash_delay_us = i * 10000;
        fill_record(&args[i].arg_record, 7800 + i);
        pthread_create(&threads[i], NULL, tls_thread_func, &args[i]);
    }

    for (int i = 0; i < NUM_TLS_THREADS; i++)
        pthread_join(threads[i], NULL);

    (void)main_rec;
}

/* =========================================================================
 * MODE 8: SIGABRT from assert in atexit destructor chain
 *
 * Registers multiple atexit handlers (simulating C++ destructor chains).
 * The handlers access increasingly corrupted global state, and one of them
 * hits an assertion failure (SIGABRT). This creates a core dump where the
 * crash is inside the exit/cleanup path, with multiple cleanup frames on
 * the stack.
 * ========================================================================= */

#define NUM_ATEXIT_HANDLERS 12

typedef struct {
    int id;
    int initialized;
    int cleanup_order;
    char resource_name[64];
    complex_record_t resource_data;
    void *handle;
    int refcount;
} managed_resource_t;

static managed_resource_t g_resources[NUM_ATEXIT_HANDLERS];
static int g_cleanup_counter = 0;
static volatile int g_corruption_injected = 0;

/* Forward declarations */
static void cleanup_handler_0(void);
static void cleanup_handler_1(void);
static void cleanup_handler_2(void);
static void cleanup_handler_3(void);
static void cleanup_handler_4(void);
static void cleanup_handler_5(void);
static void cleanup_handler_6(void);
static void cleanup_handler_7(void);
static void cleanup_handler_8(void);
static void cleanup_handler_9(void);
static void cleanup_handler_10(void);
static void cleanup_handler_11(void);

typedef void (*cleanup_func_t)(void);
static cleanup_func_t cleanup_funcs[NUM_ATEXIT_HANDLERS] = {
    cleanup_handler_0,  cleanup_handler_1,  cleanup_handler_2,
    cleanup_handler_3,  cleanup_handler_4,  cleanup_handler_5,
    cleanup_handler_6,  cleanup_handler_7,  cleanup_handler_8,
    cleanup_handler_9,  cleanup_handler_10, cleanup_handler_11,
};

static void cleanup_handler_common(int id) {
    complex_record_t cleanup_rec;
    char cleanup_msg[128];
    int cleanup_locals[16];

    fill_record(&cleanup_rec, 8000 + id);
    snprintf(cleanup_msg, sizeof(cleanup_msg),
             "cleanup_handler_%d_counter_%d", id, g_cleanup_counter);
    for (int i = 0; i < 16; i++)
        cleanup_locals[i] = id * 100 + g_cleanup_counter * 10 + i;

    g_resources[id].cleanup_order = g_cleanup_counter++;

    fprintf(stderr, "[Mode 8] Cleanup handler %d (%s) running, counter=%d\n",
            id, g_resources[id].resource_name, g_cleanup_counter);

    /*
     * Handler 7 (the 5th handler called, since atexit runs in reverse order)
     * corrupts global state that handler 3 will check.
     */
    if (id == 7 && !g_corruption_injected) {
        fprintf(stderr, "[Mode 8] Handler %d injecting corruption...\n", id);
        g_resources[3].initialized = 0;           /* Mark as uninitialized */
        g_resources[3].refcount = -1;              /* Impossible refcount */
        g_resources[3].handle = (void *)0xDEAD;    /* Bad handle */
        g_corruption_injected = 1;
    }

    /*
     * Handler 3 asserts that it is still initialized -- but handler 7
     * already corrupted it. This triggers SIGABRT inside the atexit chain.
     */
    if (id == 3) {
        fprintf(stderr, "[Mode 8] Handler %d checking invariants...\n", id);
        fprintf(stderr, "[Mode 8]   initialized=%d refcount=%d handle=%p\n",
                g_resources[id].initialized, g_resources[id].refcount,
                g_resources[id].handle);

        /* This assertion will fail, causing SIGABRT */
        assert(g_resources[id].initialized == 1 &&
               "Resource was uninitialized during cleanup -- "
               "destructor ordering violation!");
        assert(g_resources[id].refcount >= 0 &&
               "Negative refcount during cleanup!");
    }

    /* Normal cleanup */
    g_resources[id].initialized = 0;
    g_resources[id].handle = NULL;

    (void)cleanup_rec;
    (void)cleanup_msg;
    (void)cleanup_locals;
}

/* Define all 12 handlers with unique names for distinct stack frames */
static void cleanup_handler_0(void)  { cleanup_handler_common(0); }
static void cleanup_handler_1(void)  { cleanup_handler_common(1); }
static void cleanup_handler_2(void)  { cleanup_handler_common(2); }
static void cleanup_handler_3(void)  { cleanup_handler_common(3); }
static void cleanup_handler_4(void)  { cleanup_handler_common(4); }
static void cleanup_handler_5(void)  { cleanup_handler_common(5); }
static void cleanup_handler_6(void)  { cleanup_handler_common(6); }
static void cleanup_handler_7(void)  { cleanup_handler_common(7); }
static void cleanup_handler_8(void)  { cleanup_handler_common(8); }
static void cleanup_handler_9(void)  { cleanup_handler_common(9); }
static void cleanup_handler_10(void) { cleanup_handler_common(10); }
static void cleanup_handler_11(void) { cleanup_handler_common(11); }

static void mode_atexit_abort(void) {
    complex_record_t setup_rec;
    fill_record(&setup_rec, 8888);

    /* Initialize all managed resources */
    for (int i = 0; i < NUM_ATEXIT_HANDLERS; i++) {
        g_resources[i].id = i;
        g_resources[i].initialized = 1;
        g_resources[i].cleanup_order = -1;
        snprintf(g_resources[i].resource_name, sizeof(g_resources[i].resource_name),
                 "resource_%d_type_%s", i,
                 i % 3 == 0 ? "file" : (i % 3 == 1 ? "socket" : "memory"));
        fill_record(&g_resources[i].resource_data, 8100 + i);
        g_resources[i].handle = (void *)(uintptr_t)(0x88000000 + i * 0x1000);
        g_resources[i].refcount = i + 1;
    }

    /* Register atexit handlers (will run in reverse order: 11, 10, ..., 0) */
    for (int i = 0; i < NUM_ATEXIT_HANDLERS; i++) {
        if (atexit(cleanup_funcs[i]) != 0) {
            fprintf(stderr, "Failed to register atexit handler %d\n", i);
            exit(1);
        }
    }

    fprintf(stderr, "[Mode 8] Registered %d atexit handlers, calling exit(0)...\n",
            NUM_ATEXIT_HANDLERS);
    fprintf(stderr, "[Mode 8] Handler 7 will corrupt handler 3's state.\n");
    fprintf(stderr, "[Mode 8] Handler 3 will assert and SIGABRT.\n");

    create_stack_noise(88);

    /* exit() triggers the atexit chain, which will eventually SIGABRT */
    exit(0);

    (void)setup_rec;
}

/* =========================================================================
 * MODE 0: Run ALL modes (forks each into a separate child)
 * ========================================================================= */

typedef void (*mode_func_t)(void);

static const struct {
    int mode;
    const char *description;
    mode_func_t func;
} all_modes[] = {
    {1, "Multi-threaded deadlock + crash",        mode_deadlock_crash},
    {2, "Signal handler crash (double fault)",     mode_signal_handler_crash},
    {3, "Heap corruption (use-after-free)",        mode_heap_corruption},
    {4, "Deep recursion through function pointers",mode_deep_recursion},
    {5, "Fork + shared memory corruption + crash", mode_fork_crash},
    {6, "Stack buffer overflow",                   mode_stack_overflow},
    {7, "Thread-local storage crash",              mode_tls_crash},
    {8, "SIGABRT from atexit destructor chain",    mode_atexit_abort},
};

static void run_all_modes(void) {
    int num_modes = sizeof(all_modes) / sizeof(all_modes[0]);

    fprintf(stderr, "\n=== Running all %d crash modes ===\n\n", num_modes);

    for (int i = 0; i < num_modes; i++) {
        fprintf(stderr, "--- Mode %d: %s ---\n",
                all_modes[i].mode, all_modes[i].description);

        pid_t child = fork();
        if (child < 0) {
            perror("fork");
            continue;
        }

        if (child == 0) {
            /* Child: run the mode (will crash and produce a core) */
            fprintf(stderr, "[Mode %d] Child PID: %d\n", all_modes[i].mode, getpid());
            all_modes[i].func();
            _exit(0); /* Should not reach here */
        }

        /* Parent: wait for child to crash */
        int status;
        waitpid(child, &status, 0);

        if (WIFSIGNALED(status)) {
            fprintf(stderr, "[Mode %d] Child %d killed by signal %d (%s)\n",
                    all_modes[i].mode, child, WTERMSIG(status),
                    strsignal(WTERMSIG(status)));
        } else if (WIFEXITED(status)) {
            fprintf(stderr, "[Mode %d] Child %d exited with status %d\n",
                    all_modes[i].mode, child, WEXITSTATUS(status));
        }

        fprintf(stderr, "\n");
        usleep(100000); /* Brief pause between modes */
    }

    fprintf(stderr, "=== All modes complete. Check for core files. ===\n");
}

/* =========================================================================
 * main
 * ========================================================================= */

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Linux Complex Crasher - Hard-to-parse core dump generator\n");
        fprintf(stderr, "Usage: %s <mode>\n\n", argv[0]);
        fprintf(stderr, "Modes:\n");
        fprintf(stderr, "  0 - Run ALL modes (forks each as a child process)\n");
        fprintf(stderr, "  1 - Multi-threaded deadlock + crash (8 threads)\n");
        fprintf(stderr, "  2 - Signal handler crash (double fault)\n");
        fprintf(stderr, "  3 - Heap corruption (use-after-free, delayed crash)\n");
        fprintf(stderr, "  4 - Deep recursion through function pointers (250+ frames)\n");
        fprintf(stderr, "  5 - Fork + shared memory corruption + crash\n");
        fprintf(stderr, "  6 - Stack buffer overflow (corrupts frame pointer)\n");
        fprintf(stderr, "  7 - Thread-local storage crash\n");
        fprintf(stderr, "  8 - SIGABRT from assert in atexit destructor chain\n");
        fprintf(stderr, "\nREMINDER: Run 'ulimit -c unlimited' before executing!\n");
        return 1;
    }

    int mode = atoi(argv[1]);

    fprintf(stderr, "===========================================\n");
    fprintf(stderr, " Linux Complex Crasher\n");
    fprintf(stderr, " PID: %d\n", getpid());
    fprintf(stderr, " Mode: %d\n", mode);
    fprintf(stderr, " REMINDER: ulimit -c unlimited\n");
    fprintf(stderr, "===========================================\n\n");

    /* Create some global stack noise visible in core */
    complex_record_t main_record;
    linked_node_t main_nodes[4];
    char main_banner[256];

    fill_record(&main_record, 9999);
    for (int i = 0; i < 4; i++) {
        main_nodes[i].key = 9000 + i;
        fill_record(&main_nodes[i].record, 9100 + i);
    }
    snprintf(main_banner, sizeof(main_banner),
             "linux_complex_crasher_pid_%d_mode_%d", getpid(), mode);

    switch (mode) {
        case 0: run_all_modes(); break;
        case 1: mode_deadlock_crash(); break;
        case 2: mode_signal_handler_crash(); break;
        case 3: mode_heap_corruption(); break;
        case 4: mode_deep_recursion(); break;
        case 5: mode_fork_crash(); break;
        case 6: mode_stack_overflow(); break;
        case 7: mode_tls_crash(); break;
        case 8: mode_atexit_abort(); break;
        default:
            fprintf(stderr, "Unknown mode: %d (valid: 0-8)\n", mode);
            return 1;
    }

    /* Should not reach here for most modes */
    fprintf(stderr, "[main] Mode %d completed without crashing (unexpected)\n", mode);

    (void)main_record;
    (void)main_nodes;
    (void)main_banner;

    return 0;
}
