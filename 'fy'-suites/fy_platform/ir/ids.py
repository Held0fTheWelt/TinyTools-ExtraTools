"""Ids for fy_platform.ir.

"""
from __future__ import annotations

import uuid


def new_ir_id(namespace: str) -> str:
    """New ir id.

    Args:
        namespace: Primary namespace used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return f'{namespace}-{uuid.uuid4().hex[:12]}'
