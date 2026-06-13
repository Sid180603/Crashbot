"""
API schemas for Phase 5 features.
Python 3.12 optimized with modern type hints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Any


# Batch Analysis Schemas
class BatchAnalysisRequest(BaseModel):
    """Request to analyze multiple crashes"""
    model_config = ConfigDict(from_attributes=True)
    
    crash_ids: list[str] = Field(
        ...,
        description="List of crash analysis UUIDs to analyze together",
        min_length=2
    )


class ClusterInfo(BaseModel):
    """Information about a crash cluster"""
    cluster_id: int
    crash_count: int
    crash_ids: list[str]
    pattern: str


class BatchAnalysisResponse(BaseModel):
    """Response from batch analysis"""
    model_config = ConfigDict(from_attributes=True)
    
    total_crashes: int
    common_exceptions: dict[str, int]
    common_modules: dict[str, int]
    clusters: list[ClusterInfo]
    regression_detected: bool
    timeline: list[dict[str, Any]]


# Crash Clustering Schemas
class SimilarCrashRequest(BaseModel):
    """Request to find similar crashes"""
    model_config = ConfigDict(from_attributes=True)
    
    crash_id: str = Field(..., description="Crash ID to find similarities for")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of results")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SimilarCrashResult(BaseModel):
    """A similar crash result"""
    crash_id: str
    similarity: float
    exception_code: str | None
    faulting_module: str | None
    platform: str | None


class SimilarCrashesResponse(BaseModel):
    """Response with similar crashes"""
    model_config = ConfigDict(from_attributes=True)
    
    crash_id: str
    similar_crashes: list[SimilarCrashResult]
    count: int


# Chat Schemas
class ChatMessage(BaseModel):
    """A chat message"""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: str | None = None


class ChatRequest(BaseModel):
    """Request to chat about a crash"""
    model_config = ConfigDict(from_attributes=True)
    
    question: str = Field(..., min_length=3, description="Question about the crash")


class ChatResponse(BaseModel):
    """Response from chatbot"""
    model_config = ConfigDict(from_attributes=True)
    
    answer: str
    conversation_history: list[ChatMessage]


# Integration Schemas
class SlackNotificationRequest(BaseModel):
    """Request to send Slack notification"""
    model_config = ConfigDict(from_attributes=True)
    
    crash_id: str
    channel: str | None = Field(None, description="Optional Slack channel override")


class JiraIssueRequest(BaseModel):
    """Request to create JIRA issue"""
    model_config = ConfigDict(from_attributes=True)
    
    crash_id: str
    project_key: str = Field(..., description="JIRA project key (e.g., 'CRASH')")
    issue_type: str = Field("Bug", description="JIRA issue type")
    priority: str | None = Field(None, description="Override auto-detected priority")


class JiraIssueResponse(BaseModel):
    """Response from JIRA issue creation"""
    issue_key: str
    issue_url: str
    created: bool


class GitHubIssueRequest(BaseModel):
    """Request to create GitHub issue"""
    model_config = ConfigDict(from_attributes=True)
    
    crash_id: str
    repository: str = Field(..., description="Repository (owner/repo)")
    labels: list[str] = Field(default_factory=list, description="Additional labels")


class GitHubIssueResponse(BaseModel):
    """Response from GitHub issue creation"""
    issue_number: int
    issue_url: str
    created: bool


class IntegrationResponse(BaseModel):
    """Generic integration response"""
    success: bool
    message: str
    details: dict[str, Any] | None = None


# Severity Classification Schemas
class SeverityClassificationRequest(BaseModel):
    """Request to classify crash severity"""
    model_config = ConfigDict(from_attributes=True)
    
    crash_ids: list[str] = Field(..., description="Crash IDs to classify")


class SeverityResult(BaseModel):
    """Severity classification result"""
    crash_id: str
    severity: str
    confidence: float
    explanation: str


class SeverityClassificationResponse(BaseModel):
    """Response with severity classifications"""
    model_config = ConfigDict(from_attributes=True)
    
    results: list[SeverityResult]
    distribution: dict[str, int]
