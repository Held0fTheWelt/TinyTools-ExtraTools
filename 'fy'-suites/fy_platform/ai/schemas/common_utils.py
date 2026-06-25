"""Common utils for fy_platform.ai.schemas.

"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any


def to_jsonable(value: Any) -> Any:
    """To jsonable.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        value: Primary value used by this step.

    Returns:
        Any:
            Value produced by this callable as ``Any``.
    """
    # Branch on hasattr(value, '__dataclass_fields__') so to_jsonable only continues
    # along the matching state path.
    if hasattr(value, '__dataclass_fields__'):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    # Branch on isinstance(value, list) so to_jsonable only continues along the matching
    # state path.
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    # Branch on isinstance(value, dict) so to_jsonable only continues along the matching
    # state path.
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return value
