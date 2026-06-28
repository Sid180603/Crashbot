# Test Dump Files for Crashbot

**27 uploadable crash dumps** across all supported formats, plus 6 C crasher
programs for generating real debugger-parseable dumps on target platforms.

## Quick Start

```bash
# Generate all synthetic dumps (basic + complex)
python generate_test_dumps.py
python generate_complex_dumps.py

# Upload to the running backend
curl -X POST http://localhost:8002/api/v1/crashes/upload \
  -F "file=@windows_minidump.dmp"

# Upload a complex multi-threaded dump
curl -X POST http://localhost:8002/api/v1/crashes/upload \
  -F "file=@complex_32thread_minidump.dmp"

# Upload a real downloaded dump
curl -X POST http://localhost:8002/api/v1/crashes/upload \
  -F "file=@real_dumps/minidump2.dmp"
```

## Directory Layout

```
test_dumps/
├── *.dmp, *.core              ← 9 basic synthetic dumps
├── complex_*.dmp, *.core      ← 12 complex synthetic dumps (hard to parse)
├── real_dumps/                 ← Real dumps downloaded from GitHub
│   ├── minidump2.dmp          ← Real Windows minidump (Breakpad)
│   ├── test.dmp               ← Real Windows minidump (rust-minidump)
│   └── ...
├── crashers/                  ← C programs to generate real dumps
│   ├── windows_crasher.c      ← Basic Windows crash scenarios
│   ├── windows_complex_crasher.c ← Advanced: race conditions, VEH chains, etc.
│   ├── linux_crasher.c        ← Basic Linux crash scenarios
│   ├── linux_complex_crasher.c   ← Advanced: deadlocks, signal chains, etc.
│   ├── macos_crasher.c        ← Basic macOS crash scenarios
│   └── macos_complex_crasher.c   ← Advanced: dispatch queues, Mach exceptions, etc.
├── generate_test_dumps.py     ← Generate basic synthetic dumps
├── generate_complex_dumps.py  ← Generate complex synthetic dumps
└── README.md
```

---

## 1. Basic Synthetic Dumps (`generate_test_dumps.py`)

9 files with correct magic bytes and minimal valid structure.
Pass upload validation; fail gracefully at parser stage.

| File | Platform | Format |
|------|----------|--------|
| `windows_minidump.dmp` | Windows | MDMP with SystemInfo, Exception, ThreadList streams |
| `windows_fulldump_pagedump.dmp` | Windows | 32-bit PAGEDUMP header |
| `windows_fulldump_du64.dmp` | Windows | 64-bit DU64 header |
| `linux_core_x64.core` | Linux | 64-bit ELF core with NT_PRSTATUS + NT_PRPSINFO + PT_LOAD |
| `linux_core_x86.core` | Linux | 32-bit ELF core with NT_PRSTATUS |
| `macos_core_64_feedfacf.core` | macOS | MH_MAGIC_64 with LC_SEGMENT_64 + LC_THREAD |
| `macos_core_32_feedface.core` | macOS | MH_MAGIC with LC_SEGMENT + LC_THREAD |
| `macos_core_64_cffaedfe.core` | macOS | MH_CIGAM_64 (reversed byte order) |
| `macos_core_32_cefaedfe.core` | macOS | MH_CIGAM (reversed byte order) |

---

## 2. Complex Synthetic Dumps (`generate_complex_dumps.py`)

12 files designed to stress-test parsers with realistic edge cases.

### Windows (6 files)

| File | Challenge |
|------|-----------|
| `complex_32thread_minidump.dmp` | 32 threads in various states + 80 loaded modules |
| `complex_deepstack_minidump.dmp` | Stack overflow scenario with 256 return addresses |
| `complex_excchain_minidump.dmp` | Nested exception records (exception during exception handling) |
| `complex_corrupted_minidump.dmp` | Claims 5 streams but 3 are invalid (bad RVA, zero size, unknown type) |
| `complex_truncated_minidump.dmp` | Valid header but file truncated mid-stream |
| `complex_zero_threads_minidump.dmp` | Zero threads — edge case |

### Linux (4 files)

| File | Challenge |
|------|-----------|
| `complex_16thread_core.core` | 16 threads (247KB) + 120 shared libs + NT_FILE + NT_AUXV + 24 memory regions |
| `complex_sigchain_core.core` | SIGABRT from inside SIGSEGV handler (double fault) + NT_SIGINFO |
| `complex_stripped_core.core` | Stripped binary (no symbols) + 64KB .text data blob — production-realistic |
| `complex_oversized_hdr.core` | Claims 100 program headers but only has 1 |

### macOS (2 files)

| File | Challenge |
|------|-----------|
| `complex_12thread_macho.core` | 12 threads + 4 segment regions including dyld shared cache |
| `complex_apple_silicon.core` | ARM64 thread state (different register layout than x86_64) |

---

## 3. Downloaded Real Dumps (`real_dumps/`)

Real minidump files downloaded from open-source crash analysis tool repos.
These contain genuine crash data from actual programs.

| File | Source | Notes |
|------|--------|-------|
| `minidump2.dmp` | Google Breakpad | Real Windows minidump from Breakpad test suite |
| `test.dmp` | rust-minidump | Real Windows minidump |
| `linux-mini.dmp` | Breakpad | Windows-format minidump from Linux process |
| `invalid-parameter.dmp` | rust-minidump | Malformed — tests error handling |
| `invalid-range.dmp` | rust-minidump | Malformed — tests error handling |
| `invalid-record-count.dmp` | rust-minidump | Malformed — tests error handling |
| `microdump-arm.dmp` | Breakpad | Text-format Breakpad microdump (NOT binary — won't pass upload) |
| `microdump-arm64.dmp` | Breakpad | Text-format Breakpad microdump (NOT binary) |
| `microdump-x86.dmp` | Breakpad | Text-format Breakpad microdump (NOT binary) |

---

## 4. Crasher Programs (`crashers/`)

C programs that crash intentionally to produce **real, debugger-parseable** dumps.

### Basic Crashers

| File | Platform | Build | Crash Modes |
|------|----------|-------|-------------|
| `windows_crasher.c` | Windows | `cl /Zi windows_crasher.c /link dbghelp.lib` | NULL deref, stack overflow, div-by-zero, heap corruption |
| `linux_crasher.c` | Linux | `gcc -g -o linux_crasher linux_crasher.c -lpthread` | SIGSEGV, SIGABRT, SIGFPE, SIGBUS, multi-threaded |
| `macos_crasher.c` | macOS | `clang -g -o macos_crasher macos_crasher.c` | EXC_BAD_ACCESS, EXC_CRASH, EXC_ARITHMETIC, EXC_BREAKPOINT |

### Complex Crashers (production-realistic, hard to debug)

| File | Platform | Build | Crash Modes |
|------|----------|-------|-------------|
| `windows_complex_crasher.c` | Windows | `cl /Zi /Od windows_complex_crasher.c /link /DEBUG:FULL dbghelp.lib` | 6 modes: multi-thread race, mixed calling conventions, exception chains, corrupted stack frames, DLL callback crash, VEH chain with register corruption |
| `linux_complex_crasher.c` | Linux | `gcc -g -O0 -o lcc linux_complex_crasher.c -lpthread` | 8 modes: deadlock+crash, signal double fault, heap use-after-free, 250-deep function pointer dispatch, fork+shared memory corruption, stack buffer overflow, TLS crash, SIGABRT in atexit chain |
| `macos_complex_crasher.c` | macOS | `clang -g -O0 -o mcc macos_complex_crasher.c -lpthread` | 7 modes: ObjC-style dispatch table crash, GCD-style work queue crash, Mach exception port crash, guard page crash, dyld interposition chain, runloop crash, cleanup handler crash |

#### Generating Real Dumps

**Windows:**
```powershell
cl /Zi /Od windows_complex_crasher.c /link /DEBUG:FULL dbghelp.lib
.\windows_complex_crasher.exe 1    # mode 1: multi-thread race
# Output: crasher_output_*.dmp in current directory
```

**Linux:**
```bash
ulimit -c unlimited
echo "core.%e.%p" | sudo tee /proc/sys/kernel/core_pattern
gcc -g -O0 -o linux_complex_crasher linux_complex_crasher.c -lpthread
./linux_complex_crasher 2          # mode 2: signal double fault
# Output: core.linux_complex_crasher.<pid>
```

**macOS:**
```bash
ulimit -c unlimited
clang -g -O0 -o macos_complex_crasher macos_complex_crasher.c -lpthread
./macos_complex_crasher 4          # mode 4: guard page crash
# Output: /cores/core.<pid>
```

---

## Additional Download Sources

For more real dump files beyond what's in `real_dumps/`:

- **Google Breakpad** `src/processor/testdata/`: https://github.com/google/breakpad
- **rust-minidump** `testdata/`: https://github.com/rust-minidump/rust-minidump
- **pycrashreport** (macOS .ips/.crash text reports): https://github.com/doronz88/pycrashreport
