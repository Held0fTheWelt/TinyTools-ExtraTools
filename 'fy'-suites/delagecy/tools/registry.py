"""Registry operations for delagecy."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "delagecy.registry.v1"
REMOVAL_ALLOWED_STATUSES = {"approved_for_removal", "removal_in_progress"}
CANONICALIZATION_ALLOWED_STATUSES = {
    "reported",
    "blocked",
    "retained",
    "approved_for_removal",
    "removal_in_progress",
    "removed",
}
CANONICALIZED_STATUS = "canonicalized_active_behavior"
CANONICALIZATION_COMPATIBILITY_SCOPES = {
    "current_required_behavior",
    "alternative_use",
    "provider_or_adapter_variation",
}
REJECTED_CANONICALIZATION_SCOPES = {"previous_version", "old_version", "backward_compatibility"}


def utc_now() -> str:
    """Return an ISO UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_registry() -> dict[str, Any]:
    """Return a new registry payload."""
    return {
        "schema_version": SCHEMA_VERSION,
        "policy": {
            "new_findings_must_be_registered_before_removal": True,
            "approval_required_before_removal": True,
            "ui_residue_must_be_removed": True,
            "problems_require_user_discussion": True,
            "legacy_is_not_active_compatibility": True,
            "active_behavior_must_be_preserved": True,
            "previous_version_compatibility_must_be_removed": True,
            "alternative_usage_compatibility_may_be_canonicalized": True,
        },
        "findings": [],
    }


def load_registry(path: Path) -> dict[str, Any]:
    """Load or initialize the registry."""
    if not path.is_file():
        return empty_registry()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return empty_registry()
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("policy", empty_registry()["policy"])
    data.setdefault("findings", [])
    return data


def save_registry(path: Path, data: dict[str, Any]) -> None:
    """Persist the registry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def next_id(data: dict[str, Any]) -> str:
    """Return the next DLG id."""
    highest = 0
    for row in data.get("findings") or []:
        raw = str((row or {}).get("id") or "")
        if raw.startswith("DLG-"):
            try:
                highest = max(highest, int(raw.split("-", 1)[1]))
            except ValueError:
                continue
    return f"DLG-{highest + 1:03d}"


def registered_fingerprints(data: dict[str, Any]) -> set[str]:
    """Return all known fingerprints."""
    out: set[str] = set()
    for row in data.get("findings") or []:
        value = str((row or {}).get("fingerprint") or "").strip()
        if value:
            out.add(value)
    return out


def find_by_id(data: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    """Find one registry row."""
    for row in data.get("findings") or []:
        if isinstance(row, dict) and row.get("id") == finding_id:
            return row
    return None


def register_hit(data: dict[str, Any], hit: dict[str, Any], *, title: str, reported_to: str = "") -> dict[str, Any]:
    """Register a scanner hit as reported."""
    fp = str(hit.get("fingerprint") or "").strip()
    if fp in registered_fingerprints(data):
        raise ValueError(f"fingerprint already registered: {fp}")
    row = {
        "id": next_id(data),
        "status": "reported",
        "title": title,
        "fingerprint": fp,
        "path": hit.get("path"),
        "line": hit.get("line"),
        "kind": hit.get("kind"),
        "pattern": hit.get("pattern"),
        "match_text": hit.get("text"),
        "reported_at": utc_now(),
        "reported_to": reported_to,
        "approval": None,
        "removal": None,
        "discussion_required": False,
        "notes": [],
    }
    data.setdefault("findings", []).append(row)
    return row


def approve(data: dict[str, Any], finding_id: str, *, approved_by: str, note: str) -> dict[str, Any]:
    """Mark a finding approved for removal."""
    row = find_by_id(data, finding_id)
    if row is None:
        raise KeyError(f"unknown finding id: {finding_id}")
    if row.get("status") not in {"reported", "blocked", "retained"}:
        raise ValueError(f"{finding_id} is not awaiting approval")
    row["status"] = "approved_for_removal"
    row["approval"] = {
        "approved_by": approved_by,
        "approved_at": utc_now(),
        "note": note,
    }
    return row


def mark_removed(data: dict[str, Any], finding_id: str, *, verification: str) -> dict[str, Any]:
    """Mark a finding removed after verification."""
    row = find_by_id(data, finding_id)
    if row is None:
        raise KeyError(f"unknown finding id: {finding_id}")
    if row.get("status") not in REMOVAL_ALLOWED_STATUSES:
        raise ValueError(f"{finding_id} must be approved before it can be marked removed")
    row["status"] = "removed"
    row["removal"] = {
        "removed_at": utc_now(),
        "verification": verification,
    }
    return row


def mark_canonicalized(
    data: dict[str, Any],
    finding_id: str,
    *,
    compatibility_scope: str,
    reason: str,
    evidence: str,
) -> dict[str, Any]:
    """Mark a finding as canonicalized active behavior, not true removal."""
    scope = compatibility_scope.strip()
    if scope in REJECTED_CANONICALIZATION_SCOPES:
        raise ValueError(
            f"{finding_id} describes previous-version compatibility; remove it instead of marking canonicalized"
        )
    if scope not in CANONICALIZATION_COMPATIBILITY_SCOPES:
        allowed = ", ".join(sorted(CANONICALIZATION_COMPATIBILITY_SCOPES))
        raise ValueError(f"compatibility_scope must be one of: {allowed}")
    row = find_by_id(data, finding_id)
    if row is None:
        raise KeyError(f"unknown finding id: {finding_id}")
    if row.get("status") not in CANONICALIZATION_ALLOWED_STATUSES:
        raise ValueError(f"{finding_id} cannot be marked canonicalized from status {row.get('status')}")
    row["status"] = CANONICALIZED_STATUS
    row["canonicalization"] = {
        "canonicalized_at": utc_now(),
        "compatibility_scope": scope,
        "reason": reason,
        "evidence": evidence,
    }
    row["removal"] = None
    return row


def tracker_markdown(data: dict[str, Any]) -> str:
    """Render the human tracker markdown."""
    lines = [
        "# Delagecy Legacy Removal Tracker",
        "",
        "Generated from `delagecy_registry.json`.",
        "",
        "## Rules",
        "",
        "- New findings must be registered and reported before removal.",
        "- Removal requires explicit approval.",
        "- UI residue must be removed with the code path.",
        "- Legacy is not active compatibility.",
        "- Compatibility with earlier repo/product versions is removed, not preserved.",
        "- Compatibility for active alternative usage, such as provider or adapter variation, may be preserved and canonicalized.",
        "- Active, required behavior is preserved and canonicalized; it is not marked as true removal.",
        "- Ambiguity or breakage risk must be discussed before continuing.",
        "",
        "## Findings",
        "",
        "| ID | Status | Kind | Path | Title |",
        "|----|--------|------|------|-------|",
    ]
    findings = data.get("findings") or []
    if not findings:
        lines.append("| - | - | - | - | No findings registered. |")
    for row in findings:
        path = f"{row.get('path')}:{row.get('line')}" if row.get("line") else str(row.get("path") or "")
        lines.append(
            "| {id} | {status} | {kind} | `{path}` | {title} |".format(
                id=row.get("id"),
                status=row.get("status"),
                kind=row.get("kind"),
                path=path,
                title=str(row.get("title") or "").replace("|", "\\|"),
            )
        )
    return "\n".join(lines) + "\n"
