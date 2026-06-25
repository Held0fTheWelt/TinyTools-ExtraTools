"""Generate human-visible ADR investigation docs, maps, and gap views."""
from __future__ import annotations

from pathlib import Path

from contractify.tools.adr_governance import discover_adr_governance
from contractify.tools.runtime_mvp_spine import build_runtime_mvp_spine


DEFAULT_ADR_INVESTIGATION_DIR = "'fy'-suites/contractify/investigations/adr"


def _class_name(text: str) -> str:
    """Class name.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return "".join(ch if ch.isalnum() else "_" for ch in text)


def build_adr_investigation_bundle(repo: Path) -> dict:
    """Build adr investigation bundle.

    Args:
        repo: Primary repo used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    repo = repo.resolve()
    adr = discover_adr_governance(repo)
    contracts, _projections, relations, conflicts, _families = build_runtime_mvp_spine(repo)
    adr_contracts = [c for c in contracts if c.contract_type == "adr"]
    adr_ids = {c.id for c in adr_contracts}
    adr_relations = [r for r in relations if r.source_id in adr_ids or r.target_id in adr_ids]
    return {
        "adr_governance": adr,
        "adr_contracts": [
            {
                "id": c.id,
                "title": c.title,
                "anchor_location": c.anchor_location,
                "implemented_by": c.implemented_by,
                "validated_by": c.validated_by,
                "documented_in": c.documented_in,
                "precedence_tier": c.precedence_tier,
            }
            for c in adr_contracts
        ],
        "adr_relations": [
            {
                "relation": r.relation,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "evidence": r.evidence,
            }
            for r in adr_relations
        ],
        "manual_unresolved_areas": [
            {
                "id": c.id,
                "summary": c.summary,
                "sources": c.sources,
                "severity": c.severity,
            }
            for c in conflicts
            if any("ADR" in src or "adr-" in src.lower() for src in c.sources)
        ],
    }


def render_adr_relation_map(bundle: dict) -> str:
    """Render adr relation map.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        bundle: Primary bundle used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = ["graph TD"]
    seen: set[str] = set()
    for row in bundle["adr_contracts"]:
        node = _class_name(row["id"])
        label = row["title"].replace('"', "'")
        if node not in seen:
            lines.append(f'    {node}["{label}"]')
            seen.add(node)
        for rel in row.get("implemented_by", []):
            impl = _class_name(f"impl_{rel}")
            if impl not in seen:
                lines.append(f'    {impl}["{rel}"]')
                seen.add(impl)
            lines.append(f"    {node} -->|implemented_by| {impl}")
        for rel in row.get("validated_by", []):
            ver = _class_name(f"ver_{rel}")
            if ver not in seen:
                lines.append(f'    {ver}["{rel}"]')
                seen.add(ver)
            lines.append(f"    {node} -->|validated_by| {ver}")
        for rel in row.get("documented_in", []):
            doc = _class_name(f"doc_{rel}")
            if doc not in seen:
                lines.append(f'    {doc}["{rel}"]')
                seen.add(doc)
            lines.append(f"    {node} -.->|documented_in| {doc}")
    for rel in bundle["adr_relations"]:
        src = _class_name(rel["source_id"])
        tgt = _class_name(rel["target_id"])
        if src not in seen:
            lines.append(f'    {src}["{rel["source_id"]}"]')
            seen.add(src)
        if tgt not in seen:
            lines.append(f'    {tgt}["{rel["target_id"]}"]')
            seen.add(tgt)
        lines.append(f'    {src} -->|{rel["relation"]}| {tgt}')
    return "\n".join(lines) + "\n"


def render_adr_conflict_map(bundle: dict) -> str:
    """Render adr conflict map.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        bundle: Primary bundle used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = ["graph TD"]
    adr = bundle["adr_governance"]
    for finding in adr["findings"]:
        fid = _class_name(finding["id"])
        sev = finding["severity"]
        lines.append(f'    {fid}["{finding["kind"]}\\n{sev}"]')
        for src in finding["sources"]:
            sid = _class_name(src)
            lines.append(f'    {sid}["{src}"]')
            lines.append(f"    {fid} --> {sid}")
    for unresolved in bundle.get("manual_unresolved_areas", []):
        uid = _class_name(unresolved["id"])
        lines.append(f'    {uid}["{unresolved["id"]}\\nmanual unresolved"]')
        for src in unresolved.get("sources", []):
            sid = _class_name(src)
            lines.append(f'    {sid}["{src}"]')
            lines.append(f"    {uid} -.-> {sid}")
    return "\n".join(lines) + "\n"


def render_adr_investigation_markdown(bundle: dict) -> str:
    """Render adr investigation markdown.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        bundle: Primary bundle used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    adr = bundle["adr_governance"]
    lines: list[str] = []
    lines.extend(
        [
            "# ADR governance investigation",
            "",
            "- Canonical ADR home: `docs/ADR`",
            f"- ADR files discovered: {adr['stats']['n_adrs']}",
            f"- Canonical ADR files already in place: {adr['stats']['n_canonical_adrs']}",
            f"- Legacy ADR files still outside `docs/ADR`: {adr['stats']['n_legacy_adrs']}",
            f"- Findings: {adr['stats']['n_findings']}",
            "",
            "## What this suite is for",
            "",
            "This investigation suite makes ADR state visible in one place: current locations, proposed canonical names, duplicate pressure, migration gaps, and relation maps into the governed runtime/MVP spine.",
            "",
            "## ADR inventory",
            "",
            "| Current path | Declared id | Status | Family | Proposed canonical id | Proposed canonical path | Issues |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in adr["records"]:
        issues = ", ".join(row["issues"] or ["none"])
        lines.append(
            f"| `{row['current_path']}` | `{row['declared_id']}` | `{row['status']}` | `{row['family']}` | "
            f"`{row['proposed_canonical_id']}` | `{row['proposed_canonical_path']}` | {issues} |"
        )

    lines.extend(
        [
            "",
            "## Findings",
            "",
            "| Kind | Severity | Summary | Recommended action | Sources |",
            "|---|---|---|---|---|",
        ]
    )
    if adr["findings"]:
        for finding in adr["findings"]:
            lines.append(
                f"| `{finding['kind']}` | `{finding['severity']}` | {finding['summary']} | "
                f"{finding['recommended_action']} | " + ", ".join(f"`{s}`" for s in finding["sources"]) + " |"
            )
    else:
        lines.append("| none | none | no current ADR governance findings | keep canonical placement stable | — |")

    lines.extend(
        [
            "",
            "## Governed runtime/MVP ADR attachment view",
            "",
            "| ADR contract | Anchor | Implemented by | Validated by | Documented in | Precedence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in bundle["adr_contracts"]:
        lines.append(
            f"| `{row['id']}` | `{row['anchor_location']}` | "
            + ", ".join(f"`{x}`" for x in row["implemented_by"]) + " | "
            + ", ".join(f"`{x}`" for x in row["validated_by"]) + " | "
            + ", ".join(f"`{x}`" for x in row["documented_in"]) + " | "
            + f"`{row['precedence_tier']}` |"
        )

    lines.extend(
        [
            "",
            "## Maps",
            "",
            "- Relation map: `ADR_RELATION_MAP.mmd`",
            "- Conflict / gap map: `ADR_CONFLICT_MAP.mmd`",
            "",
            "## Gaps to keep visible",
            "",
        ]
    )
    gap_lines = []
    for finding in adr["findings"]:
        if finding["severity"] in {"high", "medium"}:
            gap_lines.append(f"- `{finding['kind']}` — {finding['summary']}")
    if bundle.get("manual_unresolved_areas"):
        for unresolved in bundle["manual_unresolved_areas"]:
            gap_lines.append(f"- manual unresolved `{unresolved['id']}` — {unresolved['summary']}")
    if not gap_lines:
        gap_lines.append("- No current ADR governance gaps beyond the canonical inventory rules.")
    lines.extend(gap_lines)
    lines.append("")
    return "\n".join(lines)


def write_adr_investigation_suite(repo: Path, *, out_dir_rel: str = DEFAULT_ADR_INVESTIGATION_DIR) -> dict:
    """Write adr investigation suite.

    This callable writes or records artifacts as part of its workflow.

    Args:
        repo: Primary repo used by this step.
        out_dir_rel: Primary out dir rel used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    repo = repo.resolve()
    bundle = build_adr_investigation_bundle(repo)
    out_dir = repo / out_dir_rel
    out_dir.mkdir(parents=True, exist_ok=True)

    readme = out_dir / "README.md"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    readme.write_text(
        "# ADR investigation suite\n\n"
        "Generated / refreshed by `python -m contractify.tools adr-investigation`.\n\n"
        "- `ADR_GOVERNANCE_INVESTIGATION.md` — human-readable inventory, findings, and gap list\n"
        "- `ADR_RELATION_MAP.mmd` — Mermaid relation graph\n"
        "- `ADR_CONFLICT_MAP.mmd` — Mermaid conflict / gap graph\n",
        encoding="utf-8",
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (out_dir / "ADR_GOVERNANCE_INVESTIGATION.md").write_text(render_adr_investigation_markdown(bundle), encoding="utf-8")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (out_dir / "ADR_RELATION_MAP.mmd").write_text(render_adr_relation_map(bundle), encoding="utf-8")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (out_dir / "ADR_CONFLICT_MAP.mmd").write_text(render_adr_conflict_map(bundle), encoding="utf-8")
    return bundle
