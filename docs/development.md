# Crashbot Development Guide

> **Last verified:** March 2026

## Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.12+ | Backend |
| Node.js | 18+ | Frontend |
| Docker & Docker Compose | Latest | Database, Redis, full-stack |
| WinDbg/CDB | Win SDK | Windows crash dump parsing (optional) |
| GDB | Latest | Linux crash dump parsing (optional) |

## Initial Setup

### 1. Start Database & Redis

```powershell
docker-compose -f docker-compose.dev.yml up -d
```

This starts only PostgreSQL (port 5435) and Redis (port 6381).

### 2. Backend Setup

```powershell
cd backend

# Create virtual environment (one-time)
python -m venv ..\venv

# Activate
..\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env (one-time)
copy ..\.env.example ..\.env
# Edit ..\.env — set at least one LLM API key

# Start server
python -m app.main
```

Backend runs at: http://localhost:8002
Swagger docs at: http://localhost:8002/docs

### 3. Frontend Setup

```powershell
cd frontend

# Install dependencies (one-time)
npm install

# Start dev server
npm run dev
```

Frontend runs at: http://localhost:3002

### 4. Full Docker Stack (Alternative)

```powershell
docker-compose up --build
```

Starts: PostgreSQL, Redis, backend, frontend, worker (crashes), flower (crashes).

> **Note:** Worker and flower containers fail because `app.workers.celery_app` does not exist. This is a known issue (Bug #16).

## Environment Variables

Copy `.env.example` to `.env` at the project root. Key settings:

```env
# Database — MUST use asyncpg driver
DATABASE_URL=postgresql+asyncpg://crashbot:crashbot_password@localhost:5435/crashbot_db

# Redis
REDIS_URL=redis://localhost:6381/0

# LLM Provider (siemens | openai | anthropic)
LLM_PROVIDER=siemens
LLM_MODEL=qwen3-30b-a3b-instruct-2507

# API keys — set at least one
SIEMENS_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Security — CHANGE for production
SECRET_KEY=change-this-in-production
```

Full list of settings: see `backend/app/core/config.py`.

## Project Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8002 | http://localhost:8002/docs |
| Frontend | 3002 | http://localhost:3002 |
| PostgreSQL | 5435 | `postgresql://localhost:5435` |
| Redis | 6381 | `redis://localhost:6381` |

## Running Tests

```powershell
cd backend
..\venv\Scripts\Activate.ps1

# Run all tests
python -m pytest -v

# Run with coverage
python -m pytest -v --cov=app --cov-report=html

# Run a specific test file
python -m pytest tests/test_upload.py -v
```

**Current state:** Tests cannot run because importing the app triggers a `SyntaxError` in `app/llm/analyzer.py`. See Bug #1 in [REMAINING_WORK_AND_IMPROVEMENTS.md](../REMAINING_WORK_AND_IMPROVEMENTS.md).

After fixing Bug #1, expected pass rate is ~48% (10/21 tests). See the test suite analysis in the bug report for per-test details.

## Code Structure

```
backend/app/
├── main.py              # App entry, CORS, lifespan
├── core/                # Config, security, logging
├── api/v1/              # Routes, schemas
├── db/                  # Models, session
├── parsers/             # WinDbg, GDB, LLDB parsers
├── llm/                 # LLM analyzer + Redis cache
├── rag/                 # ChromaDB vector store
└── ml/                  # Clustering, classification, chat, integrations
```

See [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) for full file listing.

## Development Workflow

### Making Changes

1. **Read the bug report** — [REMAINING_WORK_AND_IMPROVEMENTS.md](../REMAINING_WORK_AND_IMPROVEMENTS.md) lists every known bug with exact line numbers and fix instructions
2. **Fix Bug #1 first** — nothing works until the syntax error in `analyzer.py` is resolved
3. **Verify with:** `python -m py_compile app/llm/analyzer.py`
4. **Then verify:** `python -c "import app.main; print('OK')"`

### Adding a New Endpoint

1. Add route in `backend/app/api/v1/endpoints/crashes.py`
2. Add Pydantic schemas in `schemas/crash.py` or `schemas/batch.py`
3. Check feature flag pattern: `if not settings.ENABLE_YOUR_FEATURE: raise HTTPException(403, ...)`
4. Add test in `backend/tests/`

### Database Changes

The app uses `Base.metadata.create_all()` in the lifespan function, so model changes are applied automatically on restart. Alembic migrations exist but are out of sync with models (Bug #8) — don't run `alembic upgrade head` without fixing them first.

To add a new model column:
1. Add it to the SQLAlchemy model (`db/models/crash.py`)
2. Restart the server — `create_all()` will add the column if the table exists

### Frontend Changes

```powershell
cd frontend
npm run dev    # Hot reload enabled
```

Key files:
- [src/app/page.tsx](../frontend/src/app/page.tsx) — Home page
- [src/app/analysis/\[id\]/page.tsx](../frontend/src/app/analysis/[id]/page.tsx) — Analysis detail
- [src/api/client.ts](../frontend/src/api/client.ts) — API client (has SSR bug — Bug #23)

## Debugging

### Backend Logs

```powershell
# Console output is human-readable
# File output is JSON (in backend/logs/)

# Check if app can import
cd backend
..\venv\Scripts\python -c "import app.main"

# Compile-check a single file
..\venv\Scripts\python -m py_compile app/llm/analyzer.py
```

### Database Access

```powershell
# Via Docker
docker exec -it crashbot-database psql -U crashbot -d crashbot_db

# Via psql directly
psql -h localhost -p 5435 -U crashbot -d crashbot_db
```

### Redis Access

```powershell
# Via Docker
docker exec -it crashbot-redis redis-cli

# Directly
redis-cli -h localhost -p 6381
```

## Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SyntaxError` on import | Corrupted quotes in `analyzer.py` | Fix Bug #1 |
| `AttributeError` on `openai.api_key` | openai v2.x API change | Fix Bug #2 |
| Upload returns `FileNotFoundError` | `storage/dumps/` doesn't exist | `mkdir storage\dumps` or fix Bug #11 |
| Frontend shows no AI results | `llm_analysis` missing from schema | Fix Bug #4 |
| `alembic upgrade head` fails | Migrations out of sync | Fix Bug #8 |
| Tests won't run | Import chain hits syntax error | Fix Bug #1 first |
| Pylance shows 500+ warnings | VSCode not using venv interpreter | Select `./venv/Scripts/python.exe` |

## Key Documentation

| Document | Content |
|----------|---------|
| [REMAINING_WORK_AND_IMPROVEMENTS.md](../REMAINING_WORK_AND_IMPROVEMENTS.md) | 33 bugs with line numbers, fix roadmap |
| [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) | Full directory tree, endpoint table |
| [SIEMENS_AI_SETUP.md](../SIEMENS_AI_SETUP.md) | Siemens AI configuration |
| [Crash_Analyzer_Architecture.md](../Crash_Analyzer_Architecture.md) | Original architecture design |
| [docs/api.md](api.md) | API endpoint reference |
