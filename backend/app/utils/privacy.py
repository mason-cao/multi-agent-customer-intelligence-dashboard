"""Helpers for logging user-provided text without retaining the text itself."""

import hashlib


def text_log_metadata(value: str) -> dict[str, int | str]:
    """Return stable metadata for text logs without exposing the raw value."""
    return {
        "question_length": len(value),
        "question_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
    }
