/*
 * Linux core dump generator.
 * Crashes intentionally to produce a core file.
 *
 * Build:
 *   gcc -g -o linux_crasher linux_crasher.c -lpthread
 *
 * Before running, enable core dumps:
 *   ulimit -c unlimited
 *   # optionally control core pattern:
 *   echo "core.%e.%p" | sudo tee /proc/sys/kernel/core_pattern
 *
 * Usage:
 *   ./linux_crasher                -- SIGSEGV (null-pointer dereference)
 *   ./linux_crasher sigabrt        -- SIGABRT (abort)
 *   ./linux_crasher sigfpe         -- SIGFPE (division by zero)
 *   ./linux_crasher sigbus         -- SIGBUS (bus error)
 *   ./linux_crasher multithread    -- SIGSEGV in a secondary thread
 *
 * The resulting core file can be analyzed with:
 *   gdb ./linux_crasher core.linux_crasher.<pid>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <pthread.h>
#include <sys/mman.h>

static volatile int sink;

static void crash_sigsegv(void)
{
    printf("[*] Triggering SIGSEGV (null-pointer dereference)...\n");
    int *p = NULL;
    sink = *p;
}

static void crash_sigabrt(void)
{
    printf("[*] Triggering SIGABRT...\n");
    abort();
}

static void crash_sigfpe(void)
{
    printf("[*] Triggering SIGFPE (division by zero)...\n");
    volatile int a = 42;
    volatile int b = 0;
    sink = a / b;
}

static void crash_sigbus(void)
{
    printf("[*] Triggering SIGBUS (unaligned access)...\n");
    /* mmap a page, munmap it, then access it */
    char *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) {
        perror("mmap");
        exit(1);
    }
    munmap(p, 4096);
    sink = *p;  /* SIGBUS or SIGSEGV depending on kernel */
}

static void *thread_crash(void *arg)
{
    (void)arg;
    printf("[*] Thread %lu triggering SIGSEGV...\n", (unsigned long)pthread_self());
    int *p = NULL;
    sink = *p;
    return NULL;
}

static void crash_multithread(void)
{
    printf("[*] Spawning worker threads, one will crash...\n");
    pthread_t threads[4];
    for (int i = 0; i < 4; i++) {
        if (i == 2) {
            pthread_create(&threads[i], NULL, thread_crash, NULL);
        } else {
            pthread_create(&threads[i], NULL, thread_crash, (void *)(long)(i + 100));
        }
    }
    for (int i = 0; i < 4; i++)
        pthread_join(threads[i], NULL);
}

int main(int argc, char *argv[])
{
    const char *mode = (argc > 1) ? argv[1] : "sigsegv";

    printf("[*] Crashbot Linux test crasher — mode: %s (PID: %d)\n", mode, getpid());
    printf("[*] Make sure core dumps are enabled: ulimit -c unlimited\n\n");

    if (strcmp(mode, "sigabrt") == 0)
        crash_sigabrt();
    else if (strcmp(mode, "sigfpe") == 0)
        crash_sigfpe();
    else if (strcmp(mode, "sigbus") == 0)
        crash_sigbus();
    else if (strcmp(mode, "multithread") == 0)
        crash_multithread();
    else
        crash_sigsegv();

    return 0;
}
