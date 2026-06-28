"""
Parser types using Python 3.12 syntax.
Optimized for Python 3.12.10 with modern type hints.
"""

from enum import StrEnum
from typing import Any
from dataclasses import dataclass, field


# Use StrEnum instead of str + Enum (better performance in 3.12)
class DumpType(StrEnum):
    """Crash dump types"""
    WINDOWS_MINIDUMP = "windows_minidump"
    WINDOWS_FULLDUMP = "windows_fulldump"
    LINUX_CORE = "linux_core"
    MACOS_CORE = "macos_core"


class Platform(StrEnum):
    """Supported platforms"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"


# Python 3.12 type aliases (PEP 695)
type MagicBytes = bytes
type FilePath = str
type ExceptionCode = str


@dataclass
class StackFrame:
    """Stack frame information"""
    frame_number: int
    function: str
    module: str
    offset: str
    source_line: str | None = None


@dataclass
class ModuleInfo:
    """Loaded module/library information"""
    name: str
    path: str
    base_address: str
    size: str


@dataclass
class CrashData:
    """
    Structured crash dump data using Python 3.12 features.
    Uses dataclass for clean initialization and type safety.
    """
    
    # Required fields
    platform: str
    dump_type: DumpType
    
    # Optional fields with defaults
    signal: str | None = None
    exception_code: ExceptionCode | None = None
    exception_message: str | None = None
    exception_address: str | None = None
    faulting_module: str | None = None
    faulting_function: str | None = None
    faulting_address: str | None = None
    
    # Stack and thread info
    stack_trace: list[StackFrame] = field(default_factory=list)
    threads: list[dict[str, Any]] = field(default_factory=list)
    loaded_modules: list[ModuleInfo] = field(default_factory=list)
    
    # System info
    thread_count: int = 0
    architecture: str | None = None
    os_version: str | None = None
    registers: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage"""
        import dataclasses
        return {
            "platform": self.platform,
            "dump_type": self.dump_type.value,
            "exception_code": self.exception_code,
            "exception_message": self.exception_message,
            "faulting_module": self.faulting_module,
            "faulting_function": self.faulting_function,
            "faulting_address": self.faulting_address,
            "stack_trace": [dataclasses.asdict(f) for f in self.stack_trace],
            "loaded_modules": [dataclasses.asdict(m) for m in self.loaded_modules],
            "threads": self.threads,
            "architecture": self.architecture,
        }


class UnsupportedDumpFormat(Exception):
    """Raised when dump format cannot be determined."""
    pass


class ParserError(Exception):
    """Base exception for parser errors."""
    pass


class DebuggerNotFoundError(ParserError):
    """Raised when debugger executable is not found."""
    pass


class DebuggerTimeoutError(ParserError):
    """Raised when debugger execution times out."""
    pass
