"""Token authentication helpers."""

import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request

from app.config import settings

ADMIN_TOKEN_HEADER = "x-admin-token"
WORKSPACE_ID_HEADER = "x-workspace-id"
WORKSPACE_TOKEN_HEADER = "x-workspace-token"


def generate_workspace_token() -> str:
    """Return a high-entropy token safe to show once to the workspace owner."""
    return secrets.token_urlsafe(32)


def hash_workspace_token(token: str) -> str:
    """Hash a workspace token for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def workspace_token_matches(token: str, stored_hash: str | None) -> bool:
    """Return whether a plaintext token matches the stored token hash."""
    if not stored_hash:
        return False
    candidate = hash_workspace_token(token)
    return hmac.compare_digest(candidate, stored_hash)


def require_admin_token(request: Request) -> None:
    """Require the configured admin token for workspace-management routes."""
    configured_token = settings.admin_api_token
    if not configured_token:
        raise HTTPException(
            status_code=503,
            detail="Admin token is not configured",
        )

    supplied_token = request.headers.get(ADMIN_TOKEN_HEADER)
    if not supplied_token:
        raise HTTPException(status_code=401, detail="Admin token required")

    if not hmac.compare_digest(supplied_token, configured_token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
