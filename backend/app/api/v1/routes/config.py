"""
Configuration status endpoint.

    GET /api/v1/config/status

Tells us (and the frontend) whether the backend is configured correctly:
are the Supabase keys present, and can we reach Supabase?
This is how we verify Stage 3 before building anything on top of it.
No secrets are ever returned — only true/false style information.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.db.supabase import check_supabase_connection

router = APIRouter(tags=["config"])


@router.get("/config/status")
def config_status() -> dict:
    """Report configuration health. Safe to call without authentication."""
    supabase = check_supabase_connection()
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "supabase": supabase,
    }
