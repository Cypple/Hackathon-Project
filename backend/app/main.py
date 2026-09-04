"""
Entry point of the backend.

This file creates the FastAPI application object called `app`.
The server (uvicorn) looks for exactly this object when we run:

    uvicorn app.main:app --reload

Keep this file small: it only wires pieces together.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.api.v1.routes import health
from app.core.config import settings
from app.core.logging_config import get_logger, setup_logging

# Turn logging on before anything else, so startup messages are visible.
setup_logging()
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Build and return the FastAPI application.

    Using a function (a "factory") instead of top-level code makes the app
    easy to create inside tests as well.
    """
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        # Auto-generated interactive documentation lives at these URLs.
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS: allow our frontend (running on another address) to call this API
    # from the browser. Without this the browser blocks the requests.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Public endpoints that are NOT versioned (health checks stay at /health).
    application.include_router(health.router)

    # Everything else lives under /api/v1
    application.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    @application.on_event("startup")
    def on_startup() -> None:
        logger.info(
            "Starting %s v%s in %s mode",
            settings.APP_NAME,
            settings.APP_VERSION,
            settings.ENVIRONMENT,
        )

    @application.on_event("shutdown")
    def on_shutdown() -> None:
        logger.info("Shutting down %s", settings.APP_NAME)

    return application


app = create_app()


@app.get("/", tags=["root"])
def root() -> dict:
    """A friendly message so visiting the base URL is not confusing."""
    return {
        "message": f"{settings.APP_NAME} is running.",
        "docs": "/docs",
        "health": "/health",
    }
