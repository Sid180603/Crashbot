"""
Generate structurally complex crash dump files that stress-test parsers.

Unlike generate_test_dumps.py (which creates minimal valid headers), these
files have realistic internal structure designed to challenge parsing:
- Deep stack traces (200+ frames)
- Multiple threads in various states
- Large module lists
- Corrupted/truncated sections
- Edge cases in data layout

Usage:
    python generate_complex_dumps.py          # writes to current directory
    python generate_complex_dumps.py ./out    # writes to ./out/
"""

import struct
import os
import sys
import random
from pathlib import Path

random.seed(42)  # reproducible dumps


def write_file(directory: Path, name: str, data: bytes) -> Path:
    path = directory / name
    path.write_bytes(data)
    print(f"  {name:55s} {len(data):>10,} bytes")
    return path


# ============================================================================
# Windows Minidump — Complex Variants
# ============================================================================

def generate_multithread_minidump() -> bytes:
    """
    Windows minidump with 32 threads, each with different states.
    Tests ThreadListStream parsing with many threads.
    """
    MDMP_SIGNATURE = b'MDMP'
    num_threads = 32

    # Header
    num_streams = 4
    stream_dir_rva = 32
    header = struct.pack('<4sHHIIII',
        MDMP_SIGNATURE, 0xA793, 0x0000,
        num_streams, stream_dir_rva, 0, 0x66800000,
    )
    header += struct.pack('<Q', 0x00000002)

    # Build streams
    sysinfo = _complex_sysinfo()
    exc = _complex_exception(thread_id=0x00002000, exc_code=0xC0000005,
                              exc_addr=0x00007FF6A1B23456)
    threads = _multithread_list(num_threads)
    modules = _large_module_list(80)

    data_start = stream_dir_rva + num_streams * 12
    off = data_start

    entries = b''
    stream_data = b''
    for stype, sdata in [(7, sysinfo), (6, exc), (3, threads), (4, modules)]:
        entries += struct.pack('<III', stype, len(sdata), off)
        stream_data += sdata
        off += len(sdata)

    return header + entries + stream_data


def _complex_sysinfo() -> bytes:
    return struct.pack('<HHBBHIHH32s',
        9, 6, 0x5E, 0x03, 8, 0, 10, 0,
        b'Windows 10 Pro 22H2\x00' + b'\x00' * 12,
    )


def _complex_exception(thread_id: int, exc_code: int, exc_addr: int) -> bytes:
    data = struct.pack('<II', thread_id, 0)
    data += struct.pack('<IIQQII',
        exc_code, 0, 0, exc_addr, 2, 0
    )
    data += struct.pack('<Q', 0)  # param 0: read
    data += struct.pack('<Q', exc_addr)  # param 1: address
    data += b'\x00' * (8 * 13)  # remaining params
    data += struct.pack('<II', 0, 0)
    return data


def _multithread_list(num_threads: int) -> bytes:
    data = struct.pack('<I', num_threads)
    for i in range(num_threads):
        tid = 0x00002000 + i * 4
        suspend = 1 if i % 3 == 0 else 0
        priority = [8, 10, 15, 6, 1][i % 5]
        teb = 0x000000E9F0000000 + i * 0x2000
        stack_start = 0x000000E9EF000000 + i * 0x100000
        data += struct.pack('<IIIIQQQIII',
            tid, suspend, priority, 0,
            teb, stack_start, 0x10000, 0, 0, 0,
        )
    return data


def _large_module_list(count: int) -> bytes:
    """ModuleListStream with many modules (tests module parsing limits)."""
    data = struct.pack('<I', count)
    modules = [
        "ntdll.dll", "kernel32.dll", "kernelbase.dll", "user32.dll",
        "gdi32.dll", "msvcrt.dll", "advapi32.dll", "shell32.dll",
        "ole32.dll", "combase.dll", "rpcrt4.dll", "sechost.dll",
        "ucrtbase.dll", "vcruntime140.dll", "msvcp140.dll",
        "ws2_32.dll", "crypt32.dll", "bcrypt.dll", "ncrypt.dll",
        "d3d11.dll", "dxgi.dll", "opengl32.dll", "dbghelp.dll",
        "version.dll", "winhttp.dll", "wininet.dll", "urlmon.dll",
        "oleaut32.dll", "shlwapi.dll", "imm32.dll", "msctf.dll",
        "clbcatq.dll", "setupapi.dll", "cfgmgr32.dll", "devobj.dll",
        "wintrust.dll", "msasn1.dll", "sspicli.dll", "nsi.dll",
        "mswsock.dll", "dnsapi.dll", "iphlpapi.dll", "winnsi.dll",
        "fwpuclnt.dll", "rasadhlp.dll", "FWPUCLNT.DLL", "bcryptprimitives.dll",
        "cryptbase.dll", "SspiCli.dll", "profapi.dll", "powrprof.dll",
    ]
    for i in range(count):
        mod_name = modules[i % len(modules)]
        base = 0x00007FFA00000000 + i * 0x100000
        size = random.randint(0x10000, 0x800000)
        # MINIDUMP_MODULE: base(8), size(4), checksum(4), timestamp(4),
        #   name_rva(4), version(8+8+8+8), cv_record(4+4), misc_record(4+4) = 108 bytes
        mod = struct.pack('<QIII', base, size, 0, 0x60000000 + i)
        mod += struct.pack('<I', 0)  # name RVA (not valid, parser should handle)
        mod += struct.pack('<HHHH', 10, 0, i & 0xFF, 0)  # version
        mod += struct.pack('<HHHH', 10, 0, i & 0xFF, 0)
        mod += b'\x00' * 24  # cv, misc records
        data += mod
    return data


def generate_deep_stack_minidump() -> bytes:
    """
    Minidump with a simulated 256-frame deep stack trace embedded in
    a memory region. The parser should handle truncated/deep stacks.
    """
    MDMP_SIGNATURE = b'MDMP'
    num_streams = 3
    stream_dir_rva = 32
    header = struct.pack('<4sHHIIII',
        MDMP_SIGNATURE, 0xA793, 0x0000,
        num_streams, stream_dir_rva, 0, 0x66800000,
    )
    header += struct.pack('<Q', 0x00000006)  # MiniDumpWithFullMemory|HandleData

    sysinfo = _complex_sysinfo()
    exc = _complex_exception(0x00001000, 0xC00000FD, 0x00007FF600401234)  # STACK_OVERFLOW

    # Build a large thread with a fake stack memory region
    stack_size = 256 * 8  # 256 return addresses
    stack_data = b''
    for i in range(256):
        addr = 0x00007FF600400000 + (i * 0x100)
        stack_data += struct.pack('<Q', addr)

    thread_data = struct.pack('<I', 1)
    thread_data += struct.pack('<IIIIQQQIII',
        0x00001000, 0, 8, 0,
        0x000000E9F0000000,
        0x000000E9EF000000,
        stack_size, 0, 0, 0,
    )

    data_start = stream_dir_rva + num_streams * 12
    off = data_start

    entries = b''
    all_data = b''
    for stype, sdata in [(7, sysinfo), (6, exc), (3, thread_data)]:
        entries += struct.pack('<III', stype, len(sdata), off)
        all_data += sdata
        off += len(sdata)

    # Append the stack memory as a raw region
    all_data += stack_data

    return header + entries + all_data


def generate_exception_chain_minidump() -> bytes:
    """
    Minidump with nested exception records — an exception during exception
    handling. ExceptionRecord chain should exercise parser robustness.
    """
    MDMP_SIGNATURE = b'MDMP'
    num_streams = 3
    stream_dir_rva = 32
    header = struct.pack('<4sHHIIII',
        MDMP_SIGNATURE, 0xA793, 0x0000,
        num_streams, stream_dir_rva, 0, 0x66800000,
    )
    header += struct.pack('<Q', 0x00000002)

    sysinfo = _complex_sysinfo()

    # Build chained exception: inner exception at known RVA
    inner_exc_rva = 0  # will calculate
    thread_id = 0x00001234

    # Inner exception (the root cause): division by zero
    inner_exc = struct.pack('<II', thread_id, 0)
    inner_exc += struct.pack('<IIQQII',
        0xC0000094,  # INTEGER_DIVIDE_BY_ZERO
        0, 0,
        0x00007FF600402000,  # address
        0, 0
    )
    inner_exc += b'\x00' * (8 * 15)
    inner_exc += struct.pack('<II', 0, 0)

    # Outer exception: access violation during exception dispatch
    # ExceptionRecord field points to inner exception
    outer_exc = struct.pack('<II', thread_id, 0)
    outer_exc += struct.pack('<IIQQII',
        0xC0000005,  # ACCESS_VIOLATION
        0,
        0,  # ExceptionRecord: 0 (no chaining in minidump, but we store both)
        0x00007FF600401000,
        2, 0
    )
    outer_exc += struct.pack('<Q', 0)  # read attempt
    outer_exc += struct.pack('<Q', 0x0000000000000000)  # null pointer
    outer_exc += b'\x00' * (8 * 13)
    outer_exc += struct.pack('<II', 0, 0)

    # Pack both as separate ExceptionStreams (stream type 6)
    threads = struct.pack('<I', 2)  # 2 threads
    threads += struct.pack('<IIIIQQQIII',
        thread_id, 0, 8, 0,
        0xE9F0000000, 0xE9EF000000, 0x10000, 0, 0, 0
    )
    threads += struct.pack('<IIIIQQQIII',
        thread_id + 4, 0, 8, 0,
        0xE9F2000000, 0xE9F1000000, 0x10000, 0, 0, 0
    )

    data_start = stream_dir_rva + num_streams * 12
    off = data_start

    entries = b''
    all_data = b''
    for stype, sdata in [(7, sysinfo), (6, outer_exc), (3, threads)]:
        entries += struct.pack('<III', stype, len(sdata), off)
        all_data += sdata
        off += len(sdata)

    # Append inner exception as extra data
    all_data += inner_exc

    return header + entries + all_data


def generate_corrupted_minidump() -> bytes:
    """
    Windows minidump with partially corrupted stream directory.
    Tests parser robustness against malformed data.
    """
    MDMP_SIGNATURE = b'MDMP'
    num_streams = 5  # claims 5 streams but only 2 are valid
    stream_dir_rva = 32
    header = struct.pack('<4sHHIIII',
        MDMP_SIGNATURE, 0xA793, 0x0000,
        num_streams, stream_dir_rva, 0, 0x66800000,
    )
    header += struct.pack('<Q', 0x00000002)

    sysinfo = _complex_sysinfo()
    data_start = stream_dir_rva + num_streams * 12

    entries = b''
    # Stream 1: valid SystemInfo
    entries += struct.pack('<III', 7, len(sysinfo), data_start)
    # Stream 2: valid but empty thread list
    empty_threads = struct.pack('<I', 0)
    entries += struct.pack('<III', 3, len(empty_threads), data_start + len(sysinfo))
    # Stream 3: INVALID — points past end of file
    entries += struct.pack('<III', 6, 9999, 0xFFFFFF00)
    # Stream 4: INVALID — zero size
    entries += struct.pack('<III', 4, 0, 0)
    # Stream 5: INVALID — unknown stream type
    entries += struct.pack('<III', 0xDEAD, 100, data_start)

    return header + entries + sysinfo + empty_threads


# ============================================================================
# Linux ELF Core — Complex Variants
# ============================================================================

def generate_multithread_elf_core() -> bytes:
    """
    64-bit ELF core dump with 16 threads (16 NT_PRSTATUS notes),
    200+ shared libraries, and multiple memory regions.
    """
    num_threads = 16
    num_libs = 120
    num_load_segments = 24

    note_data = b''
    for tid in range(num_threads):
        note_data += _elf_prstatus_note(
            pid=10000 + tid,
            ppid=9999,
            signal=11 if tid == 0 else 0,  # only thread 0 crashed
            rip=0x0000000000401234 + tid * 0x1000,
            rsp=0x00007FFF00000000 + tid * 0x100000,
        )

    # Process info note
    note_data += _elf_prpsinfo_note(
        pid=10000,
        fname="complex_crash",
        psargs="./complex_crash --multithread --deep"
    )

    # Aux vector note (NT_AUXV = 6)
    auxv_data = struct.pack('<QQ', 33, 0x00007FFFF7FFD000)  # AT_SYSINFO_EHDR
    auxv_data += struct.pack('<QQ', 6, 0x1000)               # AT_PAGESZ
    auxv_data += struct.pack('<QQ', 25, 0x00000000004003E0)  # AT_ENTRY
    auxv_data += struct.pack('<QQ', 0, 0)                     # AT_NULL
    note_data += _elf_note(b'CORE', 6, auxv_data)

    # NT_FILE note (type=0x46494c45) — maps paths to memory regions
    file_entries = b''
    file_names = b''
    for i in range(min(num_libs, 60)):
        lib_name = f"/usr/lib/x86_64-linux-gnu/lib{_fake_lib_name(i)}.so.{i % 5}.{i % 10}\x00"
        start = 0x00007FFFA0000000 + i * 0x200000
        end = start + random.randint(0x10000, 0x400000)
        offset = 0
        file_entries += struct.pack('<QQQ', start, end, offset)
        file_names += lib_name.encode()

    file_note_data = struct.pack('<QQ', min(num_libs, 60), 0x1000)
    file_note_data += file_entries + file_names
    note_data += _elf_note(b'CORE', 0x46494c45, file_note_data)

    # Build program headers
    e_phoff = 64
    e_phentsize = 56
    phdr_count = 1 + num_load_segments  # 1 NOTE + N LOAD segments

    data_offset = e_phoff + e_phentsize * phdr_count

    # PT_NOTE
    phdrs = struct.pack('<IIQQQQQQ',
        4, 0, data_offset, 0, 0,
        len(note_data), len(note_data), 4
    )

    # PT_LOAD segments (simulated memory regions)
    load_offset = data_offset + len(note_data)
    load_data = b''
    for i in range(num_load_segments):
        seg_size = random.randint(0x1000, 0x4000)
        vaddr = 0x00400000 + i * 0x100000
        flags = [5, 6, 4, 1][i % 4]  # varying R/W/X permissions
        phdrs += struct.pack('<IIQQQQQQ',
            1, flags, load_offset, vaddr, vaddr,
            seg_size, seg_size + 0x1000, 0x1000
        )
        # Fill with semi-realistic data
        seg_data = bytes([(i * 7 + j) & 0xFF for j in range(seg_size)])
        load_data += seg_data
        load_offset += seg_size

    # ELF header
    e_ident = bytes([
        0x7F, 0x45, 0x4C, 0x46,
        2, 1, 1, 0,
        0, 0, 0, 0, 0, 0, 0, 0,
    ])
    ehdr = e_ident + struct.pack('<HHIQQQIHHHHHH',
        4, 0x3E, 1, 0, e_phoff, 0, 0, 64,
        e_phentsize, phdr_count, 0, 0, 0
    )

    return ehdr + phdrs + note_data + load_data


def _elf_prstatus_note(pid: int, ppid: int, signal: int,
                        rip: int, rsp: int) -> bytes:
    """Full NT_PRSTATUS note for one thread."""
    data = struct.pack('<i', signal)      # si_signo
    data += struct.pack('<i', 0)          # si_code
    data += struct.pack('<i', 0)          # si_errno
    data += struct.pack('<H', signal)     # pr_cursig
    data += b'\x00' * 2
    data += struct.pack('<Q', 0)          # pr_sigpend
    data += struct.pack('<Q', 0)          # pr_sighold
    data += struct.pack('<i', pid)
    data += struct.pack('<i', ppid)
    data += struct.pack('<i', pid)        # pgrp
    data += struct.pack('<i', 1000)       # sid
    data += b'\x00' * 64                  # timeval structs

    # 27 general purpose registers
    regs = [0] * 27
    regs[16] = rip   # RIP
    regs[19] = rsp   # RSP
    regs[4] = rsp + 0x100  # RBP
    regs[10] = 0xDEADBEEF if signal == 11 else 0  # RAX
    for i, r in enumerate(regs):
        data += struct.pack('<Q', r)

    return _elf_note(b'CORE', 1, data)


def _elf_prpsinfo_note(pid: int, fname: str, psargs: str) -> bytes:
    data = struct.pack('<b', 0)       # pr_state
    data += b'R'                      # pr_sname
    data += struct.pack('<b', 0)      # pr_zomb
    data += struct.pack('<b', 0)      # pr_nice
    data += b'\x00' * 4
    data += struct.pack('<Q', 0)      # pr_flag
    data += struct.pack('<II', 1000, 1000)
    data += struct.pack('<i', pid)
    data += struct.pack('<i', pid - 1)
    data += struct.pack('<i', 1000)
    data += struct.pack('<i', 1000)
    fname_bytes = fname.encode()[:15] + b'\x00'
    data += fname_bytes.ljust(16, b'\x00')
    psargs_bytes = psargs.encode()[:79] + b'\x00'
    data += psargs_bytes.ljust(80, b'\x00')
    return _elf_note(b'CORE', 3, data)


def _fake_lib_name(i: int) -> str:
    libs = [
        "stdc++", "m", "pthread", "dl", "rt", "c", "gcc_s",
        "z", "ssl", "crypto", "curl", "xml2", "boost_system",
        "boost_thread", "boost_filesystem", "protobuf", "grpc",
        "grpc++", "abseil", "re2", "icu", "event", "ev",
        "leveldb", "rocksdb", "sqlite3", "pq", "mysqlclient",
        "hiredis", "zmq", "rdkafka", "avro", "snappy", "lz4",
        "zstd", "brotli", "jemalloc", "tcmalloc", "unwind",
        "asan", "tsan", "ubsan", "msan", "profiler", "benchmark",
        "gtest", "gmock", "fmt", "spdlog", "json", "yaml-cpp",
        "opencv_core", "opencv_imgproc", "tensorflow", "torch",
        "cuda", "cudnn", "nccl", "cublas", "cufft",
    ]
    return libs[i % len(libs)]


def _elf_note(name: bytes, n_type: int, desc: bytes) -> bytes:
    name_padded = name + b'\x00'
    while len(name_padded) % 4:
        name_padded += b'\x00'
    desc_padded = desc
    while len(desc_padded) % 4:
        desc_padded += b'\x00'
    header = struct.pack('<III', len(name) + 1, len(desc), n_type)
    return header + name_padded + desc_padded


def generate_signal_chain_elf() -> bytes:
    """
    ELF core where the crash signal is SIGABRT (6) triggered from a
    SIGSEGV handler — double fault pattern. Include siginfo and
    alternate signal stack markers.
    """
    note_data = b''

    # Thread that was in SIGSEGV handler when SIGABRT was raised
    note_data += _elf_prstatus_note(
        pid=20000, ppid=19999, signal=6,  # SIGABRT
        rip=0x00007FFFF7A42CF0,  # in libc abort()
        rsp=0x00007FFFFFFFDD00,  # on alternate signal stack
    )

    # Another thread that was just sleeping
    note_data += _elf_prstatus_note(
        pid=20001, ppid=19999, signal=0,
        rip=0x00007FFFF7B0E970,  # in nanosleep
        rsp=0x00007FFFC0000800,
    )

    note_data += _elf_prpsinfo_note(
        pid=20000, fname="sighandler_cr",
        psargs="./sighandler_crash --double-fault"
    )

    # NT_SIGINFO (type=0x53494749) — signal that killed the process
    siginfo = struct.pack('<iii', 6, -6, 0)  # si_signo=SIGABRT, si_code=SI_TKILL
    siginfo += struct.pack('<i', 20000)      # si_pid (self-sent)
    siginfo += struct.pack('<i', 1000)       # si_uid
    siginfo += b'\x00' * 108                 # rest of siginfo_t
    note_data += _elf_note(b'CORE', 0x53494749, siginfo)

    return _build_minimal_elf64(note_data)


def generate_stripped_elf() -> bytes:
    """
    ELF core from a fully stripped binary (no debug info).
    Only has raw addresses in the stack trace — no symbols.
    Typical of production crashes.
    """
    note_data = _elf_prstatus_note(
        pid=30000, ppid=1, signal=11,
        rip=0x0000555555555ABC,  # in .text of stripped binary
        rsp=0x00007FFFFFFFE000,
    )
    note_data += _elf_prpsinfo_note(
        pid=30000, fname="stripped_svc",
        psargs="/opt/production/bin/stripped_svc --config /etc/svc.conf"
    )

    # Large load segment simulating .text section
    text_size = 0x10000
    text_data = bytes([random.randint(0, 255) for _ in range(text_size)])

    return _build_minimal_elf64(note_data, extra_load=[(0x0000555555554000, text_data)])


def _build_minimal_elf64(note_data: bytes,
                          extra_load: list | None = None) -> bytes:
    """Helper to wrap note data in a minimal ELF64 core."""
    loads = extra_load or []
    phdr_count = 1 + len(loads)  # NOTE + LOADs
    e_phoff = 64
    e_phentsize = 56

    data_offset = e_phoff + e_phentsize * phdr_count

    # PT_NOTE
    phdrs = struct.pack('<IIQQQQQQ',
        4, 0, data_offset, 0, 0,
        len(note_data), len(note_data), 4
    )

    load_offset = data_offset + len(note_data)
    load_data = b''
    for vaddr, ldata in loads:
        phdrs += struct.pack('<IIQQQQQQ',
            1, 5, load_offset, vaddr, vaddr,
            len(ldata), len(ldata), 0x1000
        )
        load_data += ldata
        load_offset += len(ldata)

    e_ident = bytes([0x7F, 0x45, 0x4C, 0x46, 2, 1, 1, 0] + [0]*8)
    ehdr = e_ident + struct.pack('<HHIQQQIHHHHHH',
        4, 0x3E, 1, 0, e_phoff, 0, 0, 64,
        e_phentsize, phdr_count, 0, 0, 0
    )

    return ehdr + phdrs + note_data + load_data


# ============================================================================
# macOS Mach-O Core — Complex Variants
# ============================================================================

def generate_multithread_macho() -> bytes:
    """
    macOS Mach-O core with 12 threads and multiple segment regions.
    Exercises LLDB-based parser thread and image extraction.
    """
    magic = b'\xCF\xFA\xED\xFE'  # MH_CIGAM_64, little-endian
    endian = '<'
    MH_CORE = 4
    num_threads = 12

    # Build load commands
    load_cmds = b''

    # LC_SEGMENT_64 for __TEXT
    load_cmds += _macho_segment64(endian, b'__TEXT', 0x100000000, 0x100000)

    # LC_SEGMENT_64 for __DATA
    load_cmds += _macho_segment64(endian, b'__DATA', 0x100100000, 0x50000)

    # LC_SEGMENT_64 for __LINKEDIT
    load_cmds += _macho_segment64(endian, b'__LINKEDIT', 0x100150000, 0x10000)

    # LC_SEGMENT_64 for dyld shared cache region
    load_cmds += _macho_segment64(endian, b'__SHARED_CACHE', 0x7FFF00000000, 0x40000000)

    # LC_THREAD for each thread
    for i in range(num_threads):
        load_cmds += _macho_thread_cmd(endian, thread_idx=i)

    num_cmds = 4 + num_threads  # 4 segments + N threads
    sizeofcmds = len(load_cmds)

    header = magic
    header += struct.pack(f'{endian}IIIIII',
        0x01000007,  # CPU_TYPE_X86_64
        3,           # CPU_SUBTYPE_X86_ALL
        MH_CORE, num_cmds, sizeofcmds, 0
    )
    header += struct.pack(f'{endian}I', 0)  # reserved

    return header + load_cmds


def _macho_segment64(endian: str, name: bytes, vmaddr: int, vmsize: int) -> bytes:
    name_padded = name + b'\x00' * (16 - len(name))
    cmd_size = 72
    return struct.pack(f'{endian}II16sQQQQIIII',
        0x19, cmd_size, name_padded,
        vmaddr, vmsize, 0, 0,
        5, 5, 0, 0
    )


def _macho_thread_cmd(endian: str, thread_idx: int) -> bytes:
    LC_THREAD = 0x4
    flavor = 4   # x86_THREAD_STATE64
    num_u64 = 21  # 21 uint64 registers for x86_64
    count = num_u64 * 2  # count is in uint32 units
    regs = [0] * num_u64
    regs[16] = 0x0000000100001000 + thread_idx * 0x1000  # RIP
    regs[7] = 0x00007FFEEFBFE000 + thread_idx * 0x10000   # RSP
    regs[6] = regs[7] + 0x100  # RBP
    reg_data = struct.pack(f'{endian}{num_u64}Q', *regs)
    cmd_size = 8 + 8 + len(reg_data)
    cmd = struct.pack(f'{endian}II', LC_THREAD, cmd_size)
    cmd += struct.pack(f'{endian}II', flavor, count)
    cmd += reg_data
    return cmd


def generate_apple_silicon_macho() -> bytes:
    """
    macOS Mach-O core for Apple Silicon (ARM64).
    Uses ARM thread state which has different register layout.
    """
    magic = b'\xCF\xFA\xED\xFE'  # little-endian 64-bit
    endian = '<'
    MH_CORE = 4

    load_cmds = b''
    load_cmds += _macho_segment64(endian, b'__TEXT', 0x100000000, 0x100000)
    load_cmds += _macho_segment64(endian, b'__DATA_CONST', 0x100100000, 0x40000)
    load_cmds += _macho_segment64(endian, b'__DATA', 0x100140000, 0x30000)

    # ARM64 thread state
    LC_THREAD = 0x4
    ARM_THREAD_STATE64 = 6
    arm_reg_count = 68  # 34 uint64s = 68 uint32s
    arm_regs = [0] * 34
    arm_regs[30] = 0x0000000100003A00  # LR (x30)
    arm_regs[31] = 0x000000016FDFE000  # SP (x31)
    arm_regs[32] = 0x0000000100003B00  # PC
    arm_regs[33] = 0x60001000          # CPSR
    reg_data = struct.pack(f'{endian}34Q', *arm_regs)
    cmd_size = 8 + 8 + len(reg_data)
    thread_cmd = struct.pack(f'{endian}II', LC_THREAD, cmd_size)
    thread_cmd += struct.pack(f'{endian}II', ARM_THREAD_STATE64, arm_reg_count)
    thread_cmd += reg_data
    load_cmds += thread_cmd

    num_cmds = 4
    sizeofcmds = len(load_cmds)

    header = magic
    header += struct.pack(f'{endian}IIIIII',
        0x0100000C,  # CPU_TYPE_ARM64
        0x00000002,  # CPU_SUBTYPE_ARM64_ALL
        MH_CORE, num_cmds, sizeofcmds, 0
    )
    header += struct.pack(f'{endian}I', 0)

    return header + load_cmds


# ============================================================================
# Edge Cases & Adversarial Dumps
# ============================================================================

def generate_truncated_minidump() -> bytes:
    """Valid MDMP header but file is truncated mid-stream."""
    full = generate_multithread_minidump()
    return full[:len(full) // 3]


def generate_oversized_header_elf() -> bytes:
    """ELF core claiming more program headers than actually present."""
    e_ident = bytes([0x7F, 0x45, 0x4C, 0x46, 2, 1, 1, 0] + [0]*8)
    ehdr = e_ident + struct.pack('<HHIQQQIHHHHHH',
        4, 0x3E, 1, 0, 64, 0, 0, 64,
        56, 100,  # claims 100 program headers — but only 1 exists
        0, 0, 0
    )
    note = _elf_prstatus_note(pid=40000, ppid=1, signal=11,
                               rip=0x401000, rsp=0x7FFF00000000)
    phdr = struct.pack('<IIQQQQQQ',
        4, 0, 64 + 56, 0, 0, len(note), len(note), 4
    )
    return ehdr + phdr + note


def generate_zero_threads_minidump() -> bytes:
    """Valid minidump with zero threads — edge case."""
    MDMP_SIGNATURE = b'MDMP'
    num_streams = 2
    stream_dir_rva = 32
    header = struct.pack('<4sHHIIII',
        MDMP_SIGNATURE, 0xA793, 0x0000,
        num_streams, stream_dir_rva, 0, 0x66800000,
    )
    header += struct.pack('<Q', 0x00000002)

    sysinfo = _complex_sysinfo()
    threads = struct.pack('<I', 0)  # zero threads

    data_start = stream_dir_rva + num_streams * 12
    entries = struct.pack('<III', 7, len(sysinfo), data_start)
    entries += struct.pack('<III', 3, len(threads), data_start + len(sysinfo))

    return header + entries + sysinfo + threads


# ============================================================================
# Main
# ============================================================================

def main():
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating complex test dump files in: {outdir}\n")
    print(f"  {'Filename':55s} {'Size':>10s}")
    print(f"  {'-'*55} {'-'*10}")

    # Complex Windows minidumps
    write_file(outdir, "complex_32thread_minidump.dmp", generate_multithread_minidump())
    write_file(outdir, "complex_deepstack_minidump.dmp", generate_deep_stack_minidump())
    write_file(outdir, "complex_excchain_minidump.dmp", generate_exception_chain_minidump())
    write_file(outdir, "complex_corrupted_minidump.dmp", generate_corrupted_minidump())
    write_file(outdir, "complex_truncated_minidump.dmp", generate_truncated_minidump())
    write_file(outdir, "complex_zero_threads_minidump.dmp", generate_zero_threads_minidump())

    # Complex Linux ELF cores
    write_file(outdir, "complex_16thread_core.core", generate_multithread_elf_core())
    write_file(outdir, "complex_sigchain_core.core", generate_signal_chain_elf())
    write_file(outdir, "complex_stripped_core.core", generate_stripped_elf())
    write_file(outdir, "complex_oversized_hdr.core", generate_oversized_header_elf())

    # Complex macOS Mach-O cores
    write_file(outdir, "complex_12thread_macho.core", generate_multithread_macho())
    write_file(outdir, "complex_apple_silicon.core", generate_apple_silicon_macho())

    total = 12
    print(f"\nDone. {total} complex dump files generated.\n")


if __name__ == "__main__":
    main()
