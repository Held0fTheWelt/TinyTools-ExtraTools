"""Workspace io for fy_platform.ai.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_text_safe(path: Path) -> str:
    """Read text safe.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return path.read_text(encoding='utf-8', errors='replace')


def write_json(path: Path, payload: Any) -> None:
    """Write json.

    This callable writes or records artifacts as part of its workflow.

    Args:
        path: Filesystem path to the file or directory being processed.
        payload: Structured data carried through this workflow.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def write_text(path: Path, text: str) -> None:
    """Write text.

    This callable writes or records artifacts as part of its workflow.

    Args:
        path: Filesystem path to the file or directory being processed.
        text: Text content to inspect or rewrite.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(text, encoding='utf-8')
