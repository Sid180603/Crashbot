# Crashbot — Project Structure

> **Last verified:** March 2026 — reflects actual files on disk.

## Directory Layout

```
crashbot/
│
├── backend/                              # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI app, CORS, lifespan, health check
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py               # Pydantic BaseSettings (33 feature flags)
│   │   │   ├── logging.py              # Structured JSON logger
│   │   │   └── security.py             # JWT, bcrypt, API keys (not enforced)
│   │   │
│   │   ├── api/v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py               # Includes crashes router
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   └── crashes.py          # 12 endpoints (upload, CRUD, batch, chat, integrations)
│   │   │   └── schemas/
│   │   │       ├── __init__.py
│   │   │       ├── crash.py            # Core Pydantic models
│   │   │       └── batch.py            # Phase 5 schemas (batch, chat, integrations)
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # SQLAlchemy declarative base
│   │   │   ├── session.py              # Async engine + session factory
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── crash.py            # CrashAnalysis model (30 columns)
│   │   │       └── user.py             # User model (unused)
│   │   │
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── crash_parser.py         # WinDbg/CDB parser + background orchestrator
│   │   │   ├── universal_parser.py     # Multi-platform router (magic byte detection)
│   │   │   ├── linux_parser.py         # GDB-based parser (async)
│   │   │   ├── macos_parser.py         # LLDB-based parser (async)
│   │   │   └── types.py               # CrashData, StackFrame, ModuleInfo dataclasses
│   │   │
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── analyzer.py             # LLM integration (Siemens AI / OpenAI / Anthropic)
│   │   │   └── cache.py               # Redis LLM response cache
│   │   │
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   └── vector_store.py         # ChromaDB vector store + embeddings
│   │   │
│   │   └── ml/
│   │       ├── __init__.py
│   │       ├── batch_analysis.py       # Multi-crash pattern detection
│   │       ├── chat.py                 # Conversational follow-up chatbot
│   │       ├── crash_clustering.py     # TF-IDF + DBSCAN clustering
│   │       ├── severity_classifier.py  # Rule-based severity scoring
│   │       └── integrations.py         # Slack, JIRA, GitHub integrations
│   │
│   ├── tests/
│   │   ├── conftest.py                 # Fixtures (async client, mock DB, temp files)
│   │   ├── test_upload.py              # 7 upload endpoint tests
│   │   ├── test_llm.py                # 8 LLM integration tests
│   │   └── test_parser.py             # 6 parser tests
│   │
│   ├── alembic/
│   │   ├── env.py                      # Migration config (reads from Settings)
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 001_initial.py          # Tables (out of sync with models)
│   │       ├── 002_add_indexes.py      # Composite indexes (references missing column)
│   │       └── 003_similar_crashes.py  # Duplicate column (already in 001)
│   │
│   ├── scripts/
│   │   ├── migrate_to_siemens.py       # Siemens AI migration/test utility
│   │   └── seed_vector_db.py           # Seed ChromaDB with sample patterns
│   │
│   ├── storage/                         # Uploaded crash dumps (gitignored)
│   ├── logs/                            # Application logs (gitignored)
│   ├── requirements.txt                # 67 Python packages
│   ├── Dockerfile
│   ├── pytest.ini
│   └── alembic.ini
│
├── frontend/                            # Next.js 14 + MUI frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Home page (upload + recent list)
│   │   │   ├── layout.tsx             # Root layout with MUI providers
│   │   │   ├── providers.tsx          # MUI ThemeProvider + CssBaseline
│   │   │   ├── globals.css            # Global styles
│   │   │   ├── theme.ts              # MUI theme (unused — see providers.tsx)
│   │   │   └── analysis/
│   │   │       └── [id]/
│   │   │           └── page.tsx       # Analysis detail page with polling
│   │   │
│   │   ├── components/
│   │   │   ├── FileUpload.tsx         # Drag-and-drop file upload
│   │   │   └── RecentAnalyses.tsx     # Recent crash analyses list
│   │   │
│   │   ├── visualizations/
│   │   │   ├── StackTraceVisualization.tsx  # D3.js stack trace (not integrated)
│   │   │   └── ThreadTimeline.tsx           # Mermaid timeline (not integrated)
│   │   │
│   │   └── api/
│   │       └── client.ts             # Axios API client wrapper
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js                 # API proxy rewrites
│   ├── next-env.d.ts
│   └── Dockerfile
│
├── docs/
│   ├── api.md                          # API endpoint reference
│   └── development.md                  # Development workflow guide
│
├── monitoring/
│   └── prometheus.yml/                 # Prometheus config (directory, not file)
│
├── storage/                            # Shared storage root (gitignored)
│
├── .env                                # Environment variables (gitignored)
├── .env.example                        # Template for .env
├── .gitignore
├── docker-compose.yml                  # Full stack (DB, Redis, backend, frontend, worker, flower)
├── docker-compose.dev.yml              # Dev-only (DB + Redis)
├── health-check.ps1                    # PowerShell service health checker
├── setup.bat                           # Windows setup script
├── start_local.bat                     # Local start script
│
├── README.md                           # Project overview & quick start
├── REMAINING_WORK_AND_IMPROVEMENTS.md  # Bug report & fix roadmap (1362 lines)
├── PROJECT_STRUCTURE.md                # This file
├── Crash_Analyzer_Architecture.md      # Original architecture design doc
├── Crashbot-Implementation-Guide-Python312.md  # Python 3.12 feature guide
├── SIEMENS_AI_SETUP.md                 # Siemens AI integration guide
└── SIEMENS_QUICK_REF.md                # Siemens AI quick reference card
```

## Key Files by Module

### Backend API (12 endpoints)

All endpoints live in `backend/app/api/v1/endpoints/crashes.py` (680 lines):

| # | Method | Path | Response Model | Feature Flag |
|---|--------|------|----------------|-------------|
| 1 | `POST` | `/upload` | `CrashAnalysisResponse` | — |
| 2 | `GET` | `/{crash_id}` | `CrashAnalysisDetail` | — |
| 3 | `GET` | `/` | `List[CrashAnalysisResponse]` | — |
| 4 | `DELETE` | `/{crash_id}` | 204 No Content | — |
| 5 | `POST` | `/batch` | `BatchAnalysisResponse` | `ENABLE_BATCH_ANALYSIS` |
| 6 | `GET` | `/{crash_id}/similar` | `SimilarCrashesResponse` | — |
| 7 | `POST` | `/cluster` | `dict` | `ENABLE_CRASH_CLUSTERING` |
| 8 | `POST` | `/{crash_id}/chat` | `ChatResponse` | `ENABLE_CHAT_FOLLOWUP` |
| 9 | `POST` | `/integrations/slack` | `IntegrationResponse` | `ENABLE_CODE_INTEGRATION` |
| 10 | `POST` | `/integrations/jira` | `JiraIssueResponse` | `ENABLE_CODE_INTEGRATION` |
| 11 | `POST` | `/integrations/github` | `GitHubIssueResponse` | `ENABLE_CODE_INTEGRATION` |
| 12 | `POST` | `/classify-severity` | `SeverityClassificationResponse` | `ENABLE_ML_CLASSIFICATION` |

### Backend Data Flow

```
Upload .dmp → POST /upload
  → Validate (magic bytes, extension, size, hash dedup)
  → Save file to storage/dumps/
  → Create CrashAnalysis record (status=pending)
  → BackgroundTask: analyze_crash_dump_async()
      → WinDbgParser.parse() (runs cdb.exe subprocess)
      → VectorStore.find_similar_crashes() (ChromaDB)
      → LLMAnalyzer.analyze_crash() (Siemens AI / OpenAI / Anthropic)
      → LLMCache checks Redis before calling LLM
      → Store results in crash.llm_analysis JSON column
      → Update status → completed
  → Return {id, filename, status, message}
```

### Configuration

`backend/app/core/config.py` — Pydantic `BaseSettings` with `.env` file support.

Key feature flags: `ENABLE_BATCH_ANALYSIS`, `ENABLE_CHAT_FOLLOWUP`, `ENABLE_CODE_INTEGRATION`, `ENABLE_ML_CLASSIFICATION`, `ENABLE_CRASH_CLUSTERING`, `ENABLE_FUNCTION_CALLING`, `ENABLE_MULTI_MODEL_ENSEMBLE`

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend framework | FastAPI | 0.104.1 |
| ORM | SQLAlchemy (async) | 2.0.23 |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7 |
| LLM (primary) | Siemens AI (OpenAI-compatible) | qwen3-30b |
| LLM (fallback) | OpenAI / Anthropic | gpt-4o-mini / claude-3-haiku |
| Vector DB | ChromaDB | 1.3.4 |
| ML | scikit-learn | 1.3.2 |
| Frontend framework | Next.js | 14.0.4 |
| UI library | MUI | 5.15.0 |
| Visualization | D3.js / Mermaid | 7.8.5 / 11.12.1 |
| Python | CPython | 3.12.10 |
| Node.js | — | 18+ |

## Known Issues

See [REMAINING_WORK_AND_IMPROVEMENTS.md](REMAINING_WORK_AND_IMPROVEMENTS.md) for the complete bug list (33 issues) and fix roadmap.

**Critical:** `app/llm/analyzer.py` lines 402–529 have a syntax error that prevents the backend from starting. This must be fixed first.
