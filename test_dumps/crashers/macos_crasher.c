/*
 * macOS core dump generator.
 * Crashes intentionally to produce a core file.
 *
 * Build:
 *   clang -g -o macos_crasher macos_crasher.c
 * Or with Xcode:
 *   cc -g -o macos_crasher macos_crasher.c
 *
 * Before running, enable core dumps:
 *   ulimit -c unlimited
 *   # Core files go to /cores/ on macOS
 *
 * Usage:
 *   ./macos_crasher                  -- EXC_BAD_ACCESS (null deref)
 *   ./macos_crasher exc_crash        -- EXC_CRASH (abort)
 *   ./macos_crasher exc_arithmetic   -- EXC_ARITHMETIC (div by zero)
 *   ./macos_crasher exc_breakpoint   -- EXC_BREAKPOINT (__builtin_trap)
 *
 * Analyze:
 *   lldb --core /cores/core.<pid> --file ./macos_crasher
 *
 * Note: On macOS 10.15+, SIP may prevent core dumps. You can use
 *       `sudo sysctl kern.coredump=1` to enable them.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static volatile int sink;

static void crash_bad_access(void)
{
    printf("[*] Triggering EXC_BAD_ACCESS (null-pointer dereference)...\n");
    int *p = NULL;
    sink = *p;
}

static void crash_exc_crash(void)
{
    printf("[*] Triggering EXC_CRASH (abort)...\n");
    abort();
}

static void crash_exc_arithmetic(void)
{
    printf("[*] Triggering EXC_ARITHMETIC (division by zero)...\n");
    volatile int a = 42;
    volatile int b = 0;
    sink = a / b;
}

static void crash_exc_breakpoint(void)
{
    printf("[*] Triggering EXC_BREAKPOINT (__builtin_trap)...\n");
    __builtin_trap();
}

int main(int argc, char *argv[])
{
    const char *mode = (argc > 1) ? argv[1] : "exc_bad_access";

    printf("[*] Crashbot macOS test crasher — mode: %s (PID: %d)\n", mode, getpid());
    printf("[*] Core files will be in /cores/ (ensure: ulimit -c unlimited)\n\n");

    if (strcmp(mode, "exc_crash") == 0)
        crash_exc_crash();
    else if (strcmp(mode, "exc_arithmetic") == 0)
        crash_exc_arithmetic();
    else if (strcmp(mode, "exc_breakpoint") == 0)
        crash_exc_breakpoint();
    else
        crash_bad_access();

    return 0;
}
