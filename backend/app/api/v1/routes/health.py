"""
Health-check endpoint.

WHAT IS A HEALTH CHECK?
A tiny public endpoint that answers "is the server alive?".
Used by us during development and by hosting platforms in production.

    GET /health        -> {"status": "ok"}
"""

from fastapi import APIRouter

from app.core.config import settings

# An APIRouter is just a group of endpoints that we later plug into the app.
router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Return a simple 'I am alive' response. No authentication needed."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }
