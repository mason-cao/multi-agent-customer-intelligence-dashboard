"""First-run owner passcode setup for workspace management."""

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Optional

from app.db.workspace_db import MetadataSession
from app.models.workspace import OwnerAccess

OWNER_ACCESS_ID = "owner"
_HASH_ALGORITHM = "pbkdf2_sha256"
_HASH_ITERATIONS = 260_000


def _hash_passcode(passcode: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        passcode.encode("utf-8"),
        bytes.fromhex(salt),
        _HASH_ITERATIONS,
    ).hex()
    return f"{_HASH_ALGORITHM}${_HASH_ITERATIONS}${salt}${digest}"


def _passcode_matches(passcode: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, stored_digest = stored_hash.split("$", 3)
        iteration_count = int(iterations)
    except ValueError:
        return False
    if algorithm != _HASH_ALGORITHM or iteration_count != _HASH_ITERATIONS:
        return False
    candidate = _hash_passcode(passcode, salt).split("$", 3)[3]
    return hmac.compare_digest(candidate, stored_digest)


def get_owner_access() -> Optional[OwnerAccess]:
    """Return the configured owner passcode row, if any."""
    db = MetadataSession()
    try:
        return db.query(OwnerAccess).filter(OwnerAccess.id == OWNER_ACCESS_ID).first()
    finally:
        db.close()


def owner_passcode_configured() -> bool:
    """Return whether first-run owner access has already been set up."""
    return get_owner_access() is not None


def create_owner_passcode(passcode: str) -> OwnerAccess:
    """Create the first-run owner passcode row."""
    db = MetadataSession()
    try:
        existing = db.query(OwnerAccess).filter(OwnerAccess.id == OWNER_ACCESS_ID).first()
        if existing:
            return existing

        owner_access = OwnerAccess(
            id=OWNER_ACCESS_ID,
            passcode_hash=_hash_passcode(passcode),
            created_at=datetime.now(timezone.utc),
        )
        db.add(owner_access)
        db.commit()
        db.refresh(owner_access)
        return owner_access
    finally:
        db.close()


def owner_passcode_matches(passcode: str) -> bool:
    """Return whether a supplied owner passcode matches the stored hash."""
    owner_access = get_owner_access()
    if not owner_access:
        return False
    return _passcode_matches(passcode, owner_access.passcode_hash)


def clear_owner_access():
    """Remove first-run owner access state. Used by tests."""
    db = MetadataSession()
    try:
        owner_access = db.query(OwnerAccess).filter(OwnerAccess.id == OWNER_ACCESS_ID).first()
        if owner_access:
            db.delete(owner_access)
            db.commit()
    finally:
        db.close()
