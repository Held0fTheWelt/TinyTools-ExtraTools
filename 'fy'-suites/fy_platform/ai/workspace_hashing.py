"""Workspace hashing for fy_platform.ai.

"""
from __future__ import annotations

import hashlib


def slugify(value: str) -> str:
    """Slugify the requested operation.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        value: Primary value used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    out = []
    # Process ch one item at a time so slugify applies the same rule across the full
    # collection.
    for ch in value.lower():
        out.append(ch if ch.isalnum() else '-')
    text = ''.join(out).strip('-')
    # Stay in this loop only while '--' in text remains true, so callers do not observe
    # a half-finished slugify state.
    while '--' in text:
        text = text.replace('--', '-')
    return text or 'unknown'


def sha256_text(text: str) -> str:
    """Sha256 text.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    """Sha256 bytes.

    Args:
        raw: Primary raw used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return hashlib.sha256(raw).hexdigest()
