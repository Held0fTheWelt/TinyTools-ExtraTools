"""Versioned machine-readable artifact envelope helpers."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_envelope(
    *,
    suite: str,
    suite_version: str,
    payload: dict[str, Any],
    manifest_ref: str = "",
    compat_mode: str = "transitional",
    deprecations: list[dict[str, str]] | None = None,
    findings: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    stats: dict[str, Any] | None = None,
    envelope_version: str = "1",
) -> dict[str, Any]:
    """Build canonical envelope around an existing suite payload.

    Args:
        suite: Primary suite used by this step.
        suite_version: Primary suite version used by this step.
        payload: Structured data carried through this workflow.
        manifest_ref: Primary manifest ref used by this step.
        compat_mode: Primary compat mode used by this step.
        deprecations: Primary deprecations used by this step.
        findings: Primary findings used by this step.
        evidence: Primary evidence used by this step.
        stats: Primary stats used by this step.
        envelope_version: Primary envelope version used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return {
        "envelopeVersion": envelope_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": suite,
        "suiteVersion": suite_version,
        "manifest_ref": manifest_ref,
        "compatMode": compat_mode,
        "findings": findings or [],
        "evidence": evidence or [],
        "stats": stats or {},
        "deprecations": deprecations or [],
        "payload": payload,
    }


def dump_envelope_json(envelope: dict[str, Any]) -> str:
    """Return canonical JSON representation for golden file stability.

    Args:
        envelope: Primary envelope used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return json.dumps(envelope, indent=2, sort_keys=True) + "\n"


def write_envelope(path: Path, envelope: dict[str, Any]) -> None:
    """Write envelope with canonical serialization.

    This callable writes or records artifacts as part of its workflow.

    Args:
        path: Filesystem path to the file or directory being processed.
        envelope: Primary envelope used by this step.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(dump_envelope_json(envelope), encoding="utf-8")
