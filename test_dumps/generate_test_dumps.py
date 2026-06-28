"""
Generate structurally valid crash dump files for testing Crashbot.

These files have correct magic bytes and realistic binary structure so they:
1. Pass validate_dump_content() header checks in crashes.py
2. Can be uploaded via the /crashes/upload endpoint
3. Have enough internal structure that parsers won't crash with cryptic errors
   (they'll fail gracefully since no real debugger output is available)

For REAL debuggable dumps, use the C programs in crashers/ or download from
the sources listed in DOWNLOAD_SOURCES.md.

Usage:
    python generate_test_dumps.py          # writes files to current directory
    python generate_test_dumps.py ./out    # writes to ./out/
"""

import struct
import os
import sys
from pathlib import Path


def write_file(directory: Path, name: str, data: bytes) -> Path:
    path = directory / name
    path.write_bytes(data)
    print(f"  {name:40s} {len(data):>8,} bytes  magic={data[:4].hex()}")
    return path


# ---------------------------------------------------------------------------
# Windows Minidump (.dmp)  —  magic: MDMP
# Spec: https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/
# ---------------------------------------------------------------------------
def generate_windows_minidump() -> bytes:
    """
    Minimal valid MINIDUMP_HEADER + stream directory.
    MDMP signature (4) + version (4) + number_of_streams (4) +
    stream_directory_rva (4) + checksum (4) + timestamp (4) + flags (8) = 32 bytes header.
    """
    MDMP_SIGNATURE = b'MDMP'
    MDMP_VERSION = 0xA793          # version 42899 (common in Win10+)
    MDMP_IMPL_VERSION = 0x0000     # implementation-specific

    num_streams = 3
    stream_dir_rva = 32  # immediately after header

    # Build header
    header = struct.pack('<4sHHIIII',
        MDMP_SIGNATURE,
        MDMP_VERSION,
        MDMP_IMPL_VERSION,
        num_streams,
        stream_dir_rva,
        0,                 # checksum (unused, always 0)
        0x66800000,        # timestamp (unix epoch, arbitrary)
    )
    header += struct.pack('<Q', 0x00000002)  # MiniDumpWithFullMemory flag

    # Stream directory entries: each is 12 bytes (type:4, size:4, rva:4)
    # We'll place 3 streams: SystemInfo, ExceptionStream, ThreadList
    stream_data_start = stream_dir_rva + num_streams * 12

    # Stream 1: SystemInfo (type=7)
    sysinfo_data = _build_sysinfo_stream()
    s1_rva = stream_data_start
    s1_entry = struct.pack('<III', 7, len(sysinfo_data), s1_rva)

    # Stream 2: ExceptionStream (type=6)
    exc_data = _build_exception_stream()
    s2_rva = s1_rva + len(sysinfo_data)
    s2_entry = struct.pack('<III', 6, len(exc_data), s2_rva)

    # Stream 3: ThreadListStream (type=3)
    thread_data = _build_thread_list_stream()
    s3_rva = s2_rva + len(exc_data)
    s3_entry = struct.pack('<III', 3, len(thread_data), s3_rva)

    return header + s1_entry + s2_entry + s3_entry + sysinfo_data + exc_data + thread_data


def _build_sysinfo_stream() -> bytes:
    """MINIDUMP_SYSTEM_INFO structure (truncated but structurally valid)."""
    return struct.pack('<HHBBHIHH32s',
        9,       # ProcessorArchitecture: PROCESSOR_ARCHITECTURE_AMD64
        6,       # ProcessorLevel (family 6 = modern Intel/AMD)
        0x5E,    # ProcessorRevision high
        0x03,    # ProcessorRevision low
        1,       # NumberOfProcessors
        0,       # ProductType (not used here)
        10,      # MajorVersion (Windows 10)
        0,       # MinorVersion
        b'Windows 10 Build 19045\x00' + b'\x00' * 9,  # CSDVersion (padded)
    )


def _build_exception_stream() -> bytes:
    """MINIDUMP_EXCEPTION_STREAM: thread ID + exception record."""
    thread_id = 0x00001A4C  # arbitrary thread ID
    exc_code = 0xC0000005   # ACCESS_VIOLATION
    exc_flags = 0
    exc_address = 0x00007FF6A1B23456
    num_params = 2
    params = [0, exc_address]  # read/write flag + address

    data = struct.pack('<I', thread_id)
    data += struct.pack('<I', 0)  # __alignment
    # MINIDUMP_EXCEPTION: code(4), flags(4), record(8), address(8), numparams(4), __unused(4)
    data += struct.pack('<IIQQII',
        exc_code, exc_flags, 0, exc_address, num_params, 0
    )
    # Parameters (up to 15, each 8 bytes)
    for p in params:
        data += struct.pack('<Q', p)
    # Pad remaining params (15 - num_params)
    data += b'\x00' * (8 * (15 - num_params))
    # MINIDUMP_LOCATION_DESCRIPTOR for thread context
    data += struct.pack('<II', 0, 0)  # size=0, rva=0 (no context blob)

    return data


def _build_thread_list_stream() -> bytes:
    """MINIDUMP_THREAD_LIST with one thread."""
    num_threads = 1
    data = struct.pack('<I', num_threads)
    # MINIDUMP_THREAD: id(4), suspendcount(4), priorityclass(4), priority(4),
    #                  teb(8), stack(MINIDUMP_MEMORY_DESCRIPTOR: start(8)+size(8)+rva(4)+datasize(4)),
    #                  context(MINIDUMP_LOCATION_DESCRIPTOR: size(4)+rva(4))
    data += struct.pack('<IIIIQQQIII',
        0x00001A4C,  # ThreadId
        0,           # SuspendCount
        8,           # PriorityClass
        0,           # Priority
        0x000000E9F0000000,  # Teb
        0x000000E9EFFF0000,  # Stack.StartOfMemoryRange
        0x10000,             # Stack.Memory.DataSize
        0,                   # Stack.Memory.Rva
        0,                   # ThreadContext.DataSize
        0,                   # ThreadContext.Rva
    )
    return data


# ---------------------------------------------------------------------------
# Windows Full Dump  —  magic: PAGEDUMP or DU64
# ---------------------------------------------------------------------------
def generate_windows_fulldump_pagedump() -> bytes:
    """PAGEDUMP signature for 32-bit full memory dump."""
    header = b'PAGEDUMP'
    header += struct.pack('<I', 0x0000000F)  # ValidDump signature
    header += struct.pack('<I', 6)            # MajorVersion
    header += struct.pack('<I', 1)            # MinorVersion (6.1 = Win7)
    header += struct.pack('<I', 0)            # DirectoryTableBase
    header += struct.pack('<I', 0)            # PfnDatabase
    header += struct.pack('<I', 0)            # PsLoadedModuleList
    header += struct.pack('<I', 0)            # PsActiveProcessHead
    header += struct.pack('<I', 0x014C)       # MachineImageType (x86)
    header += struct.pack('<I', 1)            # NumberProcessors
    header += struct.pack('<I', 0xC0000005)   # BugCheckCode (ACCESS_VIOLATION)
    header += struct.pack('<4I', 0, 0, 0, 0)  # BugCheckParameters[4]
    header += b'\x00' * (4096 - len(header))  # Pad to page size
    return header


def generate_windows_fulldump_du64() -> bytes:
    """DU64 signature for 64-bit full memory dump."""
    header = b'DU64'
    header += b'DUMP'  # secondary signature
    header += struct.pack('<I', 0x0000000F)  # ValidDump
    header += struct.pack('<I', 10)           # MajorVersion (Win10)
    header += struct.pack('<I', 0)            # MinorVersion
    header += struct.pack('<Q', 0)            # DirectoryTableBase
    header += struct.pack('<Q', 0)            # PfnDatabase
    header += struct.pack('<Q', 0)            # PsLoadedModuleList
    header += struct.pack('<Q', 0)            # PsActiveProcessHead
    header += struct.pack('<I', 0x8664)       # MachineImageType (AMD64)
    header += struct.pack('<I', 4)            # NumberProcessors
    header += struct.pack('<I', 0xC0000005)   # BugCheckCode
    header += struct.pack('<4Q', 0, 0, 0, 0)  # BugCheckParameters[4] (64-bit)
    header += b'\x00' * (4096 - len(header))
    return header


# ---------------------------------------------------------------------------
# Linux ELF Core Dump  —  magic: \x7fELF
# Spec: https://refspecs.linuxfoundation.org/elf/gabi4+/ch4.eheader.html
# ---------------------------------------------------------------------------
def generate_linux_core_64() -> bytes:
    """64-bit ELF core dump with realistic headers."""
    # ELF Header (64 bytes)
    e_ident = bytes([
        0x7F, 0x45, 0x4C, 0x46,  # magic: \x7fELF
        2,     # EI_CLASS: ELFCLASS64
        1,     # EI_DATA: ELFDATA2LSB (little-endian)
        1,     # EI_VERSION: EV_CURRENT
        0,     # EI_OSABI: ELFOSABI_NONE (System V)
        0, 0, 0, 0, 0, 0, 0, 0,  # EI_ABIVERSION + padding
    ])

    e_type = 4         # ET_CORE
    e_machine = 0x3E   # EM_X86_64
    e_version = 1
    e_entry = 0
    e_phoff = 64       # program header offset (right after ELF header)
    e_shoff = 0        # no section headers in core
    e_flags = 0
    e_ehsize = 64
    e_phentsize = 56   # size of one program header (Elf64_Phdr)
    e_phnum = 2        # 2 program headers: NOTE + LOAD
    e_shentsize = 0
    e_shnum = 0
    e_shstrndx = 0

    ehdr = e_ident + struct.pack('<HHIQQQIHHHHHH',
        e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
        e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx
    )

    # Program headers start at offset 64
    note_data = _build_elf_note_segment()
    load_data = b'\x00' * 4096  # simulated memory page

    # Data area starts after headers
    data_offset = e_phoff + e_phentsize * e_phnum

    # PT_NOTE (type=4): contains process/thread info
    pt_note = struct.pack('<IIQQQQQQ',
        4,           # p_type: PT_NOTE
        0,           # p_flags
        data_offset, # p_offset
        0,           # p_vaddr
        0,           # p_paddr
        len(note_data),  # p_filesz
        len(note_data),  # p_memsz
        4,           # p_align
    )

    # PT_LOAD (type=1): contains memory snapshot
    load_offset = data_offset + len(note_data)
    pt_load = struct.pack('<IIQQQQQQ',
        1,             # p_type: PT_LOAD
        5,             # p_flags: PF_R | PF_X
        load_offset,   # p_offset
        0x00400000,    # p_vaddr (typical executable base)
        0x00400000,    # p_paddr
        len(load_data),# p_filesz
        len(load_data),# p_memsz
        0x1000,        # p_align (page-aligned)
    )

    return ehdr + pt_note + pt_load + note_data + load_data


def _build_elf_note_segment() -> bytes:
    """Build NT_PRSTATUS and NT_PRPSINFO notes (simplified)."""
    notes = b''

    # NT_PRSTATUS (type=1): process status with registers
    prstatus_name = b'CORE\x00\x00\x00\x00'  # padded to 8 bytes
    prstatus_data = struct.pack('<i', 11)      # si_signo: SIGSEGV
    prstatus_data += struct.pack('<i', 0)      # si_code
    prstatus_data += struct.pack('<i', 0)      # si_errno
    prstatus_data += struct.pack('<H', 11)     # pr_cursig: SIGSEGV
    prstatus_data += b'\x00' * 2               # padding
    prstatus_data += struct.pack('<Q', 0)      # pr_sigpend
    prstatus_data += struct.pack('<Q', 0)      # pr_sighold
    prstatus_data += struct.pack('<i', 12345)  # pr_pid
    prstatus_data += struct.pack('<i', 12344)  # pr_ppid
    prstatus_data += struct.pack('<i', 1000)   # pr_pgrp
    prstatus_data += struct.pack('<i', 1000)   # pr_sid
    # timeval structs (user time, system time, etc.) — 4 x 16 bytes
    prstatus_data += b'\x00' * 64
    # General purpose registers (x86_64: 27 registers, each 8 bytes)
    prstatus_data += struct.pack('<27Q',
        0,                   # r15
        0,                   # r14
        0,                   # r13
        0,                   # r12
        0x00007FFF00000000,  # rbp
        0x00007FFF00001000,  # rbx
        0,                   # r11
        0,                   # r10
        0,                   # r9
        0,                   # r8
        0x00007FFF00002000,  # rax
        0,                   # rcx
        0,                   # rdx
        0,                   # rsi
        0,                   # rdi
        0xC0000005,          # orig_rax (syscall number)
        0x0000000000401234,  # rip (instruction pointer — faulting address)
        0x33,                # cs
        0x00010202,          # eflags
        0x00007FFF00003000,  # rsp
        0x2B,                # ss
        0, 0, 0, 0, 0, 0,   # fs_base, gs_base, ds, es, fs, gs
    )

    notes += _elf_note(b'CORE', 1, prstatus_data)

    # NT_PRPSINFO (type=3): process info
    prpsinfo_data = struct.pack('<b', 0)       # pr_state
    prpsinfo_data += b'R'                      # pr_sname
    prpsinfo_data += struct.pack('<b', 0)      # pr_zomb
    prpsinfo_data += struct.pack('<b', 0)      # pr_nice
    prpsinfo_data += b'\x00' * 4               # padding
    prpsinfo_data += struct.pack('<Q', 0)      # pr_flag
    prpsinfo_data += struct.pack('<II', 1000, 1000)  # pr_uid, pr_gid
    prpsinfo_data += struct.pack('<i', 12345)  # pr_pid
    prpsinfo_data += struct.pack('<i', 12344)  # pr_ppid
    prpsinfo_data += struct.pack('<i', 1000)   # pr_pgrp
    prpsinfo_data += struct.pack('<i', 1000)   # pr_sid
    prpsinfo_data += b'test_crash\x00' + b'\x00' * 5    # pr_fname (16 bytes)
    prpsinfo_data += b'./test_crash --arg1\x00' + b'\x00' * 60  # pr_psargs (80 bytes)

    notes += _elf_note(b'CORE', 3, prpsinfo_data)

    return notes


def _elf_note(name: bytes, n_type: int, desc: bytes) -> bytes:
    """Build a single ELF note entry with proper alignment."""
    # Pad name to 4-byte boundary
    name_padded = name + b'\x00'
    while len(name_padded) % 4:
        name_padded += b'\x00'

    # Pad desc to 4-byte boundary
    desc_padded = desc
    while len(desc_padded) % 4:
        desc_padded += b'\x00'

    header = struct.pack('<III', len(name) + 1, len(desc), n_type)
    return header + name_padded + desc_padded


def generate_linux_core_32() -> bytes:
    """32-bit ELF core dump."""
    e_ident = bytes([
        0x7F, 0x45, 0x4C, 0x46,  # magic
        1,     # ELFCLASS32
        1,     # ELFDATA2LSB
        1,     # EV_CURRENT
        0,     # ELFOSABI_NONE
        0, 0, 0, 0, 0, 0, 0, 0,
    ])

    e_phoff = 52  # 32-bit ELF header is 52 bytes
    e_phentsize = 32  # 32-bit Phdr

    ehdr = e_ident + struct.pack('<HHIIIIIHHHHHH',
        4,          # ET_CORE
        3,          # EM_386
        1,          # version
        0,          # entry
        e_phoff,    # phoff
        0,          # shoff
        0,          # flags
        52,         # ehsize
        e_phentsize,
        1,          # phnum (just one NOTE)
        0, 0, 0,
    )

    note_data = _elf_note(b'CORE', 1, struct.pack('<i', 11) + b'\x00' * 144)
    data_offset = e_phoff + e_phentsize

    pt_note = struct.pack('<IIIIIIII',
        4,            # PT_NOTE
        data_offset,  # offset
        0,            # vaddr
        0,            # paddr
        len(note_data),
        len(note_data),
        0,            # flags
        4,            # align
    )

    return ehdr + pt_note + note_data


# ---------------------------------------------------------------------------
# macOS Mach-O Core Dump  —  4 magic variants
# Spec: https://opensource.apple.com/source/xnu/xnu-7195.81.3/EXTERNAL_HEADERS/mach-o/loader.h
# ---------------------------------------------------------------------------
def generate_macos_core_64_be() -> bytes:
    """64-bit Mach-O, magic=\\xFE\\xED\\xFA\\xCF (MH_MAGIC_64, big-endian header)."""
    return _build_macho_core(b'\xFE\xED\xFA\xCF', '>', cputype=0x0100000C, cpusubtype=0x00000002, is_64=True)


def generate_macos_core_32_be() -> bytes:
    """32-bit Mach-O, magic=\\xFE\\xED\\xFA\\xCE (MH_MAGIC, big-endian header)."""
    return _build_macho_core(b'\xFE\xED\xFA\xCE', '>', cputype=18, cpusubtype=0, is_64=False)


def generate_macos_core_64_le() -> bytes:
    """64-bit reversed, magic=\\xCF\\xFA\\xED\\xFE (MH_CIGAM_64, little-endian header)."""
    return _build_macho_core(b'\xCF\xFA\xED\xFE', '<', cputype=0x01000007, cpusubtype=3, is_64=True)


def generate_macos_core_32_le() -> bytes:
    """32-bit reversed, magic=\\xCE\\xFA\\xED\\xFE (MH_CIGAM, little-endian header)."""
    return _build_macho_core(b'\xCE\xFA\xED\xFE', '<', cputype=7, cpusubtype=3, is_64=False)


def _build_macho_core(magic: bytes, endian: str, cputype: int, cpusubtype: int, is_64: bool) -> bytes:
    """Build a Mach-O core file with LC_THREAD and LC_SEGMENT commands."""
    MH_CORE = 0x4  # filetype: core dump

    # We'll have 2 load commands: LC_SEGMENT_64 + LC_THREAD
    num_cmds = 2

    # LC_THREAD command
    thread_cmd = _build_lc_thread(endian)

    header_size = 32 if is_64 else 28

    if is_64:
        seg_cmd_size = 72  # LC_SEGMENT_64 without sections
        seg_cmd = struct.pack(f'{endian}II16sQQQQIIII',
            0x19,          # LC_SEGMENT_64
            seg_cmd_size,
            b'__TEXT\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            0x100000000,   # vmaddr
            0x1000,        # vmsize
            0,             # fileoff (no data in this test file)
            0,             # filesize
            5,             # maxprot: VM_PROT_READ | VM_PROT_EXECUTE
            5,             # initprot
            0,             # nsects
            0,             # flags
        )
    else:
        seg_cmd_size = 56  # LC_SEGMENT
        seg_cmd = struct.pack(f'{endian}II16sIIIIIIII',
            0x1,           # LC_SEGMENT
            seg_cmd_size,
            b'__TEXT\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            0x1000,        # vmaddr
            0x1000,        # vmsize
            0,             # fileoff
            0,             # filesize
            5, 5,          # maxprot, initprot
            0,             # nsects
            0,             # flags
        )

    sizeofcmds = len(seg_cmd) + len(thread_cmd)

    rest = struct.pack(f'{endian}IIIIII',
        cputype, cpusubtype, MH_CORE, num_cmds, sizeofcmds, 0
    )
    if is_64:
        header = magic + rest + struct.pack(f'{endian}I', 0)  # reserved (64-bit)
    else:
        header = magic + rest

    return header + seg_cmd + thread_cmd


def _build_lc_thread(endian: str) -> bytes:
    """Build LC_THREAD load command with minimal register state."""
    LC_THREAD = 0x4

    # x86_64 thread state (flavor=4, count=42 uint32s = 168 bytes)
    flavor = 4
    count = 42
    regs = struct.pack(f'{endian}42I', *([0] * 42))

    cmd_size = 8 + 8 + len(regs)  # cmd(4) + cmdsize(4) + flavor(4) + count(4) + regs
    thread_cmd = struct.pack(f'{endian}II', LC_THREAD, cmd_size)
    thread_cmd += struct.pack(f'{endian}II', flavor, count)
    thread_cmd += regs

    return thread_cmd


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating test dump files in: {outdir}\n")
    print(f"  {'Filename':40s} {'Size':>10s}  Magic")
    print(f"  {'-'*40} {'-'*10}  {'-'*16}")

    # Windows
    write_file(outdir, "windows_minidump.dmp", generate_windows_minidump())
    write_file(outdir, "windows_fulldump_pagedump.dmp", generate_windows_fulldump_pagedump())
    write_file(outdir, "windows_fulldump_du64.dmp", generate_windows_fulldump_du64())

    # Linux
    write_file(outdir, "linux_core_x64.core", generate_linux_core_64())
    write_file(outdir, "linux_core_x86.core", generate_linux_core_32())

    # macOS (all 4 magic byte variants accepted by validate_dump_content)
    write_file(outdir, "macos_core_64_feedfacf.core", generate_macos_core_64_be())    # \xFE\xED\xFA\xCF
    write_file(outdir, "macos_core_32_feedface.core", generate_macos_core_32_be())    # \xFE\xED\xFA\xCE
    write_file(outdir, "macos_core_64_cffaedfe.core", generate_macos_core_64_le())    # \xCF\xFA\xED\xFE
    write_file(outdir, "macos_core_32_cefaedfe.core", generate_macos_core_32_le())    # \xCE\xFA\xED\xFE

    print(f"\nDone. {9} files generated.\n")
    print("To test uploads:")
    print("  curl -X POST http://localhost:8002/api/v1/crashes/upload \\")
    print("    -F 'file=@windows_minidump.dmp'")


if __name__ == "__main__":
    main()
