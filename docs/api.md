# Crashbot API Documentation

> **Last verified:** March 2026 — all endpoints checked against `crashes.py` source.
>
> **⚠ Note:** The backend currently cannot start due to a syntax error in `app/llm/analyzer.py`. Fix that first (see [REMAINING_WORK_AND_IMPROVEMENTS.md](../REMAINING_WORK_AND_IMPROVEMENTS.md) Bug #1).

## Base URL

```
http://localhost:8002/api/v1
```

Interactive docs (Swagger UI): http://localhost:8002/docs
ReDoc: http://localhost:8002/redoc

## Authentication

**Currently:** No authentication is enforced. All endpoints are open.

The backend has a fully implemented auth module (`app/core/security.py`) with JWT and API key support, but no endpoint uses it yet. See Bug #6 in the bug report.

---

## Utility Endpoints

These are mounted directly on the app (not under `/api/v1`):

### Root Info

```
GET /
```

Returns app name, version, and status.

### Health Check

```
GET /health
```

Returns `{"status": "healthy"}`.

---

## Crash Analysis Endpoints

All mounted under `/api/v1/crashes/`.

---

### 1. Upload Crash Dump

```
POST /crashes/upload
```

Upload a crash dump file for analysis. Triggers background parsing and LLM analysis.

**Request:** `multipart/form-data` with a `file` field.

**Accepted file types:** `.dmp`, `.dump`, `.core`, `.crash`, `.mdmp`
**Accepted magic bytes:** `MDMP` (Windows), `\x7fELF` (Linux), `\xFE\xED\xFA\xCE`/`\xCF` (macOS), `PAGEDUMP`
**Max size:** 500MB (configurable via `MAX_UPLOAD_SIZE`)

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "crash_20260322_103045.dmp",
  "status": "pending",
  "message": "Analysis started"
}
```

**Duplicate detection:** If the SHA256 hash matches an existing upload, returns `201` with the existing record (does not re-analyze).

**Errors:**
- `400` — Invalid file type, failed magic byte validation, or empty file
- `413` — File exceeds `MAX_UPLOAD_SIZE`

**Example:**
```bash
curl -X POST http://localhost:8002/api/v1/crashes/upload \
  -F "file=@crash.dmp"
```

---

### 2. Get Crash Analysis

```
GET /crashes/{crash_id}
```

Retrieve a single crash analysis by UUID.

**Response model:** `CrashAnalysisDetail`

```json
{
  "id": "uuid",
  "filename": "crash.dmp",
  "file_size": 1024000,
  "file_hash": "sha256...",
  "status": "completed",
  "platform": "Windows",
  "exception_code": "0xc0000005",
  "exception_description": "ACCESS_VIOLATION",
  "stack_trace": { ... },
  "raw_output": "...",
  "llm_analysis": {
    "root_cause": "Null pointer dereference in ProcessData",
    "explanation": "The application attempted to access memory at address 0x0...",
    "severity": "high",
    "confidence": 0.85,
    "solutions": [
      {
        "title": "Add null check",
        "description": "Check pointer before dereferencing",
        "priority": 1,
        "code_example": "if (ptr != nullptr) { ... }"
      }
    ],
    "references": ["https://learn.microsoft.com/..."]
  },
  "similar_crashes": [...],
  "created_at": "2026-03-22T10:30:00Z",
  "updated_at": "2026-03-22T10:30:09Z"
}
```

**⚠ Known issue:** The `llm_analysis` field is stored in the database but not included in the Pydantic response schema. The frontend cannot display AI results until Bug #4 is fixed.

**Errors:**
- `404` — Crash analysis not found

---

### 3. List Crash Analyses

```
GET /crashes/
```

List all crash analyses with optional filtering and pagination.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | int | 0 | Records to skip |
| `limit` | int | 50 | Max records to return (max 100) |
| `status` | string | (none) | Filter: `pending`, `parsing`, `analyzing`, `completed`, `failed` |

**Response:** `200 OK` — Array of `CrashAnalysisResponse`
```json
[
  {
    "id": "uuid",
    "filename": "crash.dmp",
    "status": "completed",
    "message": null,
    "created_at": "2026-03-22T10:30:00Z"
  }
]
```

**⚠ Known issue:** Pagination is applied before the status filter (Bug #9).

---

### 4. Delete Crash Analysis

```
DELETE /crashes/{crash_id}
```

Delete a crash analysis record and its associated file.

**Response:** `204 No Content`

**Errors:**
- `404` — Crash analysis not found

---

### 5. Batch Analysis

```
POST /crashes/batch
```

Analyze multiple crash IDs to find common patterns.

**Feature flag:** `ENABLE_BATCH_ANALYSIS` (default: `true`)

**Request:**
```json
{
  "crash_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response:** `BatchAnalysisResponse` — common patterns, shared modules, severity distribution.

---

### 6. Find Similar Crashes

```
GET /crashes/{crash_id}/similar
```

Find crashes similar to the given one using ML-based similarity.

**Response:** `SimilarCrashesResponse` — list of similar crashes with similarity scores.

---

### 7. Cluster Crashes

```
POST /crashes/cluster
```

Group all crashes into clusters using TF-IDF + DBSCAN.

**Feature flag:** `ENABLE_CRASH_CLUSTERING` (default: `true`)

**Request:**
```json
{
  "min_cluster_size": 2,
  "similarity_threshold": 0.7
}
```

**Response:** Dict of cluster labels → crash ID lists.

---

### 8. Chat Follow-up

```
POST /crashes/{crash_id}/chat
```

Ask a follow-up question about a specific crash analysis.

**Feature flag:** `ENABLE_CHAT_FOLLOWUP` (default: `true`)

**Request:**
```json
{
  "message": "Could this be caused by a race condition?"
}
```

**Response:** `ChatResponse`
```json
{
  "response": "Based on the stack trace, a race condition is unlikely because...",
  "crash_id": "uuid"
}
```

---

### 9. Slack Notification

```
POST /crashes/integrations/slack
```

Send a crash analysis summary to a Slack channel.

**Feature flag:** `ENABLE_CODE_INTEGRATION` (default: `true`)

**Request:**
```json
{
  "crash_id": "uuid",
  "webhook_url": "https://hooks.slack.com/services/..."
}
```

---

### 10. Create JIRA Issue

```
POST /crashes/integrations/jira
```

Create a JIRA issue from a crash analysis.

**Feature flag:** `ENABLE_CODE_INTEGRATION` (default: `true`)

**⚠ Not functional:** `JIRA_URL` and `JIRA_API_TOKEN` are not defined in config (Bug #24).

---

### 11. Create GitHub Issue

```
POST /crashes/integrations/github
```

Create a GitHub issue from a crash analysis.

**Feature flag:** `ENABLE_CODE_INTEGRATION` (default: `true`)

**⚠ Not functional:** `GITHUB_TOKEN` is not defined in config (Bug #24).

---

### 12. Classify Severity

```
POST /crashes/classify-severity
```

Run ML-based severity classification on crash data.

**Feature flag:** `ENABLE_ML_CLASSIFICATION` (default: `true`)

**Request:**
```json
{
  "crash_id": "uuid"
}
```

**Response:** `SeverityClassificationResponse` — severity level, confidence score, reasoning.

---

## Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created (upload) |
| `204` | No Content (deletion) |
| `400` | Bad Request (invalid input) |
| `404` | Not Found |
| `413` | Payload Too Large |
| `500` | Internal Server Error |

**Not implemented:** `401` (auth not enforced), `429` (no rate limiting).

---

## Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

Standard FastAPI/Starlette error format. No custom error codes are implemented.

---

## Features Not Implemented

The following are referenced in older documentation but **do not exist** in the current code:

- **WebSocket** real-time updates (`ws://...`) — not implemented
- **Webhook** subscriptions (`POST /webhooks/`) — not implemented
- **Rate limiting** headers (`X-RateLimit-*`) — not implemented
- **PDF/HTML report generation** endpoints — not implemented
- **Web search** integration — `search/` module does not exist
