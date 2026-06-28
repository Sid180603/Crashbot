"""
PHASE 1: Windows Crash Dump Parser
Uses WinDbg/CDB to extract crash information
"""
import subprocess
import re
import asyncio
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.db.models.crash import CrashAnalysis, AnalysisStatus
from app.llm.analyzer import analyze_with_llm
from app.llm.cache import get_cached_analysis, cache_analysis
from app.rag.vector_store import get_vector_store
from sqlalchemy import select

logger = get_logger(__name__)


# Custom Exceptions
class ParseError(Exception):
    """Raised when dump parsing fails"""
    pass


class DebuggerError(Exception):
    """Raised when debugger execution fails"""
    pass


class CorruptedDumpError(Exception):
    """Raised when dump file is corrupted or unreadable"""
    pass


class WinDbgParser:
    """Parser for Windows crash dumps using WinDbg/CDB"""
    
    def __init__(self, dump_path: str):
        self.dump_path = dump_path
        self.cdb_path = settings.WINDBG_PATH
        self.timeout = settings.DEBUGGER_TIMEOUT_SECONDS
        
    def _run_cdb_command(self, commands: List[str]) -> str:
        """Run CDB with given commands"""
        # Validate CDB exists
        if not Path(self.cdb_path).exists():
            raise DebuggerError(f"CDB not found at: {self.cdb_path}")
        
        # Validate dump file exists
        if not Path(self.dump_path).exists():
            raise CorruptedDumpError(f"Dump file not found: {self.dump_path}")
        
        # Build command line
        cmd_file_content = "\n".join(commands) + "\nq\n"
        
        # Create temporary command file
        cmd_file = Path(self.dump_path).parent / "cdb_commands.txt"
        try:
            with open(cmd_file, "w") as f:
                f.write(cmd_file_content)
        except IOError as e:
            raise ParseError(f"Failed to create command file: {e}")
        
        try:
            # Run CDB
            cmd = [
                self.cdb_path,
                "-z", self.dump_path,
                "-c", f"$$<{cmd_file}",
                "-lines"
            ]
            
            logger.info(f"Running CDB: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="ignore"
            )
            
            # Check for common error indicators in output
            if "Unable to open dump file" in result.stdout:
                raise CorruptedDumpError("CDB unable to open dump file - file may be corrupted")
            
            if "Invalid dump file" in result.stdout:
                raise CorruptedDumpError("Invalid dump file format")
            
            if result.returncode != 0 and not result.stdout:
                raise DebuggerError(f"CDB failed with return code {result.returncode}")
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            logger.error(f"CDB timeout after {self.timeout}s for {self.dump_path}")
            raise DebuggerError(f"CDB timeout after {self.timeout} seconds")
        except (DebuggerError, CorruptedDumpError):
            raise
        except Exception as e:
            logger.error(f"CDB execution failed: {e}", exc_info=True)
            raise DebuggerError(f"CDB execution failed: {str(e)}")
        finally:
            # Cleanup command file
            try:
                if cmd_file.exists():
                    cmd_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup command file: {e}")
    
    def parse(self) -> Dict[str, Any]:
        """Parse crash dump and extract information"""
        logger.info(f"Parsing crash dump: {self.dump_path}")
        
        # Run analysis commands
        commands = [
            ".sympath srv*" + settings.SYMBOL_CACHE_PATH + "*" + settings.MICROSOFT_SYMBOL_SERVER,
            ".reload",
            "!analyze -v",
            "~*kb",  # All thread stacks
            "lm",    # List modules
            ".ecxr", # Exception context
            "r",     # Registers
        ]
        
        output = self._run_cdb_command(commands)
        
        # Parse output
        parsed_data = {
            "exception_code": self._extract_exception_code(output),
            "exception_message": self._extract_exception_message(output),
            "faulting_module": self._extract_faulting_module(output),
            "faulting_address": self._extract_faulting_address(output),
            "stack_trace": self._extract_stack_trace(output),
            "loaded_modules": self._extract_modules(output),
            "threads": self._extract_threads(output),
            "platform": "Windows",
            "architecture": self._extract_architecture(output),
        }
        
        logger.info(f"Parsing complete. Exception: {parsed_data['exception_code']}")
        
        return parsed_data
    
    def _extract_exception_code(self, output: str) -> Optional[str]:
        """Extract exception code (e.g., 0xc0000005)"""
        match = re.search(r"ExceptionCode:\s*(0x[0-9a-fA-F]+)", output)
        if match:
            return match.group(1)
        
        match = re.search(r"Exception code:\s*(0x[0-9a-fA-F]+)", output)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_exception_message(self, output: str) -> Optional[str]:
        """Extract exception description"""
        # Common exception patterns
        patterns = [
            r"Exception name:\s*([^\n]+)",
            r"EXCEPTION_[A-Z_]+",
            r"ACCESS_VIOLATION",
            r"STACK_OVERFLOW",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_faulting_module(self, output: str) -> Optional[str]:
        """Extract the module that caused the crash"""
        match = re.search(r"Faulting module:\s*([^\s]+)", output, re.IGNORECASE)
        if match:
            return match.group(1)
        
        match = re.search(r"MODULE_NAME:\s*([^\s]+)", output)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_faulting_address(self, output: str) -> Optional[str]:
        """Extract faulting instruction address"""
        match = re.search(r"Faulting address:\s*(0x[0-9a-fA-F]+)", output, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_stack_trace(self, output: str) -> List[Dict[str, str]]:
        """Extract stack trace from current thread"""
        frames = []
        
        # Match stack frame pattern: # ChildEBP RetAddr  Args to Child
        pattern = r"^\s*([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([^\s!]+)!([^\s+]+)(\+0x[0-9a-f]+)?"
        
        for line in output.split("\n"):
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                frames.append({
                    "address": match.group(2),
                    "module": match.group(4),
                    "function": match.group(5),
                    "offset": match.group(6) if match.group(6) else "0x0"
                })
                
                if len(frames) >= settings.MAX_STACK_DEPTH:
                    break
        
        return frames
    
    def _extract_modules(self, output: str) -> List[Dict[str, str]]:
        """Extract loaded modules"""
        modules = []
        
        # Find module list section
        in_module_section = False
        for line in output.split("\n"):
            if "start" in line.lower() and "end" in line.lower() and "module name" in line.lower():
                in_module_section = True
                continue
            
            if in_module_section:
                # Parse module line: start_addr end_addr module_name
                match = re.match(r"([0-9a-f]+)\s+([0-9a-f]+)\s+(\S+)", line, re.IGNORECASE)
                if match:
                    modules.append({
                        "name": match.group(3),
                        "base_address": match.group(1),
                        "end_address": match.group(2)
                    })
        
        return modules[:100]  # Limit to first 100 modules
    
    def _extract_threads(self, output: str) -> List[Dict[str, Any]]:
        """Extract thread information"""
        threads = []
        
        # This is a simplified extraction
        # Full implementation would parse ~*kb output
        thread_pattern = r"^\s*\.?\s*(\d+)\s+Id:\s*([0-9a-f\.]+)\s+Suspend:\s*(\d+)"
        
        for line in output.split("\n"):
            match = re.match(thread_pattern, line, re.IGNORECASE)
            if match:
                threads.append({
                    "thread_id": int(match.group(1)),
                    "os_thread_id": match.group(2),
                    "suspended": int(match.group(3)) > 0
                })
        
        return threads
    
    def _extract_architecture(self, output: str) -> Optional[str]:
        """Extract architecture (x86, x64, ARM)"""
        if "x64" in output or "AMD64" in output:
            return "x64"
        elif "x86" in output or "i386" in output:
            return "x86"
        elif "ARM64" in output:
            return "ARM64"
        elif "ARM" in output:
            return "ARM"
        
        return None


async def analyze_crash_dump_async(crash_id: str, storage_path: str):
    """
    Background task to analyze crash dump
    Phase 1: Only parsing, Phase 2 will add LLM analysis
    """
    start_time = time.time()
    
    logger.info(f"Starting analysis for crash {crash_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Update status to PARSING
            result = await db.execute(
                select(CrashAnalysis).where(CrashAnalysis.id == crash_id)
            )
            crash = result.scalar_one()
            crash.status = AnalysisStatus.PARSING
            await db.commit()
            
            # Try universal parser first for multi-platform support
            try:
                from app.parsers.universal_parser import UniversalCrashParser
                logger.info(f"Using universal parser for crash {crash_id} (platform: {crash.platform})")
                
                universal_parser = UniversalCrashParser()
                crash_data_obj = await universal_parser.parse(storage_path)
                
                # Convert CrashData to dict format
                parsed_data = crash_data_obj.to_dict()
                
            except (ImportError, Exception) as e:
                # Fallback to Windows-only parser if universal parser fails
                logger.warning(f"Universal parser failed, falling back to WinDbg parser: {e}")
                parser = WinDbgParser(storage_path)
                parsed_data = await asyncio.get_running_loop().run_in_executor(
                    None, parser.parse
                )
            
            # Update database with parsed data
            crash.exception_code = parsed_data.get("exception_code")
            crash.exception_message = parsed_data.get("exception_message")
            crash.faulting_module = parsed_data.get("faulting_module")
            crash.faulting_address = parsed_data.get("faulting_address")
            crash.stack_trace = parsed_data.get("stack_trace")
            crash.loaded_modules = parsed_data.get("loaded_modules")
            crash.threads = parsed_data.get("threads")
            crash.platform = parsed_data.get("platform")
            crash.architecture = parsed_data.get("architecture")
            crash.parse_duration_seconds = time.time() - start_time
            
            # Update status to ANALYZING
            crash.status = AnalysisStatus.ANALYZING
            await db.commit()
            
            # Phase 1.5: Find similar crashes using RAG
            similar_crashes = []
            try:
                logger.info(f"Searching for similar crashes for {crash_id}")
                vector_store = get_vector_store()
                similar_results = await asyncio.get_running_loop().run_in_executor(
                    None, 
                    vector_store.find_similar_crashes,
                    parsed_data,
                    5,  # limit
                    0.7  # min_similarity
                )
                
                if similar_results:
                    logger.info(f"Found {len(similar_results)} similar crashes")
                    similar_crashes = [
                        {
                            "id": s["crash_id"],
                            "similarity": s["similarity"],
                            "snippet": s.get("snippet", "")
                        }
                        for s in similar_results
                    ]
                    crash.similar_crashes = similar_crashes
            except Exception as rag_error:
                logger.warning(f"RAG search failed for crash {crash_id}: {rag_error}")
                # Continue without similar crashes
            
            # Phase 2: LLM Analysis (enhanced with similar crashes context)
            llm_result = None  # Initialize to None to avoid unbound variable warning
            llm_analyzer = None  # Track analyzer instance for cost
            try:
                logger.info(f"Starting LLM analysis for crash {crash_id}")
                
                # Enhance crash data with similar crashes for better LLM analysis
                enhanced_data = parsed_data.copy()
                if similar_crashes:
                    enhanced_data["similar_crashes_context"] = similar_crashes
                
                # Check cache first
                cached_result = await get_cached_analysis(enhanced_data)
                if cached_result:
                    logger.info(f"Using cached LLM analysis for crash {crash_id}")
                    llm_result = cached_result
                    crash.llm_cost_usd = 0.0  # Cached result has no cost
                else:
                    # Use analyzer directly to get cost info
                    from app.llm.analyzer import LLMAnalyzer
                    llm_analyzer = LLMAnalyzer()
                    llm_result = await asyncio.get_running_loop().run_in_executor(
                        None, llm_analyzer.analyze_crash, enhanced_data
                    )
                    crash.llm_cost_usd = llm_analyzer.cost_usd if llm_analyzer else 0.0
                    
                    # Cache the result for future similar crashes
                    await cache_analysis(enhanced_data, llm_result, ttl=settings.REDIS_CACHE_TTL)
                
                # Store LLM analysis results
                crash.llm_analysis = {
                    "root_cause": llm_result.get("root_cause"),
                    "explanation": llm_result.get("explanation"),
                    "severity": llm_result.get("severity"),
                    "confidence": llm_result.get("confidence_score", 0) / 100.0,
                    "solutions": llm_result.get("solutions", []),
                    "references": llm_result.get("references", [])
                }
                crash.llm_provider = settings.LLM_PROVIDER
                crash.llm_model = settings.LLM_MODEL
                
                logger.info(f"LLM analysis complete for crash {crash_id} (cost: ${crash.llm_cost_usd:.4f})")
            except Exception as llm_error:
                logger.error(f"LLM analysis failed for crash {crash_id}: {llm_error}", exc_info=True)
                # Continue even if LLM fails - we have the parsed data
                llm_result = None  # Explicitly set to None on error
                crash.llm_analysis = {
                    "root_cause": "LLM analysis failed",
                    "explanation": str(llm_error),
                    "severity": "unknown",
                    "confidence": 0.0,
                    "solutions": [],
                    "references": []
                }
                crash.llm_cost_usd = llm_analyzer.cost_usd if llm_analyzer else 0.0
            
            crash.status = AnalysisStatus.COMPLETED
            crash.completed_at = datetime.now(timezone.utc)
            
            await db.commit()
            
            # Phase 1.5: Add this crash to vector store for future searches
            try:
                logger.info(f"Adding crash {crash_id} to vector store")
                vector_store = get_vector_store()
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    vector_store.add_crash_embedding,
                    crash_id,
                    {
                        "exception_code": crash.exception_code,
                        "exception_message": crash.exception_message,
                        "faulting_module": crash.faulting_module,
                        "stack_trace": parsed_data.get("stack_trace", []),
                        "platform": crash.platform,
                        "root_cause": llm_result.get("root_cause") if llm_result else None,
                        "solutions": llm_result.get("solutions") if llm_result else []
                    }
                )
                crash.embedding_id = crash_id
            except Exception as embedding_error:
                logger.warning(f"Failed to add embedding for crash {crash_id}: {embedding_error}")
                # Continue - embedding is optional
            
            await db.commit()
            
            logger.info(f"Analysis complete for crash {crash_id}")
            
        except (ParseError, DebuggerError, CorruptedDumpError) as e:
            # Known parsing errors - provide helpful messages
            logger.error(f"Parse error for crash {crash_id}: {type(e).__name__}: {e}")
            
            result = await db.execute(
                select(CrashAnalysis).where(CrashAnalysis.id == crash_id)
            )
            crash = result.scalar_one()
            crash.status = AnalysisStatus.FAILED
            crash.error_message = f"{type(e).__name__}: {str(e)}"
            await db.commit()
            
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error during analysis for crash {crash_id}: {e}", exc_info=True)
            
            # Update status to FAILED
            result = await db.execute(
                select(CrashAnalysis).where(CrashAnalysis.id == crash_id)
            )
            crash = result.scalar_one()
            crash.status = AnalysisStatus.FAILED
            crash.error_message = f"Unexpected error: {str(e)}"
            await db.commit()
