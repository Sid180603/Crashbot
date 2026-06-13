"""
Pydantic schemas for crash analysis - Phase 1
"""
from pydantic import BaseModel, UUID4, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.db.models.crash import AnalysisStatus, CrashSeverity


class CrashAnalysisBase(BaseModel):
    """Base schema for crash analysis"""
    filename: str
    

class CrashAnalysisCreate(CrashAnalysisBase):
    """Schema for creating crash analysis"""
    pass


class CrashAnalysisResponse(CrashAnalysisBase):
    """Schema for crash analysis response"""
    id: UUID4
    status: AnalysisStatus
    message: Optional[str] = None
    
    class Config:
        from_attributes = True


class StackFrame(BaseModel):
    """Stack frame schema"""
    index: int
    module: Optional[str] = None
    function: Optional[str] = None
    address: Optional[str] = None
    offset: Optional[str] = None
    source_file: Optional[str] = None
    line_number: Optional[int] = None


class ThreadInfo(BaseModel):
    """Thread information schema"""
    thread_id: int
    is_current: bool = False
    stack_frames: List[StackFrame] = []


class ModuleInfo(BaseModel):
    """Module information schema"""
    name: str
    base_address: Optional[str] = None
    size: Optional[int] = None
    version: Optional[str] = None
    path: Optional[str] = None


class CrashAnalysisDetail(CrashAnalysisBase):
    """Detailed crash analysis schema"""
    id: UUID4
    file_size: int
    file_hash: str
    status: AnalysisStatus
    error_message: Optional[str] = None
    
    # Parsed data
    exception_code: Optional[str] = None
    exception_message: Optional[str] = None
    faulting_module: Optional[str] = None
    faulting_address: Optional[str] = None
    stack_trace: Optional[List[Dict[str, Any]]] = None
    loaded_modules: Optional[List[Dict[str, Any]]] = None
    threads: Optional[List[Dict[str, Any]]] = None
    
    # LLM analysis (Phase 2)
    root_cause: Optional[str] = None
    explanation: Optional[str] = None
    solutions: Optional[List[str]] = None
    severity: Optional[CrashSeverity] = None
    confidence_score: Optional[float] = None
    references: Optional[List[str]] = None
    
    # Similar crashes (Phase 1.5)
    similar_crash_ids: Optional[List[str]] = None
    
    # Metadata
    platform: Optional[str] = None
    architecture: Optional[str] = None
    os_version: Optional[str] = None
    
    # Timing
    parse_duration_seconds: Optional[float] = None
    analysis_duration_seconds: Optional[float] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SolutionItem(BaseModel):
    """Solution schema (Phase 2)"""
    title: str
    description: str
    priority: int = Field(..., ge=1, le=5)
    code_example: Optional[str] = None
    references: Optional[List[str]] = None
