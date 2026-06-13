# Crashbot — Bug Report, Remaining Work & Improvements

> **Last reviewed:** March 22, 2026 (complete line-by-line code audit of every source file)
>
> This is the single source of truth for the project's actual state. Every issue listed below has been verified against the actual code with exact line numbers.

---

## Table of Contents

1. [Critical Bugs — App Cannot Start](#1-critical-bugs--app-cannot-start)
2. [High-Priority Bugs — Broken Features](#2-high-priority-bugs--broken-features)
3. [Medium-Priority Bugs — Incorrect Behavior](#3-medium-priority-bugs--incorrect-behavior)
4. [Low-Priority Issues — Code Quality](#4-low-priority-issues--code-quality)
5. [Architecture Overview](#5-architecture-overview)
6. [File-by-File Status](#6-file-by-file-status)
7. [Frontend Analysis](#7-frontend-analysis)
8. [Test Suite Analysis](#8-test-suite-analysis)
9. [Alembic Migration Analysis](#9-alembic-migration-analysis)
10. [Docker & Infrastructure](#10-docker--infrastructure)
11. [venv & Dependencies](#11-venv--dependencies)
12. [Security Audit](#12-security-audit)
13. [Fix Priority Order & Roadmap](#13-fix-priority-order--roadmap)
14. [External Dependencies (Blocked)](#14-external-dependencies-blocked)
15. [What Actually Works Today](#15-what-actually-works-today)
16. [Remaining Feature Work](#16-remaining-feature-work)

---

## 1. Critical Bugs — App Cannot Start

These must be fixed first. The backend fails to import and **no endpoints work at all**. The FastAPI app cannot even start `uvicorn`.

---

### Bug #1: `app/llm/analyzer.py` — Syntax Corruption (FATAL)

**File:** `backend/app/llm/analyzer.py`
**Lines:** 402–529 (128 lines of corrupted code)
**Severity:** FATAL — the Python interpreter cannot parse this file

Every double-quote character (`"`) was replaced with a backslash-escaped quote (`\"`) and every triple-quote docstring (`"""`) was corrupted to (`\"\"\"`). This is not valid Python syntax.

**Corrupted lines (exhaustive list):**

| Line | Corrupted Code |
|------|----------------|
| 402 | `self.tokens_used["input\"] = response.usage.prompt_tokens` |
| 403 | `self.tokens_used["output\"] = response.usage.completion_tokens` |
| 410 | `f\"{self.provider.upper()} API (Function Calling) usage: ...\"` |
| 411 | `f\"{response.usage.completion_tokens} output = ${self.cost_usd:.4f}\"` |
| 417 | `logger.info(\"Function calling returned structured output\")` |
| 424 | `logger.error(f\"Function calling failed: {e}, falling back...\")` |
| 429, 432 | `\"\"\"` (docstring for `analyze_crash_ensemble`) |
| 437 | `logger.info(\"Starting multi-model ensemble analysis\")` |
| 442 | `settings.ENSEMBLE_MODELS.split(\",\")` |
| 443 | `logger.info(f\"Using ensemble models: {models}\")` |
| 454 | `result[\"model\"] = model` |
| 456 | `logger.info(f\"Model {model} completed analysis\")` |
| 458 | `logger.error(f\"Model {model} failed: {e}\")` |
| 463–464 | `f\"Not enough models completed...\"` / `\"using single model\"` |
| 472 | `logger.info(f\"Ensemble analysis complete...\")` |
| 477 | `logger.error(f\"Ensemble analysis failed...\")` |
| 481, 484 | `\"\"\"` (docstring for `_aggregate_ensemble_results`) |
| 486 | `raise ValueError(\"No results to aggregate\")` |
| 489 | `root_causes = [r.get(\"root_cause\", \"\") for r in results]` |
| 493 | `severities = [r.get(\"severity\", \"medium\") for r in results]` |
| 495+ | All remaining lines through line 529 have the same corruption |

**Import chain that breaks:**
```
crashes.py (line 38) → from app.parsers.crash_parser import analyze_crash_dump_async
crash_parser.py (line 16) → from app.llm.analyzer import analyze_with_llm
analyzer.py (line 402) → SyntaxError: unterminated string literal
```

**Affected functions:**
- `_analyze_with_function_calling()` (lines 319–427)
- `analyze_crash_ensemble()` (lines 429–478)
- `_aggregate_ensemble_results()` (lines 480–529)
- `analyze_with_llm()` (lines 531–535) — the standalone function imported by crash_parser.py

**Fix:** Replace every `\"` with `"` and every `\"\"\"` with `"""` in lines 402–529. The correct versions of these functions exist in the first half of the file (lines 191–317) using proper quoting, so they can be used as reference.

**Verification command:**
```powershell
cd backend
..\venv\Scripts\python -m py_compile app/llm/analyzer.py
# Currently outputs: SyntaxError: unterminated string literal (detected at line 402)
```

---

### Bug #2: `openai` v2.x API Incompatibility

**File:** `backend/app/llm/analyzer.py` (lines 5, 48, 52–53, 217)
**Also:** `backend/app/rag/vector_store.py` (line 11)
**Severity:** FATAL — all LLM calls fail with `AttributeError`

**Installed version:** `openai==2.8.0` (confirmed via `pip list`)
**Code written for:** `openai<1.0` (pre-November 2023 API)

In openai v2.x (and v1.x), the module-level attribute pattern was removed:

```python
# BROKEN — does not work in openai>=1.0:
import openai
openai.api_key = settings.SIEMENS_API_KEY      # Line 52: AttributeError
openai.base_url = settings.LLM_BASE_URL        # Line 53: AttributeError
response = openai.chat.completions.create(...)  # Line 217: may work but uses wrong key

# CORRECT — openai>=1.0 pattern:
from openai import OpenAI
client = OpenAI(api_key=settings.SIEMENS_API_KEY, base_url=settings.LLM_BASE_URL)
response = client.chat.completions.create(...)
```

**All affected locations in `analyzer.py`:**

| Line | Broken Code | Fix |
|------|-------------|-----|
| 5 | `import openai` | `from openai import OpenAI` |
| 48 | `openai.api_key = settings.OPENAI_API_KEY` | Store in `self.client = OpenAI(api_key=...)` |
| 52 | `openai.api_key = settings.SIEMENS_API_KEY` | `self.client = OpenAI(api_key=..., base_url=...)` |
| 53 | `openai.base_url = settings.LLM_BASE_URL` | (merged into client constructor above) |
| 217 | `openai.chat.completions.create(...)` | `self.client.chat.completions.create(...)` |

**`vector_store.py` is partially correct:** Line 32–35 already uses `openai.OpenAI(api_key=..., base_url=...)` — the new pattern. However, line 11 still does `import openai` at module level, and the constructor stores it as `self.embedding_client`. This part works. The issue is only in `analyzer.py`.

**Note:** The `anthropic` client in `analyzer.py` line 50 (`self.anthropic_client = anthropic.Anthropic(...)`) is correct — Anthropic's SDK didn't have this breaking change.

---

## 2. High-Priority Bugs — Broken Features

These don't prevent startup (once Critical bugs are fixed), but cause incorrect behavior or data loss.

---

### Bug #3: FastAPI Route Ordering — Phase 5 Endpoints Unreachable

**File:** `backend/app/api/v1/endpoints/crashes.py`
**Severity:** HIGH — multiple endpoints return 404 instead of their intended response

FastAPI matches routes in the order they are defined. The current order is:

| Order | Line | Route | Problem |
|-------|------|-------|---------|
| 1 | ~120 | `POST /upload` | OK — unique path |
| 2 | ~218 | `GET /{crash_id}` | **CATCHES ALL** — `batch`, `cluster`, etc. match here as GET requests |
| 3 | ~240 | `GET /` | OK — empty path |
| 4 | ~268 | `DELETE /{crash_id}` | OK — different method from GET |
| 5 | ~295 | `POST /batch` | OK (POST doesn't conflict with GET `/{crash_id}`, but confusing) |
| 6 | ~322 | `GET /{crash_id}/similar` | OK — sub-path, different from `{crash_id}` alone |
| 7 | ~375 | `POST /cluster` | OK (POST only) |
| 8 | ~413 | `POST /{crash_id}/chat` | OK (POST only) |
| 9 | ~450 | `POST /integrations/slack` | OK — different prefix |
| 10 | ~490 | `POST /integrations/jira` | OK |
| 11 | ~545 | `POST /integrations/github` | OK |
| 12 | ~600 | `POST /classify-severity` | OK |

**Actually broken scenario:** If someone sends `GET /api/v1/crashes/batch`, it matches `GET /{crash_id}` with `crash_id="batch"`, queries the database for a crash with id "batch", fails, returns 404. The actual `/batch` endpoint is POST-only so this specific case isn't fatal, but it causes confusing error messages and will catch any future GET-specific routes added after `/{crash_id}`.

**The real problem is `GET /`:** The list endpoint `GET /` is defined AFTER `GET /{crash_id}`. If the list route were at a path like `/list` or if there were any other GET routes with specific names, they'd be shadowed.

**Fix:** Reorder routes: all specific-path routes first, then `/{crash_id}` and `DELETE /{crash_id}` last.

```python
# CORRECT ORDER:
@router.post("/upload", ...)          # specific
@router.get("/", ...)                 # list all
@router.post("/batch", ...)           # specific
@router.post("/cluster", ...)         # specific
@router.post("/classify-severity")    # specific
@router.post("/integrations/slack")   # specific
@router.post("/integrations/jira")    # specific
@router.post("/integrations/github")  # specific
@router.get("/{crash_id}", ...)       # wildcard — MUST BE LAST among GETs
@router.get("/{crash_id}/similar")    # sub-path of wildcard
@router.post("/{crash_id}/chat")      # sub-path of wildcard
@router.delete("/{crash_id}", ...)    # wildcard DELETE
```

---

### Bug #4: Frontend-Backend API Mismatch (`llm_analysis`)

**Backend schema file:** `backend/app/api/v1/schemas/crash.py`, `CrashAnalysisDetail` class
**Frontend file:** `frontend/src/app/analysis/[id]/page.tsx`
**Severity:** HIGH — AI analysis results never display in the frontend

**What the frontend expects** (from `analysis/[id]/page.tsx`):
```typescript
// Line ~169:  {analysis.llm_analysis && (
// Line ~178:  analysis.llm_analysis.severity
// Line ~183:  analysis.llm_analysis.confidence * 100  (expects 0-1 float)
// Line ~189:  analysis.llm_analysis.root_cause
// Line ~199:  analysis.llm_analysis.solutions.map(...)
// Line ~219:  analysis.llm_analysis.references
```

**What the backend returns** (`CrashAnalysisDetail` Pydantic schema):
```python
class CrashAnalysisDetail(CrashAnalysisBase):
    # These FLAT fields are defined but NEVER populated by analyze_crash_dump_async:
    root_cause: Optional[str] = None
    explanation: Optional[str] = None
    solutions: Optional[List[str]] = None  # Also wrong type — see Bug #5
    severity: Optional[CrashSeverity] = None
    confidence_score: Optional[float] = None
    references: Optional[List[str]] = None

    # MISSING from schema — but this IS populated in the DB:
    # llm_analysis: Optional[Dict[str, Any]] = None   ← not in Pydantic model
```

**What the background task actually stores** (from `crash_parser.py` lines ~340–360):
```python
crash.llm_analysis = {
    "root_cause": llm_result.get("root_cause"),
    "explanation": llm_result.get("explanation"),
    "severity": llm_result.get("severity"),
    "confidence": llm_result.get("confidence_score", 0) / 100.0,
    "solutions": llm_result.get("solutions", []),
    "references": llm_result.get("references", [])
}
# The flat fields (crash.root_cause, crash.solutions, etc.) are NEVER set
```

**Result:** The `llm_analysis` JSON blob is stored in the database but the Pydantic schema doesn't include it, so the API response omits it. The frontend reads `analysis.llm_analysis` and gets `undefined`. No AI results ever display.

**Fix options:**
1. Add `llm_analysis: Optional[Dict[str, Any]] = None` to `CrashAnalysisDetail`
2. OR populate the flat fields in `analyze_crash_dump_async` AND remove the nesting in the frontend

---

### Bug #5: `CrashAnalysisDetail.solutions` — Wrong Type

**File:** `backend/app/api/v1/schemas/crash.py` line ~71
**Severity:** HIGH — response validation failure when data is populated

```python
# CURRENT (wrong):
solutions: Optional[List[str]] = None

# ACTUAL data stored in DB (from LLM response):
[
    {"title": "Fix null pointer", "description": "Add null check...", "priority": 1, "code_example": "..."},
    {"title": "Update driver", "description": "Install latest...", "priority": 2}
]

# CORRECT type (matches both backend storage and frontend expectations):
solutions: Optional[List[Dict[str, Any]]] = None
```

**Note:** The same file defines a `SolutionItem` Pydantic model (lines ~68–75) that matches the structure, but it's never used in `CrashAnalysisDetail`. The correct fix would be:
```python
solutions: Optional[List[SolutionItem]] = None
```

---

### Bug #6: No Authentication Enforced on Any Endpoint

**File:** `backend/app/core/security.py` (56 lines, fully implemented)
**File:** `backend/app/api/v1/endpoints/crashes.py` (0 auth checks)
**File:** `backend/app/main.py` (no auth middleware)
**Severity:** HIGH — all data accessible without credentials

The security module is complete and well-written:
- `hash_password()` / `verify_password()` — bcrypt (line 19–24)
- `generate_api_key()` — `secrets.token_urlsafe(32)` (line 27)
- `hash_api_key()` — SHA256 with salt (line 31)
- `create_access_token()` / `decode_access_token()` — JWT HS256 (lines 36–66)

But **none of it is used**. No endpoint has a `Depends(verify_api_key)` or `Depends(get_current_user)` guard. The `User` model exists in the database but is never queried. The `user_id` column on `CrashAnalysis` is always `None`.

**Risk:** Anyone who can reach the API can:
- Upload arbitrary files (up to 500MB per config)
- Read all crash analyses (potentially containing sensitive crash data)
- Delete any crash analysis without authorization
- Trigger LLM API calls (cost money via Siemens AI / OpenAI)
- Send Slack/JIRA/GitHub notifications impersonating the system
- Enumerate all stored data via the list endpoint

**Required for production:** Create an auth dependency function and add it to all endpoints, or create a middleware.

**Implementation sketch:**
```python
# In crashes.py:
from app.core.security import decode_access_token
from fastapi import Depends, HTTPException, Header

async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    payload = decode_access_token(authorization.split(" ")[1])
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

@router.post("/upload", ..., dependencies=[Depends(verify_token)])
async def upload_crash_dump(...):
    ...
```

---

### Bug #7: `CrashData.to_dict()` Returns Unserializable Dataclass Objects

**File:** `backend/app/parsers/types.py` lines 83–96
**Severity:** HIGH — `TypeError` when storing parsed data in PostgreSQL JSON column

```python
def to_dict(self) -> dict[str, Any]:
    return {
        ...
        "stack_trace": list(self.stack_trace),      # ← StackFrame objects, not dicts
        "loaded_modules": list(self.loaded_modules), # ← ModuleInfo objects, not dicts
        ...
    }
```

`self.stack_trace` is `list[StackFrame]` where `StackFrame` is a dataclass:
```python
@dataclass
class StackFrame:
    frame_number: int
    function: str
    module: str
    offset: str
    source_line: str | None = None
```

`list(self.stack_trace)` just copies the list — the elements are still `StackFrame` instances. When SQLAlchemy tries to serialize this to the `JSON` column, it raises `TypeError: Object of type StackFrame is not JSON serializable`.

**Fix:**
```python
import dataclasses

def to_dict(self) -> dict[str, Any]:
    return {
        ...
        "stack_trace": [dataclasses.asdict(f) for f in self.stack_trace],
        "loaded_modules": [dataclasses.asdict(m) for m in self.loaded_modules],
        ...
    }
```

**Note:** This only affects the `UniversalCrashParser` code path (multi-platform). The old `WinDbgParser` returns plain dicts directly, so the fallback path works.

---

### Bug #8: Alembic Migrations Severely Out of Sync with Models

**Migration files:** `backend/alembic/versions/001_initial.py`, `002_add_indexes.py`, `003_similar_crashes.py`
**Model files:** `backend/app/db/models/crash.py`, `backend/app/db/models/user.py`
**Severity:** HIGH — running `alembic upgrade head` fails at migration 002

**Users table — Migration vs. Model:**

| Column | In Migration (001) | In Model (`user.py`) | Status |
|--------|-------------------|---------------------|--------|
| `id` | `Integer` | `UUID(as_uuid=True)` | **TYPE MISMATCH** |
| `email` | `String(255)` | `String(255)` | OK |
| `username` | `String(100)` | Does not exist | **MIGRATION HAS EXTRA COLUMN** |
| `full_name` | Does not exist | `String(100)` | **MODEL HAS EXTRA COLUMN** |
| `hashed_password` | `String(255)` | `String(255)` | OK |
| `api_key` | `String(255)` — plaintext | Does not exist | **SHOULD BE `api_key_hash`** |
| `api_key_hash` | Does not exist | `String(64)` | **MISSING FROM MIGRATION** |
| `api_key_created_at` | `DateTime` | Does not exist | **MIGRATION HAS EXTRA COLUMN** |
| `is_active` | `Boolean` | `Boolean` | OK |
| `created_at` / `updated_at` | `DateTime` | `DateTime` | OK |

**Crash analyses table — Migration vs. Model:**

| Column | In Migration (001) | In Model (`crash.py`) | Status |
|--------|-------------------|----------------------|--------|
| `id` | `String(36)` | `UUID(as_uuid=True)` | **TYPE MISMATCH** |
| `filename` | `String(500)` | `String(500)` | OK |
| `file_hash` | `String(64)` | `String(64)` | OK |
| `file_size` | `BigInteger` | `Integer` | **TYPE MISMATCH** |
| `platform` | `String(50)` | `String(50)` | OK |
| `status` | `String(20)` | `String(20)` | OK |
| `exception_code` | `String(20)` | `String(20)` | OK |
| `exception_description` | `Text` | `Text` | OK |
| `stack_trace` | `Text` | `JSON` | **TYPE MISMATCH** |
| `raw_output` | `Text` | `Text` | OK |
| `llm_analysis` | `JSON` | `JSON` | OK |
| `similar_crashes` | `JSON` | `JSON` | OK |
| `user_id` | `Integer` (FK to users.id) | `String(100)` | **TYPE MISMATCH + FK mismatch** |
| `completed_at` | `DateTime(timezone=True)` | `Float` | **TYPE MISMATCH** |
| `severity` | Not in 001 | `SQLEnum(CrashSeverity)` | **MISSING FROM 001** |
| `root_cause` | Not in any migration | `Text` | **MISSING FROM ALL** |
| `explanation` | Not in any migration | `Text` | **MISSING FROM ALL** |
| `solutions` | Not in any migration | `JSON` | **MISSING FROM ALL** |
| `confidence_score` | Not in any migration | `Float` | **MISSING FROM ALL** |
| `references` | Not in any migration | `JSON` | **MISSING FROM ALL** |
| `os_version` | Not in any migration | `String(100)` | **MISSING FROM ALL** |
| `session_id` | Not in any migration | `String(100)` | **MISSING FROM ALL** |
| `tags` | Not in any migration | `JSON` | **MISSING FROM ALL** |
| `crash_category` | Not in any migration | `String(50)` | **MISSING FROM ALL** |
| `related_issue_urls` | Not in any migration | `JSON` | **MISSING FROM ALL** |
| `analysis_duration_seconds` | Not in any migration | `Float` | **MISSING FROM ALL** |
| `similar_crash_ids` | Not in any migration | `JSON` | **MISSING FROM ALL** |

**Migration 002 references non-existent column:**
```python
# 002_add_indexes.py line 37:
op.create_index('idx_crash_exception_severity', 'crash_analyses', ['exception_code', 'severity'])
# BUT: 'severity' column does not exist in migration 001 — this migration FAILS
```

**Migration 003 adds already-existing column:**
```python
# 003_similar_crashes.py:
op.add_column('crash_analyses', sa.Column('similar_crashes', ...))
# BUT: 'similar_crashes' is already defined in migration 001 — this will FAIL
```

**Impact:** Running `alembic upgrade head` will fail at migration 002. The app currently works because `main.py` uses `Base.metadata.create_all()` which creates tables from models directly, bypassing Alembic entirely.

**Fix:** Delete all three migration files and regenerate from current models:
```powershell
cd backend
Remove-Item alembic\versions\*.py
..\venv\Scripts\alembic revision --autogenerate -m "initial_schema"
```

---

## 3. Medium-Priority Bugs — Incorrect Behavior

---

### Bug #9: `list_crash_analyses` — Pagination Applied Before Filter

**File:** `backend/app/api/v1/endpoints/crashes.py` lines ~248–260

```python
query = select(CrashAnalysis).offset(skip).limit(limit)    # Line ~252: pagination FIRST

if status:
    query = query.where(CrashAnalysis.status == status)     # Line ~255: filter AFTER

query = query.order_by(CrashAnalysis.created_at.desc())     # Line ~257: ordering LAST
```

**Problem:** While SQLAlchemy typically resolves the SQL in correct logical order, it is best practice and clearer to build the query in the standard SQL logical order: WHERE → ORDER BY → OFFSET/LIMIT. Some database engines or edge cases may produce subtly wrong results if the clauses are applied in the wrong order of specificity.

**Fix:**
```python
query = select(CrashAnalysis)
if status:
    query = query.where(CrashAnalysis.status == status)
query = query.order_by(CrashAnalysis.created_at.desc())
query = query.offset(skip).limit(limit)
```

---

### Bug #10: File Saved Before DB Commit — Orphaned Files on Failure

**File:** `backend/app/api/v1/endpoints/crashes.py` lines ~170–190

```python
# Line ~170: File written to disk FIRST
storage_path = os.path.join(settings.DUMP_STORAGE_PATH, safe_filename)
with open(storage_path, "wb") as f:
    f.write(content)

# Lines ~178–188: Database record created
crash_analysis = CrashAnalysis(
    id=str(uuid.uuid4()),
    filename=safe_filename,
    file_hash=file_hash,
    file_size=len(content),
    ...
)
db.add(crash_analysis)
await db.commit()  # If this fails → file stays on disk with no DB record
```

**Impact:** If the database insert fails (constraint violation, connection timeout, disk full, etc.), the file remains on disk permanently with no way to find or clean it up. Over time this leaks storage.

**Fix:** Write file after `db.commit()` succeeds, or use a try/except:
```python
try:
    db.add(crash_analysis)
    await db.commit()
except Exception:
    if os.path.exists(storage_path):
        os.unlink(storage_path)
    raise
```

---

### Bug #11: `storage/dumps` Directory Not Created

**File:** `backend/app/api/v1/endpoints/crashes.py` line ~170

The upload endpoint writes to `settings.DUMP_STORAGE_PATH` (default: `./storage/dumps`) but never creates this directory. The first upload attempt raises `FileNotFoundError: [Errno 2] No such file or directory`.

**Note:** `config.py` has an `ensure_directories()` helper function that creates `DUMP_STORAGE_PATH`, `LOG_DIR`, and `CHROMA_PERSIST_DIRECTORY`. But it is **never called** at startup. `main.py`'s lifespan only calls `setup_logging()` and creates DB tables.

**Fix — Option 1 (in `main.py` lifespan):**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    os.makedirs(settings.DUMP_STORAGE_PATH, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
```

**Fix — Option 2 (in upload handler):**
```python
os.makedirs(os.path.dirname(storage_path), exist_ok=True)
```

---

### Bug #12: Synchronous File I/O in Async Handler

**File:** `backend/app/api/v1/endpoints/crashes.py` line ~172

```python
async def upload_crash_dump(...):
    ...
    with open(storage_path, "wb") as f:  # BLOCKS the event loop
        f.write(content)
```

`aiofiles==23.2.1` is installed in the venv (confirmed via `pip list`) and listed in `requirements.txt` but not used here. For files up to 500MB (the configured `MAX_UPLOAD_SIZE`), this synchronous write blocks the entire async event loop, preventing all other requests from being processed until the write completes.

**Fix:**
```python
import aiofiles

async with aiofiles.open(storage_path, "wb") as f:
    await f.write(content)
```

**Also applies to `content = await file.read()`** — the `UploadFile.read()` is already async, so that's correct. Only the disk write is synchronous.

---

### Bug #13: `asyncio.get_event_loop()` Deprecated in Python 3.12

**File:** `backend/app/parsers/crash_parser.py` — 4 occurrences in `analyze_crash_dump_async()`:

| Approx Line | Code |
|-------------|------|
| ~312 | `await asyncio.get_event_loop().run_in_executor(None, parser.parse)` |
| ~328 | `await asyncio.get_event_loop().run_in_executor(None, vector_store.find_similar_crashes, ...)` |
| ~354 | `await asyncio.get_event_loop().run_in_executor(None, llm_analyzer.analyze_crash, ...)` |
| ~382 | `await asyncio.get_event_loop().run_in_executor(None, vector_store.add_crash_embedding, ...)` |

`asyncio.get_event_loop()` emits `DeprecationWarning` in Python 3.10+ and may raise `RuntimeError` in future versions when called outside an async context. In Python 3.12, the correct pattern is:

```python
loop = asyncio.get_running_loop()
await loop.run_in_executor(None, sync_function)
```

The fix is a simple search-and-replace: `asyncio.get_event_loop()` → `asyncio.get_running_loop()`.

---

### Bug #14: `datetime.utcnow()` Deprecated in Python 3.12

Used in multiple files across the codebase:

| File | Line | Code |
|------|------|------|
| `db/base.py` | 8 | `created_at = Column(DateTime, default=datetime.utcnow)` |
| `db/base.py` | 9 | `updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)` |
| `core/logging.py` | ~20 | `"timestamp": datetime.utcnow().isoformat()` |
| `ml/chat.py` | ~12 | `self.timestamp = timestamp or datetime.utcnow()` |
| `crashes.py` | ~168 | `datetime.utcnow().strftime("%Y%m%d_%H%M%S")` |

**Fix:** Replace with `datetime.now(timezone.utc)` (or `datetime.now(datetime.UTC)` on Python 3.11+).

```python
from datetime import datetime, timezone
# Instead of:
datetime.utcnow()
# Use:
datetime.now(timezone.utc)
```

For SQLAlchemy column defaults, the pattern changes slightly:
```python
from datetime import datetime, timezone
created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

---

### Bug #15: `declarative_base()` Deprecated Import Path

**File:** `backend/app/db/base.py` line 3

```python
from sqlalchemy.ext.declarative import declarative_base  # Deprecated in SQLAlchemy 2.0
Base = declarative_base()
```

**SQLAlchemy 2.0 deprecation notice:** The `sqlalchemy.ext.declarative` module is deprecated. The modern pattern is:

**Fix:**
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

This also enables type-safe mapped columns (`Mapped[str]`, `mapped_column()`), but the existing `Column()` pattern will still work with the new base class.

---

### Bug #16: Docker Worker/Flower Services Crash on Startup

**File:** `docker-compose.yml` — worker and flower services

```yaml
worker:
  build: ./backend
  command: celery -A app.workers.celery_app worker --loglevel=info
  depends_on:
    - redis
    - database

flower:
  build: ./backend
  command: celery -A app.workers.celery_app flower --port=5555
  depends_on:
    - redis
    - worker
```

**Problem:** The module `app.workers.celery_app` does not exist. There is no `workers/` directory anywhere in the backend. These containers crash immediately with `ModuleNotFoundError: No module named 'app.workers'`.

**Context:** The current architecture uses FastAPI's `BackgroundTasks` for async work (see `crash_parser.py` `analyze_crash_dump_async()`). Celery would be needed for distributed task processing at scale, but the integration was never built.

**Fix options:**
1. **Remove worker/flower from docker-compose.yml** — simplest, matches actual architecture
2. **Create `app/workers/celery_app.py`** — if distributed processing is planned:
```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "crashbot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
```

---

### Bug #17: `completed_at` Column — Float vs. DateTime

**File:** `backend/app/db/models/crash.py` line ~74

```python
completed_at: Mapped[Optional[float]] = Column(Float, nullable=True)  # Unix timestamp
```

All other timestamps (`created_at`, `updated_at`) use `DateTime`. The migration (001) defines it as `DateTime(timezone=True)`. The code sets it as `time.time()` (float). This causes:
- Type mismatch between migration and model (migration says DateTime, model says Float)
- Cannot sort/filter `completed_at` alongside `created_at` without conversion
- PostgreSQL stores a floating-point number instead of a proper timestamp
- Frontend cannot parse this meaningfully without knowing it's a Unix epoch

**Fix:**
```python
completed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
```
And in `analyze_crash_dump_async()`:
```python
crash.completed_at = datetime.now(timezone.utc)
```

---

### Bug #18: `.env.example` Uses Synchronous DB Driver

**File:** `.env.example` line ~12 (or similar)

```env
DATABASE_URL=postgresql://crashbot:crashbot_password@localhost:5435/crashbot_db
```

The app uses SQLAlchemy's `create_async_engine` which requires the async driver:
```env
DATABASE_URL=postgresql+asyncpg://crashbot:crashbot_password@localhost:5435/crashbot_db
```

A developer copying `.env.example` to `.env` will get:
```
sqlalchemy.exc.ArgumentError: Could not locate a dialect mapping for "postgresql" in async engine configuration. Did you mean "postgresql+asyncpg"?
```

---

### Bug #19: Integer Division in Ensemble Aggregation

**File:** `backend/app/llm/analyzer.py` line ~497 (in corrupted section)

```python
avg_confidence = sum(confidence_scores) // len(confidence_scores)
```

`//` is integer (floor) division. A confidence average of 85.7 becomes 85, 72.3 becomes 72, etc. Systematic downward bias in confidence scoring.

**Fix:** Use `/` for true division:
```python
avg_confidence = sum(confidence_scores) / len(confidence_scores)
```

---

### Bug #20: `CrashChatbot` Bypasses Provider Routing

**File:** `backend/app/ml/chat.py` line ~46

```python
class CrashChatbot:
    def __init__(self, crash_data, analysis):
        self.llm = LLMAnalyzer()

    def ask(self, question: str) -> str:
        prompt = self._build_prompt(question)
        response = self.llm._analyze_with_openai(prompt)  # PRIVATE METHOD — bypasses routing
        return response.get("explanation", "Unable to answer")
```

`_analyze_with_openai` is a private method (underscore prefix). Calling it directly means:
- If `LLM_PROVIDER` is `"anthropic"`, it still calls OpenAI
- If `LLM_PROVIDER` is `"siemens"`, it calls OpenAI without the Siemens base_url
- Cost tracking in `self.cost_usd` and `self.tokens_used` may not be updated correctly
- The caching layer in `analyze_crash()` is bypassed
- Function calling mode is bypassed

**Fix:** Use the public `analyze_crash()` method, or better yet, create a dedicated public method for prompt-based requests:
```python
# Option 1 — Quick fix:
response = self.llm.analyze_crash(prompt)

# Option 2 — Better design:
# In LLMAnalyzer, add:
def send_prompt(self, prompt: str) -> dict:
    """Public method for sending a raw prompt to the configured provider."""
    if self.provider == "anthropic":
        return self._analyze_with_anthropic(prompt)
    else:
        return self._analyze_with_openai(prompt)
```

---

### Bug #21: `session.py` — `pool_size` with `NullPool`

**File:** `backend/app/db/session.py` lines 11–16

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,      # Always passed — even with NullPool
    max_overflow=settings.DATABASE_MAX_OVERFLOW, # Always passed — even with NullPool
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
)
```

When `ENVIRONMENT == "test"`, `NullPool` is used. SQLAlchemy ignores `pool_size` and `max_overflow` with `NullPool` (each connection is created/destroyed immediately). This isn't a crash bug but is misleading—developers may try to tune pool settings and wonder why they have no effect in tests.

**Fix:** Use conditional engine creation:
```python
if settings.ENVIRONMENT == "test":
    engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )
```

---

### Bug #22: ThreadTimeline — XSS Risk via Mermaid

**File:** `frontend/src/visualizations/ThreadTimeline.tsx` line ~28

```typescript
mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',  // ALLOWS ARBITRARY HTML/JS
});
```

Crash dump data (thread names, function names, module names) comes from untrusted binary files. With `securityLevel: 'loose'`, Mermaid renders raw HTML including `<script>` tags. A crafted crash dump with a thread name like `<img src=x onerror=alert(1)>` could inject JavaScript into the visualization.

**Fix:** Change to `securityLevel: 'strict'` (which is actually the Mermaid default, so it was explicitly weakened).

---

### Bug #23: `localStorage` Access Crashes SSR

**File:** `frontend/src/api/client.ts` line ~78

```typescript
apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('auth_token');  // CRASHES in SSR
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});
```

Next.js renders pages server-side where `localStorage` is undefined. This interceptor runs on every request, including server-side data fetching. It throws `ReferenceError: localStorage is not defined`.

**Fix:**
```typescript
apiClient.interceptors.request.use((config) => {
    if (typeof window !== 'undefined') {
        const token = localStorage.getItem('auth_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
});
```

---

### Bug #24: Missing Integration Config Fields

**File:** `backend/app/api/v1/endpoints/crashes.py` lines ~510, ~555, ~603
**File:** `backend/app/core/config.py` (missing definitions)

```python
# crashes.py uses these:
jira_url = getattr(settings, 'JIRA_URL', '')           # Not defined in config.py
jira_token = getattr(settings, 'JIRA_API_TOKEN', '')    # Not defined in config.py
github_token = getattr(settings, 'GITHUB_TOKEN', '')    # Not defined in config.py
```

These fields are referenced with `getattr()` defaults, so they don't crash. But they always return `""`, making all three integration endpoints non-functional:
```json
{"detail": "JIRA integration not configured"}
{"detail": "GitHub integration not configured"}
```

The Slack webhook URL (`settings.SLACK_WEBHOOK_URL`) IS defined in config.py but defaults to `""`.

**Fix:** Add to `config.py` Settings class:
```python
JIRA_URL: str = ""
JIRA_API_TOKEN: str = ""
JIRA_PROJECT_KEY: str = "CRASH"
GITHUB_TOKEN: str = ""
GITHUB_REPO: str = ""
```

---

### Bug #25: Integration HTTP Calls — No Timeout

**File:** `backend/app/ml/integrations.py`

| Line | Code | Risk |
|------|------|------|
| ~48 | `requests.post(self.webhook_url, json=payload)` | Slack webhook — hangs if Slack is down |
| ~108 | `requests.post(f"{self.jira_url}/rest/api/2/issue", ...)` | JIRA API — hangs indefinitely |
| ~169 | `requests.post(f"{self.api_url}/repos/{self.repo}/issues", ...)` | GitHub API — hangs indefinitely |

All three use `requests.post()` with no `timeout` parameter. The default timeout in `requests` is `None` (wait forever). If the external service is unreachable, DNS resolution is slow, or the server accepts the connection but never responds, the request blocks the thread indefinitely.

In an async context, if these are called via `run_in_executor`, they block one thread from the thread pool forever.

**Fix:** Add `timeout=30` (or a configurable value) to all calls:
```python
response = requests.post(url, json=payload, timeout=30)
```

---

## 4. Low-Priority Issues — Code Quality

---

### Issue #26: Hardcoded Default Secret Keys

**File:** `backend/app/core/config.py` lines 21–22

```python
SECRET_KEY: str = "change-this-in-production"
API_KEY_SALT: str = "change-this-salt"
```

In development mode (`DEBUG=True`), these defaults are used. Any JWT token signed with `"change-this-in-production"` is trivially forgeable. Not a production issue if `.env` overrides them, but dangerous if someone deploys without configuring these.

**Recommendation:** Generate a secure random key at startup if the default is detected:
```python
import secrets
SECRET_KEY: str = secrets.token_urlsafe(32)  # Random per-process
```
Or at minimum, log a warning at startup when the default key is in use.

---

### Issue #27: Frontend Dead Dependencies

**File:** `frontend/package.json`

These packages are installed but imported nowhere in the source code:

| Package | Approx Size | Used? | Note |
|---------|-------------|-------|------|
| `@tanstack/react-query` | ~50KB | No | Axios used directly with useEffect |
| `socket.io-client` | ~100KB | No | No WebSocket integration exists |
| `zustand` | ~5KB | No | React useState and props used everywhere |
| `prismjs` | ~30KB | No | No syntax highlighting in app |
| `react-syntax-highlighter` | ~500KB | No | Not imported anywhere |

**Total wasted bundle size:** ~700KB (before tree-shaking; Next.js may partially exclude unused imports, but `react-syntax-highlighter` is notably large)

**Fix:**
```powershell
cd frontend
npm uninstall @tanstack/react-query socket.io-client zustand prismjs react-syntax-highlighter
```

---

### Issue #28: Dead Frontend File

**File:** `frontend/src/app/theme.ts`

This file exports a MUI theme object but is never imported by any other file. The actual theme used by the app is defined inline in `providers.tsx`:

```typescript
// providers.tsx:
const theme = createTheme({
    palette: { ... },
    typography: { ... },
});
```

`theme.ts` duplicates this configuration. It should either be deleted, or `providers.tsx` should import it instead of re-defining.

---

### Issue #29: `pinecone-client==2.2.4` — Dead Backend Dependency

**File:** `backend/requirements.txt` line 33

The Pinecone v2 SDK (`pinecone-client`) is fully deprecated — the replacement is the `pinecone` package (v3+). The only reference in the codebase is `_init_pinecone()` in `vector_store.py` which raises:
```python
def _init_pinecone(self):
    raise NotImplementedError("Pinecone integration coming soon")
```

Keeping the deprecated package:
- Adds attack surface via a no-longer-maintained dependency
- Causes pip resolver warnings
- Adds ~20MB to the venv

**Fix:** Remove from `requirements.txt`.

---

### Issue #30: `alembic.ini` Port Mismatch

**File:** `backend/alembic.ini`

Hardcodes `sqlalchemy.url = postgresql://crashbot:crashbot_password@localhost:5432/crashbot_db` (port 5432). Docker maps PostgreSQL to port **5435**. The `env.py` `run_migrations_online()` function overrides this URL from the Settings object, but running `alembic` CLI directly (e.g., `alembic upgrade head`) uses the ini file first and fails to connect.

**Fix:** Either:
1. Update the port in `alembic.ini` to 5435
2. Or set `DATABASE_URL` in `.env` and ensure `env.py` always overrides the ini URL (it currently does, so this is a minor issue)

---

### Issue #31: Test Mock Data Fails Magic Byte Validation

**File:** `backend/tests/conftest.py` — `temp_dump_file` fixture

```python
@pytest.fixture
def temp_dump_file(tmp_path):
    dump_file = tmp_path / "test_crash.dmp"
    dump_file.write_bytes(b"MOCK_DUMP_FILE_CONTENT")  # NOT valid magic bytes
    return str(dump_file)
```

The upload endpoint validates magic bytes (must start with `MDMP`, `PAGEDUMP`, `\x7FELF`, `\xCF\xFA\xED\xFE` etc.). `b"MOCK_DUMP_FILE_CONTENT"` doesn't match any valid signature, so `test_upload_crash_dump_success` fails at the validation step before reaching any business logic.

**Fix:**
```python
@pytest.fixture
def temp_dump_file(tmp_path):
    dump_file = tmp_path / "test_crash.dmp"
    dump_file.write_bytes(b"MDMP" + b"\x00" * 1024)  # Valid Windows minidump header
    return str(dump_file)
```

Alternatively, create fixtures for each platform:
```python
@pytest.fixture
def windows_dump(tmp_path):
    f = tmp_path / "test.dmp"
    f.write_bytes(b"MDMP" + b"\x00" * 1024)
    return f

@pytest.fixture
def linux_dump(tmp_path):
    f = tmp_path / "test.core"
    f.write_bytes(b"\x7fELF" + b"\x00" * 1024)
    return f
```

---

### Issue #32: CSS Variables Undefined Outside Media Queries

**File:** `frontend/src/app/globals.css`

CSS variables like `--foreground-rgb` and `--background-start-rgb` are only defined inside `@media (prefers-color-scheme: dark)` and `@media (prefers-color-scheme: light)` blocks. On initial page load, before the media query evaluates (or if the user agent doesn't support `prefers-color-scheme`), expressions like `rgb(var(--foreground-rgb))` expand to `rgb()` which is invalid CSS.

**Fix:** Define default values in `:root` (outside media queries):
```css
:root {
    --foreground-rgb: 0, 0, 0;
    --background-start-rgb: 214, 219, 220;
    --background-end-rgb: 255, 255, 255;
}
```

---

### Issue #33: Frontend `listCrashAnalyses` Type Mismatch

**File:** `frontend/src/api/client.ts` and `frontend/src/components/RecentAnalyses.tsx`

```typescript
// client.ts:
async listCrashAnalyses(): Promise<CrashAnalysis[]> {  // Returns FULL type with 30+ fields
    const response = await this.client.get('/api/v1/crashes/');
    return response.data;
}
```

But the backend `GET /` endpoint returns `List[CrashAnalysisResponse]` which only has `{id, filename, status, message, created_at}`. The `CrashAnalysis` TypeScript type expects many more fields. In `RecentAnalyses.tsx`, accessing `crash.exception_code`, `crash.platform`, `crash.severity`, etc. all return `undefined`.

**Fix:** Create a separate TypeScript type for the list response, or change the backend to return more fields in the list endpoint.

---

## 5. Architecture Overview

### Backend Module Map

```
backend/
├── app/
│   ├── main.py                          # FastAPI app, CORS, lifespan
│   ├── __init__.py
│   ├── core/
│   │   ├── config.py                    # 153 lines — Pydantic settings (33 feature flags)
│   │   ├── security.py                  # 56 lines — JWT, bcrypt, API keys (UNUSED)
│   │   ├── logging.py                   # 91 lines — Structured JSON logger
│   │   └── __init__.py
│   ├── db/
│   │   ├── base.py                      # 11 lines — declarative_base (deprecated API)
│   │   ├── session.py                   # 34 lines — async engine + session factory
│   │   ├── models/
│   │   │   ├── crash.py                 # 89 lines — CrashAnalysis model (30 columns)
│   │   │   ├── user.py                  # 24 lines — User model (unused)
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── api/v1/
│   │   ├── router.py                    # 12 lines — includes crashes router only
│   │   ├── endpoints/
│   │   │   ├── crashes.py               # 680 lines — ALL endpoints (12 routes)
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   ├── crash.py                 # 93 lines — Pydantic models (has type mismatches)
│   │   │   ├── batch.py                 # 126 lines — Phase 5 schemas
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── llm/
│   │   ├── analyzer.py                  # 535 lines — LLM integration (BROKEN: syntax + API)
│   │   ├── cache.py                     # 141 lines — Redis LLM cache (working)
│   │   └── __init__.py
│   ├── rag/
│   │   ├── vector_store.py              # 416 lines — ChromaDB + Siemens embeddings
│   │   └── __init__.py
│   ├── parsers/
│   │   ├── crash_parser.py              # 459 lines — WinDbg parser + background orchestrator
│   │   ├── universal_parser.py          # 178 lines — Multi-platform router (match/case)
│   │   ├── linux_parser.py              # 256 lines — GDB-based parser (async)
│   │   ├── macos_parser.py              # 241 lines — LLDB-based parser (async)
│   │   ├── types.py                     # 96 lines — Dataclasses (has to_dict bug)
│   │   └── __init__.py
│   └── ml/
│       ├── batch_analysis.py            # 116 lines — Find patterns across crashes
│       ├── chat.py                      # 101 lines — Conversational follow-ups (bug #20)
│       ├── crash_clustering.py          # 291 lines — TF-IDF + DBSCAN clustering
│       ├── severity_classifier.py       # 246 lines — Rule-based severity scoring
│       ├── integrations.py              # 215 lines — Slack/JIRA/GitHub (missing config)
│       └── __init__.py
├── tests/
│   ├── conftest.py                      # 106 lines — Fixtures (invalid mock data)
│   ├── test_upload.py                   # 89 lines — 7 upload tests
│   ├── test_llm.py                      # 160 lines — 8 LLM tests
│   └── test_parser.py                   # 83 lines — 6 parser tests
├── alembic/
│   └── versions/
│       ├── 001_initial.py               # Out of sync with models
│       ├── 002_add_indexes.py           # References non-existent column
│       └── 003_similar_crashes.py       # Adds already-existing column
├── requirements.txt                     # 67 packages (3 dead)
├── Dockerfile
├── pytest.ini
└── alembic.ini                          # Wrong port
```

**Total backend Python:** ~3,500 lines across 24 files
**Estimated working code:** ~2,400 lines (after excluding broken analyzer.py section)

### Data Flow

```
User uploads .dmp file
    → POST /upload validates magic bytes, computes SHA256, checks for duplicate
    → File saved to storage/dumps/
    → CrashAnalysis record created (status="pending")
    → BackgroundTask: analyze_crash_dump_async()
        → WinDbgParser.parse() runs cdb.exe commands (needs WinDbg)
        → VectorStore.find_similar_crashes() (ChromaDB — empty)
        → LLMAnalyzer.analyze_crash() sends prompt to Siemens AI / OpenAI / Anthropic
        → LLMCache checks Redis before calling LLM
        → Results stored in crash.llm_analysis JSON column
        → status updated to "completed"
    → Frontend polls GET /{crash_id} until status == "completed"
    → Analysis detail page renders llm_analysis data (BROKEN — see Bug #4)
```

### Configuration System

`app/core/config.py` uses Pydantic `BaseSettings` with env file support. Key feature flags:

| Flag | Default | Purpose |
|------|---------|---------|
| `ENABLE_BATCH_ANALYSIS` | `True` | POST /batch endpoint |
| `ENABLE_CHAT_FOLLOWUP` | `True` | POST /{crash_id}/chat endpoint |
| `ENABLE_CODE_INTEGRATION` | `True` | Slack/JIRA/GitHub integrations |
| `ENABLE_ML_CLASSIFICATION` | `True` | POST /classify-severity endpoint |
| `ENABLE_CRASH_CLUSTERING` | `True` | POST /cluster endpoint |
| `ENABLE_FUNCTION_CALLING` | `True` | OpenAI function calling mode |
| `ENABLE_MULTI_MODEL_ENSEMBLE` | `False` | Multi-model consensus analysis |
| `DEBUG` | `True` | SQLAlchemy echo, verbose logging |
| `ENVIRONMENT` | `"development"` | Controls NullPool in tests |

---

## 6. File-by-File Status

### Backend Core

| File | Lines | Bugs | Status |
|------|-------|------|--------|
| `main.py` | 67 | None directly, but lifespan doesn't create storage dirs (#11) | **Works** (once imports fixed) |
| `core/config.py` | 153 | Missing JIRA/GitHub fields (#24) | **Works** |
| `core/security.py` | 56 | None — but completely unused (#6) | **Works** (dead code) |
| `core/logging.py` | 91 | `datetime.utcnow()` (#14) | **Works** |
| `db/base.py` | 11 | Deprecated import (#15), deprecated utcnow (#14) | **Works** (deprecated APIs) |
| `db/session.py` | 34 | pool_size vs NullPool (#21) | **Works** (misleading config) |
| `db/models/crash.py` | 89 | `completed_at` type mismatch (#17) | **Works** (data type issue) |
| `db/models/user.py` | 24 | Migration mismatch (#8), never used | **Works** (dead code) |

### Backend API

| File | Lines | Bugs | Status |
|------|-------|------|--------|
| `api/v1/router.py` | 12 | None | **Works** |
| `api/v1/endpoints/crashes.py` | 680 | Route order (#3), pagination (#9), orphan files (#10), no mkdir (#11), sync I/O (#12), utcnow (#14), no auth (#6) | **Partially works** |
| `api/v1/schemas/crash.py` | 93 | `solutions` type (#5), missing `llm_analysis` (#4) | **Schema incorrect — API responses wrong** |
| `api/v1/schemas/batch.py` | 126 | None | **Works** |

### Backend LLM

| File | Lines | Bugs | Status |
|------|-------|------|--------|
| `llm/analyzer.py` | 535 | **SYNTAX ERROR** (#1), openai v2 (#2), integer division (#19) | **BROKEN — prevents app startup** |
| `llm/cache.py` | 141 | None | **Works** (requires Redis running) |

### Backend RAG

| File | Lines | Bugs | Status |
|------|-------|------|--------|
| `rag/vector_store.py` | 416 | Uses correct openai client pattern (partial) | **Mostly works** (empty ChromaDB) |

### Backend Parsers

| File | Lines | Bugs | Status |
|------|-------|------|--------|
| `parsers/crash_parser.py` | 459 | `get_event_loop()` (#13), utcnow (#14), imports broken analyzer | **Code correct, import chain broken** |
| `parsers/universal_parser.py` | 178 | None | **Works** |
| `parsers/linux_parser.py` | 256 | None (needs GDB installed) | **Works** (Linux only) |
| `parsers/macos_parser.py` | 241 | None (needs LLDB installed) | **Works** (macOS only) |
| `parsers/types.py` | 96 | `to_dict()` bug (#7) | **Partially broken** |

### Backend ML

| File | Lines | Bugs | Status |
|------|-------|------|--------|
| `ml/batch_analysis.py` | 116 | None | **Works** |
| `ml/chat.py` | 101 | Private method call (#20), utcnow (#14) | **Partially broken** |
| `ml/crash_clustering.py` | 291 | None | **Works** |
| `ml/severity_classifier.py` | 246 | None | **Works** |
| `ml/integrations.py` | 215 | No timeouts (#25), missing config (#24) | **Non-functional** |

---

## 7. Frontend Analysis

### File Status

| File | Lines | Issues | Status |
|------|-------|--------|--------|
| `src/app/page.tsx` | 81 | None | **Works** |
| `src/app/layout.tsx` | 77 | None | **Works** |
| `src/app/providers.tsx` | 88 | None | **Works** |
| `src/app/globals.css` | ~200 | CSS vars in media queries only (#32) | **Minor visual bug** |
| `src/app/theme.ts` | ~30 | Never imported (#28) | **Dead file** |
| `src/app/analysis/[id]/page.tsx` | 280 | `llm_analysis` field missing from API (#4) | **Broken — shows no AI results** |
| `src/components/FileUpload.tsx` | 65 | None | **Works** |
| `src/components/RecentAnalyses.tsx` | 96 | Wrong response type (#33) | **Shows partial/missing data** |
| `src/visualizations/StackTraceVisualization.tsx` | 95 | Not integrated into any page | **Dead code** |
| `src/visualizations/ThreadTimeline.tsx` | 78 | XSS risk (#22), not integrated | **Dead code with security issue** |
| `src/api/client.ts` | 173 | SSR localStorage crash (#23), type mismatch (#33) | **Partially broken** |

### Frontend Dependencies

```json
{
  "next": "14.0.4",
  "react": "18.2.0",
  "@mui/material": "^5.15.0",
  "@mui/icons-material": "^5.15.0",
  "@emotion/react": "^11.11.0",
  "@emotion/styled": "^11.11.0",
  "axios": "^1.6.2",
  "d3": "^7.8.5",
  "mermaid": "^11.12.1"
}
```

**Dead packages (not imported anywhere):**
- `@tanstack/react-query` — React Query v5, but all data fetching uses raw axios + useEffect
- `socket.io-client` — no WebSocket server exists
- `zustand` — no state management beyond component-level useState
- `prismjs` — no syntax highlighting feature
- `react-syntax-highlighter` — ~500KB, never imported

### Frontend-Backend API Contract

The frontend expects the following API shape that doesn't match the backend:

| Frontend expects | Backend returns | Mismatch? |
|------------------|----------------|-----------|
| `analysis.llm_analysis.root_cause` | `analysis.root_cause` (but never populated) | **YES** |
| `analysis.llm_analysis.confidence` (0-1) | `analysis.confidence_score` (0-100, never populated) | **YES** |
| `analysis.llm_analysis.solutions` (array of objects) | `analysis.solutions` (typed as List[str]) | **YES** |
| `analysis.llm_analysis.references` | `analysis.references` (never populated) | **YES** |
| List: 30+ fields per crash | List: only `{id, filename, status, message, created_at}` | **YES** |

---

## 8. Test Suite Analysis

### Current State: No Tests Can Run

The entire test suite fails to import because `conftest.py` imports `app.main`, which imports `app.api.v1.endpoints.crashes`, which imports `app.parsers.crash_parser`, which imports `app.llm.analyzer` — which has the syntax error.

```
$ pytest -v
ERRORS:
E   File "app/llm/analyzer.py", line 402
E       self.tokens_used["input\"] = response.usage.prompt_tokens
E                        ^
E   SyntaxError: unterminated string literal (detected at line 402)
```

### Test-by-Test Analysis (after fixing Bug #1)

**`test_upload.py` — 7 tests:**

| Test | Expected Result | Issue |
|------|----------------|-------|
| `test_upload_crash_dump_success` | **FAIL** | Mock data `b"MOCK_DUMP_FILE_CONTENT"` fails magic byte validation (#31) |
| `test_upload_invalid_file_type` | **PASS** | Tests `.txt` extension rejection — should work |
| `test_upload_file_too_large` | **FAIL** | Creates 600MB BytesIO in memory — may OOM on CI; status assertion expects 400 or 413 |
| `test_get_crash_analysis` | **FAIL** | Depends on successful upload (which fails due to #31) |
| `test_get_nonexistent_crash` | **PASS** | Tests 404 for invalid UUID — should work |
| `test_list_crash_analyses` | **PASS** | Tests empty list response — should work |
| `test_delete_crash_analysis` | **FAIL** | Depends on successful upload (which fails due to #31) |

**Expected pass rate: ~43%** (3/7 after fixing imports)

**`test_llm.py` — 8 tests:**

| Test | Expected Result | Issue |
|------|----------------|-------|
| `test_llm_initialization` | **PASS** | Tests `LLMAnalyzer()` constructor — should work |
| `test_prompt_building` | **PASS** | Tests `_build_analysis_prompt()` string output — should work |
| `test_stack_trace_formatting` | **PASS** | Tests string formatting helper — should work |
| `test_response_parsing` | **PASS** | Tests `_parse_response()` JSON parsing — should work |
| `test_response_parsing_invalid_json` | **PASS** | Tests fallback for malformed JSON — should work |
| `test_openai_api_mocking` | **FAIL** | Mocks `openai.chat.completions.create` at module level — doesn't exist in v2 (#2) |
| `test_siemens_provider` | **FAIL** | Tests `openai.api_key = ...` module attribute — removed in v2 (#2) |
| `test_analyze_with_llm_function` | **FAIL** | Calls `analyze_with_llm()` which is in the corrupted section (#1) |

**Expected pass rate: ~63%** (5/8 after fixing syntax, before fixing openai v2)

**`test_parser.py` — 6 tests:**

| Test | Expected Result | Issue |
|------|----------------|-------|
| `test_parser_initialization` | **PASS** | Tests `WinDbgParser()` constructor — should work |
| `test_cdb_command_execution` | **SKIP** | Requires WinDbg/cdb.exe installed — not available in CI |
| `test_command_timeout` | **PASS** | Tests timeout handling with mock — should work |
| `test_extract_exception_code` | **PASS/FAIL** | Depends on exact regex pattern vs test input format |
| `test_extract_stack_trace` | **FAIL** | Test input string format doesn't match the regex pattern used in production |
| `test_real_dump_parsing` | **SKIP** | Requires WinDbg + real .dmp file |

**Expected pass rate: ~40%** (2–3/6)

### Overall Test Health

- **Total tests:** 21
- **Expected to pass after fixing Bug #1:** ~10 (48%)
- **Expected to pass after fixing Bugs #1, #2, #31:** ~16 (76%)
- **Remaining failures:** require WinDbg, real .dmp files, or regex pattern updates
- **Test command:** `cd backend && ..\venv\Scripts\pytest -v --tb=short`

---

## 9. Alembic Migration Analysis

### Summary

**All three migrations are broken** and cannot be applied sequentially against a fresh database.

| Migration | Creates/Modifies | Problem |
|-----------|-----------------|---------|
| `001_initial.py` | `users`, `crash_analyses` tables | 10+ column type/name mismatches with ORM models |
| `002_add_indexes.py` | Composite indexes | References `severity` column that doesn't exist in 001 |
| `003_similar_crashes.py` | Adds `similar_crashes` column | Column already exists in 001 |

### Why It Currently Works

`main.py` uses `Base.metadata.create_all()` in the lifespan function, which creates tables directly from SQLAlchemy model definitions. This bypasses Alembic entirely. As long as developers don't run `alembic upgrade head`, the database schema matches the models.

### Recommendation

**Option A (Recommended):** Delete all migrations and regenerate:
```powershell
cd backend
Remove-Item alembic\versions\001*.py, alembic\versions\002*.py, alembic\versions\003*.py
..\venv\Scripts\alembic revision --autogenerate -m "initial_schema"
```

**Option B:** Accept that `create_all()` is the migration strategy. Remove `alembic/` directory and `alembic.ini`. Simpler but loses migration capabilities.

**Option C:** Write a corrective migration 004 that brings the schema in line with models. Most complex, preserves history.

---

## 10. Docker & Infrastructure

### `docker-compose.yml` Services

| Service | Image | Port | Status |
|---------|-------|------|--------|
| `database` | `postgres:15-alpine` | 5435:5432 | **Works** |
| `redis` | `redis:7-alpine` | 6381:6379 | **Works** |
| `backend` | Built from `./backend/Dockerfile` | 8002:8002 | **Broken** (syntax error — Bug #1) |
| `frontend` | Built from `./frontend/Dockerfile` | 3002:3002 | **Works** (limited by SSR bug #23) |
| `worker` | Same as backend image | None | **Crashes** (missing celery module — Bug #16) |
| `flower` | Same as backend image | 5555:5555 | **Crashes** (missing celery module — Bug #16) |

### `docker-compose.dev.yml`

Only runs `database` and `redis` for local development. **Works correctly.**

```powershell
# Start database and Redis for local dev:
docker-compose -f docker-compose.dev.yml up -d
```

### Docker-Specific Issues

**1. Missing `SIEMENS_API_KEY` in backend container:**
```yaml
backend:
  environment:
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    # SIEMENS_API_KEY is NOT passed — but LLM_PROVIDER defaults to "siemens"
```
Since `LLM_PROVIDER` defaults to `"siemens"`, the backend container can't make LLM calls.

**2. Frontend API URL in Docker:**
`client.ts` defaults API base to `http://localhost:8002`. In Docker, the frontend container runs in its own network namespace where `localhost` is itself, not the backend. The `next.config.js` has rewrites:
```javascript
async rewrites() {
    return [{ source: '/api/:path*', destination: 'http://localhost:8002/api/:path*' }];
}
```
This works for **client-side** requests (browser → host → backend) but fails for **server-side** rendering (frontend container → localhost → nothing).

**3. Commented-out monitoring services:**
```yaml
# prometheus:
#   image: prom/prometheus:v2.48.0
#   volumes:
#     - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
#   ports:
#     - "9090:9090"
# grafana:
#   image: grafana/grafana:10.2.0
#   ports:
#     - "3001:3000"
```
Prometheus config file exists at `monitoring/prometheus.yml/` (note: this is a **directory**, not a file — may cause mount issues). No Grafana dashboards or data sources are configured.

---

## 11. venv & Dependencies

### Python Environment

| Property | Value |
|----------|-------|
| Python version | 3.12.10 |
| venv location | `./venv/` |
| Created | November 17, 2025 |
| Base interpreter | `C:\Users\z00541ce\AppData\Local\Programs\Python\Python312\python.exe` |

### Installed Package Summary

**Total: 150+ packages** (all `requirements.txt` dependencies satisfied)

### Notable Version Issues

| Package | Required | Installed | Issue |
|---------|----------|-----------|-------|
| `openai` | `>=1.12.0` | `2.8.0` | v2.x has breaking API changes (Bug #2) |
| `pinecone-client` | `==2.2.4` | `2.2.4` | Deprecated, replaced by `pinecone` v3; never used (#29) |
| `sentence-transformers` | `==2.2.2` | `2.2.2` | Released 2023, v3.x available with breaking changes |
| `sentry-sdk` | `==1.38.0` | `1.38.0` | v1.x is legacy, v2.x available; no DSN configured anyway |
| `weasyprint` | `==60.1` | `60.1` | Requires Cairo/Pango native libs on Windows; PDF export not implemented |

### Packages Installed But Not in `requirements.txt`

| Package | Version | Disk Size | Used in Code? |
|---------|---------|-----------|---------------|
| `torch` | 2.9.1 | ~2.5GB | No — commented out in requirements.txt |
| `transformers` | 4.57.1 | ~500MB | No — commented out in requirements.txt |
| `torchvision` | 0.24.1 | ~50MB | No — pulled as torch dependency |
| `torchaudio` | 2.9.1 | ~30MB | No — pulled as torch dependency |

These were installed manually and consume ~3GB of disk space. They are not used anywhere in the codebase. The `crash_clustering.py` uses scikit-learn's TF-IDF/DBSCAN (which is lightweight), and `severity_classifier.py` uses rule-based scoring (no ML model).

### Packages in `requirements.txt` That Are Unused

| Package | Why Unused |
|---------|-----------|
| `pinecone-client==2.2.4` | `_init_pinecone()` raises `NotImplementedError` |
| `weasyprint==60.1` | PDF export feature not implemented |
| `flower==2.0.1` | Celery worker module doesn't exist |
| `sentry-sdk[fastapi]==1.38.0` | No Sentry DSN configured, no instrumentation in code |

### Recommended `requirements.txt` Cleanup

```diff
# REMOVE these:
- pinecone-client==2.2.4    # Dead dependency
- weasyprint==60.1           # Feature not implemented, requires native libs
- flower==2.0.1              # No Celery worker module
- sentry-sdk[fastapi]==1.38.0  # Not configured

# PIN these (currently unpinned or loosely pinned):
  openai>=1.12.0  →  openai==2.8.0   # Pin to tested version
```

---

## 12. Security Audit

### Critical Security Findings

| # | Issue | Severity | File | Details |
|---|-------|----------|------|---------|
| S1 | No authentication on any endpoint | **Critical** | `crashes.py` | All data readable/writable by anyone (Bug #6) |
| S2 | XSS via Mermaid `securityLevel: 'loose'` | **High** | `ThreadTimeline.tsx` | Crash data rendered as HTML (Bug #22) |
| S3 | Hardcoded `SECRET_KEY` | **High** | `config.py` | Trivially forgeable JWTs if deployed without .env (Issue #26) |
| S4 | No rate limiting | **Medium** | `main.py` | LLM calls cost money; no throttle on upload/analyze |
| S5 | HTTP timeouts missing | **Medium** | `integrations.py` | Thread pool exhaustion via slow external APIs (Bug #25) |
| S6 | `localStorage` token storage | **Low** | `client.ts` | Vulnerable to XSS; HttpOnly cookie is more secure |
| S7 | CORS allows all configured origins | **Low** | `main.py` | Default includes only `localhost` — OK for dev |
| S8 | No input sanitization on filenames | **Low** | `crashes.py` | Uses `secure_filename()` from Werkzeug — adequate |

### Authentication Gap Analysis

The security module (`security.py`) provides:
- Password hashing: `bcrypt` with automatic salt
- API key generation: `secrets.token_urlsafe(32)` — cryptographically secure
- API key hashing: SHA256 with configurable salt
- JWT creation: HS256, 30-minute expiry by default
- JWT validation: Checks expiry and signature

**What's missing to enforce auth:**
1. A `get_current_user` dependency function that extracts and validates the JWT/API key from request headers
2. User registration and login endpoints
3. `Depends(get_current_user)` on all protected endpoints
4. A way to create the first admin user (CLI command or migration seed)

---

## 13. Fix Priority Order & Roadmap

### Phase A: Make the App Start

| # | Task | File | Impact |
|---|------|------|--------|
| A1 | Fix syntax corruption — replace `\"` with `"` in lines 402–529 | `llm/analyzer.py` | **Unblocks everything** |
| A2 | Refactor `LLMAnalyzer.__init__()` to use `openai.OpenAI()` client | `llm/analyzer.py` | LLM calls work |
| A3 | Replace `openai.chat.completions.create(...)` with `self.client.chat.completions.create(...)` | `llm/analyzer.py` | LLM calls work |
| A4 | Add `os.makedirs(settings.DUMP_STORAGE_PATH, exist_ok=True)` | `main.py` lifespan | First upload works |

**Verification:**
```powershell
cd backend
..\venv\Scripts\python -m py_compile app/llm/analyzer.py
..\venv\Scripts\python -c "import app.main; print('OK')"
```

### Phase B: Make the API Correct

| # | Task | File | Impact |
|---|------|------|--------|
| B1 | Reorder routes: specific before `/{crash_id}` | `endpoints/crashes.py` | All endpoints reachable |
| B2 | Add `llm_analysis: Optional[Dict[str, Any]]` to `CrashAnalysisDetail` | `schemas/crash.py` | Frontend shows AI results |
| B3 | Fix `solutions` type to `Optional[List[SolutionItem]]` | `schemas/crash.py` | Response validation passes |
| B4 | Fix `to_dict()` to use `dataclasses.asdict()` | `parsers/types.py` | Multi-platform parsing works |
| B5 | Fix query order: `.where()` before `.offset().limit()` | `endpoints/crashes.py` | Correct pagination |
| B6 | Use `aiofiles` for file writes | `endpoints/crashes.py` | Non-blocking I/O |
| B7 | Fix `.env.example` to use `postgresql+asyncpg://` | `.env.example` | New devs don't hit errors |
| B8 | Wrap file write in try/except for orphan cleanup | `endpoints/crashes.py` | No leaked files on failure |

### Phase C: Make Tests Pass

| # | Task | File | Impact |
|---|------|------|--------|
| C1 | Fix `temp_dump_file` to use `b"MDMP" + padding` | `conftest.py` | Upload tests pass |
| C2 | Fix test assertions: status 201 not 200 for upload | `test_upload.py` | Correct assertions |
| C3 | Fix LLM test mocks for openai v2 client pattern | `test_llm.py` | LLM tests pass |
| C4 | Fix parser test input format to match regex patterns | `test_parser.py` | Parser tests pass |
| C5 | Delete and regenerate Alembic migrations | `alembic/versions/` | Clean migration history |

### Phase D: Fix Remaining Bugs

| # | Task | Bug # | File |
|---|------|-------|------|
| D1 | Replace `asyncio.get_event_loop()` with `get_running_loop()` | #13 | `crash_parser.py` |
| D2 | Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` | #14 | 5 files |
| D3 | Replace deprecated `declarative_base()` | #15 | `db/base.py` |
| D4 | Fix or remove Docker worker/flower services | #16 | `docker-compose.yml` |
| D5 | Fix `completed_at` to `DateTime` type | #17 | `db/models/crash.py` |
| D6 | Fix integer division in ensemble averaging | #19 | `llm/analyzer.py` |
| D7 | Fix `CrashChatbot` to use public method | #20 | `ml/chat.py` |
| D8 | Fix engine config for NullPool test mode | #21 | `db/session.py` |
| D9 | Set Mermaid `securityLevel: 'strict'` | #22 | `ThreadTimeline.tsx` |
| D10 | Guard `localStorage` with `typeof window` check | #23 | `client.ts` |
| D11 | Add JIRA/GitHub config fields | #24 | `core/config.py` |
| D12 | Add `timeout=30` to all HTTP calls | #25 | `ml/integrations.py` |

### Phase E: Security & Production

| # | Task | Priority |
|---|------|----------|
| E1 | Enforce authentication on all endpoints | **Required** before production |
| E2 | Generate strong default SECRET_KEY or fail on default | **Required** before production |
| E3 | Implement rate limiting (`slowapi` or custom middleware) | **Should have** |
| E4 | Restrict CORS to actual frontend origins | **Should have** |
| E5 | Add request logging / audit trail | **Should have** |
| E6 | Remove dead dependencies from requirements.txt and package.json | Nice to have |
| E7 | Clean up dead frontend files (theme.ts, unused components) | Nice to have |
| E8 | Implement Celery workers OR remove from docker-compose | Nice to have |
| E9 | Configure Sentry or remove SDK | Nice to have |

---

## 14. External Dependencies (Blocked)

These require resources that can't be created through code changes:

### WinDbg / CDB Installation

**Required for:** Actual Windows crash dump parsing
**Status:** Code is 100% ready in `crash_parser.py` (lines ~45–190)
**Config field:** `WINDBG_PATH` defaults to `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe`
**Action:** Download "Debugging Tools for Windows" from the Windows SDK:
```
https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/debugger-download-tools
```
After installation, verify: `& "C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe" -version`

### Real .dmp Files

**Required for:** End-to-end testing, prompt engineering, validation of parser regex patterns
**Action:** Obtain 5–10 crash dumps covering different exception types:
- Access violation (`0xC0000005`) — most common
- Stack overflow (`0xC00000FD`) — recursive functions
- Heap corruption (`0xC0000374`) — buffer overflows
- Null pointer dereference — subset of `0xC0000005`
- Use-after-free — heap-related crashes

### LLM API Keys

**Required for:** AI-powered root cause analysis
**Supported providers (in `config.py`):**
- Siemens AI (primary): `SIEMENS_API_KEY` + `LLM_BASE_URL` — uses `qwen3-30b-a3b-instruct-2507` model
- OpenAI (fallback): `OPENAI_API_KEY` — uses `gpt-4o-mini`
- Anthropic (fallback): `ANTHROPIC_API_KEY` — uses `claude-3-haiku-20240307`

**Action:** Obtain at least one valid API key and add to `.env`.

### ChromaDB Seed Data

**Required for:** RAG similarity search to find past similar crashes
**Status:** Vector store code works, ChromaDB collection is empty
**Action:** After fixing bugs and obtaining real crashes, analyze 50+ dumps to build the vector database. Each analyzed crash is automatically added via `vector_store.add_crash_embedding()` in the background task pipeline.

---

## 15. What Actually Works Today

Once the critical bugs (#1, #2) are fixed, these features function correctly:

### Infrastructure & Framework
| Feature | Status |
|---------|--------|
| FastAPI app startup with async lifespan | Works |
| CORS middleware with configurable origins | Works |
| GZip compression middleware | Works |
| Health check endpoint (`GET /health`) | Works |
| Root info endpoint (`GET /`) with version/status | Works |
| Swagger/OpenAPI docs (`/docs`) and ReDoc (`/redoc`) | Works |
| Structured JSON logging with rotation | Works |
| PostgreSQL async ORM (SQLAlchemy 2.0 + asyncpg) | Works |
| Redis connection for LLM caching | Works (Redis must be running) |

### Upload & Storage
| Feature | Status |
|---------|--------|
| File upload with extension validation | Works |
| Magic byte validation (MDMP, ELF, Mach-O, PAGEDUMP) | Works |
| SHA256 deduplication (returns existing if hash matches) | Works |
| Background task orchestration via BackgroundTasks | Works |
| Pydantic validation on all request/response schemas | Works |

### ML & Analytics
| Feature | Status |
|---------|--------|
| Severity classification (rule-based scoring) | Works |
| TF-IDF crash clustering with DBSCAN | Works |
| Batch pattern analysis | Works |
| ChromaDB vector store initialization | Works (empty collection) |

### Security (Built, Not Enforced)
| Feature | Status |
|---------|--------|
| JWT token creation/verification (HS256) | Works (not used) |
| Bcrypt password hashing | Works (not used) |
| API key generation (secrets.token_urlsafe) | Works (not used) |
| API key hashing (SHA256 + salt) | Works (not used) |

### Frontend
| Feature | Status |
|---------|--------|
| Next.js 14 app with MUI 5 component library | Works |
| Drag-and-drop file upload UI | Works |
| Recent analyses list (with partial data) | Works |
| Analysis detail page with status polling | Works (empty until Bug #4 fixed) |
| MUI theme with responsive layout | Works |

---

## 16. Remaining Feature Work

Features that are scaffolded or planned but not yet functional:

| Feature | Code Exists? | Lines | Blocked By |
|---------|-------------|-------|------------|
| Windows crash dump parsing (WinDbg/CDB) | Yes | 459 lines in `crash_parser.py` | WinDbg not installed |
| Linux crash dump parsing (GDB) | Yes | 256 lines in `linux_parser.py` | GDB not available on Windows |
| macOS crash dump parsing (LLDB) | Yes | 241 lines in `macos_parser.py` | LLDB not available on Windows |
| LLM root cause analysis | Yes | 535 lines in `analyzer.py` | Bug #1, Bug #2 |
| Multi-model ensemble analysis | Yes | 80 lines in `analyzer.py` | Bug #1, Bug #2, `ENABLE_MULTI_MODEL_ENSEMBLE=False` |
| LLM function calling mode | Yes | 110 lines in `analyzer.py` | Bug #1, Bug #2, `ENABLE_FUNCTION_CALLING=True` |
| RAG similar crash search | Yes | 416 lines in `vector_store.py` | Empty ChromaDB — need seed data |
| Conversational chat follow-ups | Yes | 101 lines in `chat.py` | Bug #20 (private method), Bug #1 |
| Slack notifications | Yes | 60 lines in `integrations.py` | Missing `SLACK_WEBHOOK_URL` in .env |
| JIRA ticket creation | Yes | 80 lines in `integrations.py` | Missing config fields (#24) |
| GitHub issue creation | Yes | 75 lines in `integrations.py` | Missing config fields (#24) |
| PDF export | Button in UI | 0 lines of export code | Feature not implemented |
| D3.js stack trace visualization | Component only | 95 lines in `StackTraceVisualization.tsx` | Not imported into any page |
| Mermaid thread timeline | Component only | 78 lines in `ThreadTimeline.tsx` | Not imported, XSS risk (#22) |
| Celery distributed workers | Docker config only | 0 lines of worker code | Module doesn't exist (#16) |
| Prometheus metrics | Docker config only | 0 lines of instrumentation | Monitoring dir is empty |
| Grafana dashboards | N/A | 0 dashboards | No data source, no dashboards |
| User registration/login | Model only | 24 lines in `user.py` (model) | No endpoints, auth not enforced (#6) |
| Dark mode toggle | Theme infra | Theme exists in `theme.ts` | Toggle UI not built |
| WebSocket real-time updates | Dependency only | `socket.io-client` installed | No server-side WebSocket handler |

---

**Document end. Total tracked issues: 33 bugs + 19 remaining features.**

**Bug severity breakdown:**
- Critical: 2 (app cannot start)
- High: 6 (broken features)
- Medium: 17 (incorrect behavior, deprecated APIs)
- Low: 8 (code quality, dead code)

**Next action:** Fix Bug #1 (syntax corruption in `analyzer.py` lines 402–529) and Bug #2 (openai v2 client pattern), then verify with:
```powershell
cd backend
..\venv\Scripts\python -m py_compile app/llm/analyzer.py
..\venv\Scripts\python -c "import app.main; print('OK')"
```
