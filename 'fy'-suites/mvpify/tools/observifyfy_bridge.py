"""Observifyfy bridge for mvpify.tools.

"""
from __future__ import annotations

from pathlib import Path


def load_observifyfy_signal(repo_root: Path) -> dict:
    """Load observifyfy signal.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    # Process report one item at a time so load_observifyfy_signal applies the same rule
    # across the full collection.
    for report in [
        repo_root / 'observifyfy' / 'reports' / 'observifyfy_next_steps.json',
        repo_root / 'docs' / 'platform' / 'observifyfy_next_steps.json',
    ]:
        # Branch on report.exists() so load_observifyfy_signal only continues along the
        # matching state path.
        if report.exists():
            # Protect the critical load_observifyfy_signal work so failures can be
            # turned into a controlled result or cleanup path.
            try:
                import json
                return {'present': True, 'payload': json.loads(report.read_text(encoding='utf-8')), 'path': str(report.relative_to(repo_root))}
            except Exception as exc:
                return {'present': True, 'error': str(exc), 'path': str(report.relative_to(repo_root))}
    return {'present': False}
