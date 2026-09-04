"""
Supabase client factory.

WHAT IS THIS?
Supabase is our hosted database + auth provider. To talk to it from Python
we create a "client" object using two things from our .env file:

    SUPABASE_URL  -> where our Supabase project lives
    a key         -> proves we are allowed to talk to it

WHY TWO KEYS?
- ANON key: safe to expose; it respects the database's access rules (RLS).
  We use it for things a normal logged-in user may do.
- SERVICE_ROLE key: very powerful, bypasses all access rules. Only ever
  used on the server, never sent to a browser.

USAGE (from Stage 4 onwards):
    from app.db.supabase import get_supabase_client
    client = get_supabase_client()

Both functions raise a clear error if the .env values are still empty,
so misconfiguration fails loudly instead of mysteriously.
"""

from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class SupabaseNotConfiguredError(RuntimeError):
    """Raised when code tries to use Supabase before the .env keys are set."""


def _require(value: str, name: str) -> str:
    """Return the value if set, otherwise raise a beginner-friendly error."""
    if not value:
        raise SupabaseNotConfiguredError(
            f"{name} is empty. Fill it in backend/.env "
            "(Supabase dashboard -> Project Settings -> API)."
        )
    return value


@lru_cache
def get_supabase_client() -> Client:
    """
    Client built with the ANON key. Use this for normal user-facing work:
    it respects the database's row-level security rules.
    Cached so we only create one client for the whole app.
    """
    url = _require(settings.SUPABASE_URL, "SUPABASE_URL")
    key = _require(settings.SUPABASE_ANON_KEY, "SUPABASE_ANON_KEY")
    logger.info("Creating Supabase client (anon key) for %s", url)
    return create_client(url, key)


@lru_cache
def get_supabase_admin_client() -> Client:
    """
    Client built with the SERVICE_ROLE key. It bypasses ALL access rules,
    so only use it for trusted server-side jobs (never in user endpoints
    without careful checks).
    """
    url = _require(settings.SUPABASE_URL, "SUPABASE_URL")
    key = _require(settings.SUPABASE_SERVICE_ROLE_KEY, "SUPABASE_SERVICE_ROLE_KEY")
    logger.info("Creating Supabase admin client (service role) for %s", url)
    return create_client(url, key)


def supabase_is_configured() -> bool:
    """True when the minimum settings (URL + anon key) are filled in."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY)


def check_supabase_connection() -> dict:
    """
    Try a lightweight call to Supabase and report the result.
    Used by the /api/v1/config/status endpoint so we can verify Stage 3
    without any real data tables existing yet.
    """
    if not supabase_is_configured():
        return {"configured": False, "reachable": False,
                "detail": "SUPABASE_URL / SUPABASE_ANON_KEY not set in .env"}
    try:
        client = get_supabase_client()
        # An anonymous auth settings call: needs no tables, just a live project.
        client.auth.get_session()
        return {"configured": True, "reachable": True,
                "detail": "Supabase client created successfully"}
    except Exception as exc:  # noqa: BLE001 - we report the error, not crash
        logger.warning("Supabase connection check failed: %s", exc)
        return {"configured": True, "reachable": False, "detail": str(exc)}
