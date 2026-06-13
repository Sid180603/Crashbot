"""
macOS crash dump parser using LLDB.
Optimized for Python 3.12.10 with modern async patterns.
"""

import re
import asyncio
from pathlib import Path
from typing import Any

from .types import CrashData, DumpType, FilePath, ParserError, DebuggerNotFoundError, DebuggerTimeoutError, StackFrame, ModuleInfo
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MacOSCrashParser:
    """
    Parse macOS core dumps using LLDB.
    Uses Python 3.12 optimizations for better performance.
    """
    
    def __init__(self):
        self.lldb_path = getattr(settings, 'LLDB_PATH', '/usr/bin/lldb')
        self.timeout = getattr(settings, 'DEBUGGER_TIMEOUT_SECONDS', 120)
    
    async def parse(self, core_path: FilePath, executable_path: FilePath | None = None) -> CrashData:
        """
        Parse macOS core dump using LLDB.
        
        Args:
            core_path: Path to core dump file
            executable_path: Optional path to executable binary
            
        Returns:
            CrashData object with parsed information
            
        Raises:
            DebuggerNotFoundError: If LLDB is not installed
            DebuggerTimeoutError: If LLDB times out
            ParserError: If parsing fails
        """
        logger.info(f"Parsing macOS core dump: {core_path}")
        
        # Verify LLDB exists
        if not Path(self.lldb_path).exists():
            raise DebuggerNotFoundError(
                f"LLDB not found at: {self.lldb_path}. "
                "Install with: xcode-select --install"
            )
        
        # Build LLDB command
        cmd = [self.lldb_path, '--core', core_path]
        
        if executable_path:
            cmd.extend(['--file', executable_path])
        
        # LLDB commands to execute
        lldb_commands = [
            'bt all',               # Backtrace all threads
            'register read',        # CPU registers
            'thread list',          # Thread information
            'image list',           # Loaded libraries
            'target modules list',  # Module details
            'quit',
        ]
        
        for lldb_cmd in lldb_commands:
            cmd.extend(['--one-line', lldb_cmd])
        
        # Execute LLDB
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            output = stdout.decode('utf-8', errors='replace')
            
            if not output:
                raise ParserError("LLDB produced no output")
            
            return self._parse_lldb_output(output, core_path)
            
        except asyncio.TimeoutError:
            logger.error(f"LLDB timeout after {self.timeout}s")
            raise DebuggerTimeoutError(f"LLDB timeout after {self.timeout} seconds")
        except Exception as e:
            logger.error(f"LLDB execution failed: {e}", exc_info=True)
            raise ParserError(f"LLDB execution failed: {str(e)}")
    
    def _parse_lldb_output(self, output: str, core_path: FilePath) -> CrashData:
        """
        Extract structured data from LLDB output.
        Uses Python 3.12 f-string improvements for better error messages.
        """
        crash_data = CrashData(
            platform="macOS",
            dump_type=DumpType.MACOS_CORE
        )
        
        # Extract exception information (EXC_BAD_ACCESS, EXC_CRASH, etc.)
        exc_match = re.search(
            r'exception:\s+(EXC_\w+)\s+\((.*?)\)',
            output,
            re.IGNORECASE
        )
        if exc_match:
            crash_data.signal = exc_match.group(1)
            crash_data.exception_message = exc_match.group(2).strip()
            crash_data.exception_code = self._exception_to_code(exc_match.group(1))
            logger.info(f"Exception: {crash_data.signal} - {crash_data.exception_message}")
        
        # Extract stop reason
        stop_match = re.search(r'stop reason:\s+(.+)', output, re.IGNORECASE)
        if stop_match and not crash_data.exception_message:
            crash_data.exception_message = stop_match.group(1).strip()
        
        # Extract stack trace
        crash_data.stack_trace = self._extract_stack_trace(output)
        
        # Extract thread information
        crash_data.threads = self._extract_threads(output)
        crash_data.thread_count = len(crash_data.threads)
        
        # Extract loaded modules/frameworks
        crash_data.loaded_modules = self._extract_images(output)
        
        # Extract registers
        registers_section = re.search(
            r'General Purpose Registers:(.*?)(?:\n\n|\Z)',
            output,
            re.IGNORECASE | re.DOTALL
        )
        if registers_section:
            crash_data.registers = registers_section.group(1).strip()
        
        # Extract architecture
        if 'x86_64' in output:
            crash_data.architecture = 'x64'
        elif 'arm64' in output or 'aarch64' in output:
            crash_data.architecture = 'ARM64'
        elif 'i386' in output:
            crash_data.architecture = 'x86'
        
        return crash_data
    
    def _exception_to_code(self, exception_name: str) -> str:
        """
        Convert macOS exception to exception code.
        Using Python 3.12 match-case for cleaner code.
        """
        match exception_name.upper():
            case 'EXC_BAD_ACCESS':
                return '0xC0000005'  # Similar to Windows ACCESS_VIOLATION
            case 'EXC_BAD_INSTRUCTION':
                return '0xC000001D'  # Illegal instruction
            case 'EXC_ARITHMETIC':
                return '0xC0000094'  # Floating point exception
            case 'EXC_BREAKPOINT':
                return '0x80000003'  # Breakpoint
            case 'EXC_CRASH':
                return '0xC0000409'  # Fatal app exit
            case 'EXC_GUARD':
                return '0xC0000008'  # Guard exception
            case 'EXC_RESOURCE':
                return '0xC0000017'  # Resource limit
            case _:
                return '0x00000000'  # Unknown
    
    def _extract_stack_trace(self, output: str) -> list[StackFrame]:
        """Extract stack trace from LLDB output"""
        frames: list[StackFrame] = []
        
        # Pattern: * frame #0: 0x00007fff12345678 libsystem_c.dylib`function_name + 123
        pattern = r'[*\s]+frame #(\d+):\s+(0x[0-9a-f]+)\s+([^\s`]+)`?([^\s+]*)\s*\+?\s*(\d+)?'
        
        for line in output.split('\n'):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                frame_num = int(match.group(1))
                address = match.group(2)
                module = match.group(3)
                function = match.group(4) if match.group(4) else 'unknown'
                offset = match.group(5) if match.group(5) else '0'
                
                frames.append(StackFrame(
                    frame_number=frame_num,
                    function=function,
                    module=module,
                    offset=f"{address}+{offset}"
                ))
                
                if len(frames) >= getattr(settings, 'MAX_STACK_DEPTH', 50):
                    break
        
        return frames
    
    def _extract_threads(self, output: str) -> list[dict[str, Any]]:
        """Extract thread information from LLDB output"""
        threads = []
        
        # Pattern: * thread #1: tid = 0x12345, 0x00007fff12345678, name = 'com.apple.main-thread'
        pattern = r'[*\s]+thread #(\d+):\s+tid\s+=\s+(0x[0-9a-f]+).*?(?:name\s+=\s+[\'"](.*?)[\'"])?'
        
        for line in output.split('\n'):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                threads.append({
                    "thread_id": int(match.group(1)),
                    "tid": match.group(2),
                    "name": match.group(3) if match.group(3) else None,
                    "is_current": line.strip().startswith('*')
                })
        
        return threads
    
    def _extract_images(self, output: str) -> list[ModuleInfo]:
        """Extract loaded frameworks and dylibs"""
        images: list[ModuleInfo] = []
        
        # Pattern: [  0] 12345678-90ABCDEF-1234-5678 0x00007fff12345000 /System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation
        pattern = r'\[\s*\d+\]\s+[0-9A-Fa-f-]+\s+(0x[0-9a-f]+)\s+(.+\.(?:dylib|framework)[^\s]*)'
        
        for line in output.split('\n'):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                lib_path = match.group(2).strip()
                images.append(ModuleInfo(
                    name=Path(lib_path).name,
                    path=lib_path,
                    base_address=match.group(1),
                    size="0x0"  # LLDB doesn't always provide size
                ))
                
                if len(images) >= 100:  # Limit to first 100
                    break
        
        return images
