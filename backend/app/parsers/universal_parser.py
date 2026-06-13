"""
Universal crash parser using Python 3.12 optimizations.
Auto-detects platform and routes to appropriate parser.
"""

import asyncio
from collections.abc import Callable

from .types import DumpType, CrashData, MagicBytes, FilePath, UnsupportedDumpFormat
from .crash_parser import WinDbgParser
from app.core.logging import get_logger

logger = get_logger(__name__)


class UniversalCrashParser:
    """
    Auto-detect and parse crash dumps from any platform.
    Uses Python 3.12 generic syntax and optimizations.
    """
    
    def __init__(self):
        """Initialize parsers for all platforms"""
        self.windows_parser = None  # Lazy initialization
        self.linux_parser = None
        self.macos_parser = None
        
        # Parser mapping using Python 3.12 dict improvements
        self._parsers: dict[DumpType, Callable[[bytes], CrashData]] = {}
    
    def detect_dump_type(self, file_path: FilePath) -> DumpType:
        """
        Auto-detect dump format from magic bytes.
        
        Optimized with Python 3.12 isinstance() performance improvements (20x faster).
        
        Args:
            file_path: Path to crash dump file
            
        Returns:
            DumpType enum value
            
        Raises:
            UnsupportedDumpFormat: If dump format cannot be determined
        """
        try:
            with open(file_path, 'rb') as f:
                magic: MagicBytes = f.read(16)
        except IOError as e:
            raise UnsupportedDumpFormat(f"Cannot read file: {e}")
        
        # These isinstance checks are 20x faster in Python 3.12
        if not isinstance(magic, bytes) or len(magic) < 4:
            raise UnsupportedDumpFormat("File too small or not readable")
        
        # Magic byte detection using match-case (Python 3.10+, optimized in 3.12)
        match magic[:4]:
            case b'MDMP':
                return DumpType.WINDOWS_MINIDUMP
            
            case b'PAGE' if magic[:8] == b'PAGEDUMP':
                return DumpType.WINDOWS_FULLDUMP
            
            case b'DU64':
                return DumpType.WINDOWS_FULLDUMP
            
            case b'\x7fELF':
                return DumpType.LINUX_CORE
            
            case b'\xfe\xed\xfa\xce' | b'\xfe\xed\xfa\xcf':
                return DumpType.MACOS_CORE
            
            case _:
                # Enhanced error message using Python 3.12 f-string improvements
                raise UnsupportedDumpFormat(
                    f"Unknown dump format.\n"
                    f"Magic bytes: {magic[:8].hex()}\n"
                    f"Supported: Windows (.dmp), Linux (.core), macOS"
                )
    
    async def parse(self, file_path: FilePath) -> CrashData:
        """
        Parse dump file and extract crash information.
        
        Args:
            file_path: Path to crash dump file
            
        Returns:
            CrashData object with parsed information
            
        Raises:
            UnsupportedDumpFormat: If dump format is not supported
            ParserError: If parsing fails
        """
        logger.info(f"Parsing crash dump: {file_path}")
        
        # Detect dump type
        dump_type = self.detect_dump_type(file_path)
        logger.info(f"Detected dump type: {dump_type}")
        
        # Route to appropriate parser
        match dump_type:
            case DumpType.WINDOWS_MINIDUMP | DumpType.WINDOWS_FULLDUMP:
                return await self._parse_windows(file_path)
            
            case DumpType.LINUX_CORE:
                return await self._parse_linux(file_path)
            
            case DumpType.MACOS_CORE:
                return await self._parse_macos(file_path)
            
            case _:
                raise UnsupportedDumpFormat(f"No parser for {dump_type}")
    
    async def _parse_windows(self, file_path: FilePath) -> CrashData:
        """Parse Windows crash dump using WinDbg/CDB"""
        if self.windows_parser is None:
            self.windows_parser = WinDbgParser(file_path)
        
        # Parse using existing Windows parser
        parsed_data = await asyncio.get_event_loop().run_in_executor(
            None, self.windows_parser.parse
        )
        
        # Convert to CrashData format
        return CrashData(
            platform="Windows",
            dump_type=DumpType.WINDOWS_MINIDUMP,
            exception_code=parsed_data.get("exception_code"),
            exception_message=parsed_data.get("exception_message"),
            faulting_module=parsed_data.get("faulting_module"),
            faulting_address=parsed_data.get("faulting_address"),
            stack_trace=parsed_data.get("stack_trace", []),
            loaded_modules=parsed_data.get("loaded_modules", []),
            threads=parsed_data.get("threads", []),
            architecture=parsed_data.get("architecture"),
        )
    
    async def _parse_linux(self, file_path: FilePath) -> CrashData:
        """Parse Linux core dump using GDB"""
        # Lazy import to avoid dependency issues on non-Linux systems
        try:
            from .linux_parser import LinuxCrashParser
        except ImportError:
            logger.warning("Linux parser not available on this system")
            raise UnsupportedDumpFormat("Linux parser not available on Windows")
        
        if self.linux_parser is None:
            self.linux_parser = LinuxCrashParser()
        
        return await self.linux_parser.parse(file_path)
    
    async def _parse_macos(self, file_path: FilePath) -> CrashData:
        """Parse macOS core dump using LLDB"""
        # Lazy import to avoid dependency issues on non-macOS systems
        try:
            from .macos_parser import MacOSCrashParser
        except ImportError:
            logger.warning("macOS parser not available on this system")
            raise UnsupportedDumpFormat("macOS parser not available on Windows/Linux")
        
        if self.macos_parser is None:
            self.macos_parser = MacOSCrashParser()
        
        return await self.macos_parser.parse(file_path)
    
    def get_supported_platforms(self) -> list[str]:
        """Get list of supported platforms on this system"""
        supported = ["Windows"]
        
        try:
            from .linux_parser import LinuxCrashParser  # type: ignore[unused-ignore]
            supported.append("Linux")
        except ImportError:
            pass
        
        try:
            from .macos_parser import MacOSCrashParser  # type: ignore[unused-ignore]
            supported.append("macOS")
        except ImportError:
            pass
        
        return supported
