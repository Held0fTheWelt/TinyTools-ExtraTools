"""Final product catalog for fy_platform.ai.

"""
from __future__ import annotations

from fy_platform.ai.final_product_catalog_data import (
    GENERIC_LIFECYCLE_COMMANDS,
    SUITE_NATIVE_COMMANDS,
    SUITE_SUMMARIES,
    command_reference_payload,
    suite_catalog_payload,
)
from fy_platform.ai.final_product_catalog_render import render_command_reference_markdown, render_suite_catalog_markdown

__all__ = [
    'GENERIC_LIFECYCLE_COMMANDS',
    'SUITE_NATIVE_COMMANDS',
    'SUITE_SUMMARIES',
    'command_reference_payload',
    'suite_catalog_payload',
    'render_command_reference_markdown',
    'render_suite_catalog_markdown',
]
