"""
Crash Analysis Model - Phase 1
Stores crash dump analysis results
"""
from sqlalchemy import Column, Integer, String, Text, JSON, Enum as SQLEnum, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from typing import Optional, List, Dict, Any

from app.db.base import Base, TimestampMixin


class AnalysisStatus(str, enum.Enum):
    """Analysis status enumeration"""
    QUEUED = "queued"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class CrashSeverity(str, enum.Enum):
    """Crash severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class CrashAnalysis(Base, TimestampMixin):
    """Crash analysis table"""
    __tablename__ = "crash_analyses"
    
    # Primary key
    id: Mapped[uuid.UUID] = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # File information
    filename: Mapped[str] = Column(String(255), nullable=False)
    file_size: Mapped[int] = Column(Integer, nullable=False)  # in bytes
    file_hash: Mapped[str] = Column(String(64), nullable=False, index=True)  # SHA256
    storage_path: Mapped[str] = Column(String(512), nullable=False)
    
    # Analysis status
    status: Mapped[AnalysisStatus] = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.QUEUED, nullable=False, index=True)
    error_message: Mapped[Optional[str]] = Column(Text, nullable=True)
    
    # Parsed data (Phase 1)
    exception_code: Mapped[Optional[str]] = Column(String(20), nullable=True, index=True)
    exception_message: Mapped[Optional[str]] = Column(Text, nullable=True)
    faulting_module: Mapped[Optional[str]] = Column(String(255), nullable=True, index=True)
    faulting_address: Mapped[Optional[str]] = Column(String(20), nullable=True)
    stack_trace: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # List of stack frames
    loaded_modules: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # List of modules
    threads: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # Thread information
    
    # LLM Analysis (Phase 2)
    root_cause: Mapped[Optional[str]] = Column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = Column(Text, nullable=True)
    solutions: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # List of solutions
    severity: Mapped[Optional[CrashSeverity]] = Column(SQLEnum(CrashSeverity), default=CrashSeverity.UNKNOWN, nullable=True, index=True)
    confidence_score: Mapped[Optional[float]] = Column(Float, nullable=True)  # 0-100
    references: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # URLs to documentation/forums
    llm_analysis: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # Full LLM analysis result
    llm_provider: Mapped[Optional[str]] = Column(String(50), nullable=True)  # openai, anthropic, etc.
    llm_model: Mapped[Optional[str]] = Column(String(100), nullable=True)  # gpt-4, claude-3, etc.
    llm_cost_usd: Mapped[Optional[float]] = Column(Float, nullable=True)  # Cost of LLM analysis
    completed_at: Mapped[Optional[float]] = Column(Float, nullable=True)  # Unix timestamp
    
    # RAG/Similar crashes (Phase 1.5)
    similar_crash_ids: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # List of similar crash UUIDs
    similar_crashes: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # Detailed similar crash info with similarity scores
    embedding_id: Mapped[Optional[str]] = Column(String(100), nullable=True)  # Vector DB reference
    
    # Metadata
    platform: Mapped[Optional[str]] = Column(String(50), nullable=True)  # Windows, Linux, etc.
    architecture: Mapped[Optional[str]] = Column(String(20), nullable=True)  # x64, x86, ARM
    os_version: Mapped[Optional[str]] = Column(String(100), nullable=True)
    
    # User/Session info
    user_id: Mapped[Optional[str]] = Column(String(100), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = Column(String(100), nullable=True, index=True)
    
    # Timing
    parse_duration_seconds: Mapped[Optional[float]] = Column(Float, nullable=True)
    analysis_duration_seconds: Mapped[Optional[float]] = Column(Float, nullable=True)
    
    # Phase 5: Advanced features
    tags: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # User-defined tags
    crash_category: Mapped[Optional[str]] = Column(String(50), nullable=True, index=True)  # ML classification
    related_issue_urls: Mapped[Optional[Any]] = Column(JSON, nullable=True)  # GitHub/JIRA links
    
    def __repr__(self):
        return f"<CrashAnalysis(id={self.id}, filename={self.filename}, status={self.status})>"
