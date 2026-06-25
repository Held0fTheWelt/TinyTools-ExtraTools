"""Final product for fy_platform.ai.

"""
from __future__ import annotations

"""Thin compatibility surface for final-product platform reports."""

from fy_platform.ai.final_product_capability import ai_capability_payload, render_ai_capability_markdown
from fy_platform.ai.final_product_catalog import (
    GENERIC_LIFECYCLE_COMMANDS,
    SUITE_NATIVE_COMMANDS,
    SUITE_SUMMARIES,
    command_reference_payload,
    render_command_reference_markdown,
    render_suite_catalog_markdown,
    suite_catalog_payload,
)
from fy_platform.ai.final_product_health import doctor_payload, final_release_bundle, render_doctor_markdown
from fy_platform.ai.final_product_schemas import export_contract_schemas

__all__ = [
    "GENERIC_LIFECYCLE_COMMANDS",
    "SUITE_NATIVE_COMMANDS",
    "SUITE_SUMMARIES",
    "ai_capability_payload",
    "command_reference_payload",
    "doctor_payload",
    "export_contract_schemas",
    "final_release_bundle",
    "render_ai_capability_markdown",
    "render_command_reference_markdown",
    "render_doctor_markdown",
    "render_suite_catalog_markdown",
    "suite_catalog_payload",
]
