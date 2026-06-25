"""Public cli for fy_platform.surfaces.

"""
from __future__ import annotations

"""Thin public CLI compatibility layer for platform-first mode dispatch."""

from fy_platform.surfaces.platform_dispatch import (
    cmd_analyze,
    cmd_explain_mode,
    cmd_generate,
    cmd_govern,
    cmd_import_mode,
    cmd_inspect_mode,
    cmd_metrics_mode,
)

__all__ = [
    'cmd_analyze',
    'cmd_explain_mode',
    'cmd_generate',
    'cmd_govern',
    'cmd_import_mode',
    'cmd_inspect_mode',
    'cmd_metrics_mode',
]
