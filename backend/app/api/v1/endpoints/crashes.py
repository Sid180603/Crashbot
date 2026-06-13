"""
PHASE 1: Crash Analysis API Endpoints
File upload, status check, result retrieval
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import hashlib
import os
from datetime import datetime

from app.db.session import get_db
from app.db.models.crash import CrashAnalysis, AnalysisStatus
from app.core.config import settings
from app.core.logging import get_logger
from app.api.v1.schemas.crash import (
    CrashAnalysisResponse,
    CrashAnalysisCreate,
    CrashAnalysisDetail
)
from app.api.v1.schemas.batch import (
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    SimilarCrashRequest,
    SimilarCrashesResponse,
    SimilarCrashResult,
    ChatRequest,
    ChatResponse,
    SlackNotificationRequest,
    JiraIssueRequest,
    JiraIssueResponse,
    GitHubIssueRequest,
    GitHubIssueResponse,
    IntegrationResponse,
    SeverityClassificationRequest,
    SeverityClassificationResponse
)
from app.parsers.crash_parser import analyze_crash_dump_async
from app.ml.batch_analysis import BatchAnalyzer
from app.ml.crash_clustering import CrashClusterer
from app.ml.severity_classifier import SeverityClassifier
from app.ml.chat import CrashChatbot
from app.ml.integrations import SlackNotifier, JiraIntegration, GitHubIntegration
from sqlalchemy import select

logger = get_logger(__name__)
router = APIRouter(prefix="/crashes", tags=["crashes"])


def validate_dump_file(file: UploadFile) -> None:
    """Validate uploaded crash dump file"""
    # Check file extension
    allowed_extensions = [".dmp", ".dump", ".core"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check filename for suspicious patterns
    if ".." in file.filename or "/" in file.filename or "\\" in file.filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: contains path traversal characters"
        )


def validate_dump_content(content: bytes) -> str:
    """
    Validate dump file content by checking magic bytes.
    Returns the detected platform.
    """
    if len(content) < 4:
        raise HTTPException(
            status_code=400,
            detail="File too small to be a valid crash dump"
        )
    
    # Check for Windows Minidump magic bytes (MDMP)
    if content[:4] == b'MDMP':
        return "Windows"
    
    # Check for Windows full dump
    if content[:8] == b'PAGEDUMP' or content[:4] == b'DU64':
        return "Windows"
    
    # Check for ELF core dump magic bytes (0x7F 'ELF')
    if content[:4] == b'\x7FELF':
        return "Linux"
    
    # Check for Mach-O core dump (0xFEEDFACE or 0xFEEDFACF)
    if content[:4] in [b'\xFE\xED\xFA\xCE', b'\xFE\xED\xFA\xCF']:
        return "macOS"
    
    # Check for Mach-O 64-bit reversed
    if content[:4] in [b'\xCF\xFA\xED\xFE', b'\xCE\xFA\xED\xFE']:
        return "macOS"
    
    raise HTTPException(
        status_code=400,
        detail=(
            f"Not a valid crash dump file. "
            f"Magic bytes: {content[:8].hex()}. "
            f"Supported: Windows (.dmp), Linux (.core), macOS"
        )
    )


def calculate_file_hash(content: bytes) -> str:
    """Calculate SHA256 hash of file content"""
    return hashlib.sha256(content).hexdigest()


@router.post("/upload", response_model=CrashAnalysisResponse, status_code=201)
async def upload_crash_dump(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a crash dump file for analysis
    
    - **file**: Crash dump file (.dmp, .dump, .core)
    
    Returns the analysis ID and status
    """
    logger.info(f"Receiving crash dump upload: {file.filename}")
    
    # Validate file extension
    validate_dump_file(file)
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Check file size
    max_size_bytes = settings.MAX_DUMP_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_DUMP_SIZE_MB}MB"
        )
    
    # Validate file content (magic bytes) and detect platform
    detected_platform = validate_dump_content(content)
    
    # Calculate file hash
    file_hash = calculate_file_hash(content)
    
    # Check for duplicate
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.file_hash == file_hash)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        logger.info(f"Duplicate file detected: {file_hash}")
        return CrashAnalysisResponse(
            id=existing.id,
            filename=existing.filename,
            status=existing.status,
            message="File already analyzed"
        )
    
    # Save file to storage
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    storage_path = os.path.join(settings.DUMP_STORAGE_PATH, safe_filename)
    
    with open(storage_path, "wb") as f:
        f.write(content)
    
    logger.info(f"File saved to: {storage_path}")
    
    # Create database record
    crash_analysis = CrashAnalysis(
        filename=file.filename,
        file_size=file_size,
        file_hash=file_hash,
        storage_path=storage_path,
        platform=detected_platform,
        status=AnalysisStatus.QUEUED
    )
    
    db.add(crash_analysis)
    await db.commit()
    await db.refresh(crash_analysis)
    
    # Start background analysis
    background_tasks.add_task(
        analyze_crash_dump_async,
        crash_id=str(crash_analysis.id),
        storage_path=storage_path
    )
    
    logger.info(f"Analysis queued: {crash_analysis.id}")
    
    return CrashAnalysisResponse(
        id=crash_analysis.id,
        filename=crash_analysis.filename,
        status=crash_analysis.status,
        message="Analysis started"
    )


@router.get("/{crash_id}", response_model=CrashAnalysisDetail)
async def get_crash_analysis(
    crash_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get crash analysis by ID
    
    - **crash_id**: UUID of the crash analysis
    """
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.id == crash_id)
    )
    crash = result.scalar_one_or_none()
    
    if not crash:
        raise HTTPException(status_code=404, detail="Crash analysis not found")
    
    return crash


@router.get("/", response_model=List[CrashAnalysisResponse])
async def list_crash_analyses(
    skip: int = 0,
    limit: int = 50,
    status: AnalysisStatus = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all crash analyses
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by analysis status
    """
    query = select(CrashAnalysis).offset(skip).limit(limit)
    
    if status:
        query = query.where(CrashAnalysis.status == status)
    
    query = query.order_by(CrashAnalysis.created_at.desc())
    
    result = await db.execute(query)
    crashes = result.scalars().all()
    
    return crashes


@router.delete("/{crash_id}", status_code=204)
async def delete_crash_analysis(
    crash_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a crash analysis and its associated file
    
    - **crash_id**: UUID of the crash analysis
    """
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.id == crash_id)
    )
    crash = result.scalar_one_or_none()
    
    if not crash:
        raise HTTPException(status_code=404, detail="Crash analysis not found")
    
    # Delete file from storage
    if os.path.exists(crash.storage_path):
        os.remove(crash.storage_path)
        logger.info(f"Deleted file: {crash.storage_path}")
    
    # Delete database record
    await db.delete(crash)
    await db.commit()
    
    logger.info(f"Deleted crash analysis: {crash_id}")
    
    return None


# ============================================
# PHASE 5: BATCH ANALYSIS ENDPOINTS
# ============================================

@router.post("/batch", response_model=BatchAnalysisResponse)
async def analyze_crashes_batch(
    request: BatchAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze multiple crashes together to find patterns.
    
    - **crash_ids**: List of crash analysis UUIDs
    
    Returns batch analysis with clusters, patterns, and trends
    """
    if not settings.ENABLE_BATCH_ANALYSIS:
        raise HTTPException(
            status_code=403,
            detail="Batch analysis feature is disabled"
        )
    
    logger.info(f"Batch analysis requested for {len(request.crash_ids)} crashes")
    
    # Create analyzer
    analyzer = BatchAnalyzer(request.crash_ids)
    
    # Perform analysis
    result = await analyzer.analyze(db)
    
    return BatchAnalysisResponse(**result)


@router.get("/{crash_id}/similar", response_model=SimilarCrashesResponse)
async def get_similar_crashes(
    crash_id: str,
    limit: int = 5,
    min_similarity: float = 0.7,
    db: AsyncSession = Depends(get_db)
):
    """
    Find crashes similar to the specified crash.
    
    - **crash_id**: UUID of the crash analysis
    - **limit**: Maximum number of similar crashes to return
    - **min_similarity**: Minimum similarity threshold (0-1)
    """
    if not settings.ENABLE_CRASH_CLUSTERING:
        raise HTTPException(
            status_code=403,
            detail="Crash clustering feature is disabled"
        )
    
    # Get target crash
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.id == crash_id)
    )
    target_crash = result.scalar_one_or_none()
    
    if not target_crash:
        raise HTTPException(status_code=404, detail="Crash analysis not found")
    
    # Get all completed crashes
    result = await db.execute(
        select(CrashAnalysis).where(
            CrashAnalysis.status == AnalysisStatus.COMPLETED,
            CrashAnalysis.id != crash_id
        ).limit(1000)
    )
    all_crashes = result.scalars().all()
    
    # Find similar crashes
    clusterer = CrashClusterer(similarity_threshold=min_similarity)
    similar = clusterer.find_similar_crashes(target_crash, all_crashes, limit=limit)
    
    return SimilarCrashesResponse(
        crash_id=crash_id,
        similar_crashes=[SimilarCrashResult(**s) for s in similar],
        count=len(similar)
    )


@router.post("/cluster", response_model=dict)
async def cluster_crashes(
    crash_ids: list[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Cluster crashes into similar groups.
    
    - **crash_ids**: Optional list of specific crashes to cluster. If not provided, clusters all crashes.
    """
    if not settings.ENABLE_CRASH_CLUSTERING:
        raise HTTPException(
            status_code=403,
            detail="Crash clustering feature is disabled"
        )
    
    # Get crashes
    query = select(CrashAnalysis).where(CrashAnalysis.status == AnalysisStatus.COMPLETED)
    
    if crash_ids:
        query = query.where(CrashAnalysis.id.in_(crash_ids))
    else:
        query = query.limit(500)  # Limit for performance
    
    result = await db.execute(query)
    crashes = result.scalars().all()
    
    if len(crashes) < settings.MIN_CLUSTER_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough crashes to cluster. Need at least {settings.MIN_CLUSTER_SIZE}"
        )
    
    # Cluster crashes
    clusterer = CrashClusterer()
    clusters = clusterer.cluster_crashes(crashes)
    stats = clusterer.get_cluster_statistics(clusters)
    
    return {
        "clusters": clusters,
        "statistics": stats
    }


# ============================================
# PHASE 5: CHAT ENDPOINTS
# ============================================

@router.post("/{crash_id}/chat", response_model=ChatResponse)
async def chat_about_crash(
    crash_id: str,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ask follow-up questions about a crash analysis.
    
    - **crash_id**: UUID of the crash analysis
    - **question**: Question to ask about the crash
    """
    if not settings.ENABLE_CHAT_FOLLOWUP:
        raise HTTPException(
            status_code=403,
            detail="Chat feature is disabled"
        )
    
    # Get crash
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.id == crash_id)
    )
    crash = result.scalar_one_or_none()
    
    if not crash:
        raise HTTPException(status_code=404, detail="Crash analysis not found")
    
    if crash.status != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Crash analysis not completed yet"
        )
    
    # Create chatbot with crash context
    crash_data = {
        "exception_code": crash.exception_code,
        "exception_message": crash.exception_message,
        "faulting_module": crash.faulting_module,
        "stack_trace": crash.stack_trace,
        "platform": crash.platform
    }
    
    analysis = crash.llm_analysis or {}
    
    chatbot = CrashChatbot(crash_data, analysis)
    answer = chatbot.ask(request.question)
    history = chatbot.get_conversation_history()
    
    return ChatResponse(
        answer=answer,
        conversation_history=history
    )


# ============================================
# PHASE 5: INTEGRATION ENDPOINTS
# ============================================

@router.post("/integrations/slack", response_model=IntegrationResponse)
async def send_slack_notification(
    request: SlackNotificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send crash notification to Slack.
    
    - **crash_id**: UUID of the crash analysis
    - **channel**: Optional Slack channel override
    """
    if not settings.ENABLE_CODE_INTEGRATION:
        raise HTTPException(
            status_code=403,
            detail="Integrations feature is disabled"
        )
    
    # Get crash
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.id == request.crash_id)
    )
    crash = result.scalar_one_or_none()
    
    if not crash:
        raise HTTPException(status_code=404, detail="Crash analysis not found")
    
    # Send notification
    notifier = SlackNotifier()
    
    crash_data = {
        "exception_code": crash.exception_code,
        "faulting_module": crash.faulting_module,
        "platform": crash.platform
    }
    
    analysis = crash.llm_analysis or {}
    
    try:
        notifier.notify_crash(crash_data, analysis)
        return IntegrationResponse(
            success=True,
            message="Slack notification sent successfully"
        )
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Slack notification failed: {str(e)}")


@router.post("/integrations/jira", response_model=JiraIssueResponse)
async def create_jira_issue(
    request: JiraIssueRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create JIRA issue for crash.
    
    - **crash_id**: UUID of the crash analysis
    - **project_key**: JIRA project key
    - **issue_type**: JIRA issue type (default: Bug)
    - **priority**: Override auto-detected priority
    """
    if not settings.ENABLE_CODE_INTEGRATION:
        raise HTTPException(
            status_code=403,
            detail="Integrations feature is disabled"
        )
    
    # Get crash
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.id == request.crash_id)
    )
    crash = result.scalar_one_or_none()
    
    if not crash:
        raise HTTPException(status_code=404, detail="Crash analysis not found")
    
    # Create JIRA issue
    jira_url = getattr(settings, 'JIRA_URL', '')
    jira_token = getattr(settings, 'JIRA_API_TOKEN', '')
    
    if not jira_url or not jira_token:
        raise HTTPException(
            status_code=500,
            detail="JIRA integration not configured"
        )
    
    jira = JiraIntegration(jira_url, jira_token, request.project_key)
    
    crash_data = {
        "exception_code": crash.exception_code,
        "faulting_module": crash.faulting_module,
        "platform": crash.platform,
        "architecture": crash.architecture
    }
    
    analysis = crash.llm_analysis or {}
    
    issue_key = jira.create_issue(crash_data, analysis)
    
    if issue_key:
        return JiraIssueResponse(
            issue_key=issue_key,
            issue_url=f"{jira_url}/browse/{issue_key}",
            created=True
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to create JIRA issue")


@router.post("/integrations/github", response_model=GitHubIssueResponse)
async def create_github_issue(
    request: GitHubIssueRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create GitHub issue for crash.
    
    - **crash_id**: UUID of the crash analysis
    - **repository**: GitHub repository (owner/repo)
    - **labels**: Additional labels
    """
    if not settings.ENABLE_CODE_INTEGRATION:
        raise HTTPException(
            status_code=403,
            detail="Integrations feature is disabled"
        )
    
    # Get crash
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.id == request.crash_id)
    )
    crash = result.scalar_one_or_none()
    
    if not crash:
        raise HTTPException(status_code=404, detail="Crash analysis not found")
    
    # Create GitHub issue
    github_token = getattr(settings, 'GITHUB_TOKEN', '')
    
    if not github_token:
        raise HTTPException(
            status_code=500,
            detail="GitHub integration not configured"
        )
    
    github = GitHubIntegration(request.repository, github_token)
    
    crash_data = {
        "exception_code": crash.exception_code,
        "faulting_module": crash.faulting_module,
        "platform": crash.platform,
        "architecture": crash.architecture
    }
    
    analysis = crash.llm_analysis or {}
    
    issue_number = github.create_issue(crash_data, analysis)
    
    if issue_number:
        return GitHubIssueResponse(
            issue_number=issue_number,
            issue_url=f"https://github.com/{request.repository}/issues/{issue_number}",
            created=True
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to create GitHub issue")


# ============================================
# PHASE 5: SEVERITY CLASSIFICATION ENDPOINTS
# ============================================

@router.post("/classify-severity", response_model=SeverityClassificationResponse)
async def classify_crash_severity(
    request: SeverityClassificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Classify severity of crashes using ML.
    
    - **crash_ids**: List of crash analysis UUIDs to classify
    """
    if not settings.ENABLE_ML_CLASSIFICATION:
        raise HTTPException(
            status_code=403,
            detail="ML classification feature is disabled"
        )
    
    # Get crashes
    result = await db.execute(
        select(CrashAnalysis).where(CrashAnalysis.id.in_(request.crash_ids))
    )
    crashes = result.scalars().all()
    
    if not crashes:
        raise HTTPException(status_code=404, detail="No crashes found")
    
    # Classify severity
    classifier = SeverityClassifier()
    results = classifier.classify_batch(crashes)
    distribution = classifier.get_severity_distribution(crashes)
    
    return SeverityClassificationResponse(
        results=results,
        distribution=distribution
    )
