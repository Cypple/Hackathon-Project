"""
The version 1 API router.

Every endpoint under /api/v1 gets attached here. Keeping one place for this
means adding a new feature later is a two-line change.

PLACEHOLDERS (not implemented yet, on purpose):
  /api/v1/auth/       -> Stage 4 (Supabase Auth)
  /api/v1/users/      -> Stage 5 (user profile)
  /api/v1/works/      -> [DATASET WILL BE PROVIDED LATER]
  /api/v1/anomalies/  -> [ANOMALY DEFINITIONS WILL BE PROVIDED BY DATA/ML TEAM]
  /api/v1/dashboard/  -> [FINAL DASHBOARD METRICS WILL BE DEFINED LATER]
Do NOT create these routes until the dataset and methodology are decided.
"""

from fastapi import APIRouter

from app.api.v1.routes import config,projects
api_v1_router = APIRouter()
api_v1_router.include_router(config.router)
api_v1_router.include_router(projects.router)

# Stage 3: configuration status (is Supabase reachable?)

# Stage 4 and Stage 5 will add lines like:
#   from app.api.v1.routes import auth
#   api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
