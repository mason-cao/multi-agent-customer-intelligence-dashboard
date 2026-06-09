"""Structlog configuration for the Nova Core backend."""

import logging
import structlog

from app.config import settings


def build_logging_processors(app_env: str):
    """Build structlog processors for local readability or production JSON."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if app_env.lower() in {"production", "prod"}:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    return processors


def setup_logging():
    """Configure structlog for the current runtime environment."""
    structlog.configure(
        processors=build_logging_processors(settings.app_env),
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
