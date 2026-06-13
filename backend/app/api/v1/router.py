"""
API Router - Phase 1
Combines all API endpoints
"""
from fastapi import APIRouter
from app.api.v1.endpoints import crashes

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(crashes.router)

# Phase 2: Add LLM endpoints
# Phase 3: Add report endpoints
# Phase 5: Add batch analysis, chat, etc.
