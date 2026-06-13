"""
Crash Severity Classification
ML-based severity scoring for crash prioritization.
Optimized for Python 3.12.10.
"""

from enum import IntEnum
from typing import Any
from collections.abc import Sequence

from app.core.logging import get_logger
from app.db.models.crash import CrashAnalysis, CrashSeverity

logger = get_logger(__name__)


class SeverityScore(IntEnum):
    """Numeric severity scores for ML classification"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    UNKNOWN = 1


# Python 3.12 type alias
type ExceptionMap = dict[str, SeverityScore]


class SeverityClassifier:
    """
    Classify crash severity using rule-based ML.
    Fast, deterministic classification without training data.
    """
    
    def __init__(self):
        """Initialize classifier with exception code mappings"""
        # Critical exceptions (immediate attention required)
        self.critical_exceptions: ExceptionMap = {
            '0xC0000005': SeverityScore.CRITICAL,  # ACCESS_VIOLATION
            '0xC0000374': SeverityScore.CRITICAL,  # HEAP_CORRUPTION
            '0xC0000409': SeverityScore.CRITICAL,  # STACK_BUFFER_OVERRUN
            '0xC000041D': SeverityScore.CRITICAL,  # FATAL_APP_EXIT
            '0xC0000602': SeverityScore.CRITICAL,  # FAIL_FAST_EXCEPTION
        }
        
        # High severity exceptions (security/stability issues)
        self.high_exceptions: ExceptionMap = {
            '0xC000001D': SeverityScore.HIGH,  # ILLEGAL_INSTRUCTION
            '0xC0000094': SeverityScore.HIGH,  # INTEGER_DIVIDE_BY_ZERO
            '0xC0000095': SeverityScore.HIGH,  # INTEGER_OVERFLOW
            '0xC0000096': SeverityScore.HIGH,  # PRIVILEGED_INSTRUCTION
            '0xC00000FD': SeverityScore.HIGH,  # STACK_OVERFLOW
            '0xC0000194': SeverityScore.HIGH,  # POSSIBLE_DEADLOCK
        }
        
        # Medium severity exceptions (functional issues)
        self.medium_exceptions: ExceptionMap = {
            '0x80000001': SeverityScore.MEDIUM,  # GUARD_PAGE_VIOLATION
            '0x80000003': SeverityScore.MEDIUM,  # BREAKPOINT
            '0xC0000008': SeverityScore.MEDIUM,  # INVALID_HANDLE
            '0xC000000D': SeverityScore.MEDIUM,  # INVALID_PARAMETER
            '0xC0000135': SeverityScore.MEDIUM,  # DLL_NOT_FOUND
        }
        
        # Linux/macOS signal mappings
        self.signal_severity = {
            'SIGSEGV': SeverityScore.CRITICAL,
            'SIGABRT': SeverityScore.HIGH,
            'SIGFPE': SeverityScore.HIGH,
            'SIGILL': SeverityScore.HIGH,
            'SIGBUS': SeverityScore.CRITICAL,
            'EXC_BAD_ACCESS': SeverityScore.CRITICAL,
            'EXC_CRASH': SeverityScore.CRITICAL,
        }
        
        # Security-related modules (increase severity)
        self.security_modules = [
            'kernel32.dll',
            'ntdll.dll',
            'secur32.dll',
            'crypt32.dll',
            'advapi32.dll',
        ]
    
    def classify(
        self,
        crash: CrashAnalysis
    ) -> tuple[CrashSeverity, float, str]:
        """
        Classify crash severity.
        
        Args:
            crash: CrashAnalysis object
            
        Returns:
            Tuple of (severity, confidence_score, explanation)
        """
        score = SeverityScore.UNKNOWN
        confidence = 0.5
        reasons = []
        
        # Check exception code
        exception_code = crash.exception_code
        if exception_code:
            # Python 3.12: match-case optimized
            match self._lookup_exception_severity(exception_code):
                case SeverityScore.CRITICAL:
                    score = SeverityScore.CRITICAL
                    confidence = 0.95
                    reasons.append(f"Critical exception: {exception_code}")
                
                case SeverityScore.HIGH:
                    score = SeverityScore.HIGH
                    confidence = 0.85
                    reasons.append(f"High-severity exception: {exception_code}")
                
                case SeverityScore.MEDIUM:
                    score = SeverityScore.MEDIUM
                    confidence = 0.75
                    reasons.append(f"Medium-severity exception: {exception_code}")
                
                case SeverityScore.LOW | SeverityScore.UNKNOWN:
                    # Low or unknown severity
                    pass
        
        # Check signal (Linux/macOS)
        if hasattr(crash, 'signal') and crash.platform in ['Linux', 'macOS']:
            signal_name = getattr(crash, 'signal', None)
            if signal_name and signal_name in self.signal_severity:
                signal_score = self.signal_severity[signal_name]
                if signal_score > score:
                    score = signal_score
                    confidence = 0.90
                    reasons.append(f"Fatal signal: {signal_name}")
        
        # Check module (security implications)
        if crash.faulting_module:
            module_lower = crash.faulting_module.lower()
            if any(sec_mod in module_lower for sec_mod in self.security_modules):
                if score < SeverityScore.HIGH:
                    score = SeverityScore.HIGH
                confidence = min(confidence + 0.1, 1.0)
                reasons.append(f"Security-critical module: {crash.faulting_module}")
        
        # Check for heap/memory corruption indicators in stack trace
        if crash.stack_trace:
            stack_str = str(crash.stack_trace).lower()
            if any(keyword in stack_str for keyword in ['heap', 'free', 'malloc', 'realloc']):
                if score < SeverityScore.HIGH:
                    score = SeverityScore.HIGH
                    reasons.append("Potential memory corruption")
        
        # Check for NULL pointer dereference
        if crash.faulting_address:
            try:
                addr_int = int(crash.faulting_address, 16)
                if addr_int < 0x10000:  # Low address = likely NULL deref
                    reasons.append("NULL pointer dereference")
                    confidence = min(confidence + 0.05, 1.0)
            except (ValueError, TypeError):
                pass
        
        # Convert score to severity enum
        severity = self._score_to_severity(score)
        
        # Build explanation
        explanation = "; ".join(reasons) if reasons else "Automated severity classification"
        
        logger.info(f"Classified crash {crash.id} as {severity.value} (confidence: {confidence:.2f})")
        
        return severity, confidence, explanation
    
    def classify_batch(
        self,
        crashes: Sequence[CrashAnalysis]
    ) -> list[dict[str, Any]]:
        """
        Classify multiple crashes.
        
        Args:
            crashes: List of CrashAnalysis objects
            
        Returns:
            List of classification results
        """
        # Python 3.12: List comprehensions are 2x faster
        results = [
            {
                "crash_id": str(crash.id),
                "severity": severity.value,
                "confidence": confidence,
                "explanation": explanation
            }
            for crash in crashes
            for severity, confidence, explanation in [self.classify(crash)]
        ]
        
        return results
    
    def _lookup_exception_severity(self, exception_code: str) -> SeverityScore:
        """Lookup exception code in severity maps"""
        # Normalize exception code
        code = exception_code.upper() if exception_code else ''
        
        if code in self.critical_exceptions:
            return self.critical_exceptions[code]
        elif code in self.high_exceptions:
            return self.high_exceptions[code]
        elif code in self.medium_exceptions:
            return self.medium_exceptions[code]
        else:
            return SeverityScore.UNKNOWN
    
    def _score_to_severity(self, score: SeverityScore) -> CrashSeverity:
        """Convert numeric score to CrashSeverity enum"""
        # Python 3.12: match-case pattern matching
        match score:
            case SeverityScore.CRITICAL:
                return CrashSeverity.CRITICAL
            case SeverityScore.HIGH:
                return CrashSeverity.HIGH
            case SeverityScore.MEDIUM:
                return CrashSeverity.MEDIUM
            case SeverityScore.LOW:
                return CrashSeverity.LOW
            case _:
                return CrashSeverity.UNKNOWN
    
    def get_severity_distribution(
        self,
        crashes: Sequence[CrashAnalysis]
    ) -> dict[str, int]:
        """
        Get severity distribution across crashes.
        
        Args:
            crashes: List of CrashAnalysis objects
            
        Returns:
            Dictionary with severity counts
        """
        distribution = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'unknown': 0
        }
        
        for crash in crashes:
            severity, _, _ = self.classify(crash)
            distribution[severity.value] += 1
        
        return distribution
