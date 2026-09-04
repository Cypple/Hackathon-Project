"""
Logging setup.

WHAT IS LOGGING?
Printing messages about what the server is doing, so we can understand it
(startup, errors, failed logins). Better than print() because we can control
the detail level and the format.

SECURITY RULE (very important):
NEVER log passwords, authentication tokens, or secret keys.
If you are unsure whether a value is sensitive, do not log it.
"""

import logging

from app.core.config import settings


def setup_logging() -> None:
    """Configure how log messages look. Called once when the app starts."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        # time | level | which part of the code | message
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for one file. Usage at the top of a file:

        logger = get_logger(__name__)
        logger.info("something happened")
    """
    return logging.getLogger(name)
