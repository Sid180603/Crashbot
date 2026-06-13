# Crashbot - AI-Powered Crash Dump Analyzer

An intelligent crash dump analysis system that uses AI (LLMs) to provide actionable insights from crash dump files (.dmp, .core).

## Features (Planned)

- Automated crash dump parsing (Windows via WinDbg, Linux via GDB, macOS via LLDB)
- AI-powered root cause analysis using LLMs (OpenAI / Anthropic)
- Similar crash lookup using RAG (ChromaDB vector search)
- Interactive stack trace visualizations (D3.js)
- Batch analysis, clustering, severity classification (ML)
- JIRA / Slack / GitHub integrations

## Current State

> **Last reviewed: June 2026**

This project is in **active development**. The backend now starts: the syntax
corruption in `app/llm/analyzer.py` has been repaired and the LLM layer migrated
to the `openai>=1.0` client API. See
[REMAINING_WORK_AND_IMPROVEMENTS.md](REMAINING_WORK_AND_IMPROVEMENTS.md) for the
full issue list and remaining work.

| Area | Status | Notes |
|------|--------|-------|
| Backend API (FastAPI) | Imports | `app.main` loads; all routes register |
| Frontend (Next.js) | Scaffolded | Renders, but API integration has type mismatches |
| Database (PostgreSQL) | Working | Docker container healthy on port 5435 |
| Redis | Working | Docker container healthy on port 6381 |
| LLM Integration | Migrated | Now uses `openai>=1.0` client; needs a valid API key to run |
| RAG (ChromaDB) | Scaffolded | Code exists, vector DB empty (needs seed data) |
| Authentication | Not enforced | Security module exists but no endpoints use it |
| Tests | Mostly failing | ~60% of tests fail due to mock data / import errors |
| Docker (worker/flower) | Broken | Reference non-existent `app.workers.celery_app` |
| Alembic migrations | Out of sync | Models diverged from migration schema |

## Project Structure

```text
crashbot/
├── backend/                 # FastAPI backend (Python 3.12)
│   ├── app/
│   │   ├── api/v1/         # REST endpoints & Pydantic schemas
│   │   ├── core/           # Config, security, logging
│   │   ├── db/             # SQLAlchemy async models & session
│   │   ├── parsers/        # WinDbg, GDB, LLDB crash parsers
│   │   ├── llm/            # LLM analyzer & Redis cache
│   │   ├── rag/            # ChromaDB vector store
│   │   └── ml/             # Batch analysis, clustering, chat, integrations
│   ├── tests/              # pytest (async)
│   ├── alembic/            # Database migrations (out of sync)
│   ├── scripts/            # Seed data, migration utilities
│   └── requirements.txt
├── frontend/               # Next.js 14 + MUI
│   └── src/
│       ├── app/            # Pages (upload, analysis detail)
│       ├── components/     # FileUpload, RecentAnalyses
│       ├── visualizations/ # D3.js StackTrace, Mermaid ThreadTimeline
│       └── api/            # Axios API client
├── docs/                   # API reference, development guide
├── docker-compose.yml      # Full stack (DB, Redis, backend, frontend, worker)
├── docker-compose.dev.yml  # Dev-only (DB + Redis)
└── .env.example
```

## Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- WinDbg/CDB (Windows) or GDB (Linux) — for actual crash parsing

## Quick Start

### 1. Infrastructure (Database + Redis)

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp ../.env.example .env        # Edit with your settings
python -m app.main             # Runs on http://localhost:8002
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                    # Runs on http://localhost:3002
```

### 4. Full Docker Stack

```bash
docker-compose up --build
```

> **Note:** The worker and flower containers will fail — `app.workers.celery_app` does not exist yet.

## Configuration

Copy `.env.example` to `.env`. Key settings:

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://...@localhost:5435/crashbot_db` | Must use `asyncpg` driver |
| `REDIS_URL` | `redis://localhost:6381/0` | |
| `LLM_PROVIDER` | `openai` | Options: `openai`, `anthropic` |
| `LLM_MODEL` | `gpt-4o-mini` | |
| `SECRET_KEY` | `change-this-in-production` | **Change in production** |
| `OPENAI_API_KEY` | (empty) | Required for OpenAI provider |
| `ANTHROPIC_API_KEY` | (empty) | Required for Anthropic provider |

## Ports

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8002 | <http://localhost:8002/docs> |
| Frontend | 3002 | <http://localhost:3002> |
| PostgreSQL | 5435 | `localhost:5435` |
| Redis | 6381 | `localhost:6381` |

## IDE Setup (VSCode)

If Pylance shows hundreds of "import could not be resolved" warnings, point VSCode to the venv interpreter:

1. Open Command Palette → **Python: Select Interpreter**
2. Choose `./venv/Scripts/python.exe`
3. This resolves all type-stub warnings (the packages are installed in the venv, not globally)

## LLM Cost Estimates

| Provider / Model | Approx Cost Per Crash |
|------------------|-----------------------|
| OpenAI GPT-4o-mini | ~$0.01–0.03 |
| OpenAI GPT-4 | ~$0.10–0.30 |
| Anthropic Claude 3 Haiku | ~$0.002–0.005 |
| Anthropic Claude 3 Sonnet | ~$0.02–0.05 |

Redis caching reduces repeat-analysis costs by 40–60%.

## Testing

```bash
cd backend
..\venv\Scripts\python -m pytest -v --cov=app
```

> **Note:** Most tests currently fail. See [REMAINING_WORK_AND_IMPROVEMENTS.md](REMAINING_WORK_AND_IMPROVEMENTS.md) for details.

## Documentation

| Document | Description |
|----------|-------------|
| [REMAINING_WORK_AND_IMPROVEMENTS.md](REMAINING_WORK_AND_IMPROVEMENTS.md) | Full bug list, fix plan, and roadmap |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | File-by-file structure reference |
| [Crashbot-Implementation-Guide-Python312.md](Crashbot-Implementation-Guide-Python312.md) | Enhancement implementation guide |
| [Crash_Analyzer_Architecture.md](Crash_Analyzer_Architecture.md) | Original architecture design |
| [docs/api.md](docs/api.md) | API endpoint reference |
| [docs/development.md](docs/development.md) | Development workflow guide |

## License

MIT
