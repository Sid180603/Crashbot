"""
PHASE 5: Batch Analysis
Analyze multiple crash dumps and find patterns
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from app.db.models.crash import CrashAnalysis
from app.core.logging import get_logger

logger = get_logger(__name__)


class BatchAnalyzer:
    """Analyze multiple crashes for patterns"""
    
    def __init__(self, crash_ids: List[str]):
        self.crash_ids = crash_ids
    
    async def analyze(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Analyze batch of crashes
        
        Returns:
            - Common patterns
            - Cluster information
            - Timeline analysis
            - Regression detection
        """
        logger.info(f"Starting batch analysis of {len(self.crash_ids)} crashes")
        
        # Load all crashes
        result = await db.execute(
            select(CrashAnalysis).where(CrashAnalysis.id.in_(self.crash_ids))
        )
        crashes = result.scalars().all()
        
        analysis = {
            "total_crashes": len(crashes),
            "common_exceptions": self._find_common_exceptions(crashes),
            "common_modules": self._find_common_modules(crashes),
            "timeline": self._analyze_timeline(crashes),
            "clusters": self._cluster_crashes(crashes),
            "regression_detected": self._detect_regressions(crashes)
        }
        
        return analysis
    
    def _find_common_exceptions(self, crashes: List[CrashAnalysis]) -> Dict[str, int]:
        """Find most common exception codes"""
        exceptions = {}
        for crash in crashes:
            if crash.exception_code:
                exceptions[crash.exception_code] = exceptions.get(crash.exception_code, 0) + 1
        
        return dict(sorted(exceptions.items(), key=lambda x: x[1], reverse=True))
    
    def _find_common_modules(self, crashes: List[CrashAnalysis]) -> Dict[str, int]:
        """Find most common faulting modules"""
        modules = {}
        for crash in crashes:
            if crash.faulting_module:
                modules[crash.faulting_module] = modules.get(crash.faulting_module, 0) + 1
        
        return dict(sorted(modules.items(), key=lambda x: x[1], reverse=True))
    
    def _analyze_timeline(self, crashes: List[CrashAnalysis]) -> List[Dict[str, Any]]:
        """Analyze crashes over time"""
        sorted_crashes = sorted(crashes, key=lambda x: x.created_at)
        
        return [
            {
                "timestamp": crash.created_at.isoformat(),
                "exception": crash.exception_code,
                "module": crash.faulting_module
            }
            for crash in sorted_crashes
        ]
    
    def _cluster_crashes(self, crashes: List[CrashAnalysis]) -> List[Dict[str, Any]]:
        """Cluster similar crashes together"""
        # Simplified clustering by exception code
        # Phase 5 will use ML clustering
        clusters = {}
        
        for crash in crashes:
            key = f"{crash.exception_code}_{crash.faulting_module}"
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(str(crash.id))
        
        return [
            {
                "pattern": key,
                "count": len(crash_ids),
                "crash_ids": crash_ids
            }
            for key, crash_ids in clusters.items()
        ]
    
    def _detect_regressions(self, crashes: List[CrashAnalysis]) -> bool:
        """Detect if crashes indicate a regression"""
        # Simple heuristic: if same crash pattern increases frequency
        # Phase 5 will use ML models
        
        if len(crashes) < 5:
            return False
        
        sorted_crashes = sorted(crashes, key=lambda x: x.created_at)
        recent = sorted_crashes[-5:]
        
        # Check if recent crashes have same pattern
        exception_codes = [c.exception_code for c in recent if c.exception_code]
        
        if len(set(exception_codes)) == 1 and len(exception_codes) >= 3:
            return True
        
        return False
