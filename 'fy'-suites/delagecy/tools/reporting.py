"""Markdown reporting for delagecy scan results."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from delagecy.tools.registry import CANONICALIZED_STATUS, registered_fingerprints

SCOPE_HINTS = (
    (
        "site-packages",
        "Bundled dependency files are in scope. Treat these as scan noise unless ownership is explicit.",
    ),
    (
        "htmlcov",
        "Coverage output is in scope. Generated reports should normally be excluded from removal planning.",
    ),
    (
        "/var/story_sessions/",
        "Runtime story-session snapshots are in scope. Decide whether these are fixtures or generated state before registration.",
    ),
    (
        "docs/generated",
        "Generated documentation is in scope. Prefer removing the source of residue, then regenerating docs.",
    ),
)


def _hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("hits") or []
    return [row for row in rows if isinstance(row, dict)]


def _cell(value: object, *, limit: int = 120) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) > limit:
        text = f"{text[: limit - 3]}..."
    return text.replace("|", "\\|")


def _hit_location(hit: dict[str, Any]) -> str:
    path = str(hit.get("path") or "")
    line = hit.get("line")
    return f"{path}:{line}" if line else path


def _table(headers: list[str], rows: list[list[object]], *, empty: str) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    if not rows:
        lines.append("| " + " | ".join([empty, *[""] * (len(headers) - 1)]) + " |")
        return lines
    for row in rows:
        lines.append("| " + " | ".join(_cell(item) for item in row) + " |")
    return lines


def _top_counter_rows(counter: Counter[str], limit: int) -> list[list[object]]:
    return [[key, value] for key, value in counter.most_common(limit)]


def _scope_warnings(paths: list[str]) -> list[list[str]]:
    warnings: list[list[str]] = []
    for marker, hint in SCOPE_HINTS:
        count = sum(1 for path in paths if marker in f"/{path}")
        if count:
            warnings.append([marker, count, hint])
    return warnings


def _unregistered_hits(
    scan_hits: list[dict[str, Any]],
    registry: dict[str, Any],
    new_payload: dict[str, Any] | None,
) -> tuple[int, list[dict[str, Any]]]:
    if new_payload is not None:
        rows = _hits(new_payload)
        return int(new_payload.get("unregistered_count") or len(rows)), rows
    known = registered_fingerprints(registry)
    rows = [hit for hit in scan_hits if hit.get("fingerprint") not in known]
    return len(rows), rows


def render_scan_report(
    scan_payload: dict[str, Any],
    *,
    registry: dict[str, Any],
    scan_path: Path | None = None,
    new_payload: dict[str, Any] | None = None,
    new_path: Path | None = None,
    title: str = "Delagecy Legacy Scan Report",
) -> str:
    """Render a readable Markdown report for one delagecy scan."""
    scan_hits = _hits(scan_payload)
    unregistered_count, unregistered = _unregistered_hits(scan_hits, registry, new_payload)
    known = registered_fingerprints(registry)
    active_fps = {str(hit.get("fingerprint")) for hit in scan_hits}
    findings = [row for row in registry.get("findings", []) if isinstance(row, dict)]
    removed_residue = [
        row for row in findings
        if row.get("status") == "removed" and row.get("fingerprint") in active_fps
    ]
    canonicalized_residue = [
        row for row in findings
        if row.get("status") == CANONICALIZED_STATUS and row.get("fingerprint") in active_fps
    ]
    approved_ui = [
        row for row in findings
        if (
            row.get("status") == "approved_for_removal"
            and row.get("kind") == "ui"
            and row.get("fingerprint") in active_fps
        )
    ]
    discussion_required = [
        row for row in findings
        if row.get("status") == "blocked" or row.get("discussion_required")
    ]
    gate_ok = not unregistered_count and not removed_residue and not canonicalized_residue

    kind_counts = Counter(str(hit.get("kind") or "unknown") for hit in scan_hits)
    path_counts = Counter(str(hit.get("path") or "") for hit in scan_hits)
    pattern_counts = Counter(str(hit.get("pattern") or "") for hit in scan_hits)
    status_counts = Counter(str(row.get("status") or "unknown") for row in findings)
    ui_hits = [hit for hit in scan_hits if hit.get("kind") == "ui"][:25]
    first_unregistered = unregistered[:25]

    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        f"- Gate status: **{'PASS' if gate_ok else 'FAIL'}**",
        f"- Scanned files: {scan_payload.get('scanned_file_count', 0)}",
        f"- Legacy hits: {scan_payload.get('hit_count', len(scan_hits))}",
        f"- Registered findings: {len(known)}",
        f"- Unregistered findings: {unregistered_count}",
        f"- Removed residue still visible: {len(removed_residue)}",
        f"- Canonicalized residue still visible: {len(canonicalized_residue)}",
        f"- Approved UI removals still pending: {len(approved_ui)}",
        f"- Discussion-required findings: {len(discussion_required)}",
        "",
        "## Artifacts",
        "",
        f"- Scan JSON: `{scan_path.as_posix() if scan_path else 'not provided'}`",
        f"- New-findings JSON: `{new_path.as_posix() if new_path else 'not provided'}`",
        "- Machine registry: `delagecy_registry.json`",
        "- Human tracker: `legacy_removal_tracker.md`",
        "",
        "## Required Rules",
        "",
        "1. New legacy findings must be registered and reported before removal.",
        "2. Removal requires explicit approval.",
        "3. Code, routes, tests, docs, data, and UI residue are removed together.",
        "4. Integrity risks, ownership conflicts, or ambiguous removals must be discussed before work continues.",
        "5. Compatibility with earlier repo/product versions is removed; it is not retained as active behavior.",
        "6. Compatibility for active alternative usage, such as provider or adapter variation, may be preserved and canonicalized.",
        "7. A finding is only marked removed after true removal, a clean scan, and targeted verification.",
        "",
        "## Counts By Surface",
        "",
    ]
    lines.extend(_table(["Surface", "Hits"], _top_counter_rows(kind_counts, 20), empty="No hits"))
    lines.extend(["", "## Counts By Pattern", ""])
    lines.extend(_table(["Pattern", "Hits"], _top_counter_rows(pattern_counts, 20), empty="No hits"))
    lines.extend(["", "## Registry Status", ""])
    lines.extend(_table(["Status", "Findings"], _top_counter_rows(status_counts, 20), empty="No registered findings"))
    lines.extend(["", "## Top Hit Files", ""])
    lines.extend(_table(["Path", "Hits"], _top_counter_rows(path_counts, 30), empty="No hits"))
    lines.extend(["", "## Scope Warnings", ""])
    lines.extend(_table(["Marker", "Files", "Meaning"], _scope_warnings(list(path_counts)), empty="No scope warnings"))
    lines.extend(["", "## First Unregistered Findings", ""])
    lines.extend(
        _table(
            ["Fingerprint", "Surface", "Location", "Text"],
            [
                [hit.get("fingerprint"), hit.get("kind"), _hit_location(hit), hit.get("text")]
                for hit in first_unregistered
            ],
            empty="No unregistered findings",
        )
    )
    lines.extend(["", "## UI Residue Examples", ""])
    lines.extend(
        _table(
            ["Fingerprint", "Location", "Text"],
            [[hit.get("fingerprint"), _hit_location(hit), hit.get("text")] for hit in ui_hits],
            empty="No UI residue hits",
        )
    )
    lines.extend(["", "## Next Actions", ""])
    if unregistered_count:
        lines.append(
            f"- Register and report the {unregistered_count} unregistered finding(s) before any removal work starts."
        )
    if removed_residue:
        lines.append("- Re-open removed findings that still appear in the scan; they are not cleanly removed.")
    if canonicalized_residue:
        lines.append("- Finish canonicalization for findings whose original fingerprints still appear in the scan.")
    if approved_ui:
        lines.append("- Verify approved UI removals remove visible, hidden, route, and static residue together.")
    if discussion_required:
        lines.append("- Discuss blocked or ambiguous findings before continuing.")
    if gate_ok:
        lines.append("- Gate is clean for this scan; keep the report with the removal review evidence.")
    lines.append("")
    return "\n".join(lines)
