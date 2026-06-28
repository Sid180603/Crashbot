/*
 * Windows crash dump generator.
 * Compiles with MSVC or MinGW. Crashes intentionally to produce a .dmp file.
 *
 * Build (MSVC):
 *   cl /Zi windows_crasher.c /Fe:windows_crasher.exe
 *
 * Build (MinGW):
 *   gcc -g -o windows_crasher.exe windows_crasher.c -ldbghelp
 *
 * Usage:
 *   windows_crasher.exe                  -- null-pointer dereference
 *   windows_crasher.exe stackoverflow    -- stack overflow
 *   windows_crasher.exe divzero          -- division by zero
 *   windows_crasher.exe heapcorrupt      -- heap corruption
 *
 * The program writes a minidump to "crasher_output.dmp" before crashing
 * (using the unhandled-exception filter + MiniDumpWriteDump).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <dbghelp.h>
#pragma comment(lib, "dbghelp.lib")

static LONG WINAPI dump_and_crash(EXCEPTION_POINTERS *ep)
{
    HANDLE hFile = CreateFileA(
        "crasher_output.dmp",
        GENERIC_WRITE, 0, NULL,
        CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL
    );

    if (hFile != INVALID_HANDLE_VALUE) {
        MINIDUMP_EXCEPTION_INFORMATION mei;
        mei.ThreadId = GetCurrentThreadId();
        mei.ExceptionPointers = ep;
        mei.ClientPointers = FALSE;

        MiniDumpWriteDump(
            GetCurrentProcess(),
            GetCurrentProcessId(),
            hFile,
            MiniDumpWithFullMemory | MiniDumpWithThreadInfo,
            &mei, NULL, NULL
        );
        CloseHandle(hFile);
        printf("[+] Dump written to crasher_output.dmp\n");
    } else {
        printf("[-] Failed to create dump file (error %lu)\n", GetLastError());
    }

    return EXCEPTION_EXECUTE_HANDLER;
}
#endif

static volatile int sink;

static void crash_nullptr(void)
{
    printf("[*] Triggering null-pointer dereference...\n");
    int *p = NULL;
    sink = *p;
}

static void crash_stackoverflow(void)
{
    char buf[8192];
    memset(buf, 'A', sizeof(buf));
    sink = buf[0];
    crash_stackoverflow();
}

static void crash_divzero(void)
{
    printf("[*] Triggering division by zero...\n");
    volatile int a = 1;
    volatile int b = 0;
    sink = a / b;
}

static void crash_heapcorrupt(void)
{
    printf("[*] Triggering heap corruption...\n");
    char *p = (char *)malloc(16);
    memset(p, 'X', 16);
    free(p);
    free(p);  /* double free */
}

int main(int argc, char *argv[])
{
#ifdef _WIN32
    SetUnhandledExceptionFilter(dump_and_crash);
#endif

    const char *mode = (argc > 1) ? argv[1] : "nullptr";

    printf("[*] Crashbot test crasher — mode: %s\n", mode);

    if (strcmp(mode, "stackoverflow") == 0)
        crash_stackoverflow();
    else if (strcmp(mode, "divzero") == 0)
        crash_divzero();
    else if (strcmp(mode, "heapcorrupt") == 0)
        crash_heapcorrupt();
    else
        crash_nullptr();

    return 0;
}
