"""Tests for FastAPI application configuration."""


def test_parse_cors_origins_trims_whitespace_and_ignores_blanks():
    from app.main import parse_cors_origins

    assert parse_cors_origins(
        " https://app.example.com,https://staging.example.com, , http://localhost:5173 "
    ) == [
        "https://app.example.com",
        "https://staging.example.com",
        "http://localhost:5173",
    ]


def test_cors_origins_are_trimmed(test_app):
    from starlette.middleware.cors import CORSMiddleware

    cors_middleware = next(
        middleware
        for middleware in test_app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_origins"] == ["http://localhost:5173"]
    assert all(
        origin == origin.strip()
        for origin in cors_middleware.kwargs["allow_origins"]
    )


def test_cors_methods_and_headers_are_explicit(test_app):
    from starlette.middleware.cors import CORSMiddleware

    cors_middleware = next(
        middleware
        for middleware in test_app.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_methods"] == ["GET", "POST", "DELETE", "OPTIONS"]
    assert cors_middleware.kwargs["allow_headers"] == [
        "Content-Type",
        "X-Admin-Token",
        "X-Workspace-ID",
        "X-Workspace-Token",
    ]


def test_production_logging_uses_json_renderer():
    import structlog

    from app.utils.logging import build_logging_processors

    processors = build_logging_processors("production")

    assert any(isinstance(processor, structlog.processors.JSONRenderer) for processor in processors)
    assert not any(isinstance(processor, structlog.dev.ConsoleRenderer) for processor in processors)
