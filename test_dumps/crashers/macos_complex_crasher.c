/*
 * macos_complex_crasher.c - Advanced macOS core dump generator
 *
 * Produces crash dumps that are extremely difficult for LLDB-based
 * analysis tools (like Crashbot) to parse. Each mode targets a
 * specific macOS debugging pain point: ObjC-style dispatch, GCD-like
 * work queues, Mach exception ports, guard pages, dyld interposition
 * chains, runloop-style event dispatch, and cleanup-handler crashes.
 *
 * Build (pure-POSIX, works on both macOS and Linux):
 *   clang -g -O0 -o macos_complex_crasher macos_complex_crasher.c -lpthread -ldl
 *
 * Build (macOS with Mach APIs):
 *   clang -g -O0 -DUSE_MACH -o macos_complex_crasher macos_complex_crasher.c -lpthread -ldl
 *
 * Build (macOS with Foundation framework, full features):
 *   clang -g -O0 -DUSE_MACH -framework Foundation -o macos_complex_crasher macos_complex_crasher.c -lpthread -ldl
 *
 * Before running (macOS):
 *   ulimit -c unlimited
 *   sudo sysctl kern.coredump=1        # may be needed on 10.15+
 *   # Core files go to /cores/core.<pid>
 *
 * Before running (Linux):
 *   ulimit -c unlimited
 *   echo "core.%e.%p" | sudo tee /proc/sys/kernel/core_pattern
 *
 * Usage:
 *   ./macos_complex_crasher objc_dispatch    -- ObjC-style message dispatch crash
 *   ./macos_complex_crasher gcd_queue        -- GCD-style concurrent queue crash
 *   ./macos_complex_crasher mach_exception   -- Mach exception port crash
 *   ./macos_complex_crasher guard_malloc     -- Guard-page EXC_BAD_ACCESS crash
 *   ./macos_complex_crasher dyld_interpose   -- dyld interposition chain crash
 *   ./macos_complex_crasher runloop          -- CFRunLoop-style event loop crash
 *   ./macos_complex_crasher cleanup          -- pthread cleanup handler crash
 *   ./macos_complex_crasher all              -- run all modes sequentially (first crash wins)
 *
 * Analyze with LLDB:
 *   lldb --core /cores/core.<pid> --file ./macos_complex_crasher
 *
 * Each mode is designed to produce confusing backtraces that challenge
 * automated crash analysis:
 *   - Deep function pointer indirection obscures call chains
 *   - Multiple threads with interleaved state
 *   - Unusual fault addresses from guard pages
 *   - Symbol resolution during interposition
 *   - Crash during unwind/cleanup creates paradoxical state
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <pthread.h>
#include <sys/mman.h>
#include <dlfcn.h>
#include <stdint.h>
#include <errno.h>
#include <setjmp.h>
#include <time.h>

#ifdef __APPLE__
#include <mach/mach.h>
#include <mach/mach_init.h>
#include <mach/thread_act.h>
#include <mach/thread_status.h>
#include <sys/sysctl.h>
#endif

/* ---------------------------------------------------------------------------
 * Shared helpers
 * --------------------------------------------------------------------------- */

static volatile int g_sink;
static volatile int g_keep_running = 1;

/* Prevent inlining so every helper shows up as its own frame in backtraces. */
#define NOINLINE __attribute__((noinline))
#define OPTNONE __attribute__((optnone))

static void print_banner(const char *mode)
{
    printf("====================================================================\n");
    printf("[*] Crashbot macOS complex crasher -- mode: %s\n", mode);
    printf("[*] PID: %d\n", getpid());
    printf("[*] Reminder: ulimit -c unlimited\n");
#ifdef __APPLE__
    printf("[*] Core files: /cores/core.%d\n", getpid());
    printf("[*] Also check: sudo sysctl kern.coredump=1\n");
#else
    printf("[*] Check /proc/sys/kernel/core_pattern for core location\n");
#endif
    printf("====================================================================\n\n");
}

/* Small delay to let threads interleave. */
static void spin_briefly(void)
{
    volatile int i;
    for (i = 0; i < 100000; i++)
        ;
}

/* ---------------------------------------------------------------------------
 * Mode 1: Objective-C message-send style dispatch crash
 *
 * Simulates objc_msgSend by building a multi-level dispatch table of
 * function pointers (isa -> class -> method list -> IMP). The crash
 * happens deep inside the trampoline chain, producing a backtrace that
 * looks like ObjC runtime internals.
 * --------------------------------------------------------------------------- */

/* Simulated ObjC runtime structures */
typedef void (*IMP_func)(void *self, const char *selector);

typedef struct {
    const char *name;
    IMP_func    imp;
} MethodEntry;

typedef struct {
    const char    *class_name;
    int            method_count;
    MethodEntry   *methods;
    void          *super_class;  /* for message forwarding chain */
} ClassDescriptor;

typedef struct {
    ClassDescriptor *isa;
    int              refcount;
    char             payload[64];
} FakeObject;

/* The crash happens here, deep inside the "IMP" */
static NOINLINE void _imp_dealloc(void *self, const char *selector)
{
    printf("    [IMP] -[FakeObject dealloc] self=%p sel=%s\n", self, selector);
    /* Simulate use-after-free: zero out isa, then try to message again */
    FakeObject *obj = (FakeObject *)self;
    obj->isa = NULL;
    /* Now "message send" through NULL isa -- crash */
    obj->isa->methods[0].imp(self, "release");
}

static NOINLINE void _imp_release(void *self, const char *selector)
{
    printf("    [IMP] -[FakeObject release] self=%p sel=%s\n", self, selector);
    FakeObject *obj = (FakeObject *)self;
    obj->refcount--;
    if (obj->refcount <= 0) {
        /* Forward to dealloc -- another level of dispatch */
        obj->isa->methods[1].imp(self, "dealloc");
    }
}

static NOINLINE void _imp_autorelease(void *self, const char *selector)
{
    printf("    [IMP] -[FakeObject autorelease] self=%p sel=%s\n", self, selector);
    /* Simulate autorelease pool drain -> release */
    _imp_release(self, "release");
}

/* Trampoline that mimics objc_msgSend lookup */
static NOINLINE void objc_msgSend_trampoline(void *self, const char *selector)
{
    FakeObject *obj = (FakeObject *)self;
    ClassDescriptor *cls = obj->isa;

    printf("  [objc_msgSend] self=%p class=%s sel=%s\n",
           self, cls ? cls->class_name : "(nil)", selector);

    /* Walk method list (like real objc_msgSend cache miss -> method search) */
    for (int i = 0; i < cls->method_count; i++) {
        if (strcmp(cls->methods[i].name, selector) == 0) {
            cls->methods[i].imp(self, selector);
            return;
        }
    }
    /* Message forwarding -- walk super chain */
    if (cls->super_class) {
        obj->isa = (ClassDescriptor *)cls->super_class;
        objc_msgSend_trampoline(self, selector);
        obj->isa = cls; /* restore (won't reach here on crash) */
    } else {
        printf("  [objc_msgSend] unrecognized selector '%s'\n", selector);
        abort();
    }
}

/* Second-level trampoline to add more frames */
static NOINLINE void _objc_rootAutorelease(void *obj)
{
    printf("  [_objc_rootAutorelease] obj=%p\n", obj);
    objc_msgSend_trampoline(obj, "autorelease");
}

/* Autorelease pool drain simulation */
static NOINLINE void AutoreleasePoolPage_drain(void *obj)
{
    printf("  [AutoreleasePoolPage::drain]\n");
    _objc_rootAutorelease(obj);
}

static MethodEntry g_fake_methods[] = {
    { "release",     _imp_release },
    { "dealloc",     _imp_dealloc },
    { "autorelease", _imp_autorelease },
};

static ClassDescriptor g_NSObject_class = {
    .class_name   = "NSObject",
    .method_count = 0,
    .methods      = NULL,
    .super_class  = NULL,
};

static ClassDescriptor g_FakeObject_class = {
    .class_name   = "FakeObject",
    .method_count = 3,
    .methods      = g_fake_methods,
    .super_class  = &g_NSObject_class,
};

static NOINLINE void crash_objc_dispatch(void)
{
    printf("[Mode 1] ObjC-style message dispatch crash\n");
    printf("  Creating fake ObjC object with dispatch table...\n\n");

    FakeObject *obj = (FakeObject *)malloc(sizeof(FakeObject));
    obj->isa = &g_FakeObject_class;
    obj->refcount = 1;
    memset(obj->payload, 'A', sizeof(obj->payload));

    /* Simulate an autorelease pool drain that triggers use-after-free */
    AutoreleasePoolPage_drain(obj);
}

/* ---------------------------------------------------------------------------
 * Mode 2: Grand Central Dispatch (GCD) style crash
 *
 * Creates a libdispatch-like concurrent work queue system with nested
 * dispatch_async chains. Worker threads pick up blocks from a shared
 * queue. The crash occurs deep in a nested dispatch chain, producing
 * a backtrace full of _dispatch_* frames.
 * --------------------------------------------------------------------------- */

#define GCD_QUEUE_SIZE 64
#define GCD_NUM_WORKERS 4

typedef void (*dispatch_block_t)(void *context);

typedef struct {
    dispatch_block_t block;
    void            *context;
    const char      *label;
    int              priority;
} WorkItem;

typedef struct {
    WorkItem         items[GCD_QUEUE_SIZE];
    int              head;
    int              tail;
    int              count;
    pthread_mutex_t  lock;
    pthread_cond_t   not_empty;
    pthread_cond_t   not_full;
    const char      *queue_label;
    int              concurrent;
    volatile int     shutdown;
} DispatchQueue;

static DispatchQueue g_main_queue;
static DispatchQueue g_background_queue;
static DispatchQueue g_utility_queue;

static void dispatch_queue_init(DispatchQueue *q, const char *label, int concurrent)
{
    memset(q, 0, sizeof(*q));
    q->queue_label = label;
    q->concurrent = concurrent;
    pthread_mutex_init(&q->lock, NULL);
    pthread_cond_init(&q->not_empty, NULL);
    pthread_cond_init(&q->not_full, NULL);
}

static void dispatch_queue_submit(DispatchQueue *q, dispatch_block_t block,
                                  void *ctx, const char *label)
{
    pthread_mutex_lock(&q->lock);
    while (q->count >= GCD_QUEUE_SIZE && !q->shutdown) {
        pthread_cond_wait(&q->not_full, &q->lock);
    }
    if (q->shutdown) {
        pthread_mutex_unlock(&q->lock);
        return;
    }
    q->items[q->tail].block = block;
    q->items[q->tail].context = ctx;
    q->items[q->tail].label = label;
    q->tail = (q->tail + 1) % GCD_QUEUE_SIZE;
    q->count++;
    pthread_cond_signal(&q->not_empty);
    pthread_mutex_unlock(&q->lock);
}

/* Simulated libdispatch internal frames */
static NOINLINE void _dispatch_call_block_and_release(WorkItem *item)
{
    printf("      [_dispatch_call_block_and_release] label='%s'\n",
           item->label ? item->label : "(null)");
    item->block(item->context);
}

static NOINLINE void _dispatch_client_callout(WorkItem *item)
{
    printf("    [_dispatch_client_callout] queue_item=%p\n", (void *)item);
    _dispatch_call_block_and_release(item);
}

static NOINLINE void _dispatch_queue_drain(DispatchQueue *q, WorkItem *item)
{
    printf("  [_dispatch_queue_drain] queue='%s'\n", q->queue_label);
    _dispatch_client_callout(item);
}

static NOINLINE void _dispatch_queue_invoke(DispatchQueue *q, WorkItem *item)
{
    printf("  [_dispatch_queue_invoke] queue='%s'\n", q->queue_label);
    _dispatch_queue_drain(q, item);
}

static void *_dispatch_worker_thread(void *arg)
{
    DispatchQueue *q = (DispatchQueue *)arg;
    char thread_name[64];
    snprintf(thread_name, sizeof(thread_name), "com.apple.dispatch.%s", q->queue_label);

#ifdef __APPLE__
    pthread_setname_np(thread_name);
#elif defined(__linux__)
    pthread_setname_np(pthread_self(), thread_name);
#endif

    while (!q->shutdown) {
        WorkItem item;
        pthread_mutex_lock(&q->lock);
        while (q->count == 0 && !q->shutdown) {
            pthread_cond_wait(&q->not_empty, &q->lock);
        }
        if (q->shutdown) {
            pthread_mutex_unlock(&q->lock);
            break;
        }
        item = q->items[q->head];
        q->head = (q->head + 1) % GCD_QUEUE_SIZE;
        q->count--;
        pthread_cond_signal(&q->not_full);
        pthread_mutex_unlock(&q->lock);

        _dispatch_queue_invoke(q, &item);
    }
    return NULL;
}

/* The nested dispatch blocks that form a confusing chain */
static int g_dispatch_depth = 0;

static NOINLINE void gcd_inner_block_crash(void *ctx)
{
    (void)ctx;
    printf("        [block] INNER CRASH BLOCK (depth=%d)\n", g_dispatch_depth);
    printf("        [block] Accessing freed dispatch_queue...\n");
    /* Simulate accessing a freed queue's vtable */
    DispatchQueue *freed_q = (DispatchQueue *)0xDEADBEEF0000ULL;
    freed_q->count = 42; /* EXC_BAD_ACCESS */
}

static NOINLINE void gcd_middle_block(void *ctx)
{
    g_dispatch_depth++;
    printf("      [block] middle_block (depth=%d) -> re-dispatching to utility queue\n",
           g_dispatch_depth);
    /* Re-dispatch deeper */
    dispatch_queue_submit(&g_utility_queue, gcd_inner_block_crash, ctx,
                          "com.crashbot.inner-crash");
    spin_briefly();
}

static NOINLINE void gcd_outer_block(void *ctx)
{
    g_dispatch_depth++;
    printf("    [block] outer_block (depth=%d) -> re-dispatching to background queue\n",
           g_dispatch_depth);
    dispatch_queue_submit(&g_background_queue, gcd_middle_block, ctx,
                          "com.crashbot.middle");
    spin_briefly();
}

static NOINLINE void crash_gcd_queue(void)
{
    printf("[Mode 2] GCD-style concurrent queue crash\n");
    printf("  Setting up dispatch queues with worker threads...\n\n");

    dispatch_queue_init(&g_main_queue, "com.apple.main-thread", 0);
    dispatch_queue_init(&g_background_queue, "com.apple.root.background-qos", 1);
    dispatch_queue_init(&g_utility_queue, "com.apple.root.utility-qos", 1);

    /* Start worker threads for each queue */
    pthread_t bg_workers[GCD_NUM_WORKERS];
    pthread_t util_workers[2];

    for (int i = 0; i < GCD_NUM_WORKERS; i++)
        pthread_create(&bg_workers[i], NULL, _dispatch_worker_thread, &g_background_queue);
    for (int i = 0; i < 2; i++)
        pthread_create(&util_workers[i], NULL, _dispatch_worker_thread, &g_utility_queue);

    /* Submit the outer block -- it will chain through queues and crash */
    dispatch_queue_submit(&g_background_queue, gcd_outer_block, NULL,
                          "com.crashbot.outer");

    /* Wait for crash (workers will die) */
    for (int i = 0; i < GCD_NUM_WORKERS; i++)
        pthread_join(bg_workers[i], NULL);
    for (int i = 0; i < 2; i++)
        pthread_join(util_workers[i], NULL);
}

/* ---------------------------------------------------------------------------
 * Mode 3: Mach exception port crash
 *
 * On macOS, manipulates thread exception ports using Mach APIs.
 * On Linux, falls back to signal handler manipulation.
 * The crash occurs while exception ports are in an inconsistent state.
 * --------------------------------------------------------------------------- */

#ifdef __APPLE__

/* Store original exception ports so we can create inconsistent state */
static mach_port_t g_original_exception_port = MACH_PORT_NULL;
static mach_port_t g_custom_exception_port = MACH_PORT_NULL;

static NOINLINE void mach_exc_crash_in_handler(void)
{
    printf("    [mach_exc_handler] Exception received on custom port\n");
    printf("    [mach_exc_handler] Attempting to forward to original port...\n");
    printf("    [mach_exc_handler] Original port: 0x%x (DEALLOCATED!)\n",
           g_original_exception_port);

    /* Crash: access through a bad Mach port / pointer */
    volatile int *bad = (volatile int *)(uintptr_t)0xFEEDFACECAFEULL;
    g_sink = *bad;
}

static void *mach_exception_thread(void *arg)
{
    (void)arg;

#ifdef __APPLE__
    pthread_setname_np("com.apple.exc-thread");
#endif

    printf("  [exc_thread] Exception handler thread started\n");

    /* Wait a moment then trigger the crash */
    spin_briefly();
    spin_briefly();

    mach_exc_crash_in_handler();
    return NULL;
}

static NOINLINE void crash_mach_exception(void)
{
    printf("[Mode 3] Mach exception port crash\n");
    printf("  Manipulating thread exception ports...\n\n");

    kern_return_t kr;
    mach_port_t task = mach_task_self();
    mach_port_t thread = mach_thread_self();

    /* Allocate a custom exception port */
    kr = mach_port_allocate(task, MACH_PORT_RIGHT_RECEIVE, &g_custom_exception_port);
    if (kr != KERN_SUCCESS) {
        printf("  [!] mach_port_allocate failed: %s\n", mach_error_string(kr));
        abort();
    }

    kr = mach_port_insert_right(task, g_custom_exception_port,
                                 g_custom_exception_port, MACH_MSG_TYPE_MAKE_SEND);
    if (kr != KERN_SUCCESS) {
        printf("  [!] mach_port_insert_right failed: %s\n", mach_error_string(kr));
        abort();
    }

    printf("  Custom exception port: 0x%x\n", g_custom_exception_port);

    /* Save original exception ports */
    exception_mask_t masks[EXC_TYPES_COUNT];
    mach_msg_type_number_t count = EXC_TYPES_COUNT;
    mach_port_t ports[EXC_TYPES_COUNT];
    exception_behavior_t behaviors[EXC_TYPES_COUNT];
    thread_state_flavor_t flavors[EXC_TYPES_COUNT];

    kr = thread_get_exception_ports(thread,
                                     EXC_MASK_BAD_ACCESS | EXC_MASK_CRASH,
                                     masks, &count, ports, behaviors, flavors);
    if (kr == KERN_SUCCESS && count > 0) {
        g_original_exception_port = ports[0];
        printf("  Original exception port: 0x%x\n", g_original_exception_port);
    }

    /* Set our custom port for the current thread */
    kr = thread_set_exception_ports(thread,
                                     EXC_MASK_BAD_ACCESS,
                                     g_custom_exception_port,
                                     EXCEPTION_DEFAULT | MACH_EXCEPTION_CODES,
                                     THREAD_STATE_NONE);
    printf("  Set custom exception port: %s\n",
           kr == KERN_SUCCESS ? "OK" : mach_error_string(kr));

    /* Now deallocate the port to create inconsistent state */
    mach_port_deallocate(task, g_custom_exception_port);
    printf("  Deallocated custom exception port (now dangling!)\n");

    /* Spawn a thread that will try to handle exceptions */
    pthread_t exc_thread;
    pthread_create(&exc_thread, NULL, mach_exception_thread, NULL);

    /* Trigger EXC_BAD_ACCESS on this thread with broken exception port */
    spin_briefly();
    printf("  Triggering crash with dangling exception port...\n");
    volatile int *p = NULL;
    g_sink = *p;

    pthread_join(exc_thread, NULL);
}

#else /* !__APPLE__ -- Linux fallback */

static volatile sig_atomic_t g_in_signal_handler = 0;

static void nested_signal_handler(int sig)
{
    (void)sig;
    printf("    [nested_handler] SIGSEGV inside SIGSEGV handler!\n");
    /* Double fault -- crash hard */
    volatile int *p = (volatile int *)0xDEADDEAD;
    g_sink = *p;
}

static void primary_signal_handler(int sig)
{
    (void)sig;
    g_in_signal_handler = 1;
    printf("  [primary_handler] Caught SIGSEGV, installing nested handler...\n");

    /* Install a different handler for the nested signal */
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = nested_signal_handler;
    sa.sa_flags = 0; /* no SA_RESETHAND */
    sigaction(SIGSEGV, &sa, NULL);

    printf("  [primary_handler] Triggering nested SIGSEGV...\n");
    volatile int *p = (volatile int *)0xBADBAD;
    g_sink = *p;
}

static NOINLINE void crash_mach_exception(void)
{
    printf("[Mode 3] Signal handler nesting crash (Linux fallback for Mach)\n");
    printf("  Installing nested signal handlers...\n\n");

    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = primary_signal_handler;
    sa.sa_flags = 0;
    sigaction(SIGSEGV, &sa, NULL);

    printf("  Triggering initial SIGSEGV...\n");
    volatile int *p = NULL;
    g_sink = *p;
}

#endif /* __APPLE__ */

/* ---------------------------------------------------------------------------
 * Mode 4: Guard malloc style crash
 *
 * Uses mmap to create memory regions surrounded by PROT_NONE guard
 * pages. Accesses the guard page to trigger EXC_BAD_ACCESS with
 * unusual fault addresses that confuse analysis tools.
 * --------------------------------------------------------------------------- */

#define GUARD_PAGE_SIZE 4096
#define NUM_GUARD_ALLOCS 8

typedef struct {
    void  *base;       /* start of entire mmap region */
    void  *usable;     /* usable region between guard pages */
    size_t total_size; /* total mmap size */
    size_t usable_size;
    int    slot_id;
} GuardedAlloc;

static GuardedAlloc g_guarded_allocs[NUM_GUARD_ALLOCS];

static NOINLINE void *guard_malloc(size_t size, int slot)
{
    /* Layout: [GUARD PAGE] [usable region] [GUARD PAGE] */
    size_t usable_pages = (size + GUARD_PAGE_SIZE - 1) / GUARD_PAGE_SIZE;
    size_t total = (usable_pages + 2) * GUARD_PAGE_SIZE;

    void *base = mmap(NULL, total, PROT_NONE,
                      MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (base == MAP_FAILED) {
        perror("mmap");
        return NULL;
    }

    void *usable = (char *)base + GUARD_PAGE_SIZE;
    if (mprotect(usable, usable_pages * GUARD_PAGE_SIZE,
                 PROT_READ | PROT_WRITE) != 0) {
        perror("mprotect");
        munmap(base, total);
        return NULL;
    }

    g_guarded_allocs[slot].base = base;
    g_guarded_allocs[slot].usable = usable;
    g_guarded_allocs[slot].total_size = total;
    g_guarded_allocs[slot].usable_size = usable_pages * GUARD_PAGE_SIZE;
    g_guarded_allocs[slot].slot_id = slot;

    printf("    [guard_malloc] slot=%d base=%p usable=%p size=%zu\n",
           slot, base, usable, size);
    return usable;
}

static NOINLINE void guard_free(int slot)
{
    GuardedAlloc *ga = &g_guarded_allocs[slot];
    /* Mark the usable region as PROT_NONE (freed) but keep mapping */
    mprotect(ga->usable, ga->usable_size, PROT_NONE);
    printf("    [guard_free] slot=%d -- region now PROT_NONE (use-after-free trap)\n",
           slot);
}

/* Simulate a complex allocation pattern then access freed memory */
static NOINLINE void guard_malloc_access_freed(int slot)
{
    GuardedAlloc *ga = &g_guarded_allocs[slot];
    printf("    [guard_malloc_access] Accessing freed slot %d at %p\n",
           slot, ga->usable);
    /* This triggers EXC_BAD_ACCESS on the guard-freed page */
    volatile char *p = (volatile char *)ga->usable;
    g_sink = p[0]; /* BOOM */
}

static NOINLINE void guard_malloc_overflow(int slot)
{
    GuardedAlloc *ga = &g_guarded_allocs[slot];
    volatile char *p = (volatile char *)ga->usable;
    printf("    [guard_malloc_overflow] Writing past end of slot %d\n", slot);
    /* Write past the usable region into the trailing guard page */
    size_t off = ga->usable_size; /* first byte of trailing guard */
    p[off] = 'X'; /* EXC_BAD_ACCESS at guard page boundary */
}

/* Thread that performs guard-malloc operations */
static void *guard_malloc_worker(void *arg)
{
    int worker_id = (int)(intptr_t)arg;
    char name[64];
    snprintf(name, sizeof(name), "guard-worker-%d", worker_id);
#ifdef __APPLE__
    pthread_setname_np(name);
#elif defined(__linux__)
    pthread_setname_np(pthread_self(), name);
#endif

    printf("  [worker-%d] Started\n", worker_id);
    spin_briefly();

    if (worker_id == 0) {
        /* Worker 0: allocate, free, then access (use-after-free) */
        guard_malloc(256, 0);
        guard_free(0);
        spin_briefly();
        guard_malloc_access_freed(0);
    } else if (worker_id == 1) {
        /* Worker 1: allocate then overflow */
        guard_malloc(128, 1);
        spin_briefly();
        guard_malloc_overflow(1);
    } else {
        /* Other workers just allocate and spin (provide thread noise) */
        guard_malloc(64 * (worker_id + 1), worker_id);
        while (g_keep_running) {
            spin_briefly();
        }
    }
    return NULL;
}

static NOINLINE void crash_guard_malloc(void)
{
    printf("[Mode 4] Guard malloc style crash\n");
    printf("  Creating guarded allocations with PROT_NONE guard pages...\n\n");

    g_keep_running = 1;
    pthread_t workers[4];
    for (int i = 0; i < 4; i++)
        pthread_create(&workers[i], NULL, guard_malloc_worker, (void *)(intptr_t)i);

    for (int i = 0; i < 4; i++)
        pthread_join(workers[i], NULL);

    g_keep_running = 0;
}

/* ---------------------------------------------------------------------------
 * Mode 5: dyld interposition crash
 *
 * Simulates a dyld-like dynamic symbol resolution chain using dlopen
 * and function pointer tables. Creates a deep interposition chain
 * where the crash occurs during symbol lookup, producing confusing
 * _dyld_* frames in the backtrace.
 * --------------------------------------------------------------------------- */

/* Simulated interposition table entry */
typedef struct {
    const char *symbol_name;
    void       *replacement;
    void       *original;
    int         depth;
} InterpositionEntry;

#define MAX_INTERPOSITIONS 16
static InterpositionEntry g_interposition_table[MAX_INTERPOSITIONS];
static int g_interposition_count = 0;
static pthread_mutex_t g_dyld_lock = PTHREAD_MUTEX_INITIALIZER;

typedef int (*MallocFunc)(size_t);
typedef void (*FreeFunc)(void *);

/* Simulate deeply nested dyld symbol resolution */
static NOINLINE void *_dyld_fast_stub_entry(const char *symbol, int depth);

static NOINLINE void *_dyld_resolve_symbol_lazy(const char *symbol, int depth)
{
    printf("      [_dyld_resolve_symbol_lazy] '%s' depth=%d\n", symbol, depth);
    /* Check interposition table */
    for (int i = 0; i < g_interposition_count; i++) {
        if (strcmp(g_interposition_table[i].symbol_name, symbol) == 0) {
            printf("        -> interposed! replacement=%p\n",
                   g_interposition_table[i].replacement);
            if (g_interposition_table[i].depth < depth) {
                /* Chain to next interposition level */
                return _dyld_fast_stub_entry(symbol, depth - 1);
            }
            return g_interposition_table[i].replacement;
        }
    }
    return NULL;
}

static NOINLINE void *_dyld_image_lookup(const char *symbol, int depth)
{
    printf("    [_dyld_image_lookup] '%s' in image %d\n", symbol, depth);
    return _dyld_resolve_symbol_lazy(symbol, depth);
}

static NOINLINE void *_dyld_fast_stub_entry(const char *symbol, int depth)
{
    printf("  [_dyld_fast_stub_entry] '%s' depth=%d\n", symbol, depth);
    if (depth <= 0) {
        printf("  [_dyld_fast_stub_entry] Resolution depth exhausted -- NULL!\n");
        return NULL;
    }
    return _dyld_image_lookup(symbol, depth);
}

/* The interposed functions */
static NOINLINE int interposed_malloc_v3(size_t size)
{
    printf("        [interposed_malloc_v3] size=%zu (CRASHING)\n", size);
    /* Simulate crash during interposed malloc: corrupt function pointer */
    void *(*bad_func)(void) = (void *(*)(void))0x4141414141414141ULL;
    bad_func(); /* EXC_BAD_ACCESS at 0x4141414141414141 */
    return 0;
}

static NOINLINE int interposed_malloc_v2(size_t size)
{
    printf("      [interposed_malloc_v2] size=%zu -> chaining deeper\n", size);
    /* Resolve the next level of interposition */
    void *resolved = _dyld_fast_stub_entry("malloc", 1);
    if (resolved) {
        return ((MallocFunc)resolved)(size);
    }
    /* Fell through -- crash on NULL function pointer */
    ((MallocFunc)NULL)(size);
    return 0;
}

static NOINLINE int interposed_malloc_v1(size_t size)
{
    printf("    [interposed_malloc_v1] size=%zu -> looking up next interposition\n",
           size);
    void *resolved = _dyld_fast_stub_entry("malloc", 2);
    if (resolved) {
        return ((MallocFunc)resolved)(size);
    }
    return 0;
}

/* Thread that loads "libraries" and triggers the interposition crash */
static void *dyld_loader_thread(void *arg)
{
    int thread_id = (int)(intptr_t)arg;
    char name[64];
    snprintf(name, sizeof(name), "dyld-loader-%d", thread_id);
#ifdef __APPLE__
    pthread_setname_np(name);
#elif defined(__linux__)
    pthread_setname_np(pthread_self(), name);
#endif

    printf("  [loader-%d] Simulating library load...\n", thread_id);

    pthread_mutex_lock(&g_dyld_lock);

    /* Register interpositions (simulating DYLD_INSERT_LIBRARIES) */
    if (g_interposition_count == 0) {
        g_interposition_table[0] = (InterpositionEntry){
            .symbol_name = "malloc",
            .replacement = (void *)interposed_malloc_v1,
            .original = NULL,
            .depth = 3,
        };
        g_interposition_table[1] = (InterpositionEntry){
            .symbol_name = "malloc",
            .replacement = (void *)interposed_malloc_v2,
            .original = (void *)interposed_malloc_v1,
            .depth = 2,
        };
        g_interposition_table[2] = (InterpositionEntry){
            .symbol_name = "malloc",
            .replacement = (void *)interposed_malloc_v3,
            .original = (void *)interposed_malloc_v2,
            .depth = 1,
        };
        g_interposition_count = 3;
        printf("  [loader-%d] Registered %d interpositions for 'malloc'\n",
               thread_id, g_interposition_count);
    }
    pthread_mutex_unlock(&g_dyld_lock);

    if (thread_id == 0) {
        spin_briefly();
        printf("  [loader-%d] Calling interposed malloc chain...\n", thread_id);
        interposed_malloc_v1(1024);
    } else {
        /* Other threads spin to add noise to the thread list */
        while (g_keep_running) {
            spin_briefly();
        }
    }
    return NULL;
}

static NOINLINE void crash_dyld_interpose(void)
{
    printf("[Mode 5] dyld interposition chain crash\n");
    printf("  Setting up nested interposition tables...\n\n");

    g_interposition_count = 0;
    g_keep_running = 1;

    pthread_t loaders[3];
    for (int i = 0; i < 3; i++)
        pthread_create(&loaders[i], NULL, dyld_loader_thread, (void *)(intptr_t)i);

    for (int i = 0; i < 3; i++)
        pthread_join(loaders[i], NULL);

    g_keep_running = 0;
}

/* ---------------------------------------------------------------------------
 * Mode 6: CFRunLoop-style event loop crash
 *
 * Simulates a macOS run loop with multiple sources, timers, and
 * observers. The crash occurs during event dispatch with complex
 * thread state (multiple pending timers, partially processed sources).
 * --------------------------------------------------------------------------- */

#define RUNLOOP_MAX_SOURCES 16
#define RUNLOOP_MAX_TIMERS  8

typedef void (*RunLoopCallback)(void *info);

typedef struct {
    const char      *name;
    RunLoopCallback  callback;
    void            *info;
    int              is_valid;
    int              is_signaled;
} RunLoopSource;

typedef struct {
    const char      *name;
    RunLoopCallback  callback;
    void            *info;
    int              is_valid;
    struct timespec  fire_time;
    int              repeats;
} RunLoopTimer;

typedef struct {
    const char       *mode_name;
    RunLoopSource     sources[RUNLOOP_MAX_SOURCES];
    int               source_count;
    RunLoopTimer      timers[RUNLOOP_MAX_TIMERS];
    int               timer_count;
    pthread_mutex_t   lock;
    pthread_cond_t    wakeup;
    volatile int      is_running;
    volatile int      should_stop;
} FakeRunLoop;

static FakeRunLoop g_runloop;

static NOINLINE void __CFRunLoopDoSource0(RunLoopSource *source)
{
    printf("      [__CFRunLoopDoSource0] '%s' signaled=%d\n",
           source->name, source->is_signaled);
    if (source->is_signaled && source->callback) {
        source->is_signaled = 0;
        source->callback(source->info);
    }
}

static NOINLINE void __CFRunLoopDoTimers(FakeRunLoop *rl)
{
    printf("    [__CFRunLoopDoTimers] checking %d timers\n", rl->timer_count);
    for (int i = 0; i < rl->timer_count; i++) {
        if (rl->timers[i].is_valid && rl->timers[i].callback) {
            printf("      firing timer '%s'\n", rl->timers[i].name);
            rl->timers[i].callback(rl->timers[i].info);
        }
    }
}

static NOINLINE void __CFRunLoopDoSources0(FakeRunLoop *rl)
{
    printf("    [__CFRunLoopDoSources0] processing %d sources\n", rl->source_count);
    for (int i = 0; i < rl->source_count; i++) {
        if (rl->sources[i].is_valid) {
            __CFRunLoopDoSource0(&rl->sources[i]);
        }
    }
}

static NOINLINE void __CFRunLoopRun(FakeRunLoop *rl)
{
    printf("  [__CFRunLoopRun] mode='%s'\n", rl->mode_name);
    rl->is_running = 1;

    int iteration = 0;
    while (!rl->should_stop && iteration < 10) {
        printf("  [__CFRunLoopRun] iteration %d\n", iteration);

        /* Process sources */
        __CFRunLoopDoSources0(rl);

        /* Process timers */
        __CFRunLoopDoTimers(rl);

        iteration++;
        spin_briefly();
    }

    rl->is_running = 0;
}

static NOINLINE void CFRunLoopRun(FakeRunLoop *rl)
{
    printf("  [CFRunLoopRun] entering run loop\n");
    __CFRunLoopRun(rl);
}

/* Source callbacks */
static NOINLINE void socket_source_callback(void *info)
{
    printf("        [socket_source] Processing network event, info=%p\n", info);
    /* This source is fine */
}

static NOINLINE void ui_event_source_callback(void *info)
{
    printf("        [ui_event_source] Processing UI event, info=%p\n", info);
    /* This source is fine too */
}

static NOINLINE void crash_source_callback(void *info)
{
    printf("        [crash_source] CORRUPTED EVENT -- dereferencing bad pointer!\n");
    (void)info;
    /* Simulate dispatching to a freed responder chain */
    typedef void (*ResponderMethod)(void *, int);
    ResponderMethod method = (ResponderMethod)0x7FFF00001000ULL;
    method(info, 42);
}

/* Timer callbacks */
static NOINLINE void animation_timer_callback(void *info)
{
    printf("        [animation_timer] Tick (info=%p)\n", info);
}

static NOINLINE void crash_timer_callback(void *info)
{
    printf("        [crash_timer] Timer fire with stale info pointer!\n");
    /* info was freed -- use-after-free */
    volatile char *p = (volatile char *)info;
    g_sink = p[0];
}

/* Thread to signal sources while runloop runs */
static void *runloop_signal_thread(void *arg)
{
    FakeRunLoop *rl = (FakeRunLoop *)arg;

#ifdef __APPLE__
    pthread_setname_np("com.apple.CFRunLoop.signal");
#elif defined(__linux__)
    pthread_setname_np(pthread_self(), "runloop-signal");
#endif

    /* Wait for runloop to start */
    while (!rl->is_running)
        spin_briefly();

    /* Signal sources in sequence */
    printf("  [signal_thread] Signaling socket source...\n");
    pthread_mutex_lock(&rl->lock);
    rl->sources[0].is_signaled = 1;
    pthread_cond_signal(&rl->wakeup);
    pthread_mutex_unlock(&rl->lock);
    spin_briefly();

    printf("  [signal_thread] Signaling UI event source...\n");
    pthread_mutex_lock(&rl->lock);
    rl->sources[1].is_signaled = 1;
    pthread_cond_signal(&rl->wakeup);
    pthread_mutex_unlock(&rl->lock);
    spin_briefly();

    printf("  [signal_thread] Signaling CRASH source...\n");
    pthread_mutex_lock(&rl->lock);
    rl->sources[2].is_signaled = 1;
    pthread_cond_signal(&rl->wakeup);
    pthread_mutex_unlock(&rl->lock);

    return NULL;
}

static NOINLINE void crash_runloop(void)
{
    printf("[Mode 6] CFRunLoop-style event loop crash\n");
    printf("  Setting up run loop with sources, timers, and observers...\n\n");

    memset(&g_runloop, 0, sizeof(g_runloop));
    g_runloop.mode_name = "kCFRunLoopDefaultMode";
    pthread_mutex_init(&g_runloop.lock, NULL);
    pthread_cond_init(&g_runloop.wakeup, NULL);

    /* Add sources */
    g_runloop.sources[0] = (RunLoopSource){
        .name = "com.apple.network.socket",
        .callback = socket_source_callback,
        .info = (void *)0x1234,
        .is_valid = 1,
        .is_signaled = 0,
    };
    g_runloop.sources[1] = (RunLoopSource){
        .name = "com.apple.uikit.event",
        .callback = ui_event_source_callback,
        .info = (void *)0x5678,
        .is_valid = 1,
        .is_signaled = 0,
    };
    g_runloop.sources[2] = (RunLoopSource){
        .name = "com.crashbot.corrupt-source",
        .callback = crash_source_callback,
        .info = (void *)0xDEAD,
        .is_valid = 1,
        .is_signaled = 0,
    };
    g_runloop.source_count = 3;

    /* Add timers */
    g_runloop.timers[0] = (RunLoopTimer){
        .name = "com.apple.coreanimation.timer",
        .callback = animation_timer_callback,
        .info = (void *)0xAAAA,
        .is_valid = 1,
        .repeats = 1,
    };
    /* Timer with freed info pointer */
    void *timer_info = malloc(64);
    memset(timer_info, 'T', 64);
    free(timer_info); /* free it before the timer fires */
    g_runloop.timers[1] = (RunLoopTimer){
        .name = "com.crashbot.stale-timer",
        .callback = crash_timer_callback,
        .info = timer_info,  /* dangling pointer */
        .is_valid = 1,
        .repeats = 0,
    };
    g_runloop.timer_count = 2;

    /* Start signal thread */
    pthread_t sig_thread;
    pthread_create(&sig_thread, NULL, runloop_signal_thread, &g_runloop);

    /* Enter the run loop (crash will happen during dispatch) */
    CFRunLoopRun(&g_runloop);

    pthread_join(sig_thread, NULL);
}

/* ---------------------------------------------------------------------------
 * Mode 7: pthread cleanup handler crash
 *
 * Uses pthread_cleanup_push/pop to register cleanup handlers, then
 * crashes inside a cleanup handler during thread cancellation. This
 * creates confusing unwind state where the crash appears to be inside
 * cleanup/unwinding code.
 * --------------------------------------------------------------------------- */

/* Resources that cleanup handlers will try to free */
typedef struct {
    int   *buffer;
    size_t size;
    int    id;
    int    freed;
} ManagedResource;

static ManagedResource g_resources[4];

static NOINLINE void cleanup_level_3(void *arg)
{
    ManagedResource *res = (ManagedResource *)arg;
    printf("      [cleanup_level_3] Cleaning up resource %d (CRASH!)\n", res->id);
    printf("      [cleanup_level_3] Resource buffer=%p freed=%d\n",
           (void *)res->buffer, res->freed);

    /* Buffer was already freed -- use-after-free in cleanup */
    if (res->freed) {
        printf("      [cleanup_level_3] Double-free detected, accessing anyway...\n");
        /* Access the freed buffer */
        volatile int val = res->buffer[0]; /* may crash */
        (void)val;
        /* Now write to a completely bad address to ensure crash */
        volatile int *bad = (volatile int *)0xCAFEBABE;
        *bad = 42;
    }
    res->freed = 1;
}

static NOINLINE void cleanup_level_2(void *arg)
{
    ManagedResource *res = (ManagedResource *)arg;
    printf("    [cleanup_level_2] Cleaning up resource %d\n", res->id);
    /* Free the buffer so level_3 gets a use-after-free */
    if (res->buffer && !res->freed) {
        free(res->buffer);
        res->buffer = NULL;
        res->freed = 1;
    }
}

static NOINLINE void cleanup_level_1(void *arg)
{
    ManagedResource *res = (ManagedResource *)arg;
    printf("  [cleanup_level_1] Cleaning up resource %d\n", res->id);
}

/* Worker function with deeply nested cleanup handlers */
static NOINLINE void deep_work_with_cleanup(ManagedResource *res)
{
    printf("    [deep_work] Inside deep work function, resource %d\n", res->id);

    /* Push another cleanup (level 3 -- will crash) */
    pthread_cleanup_push(cleanup_level_3, res);

    printf("    [deep_work] Doing work... (checking for cancellation)\n");
    spin_briefly();

    /* Check for cancellation -- this triggers the cleanup chain */
    pthread_testcancel();

    printf("    [deep_work] Work complete (not cancelled)\n");
    pthread_cleanup_pop(0);
}

static void *cleanup_crash_thread(void *arg)
{
    int thread_id = (int)(intptr_t)arg;
    char name[64];
    snprintf(name, sizeof(name), "cleanup-thread-%d", thread_id);
#ifdef __APPLE__
    pthread_setname_np(name);
#elif defined(__linux__)
    pthread_setname_np(pthread_self(), name);
#endif

    printf("[thread-%d] Started with cleanup handlers\n", thread_id);

    ManagedResource *res = &g_resources[thread_id];
    res->id = thread_id;
    res->size = 256;
    res->buffer = (int *)malloc(res->size);
    res->freed = 0;
    memset(res->buffer, 0xAA + thread_id, res->size);

    /* Push cleanup handlers (LIFO order) */
    pthread_cleanup_push(cleanup_level_1, res);
    pthread_cleanup_push(cleanup_level_2, res);

    printf("[thread-%d] Entering deep work...\n", thread_id);
    deep_work_with_cleanup(res);

    printf("[thread-%d] Popping cleanups (normal exit)\n", thread_id);
    pthread_cleanup_pop(0); /* level 2 */
    pthread_cleanup_pop(0); /* level 1 */

    return NULL;
}

/* Thread that cancels the worker threads at the worst moment */
static void *cancellation_thread(void *arg)
{
    pthread_t *targets = (pthread_t *)arg;

#ifdef __APPLE__
    pthread_setname_np("cancellation-thread");
#elif defined(__linux__)
    pthread_setname_np(pthread_self(), "cancel-thread");
#endif

    /* Let the workers get into their deep_work functions */
    spin_briefly();
    spin_briefly();

    printf("[canceller] Cancelling worker threads...\n");
    for (int i = 0; i < 3; i++) {
        printf("[canceller] Sending cancel to thread %d\n", i);
        pthread_cancel(targets[i]);
    }

    return NULL;
}

static NOINLINE void crash_cleanup(void)
{
    printf("[Mode 7] pthread cleanup handler crash\n");
    printf("  Setting up threads with nested cleanup handlers...\n\n");

    pthread_t workers[3];
    pthread_t canceller;

    /* Create worker threads */
    for (int i = 0; i < 3; i++) {
        pthread_create(&workers[i], NULL, cleanup_crash_thread,
                       (void *)(intptr_t)i);
    }

    /* Create the cancellation thread */
    pthread_create(&canceller, NULL, cancellation_thread, workers);

    /* Wait for everything */
    pthread_join(canceller, NULL);
    for (int i = 0; i < 3; i++) {
        void *retval;
        pthread_join(workers[i], &retval);
        if (retval == PTHREAD_CANCELED)
            printf("[main] Thread %d was cancelled\n", i);
    }
}

/* ---------------------------------------------------------------------------
 * Main entry point
 * --------------------------------------------------------------------------- */

typedef struct {
    const char *name;
    const char *description;
    void (*func)(void);
} CrashMode;

static const CrashMode modes[] = {
    { "objc_dispatch",   "ObjC-style message dispatch table crash",       crash_objc_dispatch },
    { "gcd_queue",       "GCD-style concurrent dispatch queue crash",     crash_gcd_queue },
    { "mach_exception",  "Mach exception port / nested signal crash",     crash_mach_exception },
    { "guard_malloc",    "Guard malloc PROT_NONE guard page crash",       crash_guard_malloc },
    { "dyld_interpose",  "dyld interposition chain crash",                crash_dyld_interpose },
    { "runloop",         "CFRunLoop-style event loop crash",              crash_runloop },
    { "cleanup",         "pthread cleanup handler crash during unwind",   crash_cleanup },
};

static const int num_modes = sizeof(modes) / sizeof(modes[0]);

static void print_usage(const char *progname)
{
    printf("Usage: %s <mode>\n\n", progname);
    printf("Available crash modes:\n");
    for (int i = 0; i < num_modes; i++) {
        printf("  %-18s  %s\n", modes[i].name, modes[i].description);
    }
    printf("  %-18s  Run all modes (first crash wins)\n", "all");
    printf("\nEach mode generates a core dump targeting specific LLDB analysis\n");
    printf("pain points. Use with Crashbot to test analysis robustness.\n");
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    const char *mode = argv[1];

    if (strcmp(mode, "--help") == 0 || strcmp(mode, "-h") == 0) {
        print_usage(argv[0]);
        return 0;
    }

    print_banner(mode);

    /* Run all modes (first crash terminates the process) */
    if (strcmp(mode, "all") == 0) {
        printf("[*] Running all crash modes sequentially...\n");
        printf("[*] First crash will terminate the process.\n\n");
        for (int i = 0; i < num_modes; i++) {
            printf("--- Running mode: %s ---\n", modes[i].name);
            modes[i].func();
            printf("--- Mode %s survived (unexpected) ---\n\n", modes[i].name);
        }
        printf("[!] All modes completed without crashing (should not happen)\n");
        return 1;
    }

    /* Find and run the requested mode */
    for (int i = 0; i < num_modes; i++) {
        if (strcmp(mode, modes[i].name) == 0) {
            modes[i].func();
            printf("[!] Mode '%s' completed without crashing (unexpected)\n", mode);
            return 1;
        }
    }

    printf("[!] Unknown mode: %s\n\n", mode);
    print_usage(argv[0]);
    return 1;
}
