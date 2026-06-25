"""Sync closed DS rows from the implementation input list into the completed log.

Runs automatically from ``hub_cli`` on every subcommand (unless skipped).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

INPUT_NAME = "despaghettification_implementation_input.md"
COMPLETED_NAME = "despaghettification_completed_log.md"
COMPLETED_EMPTY_TEMPLATE = "despaghettification_completed_log.EMPTY.md"

MARK_INFO = "## Information input list"
MARK_ORDER = "## Recommended implementation order"
MARK_ACTIVE = "## Active progress"
MARK_CLOSED_PHASES = "## Closed phases"

OPEN_DS_ROW = re.compile(r"^\|\s*\*\*(DS-\d+)\*\*\s*\|")
CLOSED_DS_ROW = re.compile(r"^\|\s*~~\s*\*{0,2}(DS-\d+)\*{0,2}\s*~~", re.I)
DS_ID_TOKEN = re.compile(r"\b(DS-\d+)\b")
PLACEHOLDER_ROW = re.compile(r"^\|\s*—\s*\|")
COMPLETED_WAVE_DS = re.compile(r"^\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*\*\*(DS-\d+)\*\*")
COMPLETED_DETAIL_DS = re.compile(r"^\|\s*\*\*(DS-\d+)\*\*\s*\|")
CLOSED_PHASE_ROW = re.compile(r"^\|\s*[^|]+\|\s*~~(DS-\d+)~~")
OPEN_PHASE_ROW = re.compile(r"^\|\s*[^|]+\|\s*\*\*(DS-\d+)\*\*\s*\|")


@dataclass
class DsTableRow:
    """One DS row parsed from a markdown table."""

    ds_id: str
    line: str
    cells: list[str]
    closed: bool


@dataclass
class SyncResult:
    """Outcome of ``sync_input_archive``."""

    changed: bool = False
    archived_ds: list[str] = field(default_factory=list)
    archived_active_rows: int = 0
    input_path: str = ""
    completed_path: str = ""
    message: str = ""


def _slice_section(md: str, start: str, end: str) -> str:
    i = md.find(start)
    j = md.find(end)
    if i == -1 or j == -1 or j <= i:
        return ""
    return md[i:j]


def _is_table_sep(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and set(s.replace("|", "").replace(":", "").strip()) <= {"-", " "}


def _parse_table_data_rows(block: str) -> list[DsTableRow]:
    rows: list[DsTableRow] = []
    header_seen = False
    for line in block.splitlines():
        if not line.strip().startswith("|"):
            continue
        if _is_table_sep(line):
            header_seen = True
            continue
        if not header_seen:
            continue
        if PLACEHOLDER_ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        closed_m = CLOSED_DS_ROW.match(line)
        open_m = OPEN_DS_ROW.match(line)
        ds_id: str | None = None
        closed = False
        if closed_m:
            ds_id = closed_m.group(1).upper()
            closed = True
        elif open_m:
            ds_id = open_m.group(1).upper()
        elif "CLOSED" in line.upper():
            dm = DS_ID_TOKEN.search(line)
            if dm:
                ds_id = dm.group(1).upper()
                closed = True
        if not ds_id:
            continue
        rows.append(DsTableRow(ds_id=ds_id, line=line, cells=cells, closed=closed))
    return rows


def _subsection_block(section: str, heading: str) -> str:
    marker = f"### {heading}"
    start = section.find(marker)
    if start == -1:
        return ""
    rest = section[start + len(marker) :]
    nxt = rest.find("\n### ")
    return rest[:nxt] if nxt != -1 else rest


def open_ds_ids_from_md(md: str) -> list[str]:
    """Return open **DS-*** ids from § *Open* (fallback: whole information list section)."""
    section = _slice_section(md, MARK_INFO, MARK_ORDER)
    if not section:
        return []

    def _collect(block: str) -> set[str]:
        return {r.ds_id for r in _parse_table_data_rows(block) if not r.closed}

    open_block = _subsection_block(section, "Open")
    seen = _collect(open_block) if open_block else set()
    if not seen:
        seen = _collect(section)
    if not seen:
        for line in section.splitlines():
            m = OPEN_DS_ROW.match(line)
            if m and not CLOSED_DS_ROW.match(line):
                seen.add(m.group(1).upper())
    return sorted(seen, key=lambda s: int(s.split("-")[1]))


def _existing_completed_ds(completed_md: str) -> set[str]:
    found: set[str] = set()
    for line in completed_md.splitlines():
        m = COMPLETED_WAVE_DS.match(line) or COMPLETED_DETAIL_DS.match(line)
        if m:
            found.add(m.group(1).upper())
    return found


def _ds_ids_in_cell(text: str) -> list[str]:
    return sorted({m.group(1).upper() for m in DS_ID_TOKEN.finditer(text)}, key=lambda s: int(s.split("-")[1]))


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def completed_log_empty_template_path(hub_dir: Path) -> Path:
    """Path to the canonical EMPTY completed-log template."""
    return hub_dir / "templates" / COMPLETED_EMPTY_TEMPLATE


def load_completed_log_template(hub_dir: Path) -> str:
    """Load EMPTY completed-log body; minimal fallback if template is missing."""
    path = completed_log_empty_template_path(hub_dir)
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return (
        "# Despaghettification — completed work log (archive)\n\n"
        "## Closed DS detail\n\n"
        "| ID | pattern | location (typical) | outcome (done) | gates / evidence |\n"
        "|----|---------|--------------------|----------------|------------------|\n\n"
        "## Completed waves\n\n"
        "| date | ID(s) | short description | pre artefacts (rel. to `despaghettify/state/`) | "
        "post artefacts (rel. to `despaghettify/state/`) | state doc(s) updated | PR / commit |\n"
        "|------|-------|-------------------|----------------------------------------|"
        "----------------------------------------|----------------------|-------------|\n"
    )


def _insert_after_table_header(lines: list[str], header_prefix: str) -> int | None:
    """Return line index after the separator row following a table header."""
    for i, line in enumerate(lines):
        if line.strip().startswith(header_prefix):
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("|") and _is_table_sep(lines[j]):
                    return j + 1
    return None


def _append_completed_detail(completed_md: str, row: DsTableRow, date: str) -> str:
    pattern = row.cells[1] if len(row.cells) > 1 else "—"
    location = row.cells[2] if len(row.cells) > 2 else "—"
    outcome = row.cells[3] if len(row.cells) > 3 else "—"
    gates = row.cells[3] if len(row.cells) > 3 and "Done" in row.cells[3] else (row.cells[4] if len(row.cells) > 4 else "—")
    if "Done" in outcome or len(outcome) > 120:
        gates = outcome
        outcome = row.cells[4] if len(row.cells) > 4 else "Closed (auto-archived)"
    new_line = (
        f"| **{row.ds_id}** | {pattern} | {location} | {outcome} | {gates} |"
    )
    if "## Closed DS detail" not in completed_md:
        return completed_md
    lines = completed_md.splitlines()
    insert_at = _insert_after_table_header(lines, "| ID | pattern | location (typical) |")
    if insert_at is None:
        return completed_md
    if insert_at < len(lines) and PLACEHOLDER_ROW.match(lines[insert_at]):
        lines[insert_at] = new_line
    else:
        lines.insert(insert_at, new_line)
    return "\n".join(lines) + ("\n" if completed_md.endswith("\n") else "")


def _append_completed_wave(
    completed_md: str,
    row: DsTableRow,
    date: str,
) -> str:
    short = row.cells[3] if len(row.cells) > 3 else f"Closed {row.ds_id} (auto-archived from input list)."
    if len(short) > 200:
        short = short[:197] + "..."
    new_line = (
        f"| {date} | **{row.ds_id}** | {short} | — | — | — | — |"
    )
    if "## Completed waves" not in completed_md:
        return completed_md
    lines = completed_md.splitlines()
    insert_at = _insert_after_table_header(lines, "| date | ID(s) |")
    if insert_at is None:
        return completed_md
    if insert_at < len(lines) and PLACEHOLDER_ROW.match(lines[insert_at]):
        lines[insert_at] = new_line
    else:
        lines.insert(insert_at, new_line)
    return "\n".join(lines) + ("\n" if completed_md.endswith("\n") else "")


def _render_info_section(open_rows: list[DsTableRow], closed_ids: list[str], batch_date: str) -> str:
    open_lines = [r.line for r in open_rows if not r.closed]
    if not open_lines:
        open_body = "| — | — | — | — | — | — |\n"
        no_open_note = (
            "\n*No open **DS-*** rows. Next backlog comes from **`spaghetti-check`** when "
            "[trigger policy](#trigger-policy-for-check-task-updates) fires — do not hand-copy closed rows back here.*\n"
        )
    else:
        open_body = "\n".join(open_lines) + "\n"
        no_open_note = ""

    if closed_ids:
        chain = " → ".join(
            f"**{ds}** ({_pattern_hint(ds)})" for ds in closed_ids
        )
        closed_note = (
            f"\n### Closed (archived — do not duplicate here)\n\n"
            f"**Batch closed {batch_date}:** {chain}. Per-DS outcomes, gates, and artefact paths: "
            f"**[despaghettification_completed_log.md](despaghettification_completed_log.md)** § *Completed waves*. "
            f"Workstream evidence: `WORKSTREAM_*_STATE.md` under `despaghettify/state/`.\n"
        )
    else:
        closed_note = (
            "\n### Closed (archived)\n\n"
            "*None.* Closed **DS-*** detail lives in "
            "[despaghettification_completed_log.md](despaghettification_completed_log.md).\n"
        )

    known_ids = [r.ds_id for r in open_rows] + closed_ids
    next_num = max((int(ds.split("-")[1]) for ds in known_ids), default=5) + 1
    next_id = f"DS-{next_num:03d}"

    return (
        "## Information input list (extensible)\n\n"
        "Each **open** row: **ID**, **pattern** (lead with **C1..C7** from "
        "[spaghetti-setup.md](../spaghetti-setup.md) § *Per-category trigger bars*, e.g. **`C3 ·`** …), "
        "**location**, **hint / measurement idea**, **direction**, **collision hint**.\n\n"
        "### Open\n\n"
        "| ID | pattern | location (typical) | hint / measurement idea | direction (solution sketch) | collision hint |\n"
        "|----|---------|--------------------|-------------------------|----------------------------|----------------|\n"
        f"{open_body}"
        f"{no_open_note}"
        f"{closed_note}\n"
        f"**New rows:** next **{next_id}**+ when check fills the open table; on closure append "
        "[despaghettification_completed_log.md](despaghettification_completed_log.md) and remove from *Open* above.\n"
    )


def _pattern_hint(ds_id: str) -> str:
    n = ds_id.split("-")[1]
    hints = {
        "001": "C1",
        "002": "C4",
        "003": "C6",
        "004": "C5",
        "005": "C7",
    }
    return hints.get(n, "Cx")


def _render_order_section(
    open_phase_lines: list[str],
    closed_phase_ids: list[str],
    batch_date: str,
    keep_mermaid: bool,
    mermaid_block: str,
) -> str:
    if not open_phase_lines:
        open_body = "| — | — | — | — | — |\n"
        open_note = (
            "\n*Filled on next **`spaghetti-check`** when trigger policy adds **DS-006**+ to § *Open*.*\n"
        )
    else:
        open_body = "\n".join(open_phase_lines) + "\n"
        open_note = ""

    open_mermaid = ""
    if open_phase_lines and mermaid_block.strip():
        open_mermaid = f"\n{mermaid_block.strip()}\n"

    mermaid_note = (
        "**Mermaid:** present because open phase rows exist."
        if open_phase_lines and mermaid_block.strip()
        else "**Mermaid:** omit while the open table is only `—`."
    )

    return (
        "## Recommended implementation order\n\n"
        "Prioritised **phases** for **open** **DS-*** only — aligned with § *Open* in the information input list "
        "and [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md). **Mandatory** Mermaid `flowchart` "
        "**below** the table once open phase rows exist ([spaghetti-check-task.md](../spaghetti-check-task.md) §3).\n\n"
        "### Open phases\n\n"
        "| Priority / phase | DS-ID(s) | short logic | workstream (primary) | note (dependencies, gates) |\n"
        "|------------------|----------|-------------|----------------------|----------------------------|\n"
        f"{open_body}"
        f"{open_note}"
        f"{open_mermaid}\n"
        "**Fill in:** one phase row per **open** **DS-*** when check repopulates the backlog. "
        f"{mermaid_note}\n\n"
        "**Implementation:** invoke [spaghetti-solve-task.md](../spaghetti-solve-task.md) with **one** **DS-ID** per run.\n"
    )


def _render_closed_phases_section(
    closed_phase_ids: list[str],
    batch_date: str,
    keep_mermaid: bool,
    mermaid_block: str,
) -> str:
    if closed_phase_ids:
        chain = " → ".join(closed_phase_ids)
        body = (
            f"Executed **{batch_date}** in order: **{chain}**. Detail and gates: "
            f"[despaghettification_completed_log.md](despaghettification_completed_log.md).\n"
        )
        if keep_mermaid and mermaid_block.strip():
            body += f"\nHistorical flow (reference only):\n\n{mermaid_block.strip()}\n"
    else:
        body = "*None.* See [despaghettification_completed_log.md](despaghettification_completed_log.md).\n"
    return f"## Closed phases (archived)\n\n{body}\n"


def _extract_mermaid(order_section: str) -> str:
    start = order_section.find("```mermaid")
    if start == -1:
        return ""
    end = order_section.find("```", start + 3)
    if end == -1:
        return ""
    return order_section[start : end + 3]


def _replace_section(md: str, start: str, end: str, new_body: str) -> str:
    i = md.find(start)
    j = md.find(end)
    if i == -1 or j == -1 or j <= i:
        return md
    return md[:i] + new_body + md[j:]


def _find_next_h2(md: str, start: int) -> int:
    """Return the next level-2 heading after ``start`` or EOF."""
    match = re.search(r"\n## ", md[start + 1 :])
    if not match:
        return len(md)
    return start + 1 + match.start()


def _replace_or_insert_closed_phases(md: str, new_body: str) -> str:
    start = md.find(MARK_CLOSED_PHASES)
    if start != -1:
        end = _find_next_h2(md, start)
        return md[:start] + new_body + md[end:]
    active = md.find(MARK_ACTIVE)
    if active == -1:
        return md
    insert_at = _find_next_h2(md, active)
    return md[:insert_at] + new_body + md[insert_at:]


def sync_input_archive(hub_dir: Path, *, dry_run: bool = False) -> SyncResult:
    """Archive closed DS rows from the input list into the completed log and normalize layout."""
    hub = hub_dir.resolve()
    input_path = hub / INPUT_NAME
    completed_path = hub / COMPLETED_NAME
    result = SyncResult(
        input_path=input_path.as_posix(),
        completed_path=completed_path.as_posix(),
    )
    if not input_path.is_file():
        result.message = "input list missing"
        return result

    md = input_path.read_text(encoding="utf-8", errors="replace")
    completed_md = (
        completed_path.read_text(encoding="utf-8", errors="replace")
        if completed_path.is_file()
        else ""
    )
    if not completed_md and not dry_run:
        completed_md = load_completed_log_template(hub)

    info_sec = _slice_section(md, MARK_INFO, MARK_ORDER)
    order_sec = _slice_section(md, MARK_ORDER, MARK_ACTIVE)
    active_end_marker = MARK_CLOSED_PHASES if MARK_CLOSED_PHASES in md else "## Canonical"
    active_sec = _slice_section(md, MARK_ACTIVE, active_end_marker)
    closed_start = md.find(MARK_CLOSED_PHASES)
    closed_sec = md[closed_start : _find_next_h2(md, closed_start)] if closed_start != -1 else ""

    all_info_rows = _parse_table_data_rows(info_sec)
    open_block_rows = _parse_table_data_rows(_subsection_block(info_sec, "Open") or info_sec)
    closed_rows = [r for r in all_info_rows if r.closed]
    open_rows = [r for r in open_block_rows if not r.closed]

    # Legacy: closed rows outside ### Open still in section
    for r in all_info_rows:
        if r.closed and r.ds_id not in {x.ds_id for x in closed_rows}:
            closed_rows.append(r)

    open_phase_lines: list[str] = []
    closed_phase_ids: list[str] = []
    for line in (order_sec + "\n" + closed_sec).splitlines():
        if CLOSED_PHASE_ROW.match(line):
            closed_phase_ids.append(CLOSED_PHASE_ROW.match(line).group(1).upper())
        elif OPEN_PHASE_ROW.match(line):
            open_phase_lines.append(line)
        elif "~~DS-" in line and "|" in line:
            dm = DS_ID_TOKEN.search(line)
            if dm and "~~" in line.split("|")[1]:
                closed_phase_ids.append(dm.group(1).upper())

    existing = _existing_completed_ds(completed_md)
    date = _today_utc()
    new_completed = completed_md
    for row in closed_rows:
        rid = row.ds_id
        if rid in existing:
            continue
        new_completed = _append_completed_detail(new_completed, row, date)
        new_completed = _append_completed_wave(new_completed, row, date)
        result.archived_ds.append(rid)
        existing.add(rid)

    # Active progress: archive rows that only reference closed DS (not open backlog)
    open_ids = {r.ds_id for r in open_rows}
    table_header: list[str] = []
    active_table_rows: list[str] = []
    phase = "prose"
    for line in active_sec.splitlines():
        if line.strip().startswith("| date |"):
            phase = "header"
            table_header.append(line)
            continue
        if phase == "header" and _is_table_sep(line):
            table_header.append(line)
            phase = "rows"
            continue
        if phase == "rows" and line.strip().startswith("|"):
            ids = _ds_ids_in_cell(line)
            if ids and not PLACEHOLDER_ROW.match(line) and all(i not in open_ids for i in ids):
                if not dry_run:
                    new_completed = _append_completed_wave_from_active(new_completed, line, date)
                result.archived_active_rows += 1
                continue
            active_table_rows.append(line)
            continue
        if phase == "rows":
            phase = "suffix"
    if not active_table_rows:
        active_table_rows = ["| — | — | — | — | — | — | — |"]

    closed_ids_sorted = sorted({r.ds_id for r in closed_rows}, key=lambda s: int(s.split("-")[1]))
    batch_date = date
    if "Batch closed" in info_sec:
        bm = re.search(r"Batch closed (\d{4}-\d{2}-\d{2})", info_sec)
        if bm:
            batch_date = bm.group(1)

    new_info = _render_info_section(open_rows, closed_ids_sorted, batch_date)
    mermaid = _extract_mermaid(order_sec)
    new_order = _render_order_section(
        open_phase_lines,
        sorted(set(closed_phase_ids), key=lambda s: int(s.split("-")[1])),
        batch_date,
        keep_mermaid=bool(closed_phase_ids),
        mermaid_block=mermaid,
    )
    new_closed_phases = _render_closed_phases_section(
        sorted(set(closed_phase_ids), key=lambda s: int(s.split("-")[1])),
        batch_date,
        keep_mermaid=bool(closed_phase_ids),
        mermaid_block=mermaid,
    )

    new_md = _replace_section(md, MARK_INFO, MARK_ORDER, new_info)
    new_md = _replace_section(new_md, MARK_ORDER, MARK_ACTIVE, new_order)
    new_md = _replace_or_insert_closed_phases(new_md, new_closed_phases)

    if result.archived_active_rows > 0:
        prose_end = active_sec.find("| date |")
        prose = ""
        if prose_end > 0:
            prose = active_sec[:prose_end].strip()
            if "\n" in prose:
                prose = prose.split("\n", 1)[1].strip() + "\n\n"
        suffix_start = active_sec.find("**Rules:**")
        suffix = active_sec[suffix_start:] if suffix_start >= 0 else ""
        rebuilt_active = (
            "## Active progress (in-flight only)\n\n"
            + prose
            + "\n".join(table_header)
            + "\n"
            + "\n".join(active_table_rows)
            + "\n\n"
            + suffix
        )
        new_md = _replace_section(new_md, MARK_ACTIVE, active_end_marker, rebuilt_active)

    open_block = _subsection_block(info_sec, "Open") or ""
    needs_layout = (
        "### Open" not in info_sec
        or any(r.closed for r in _parse_table_data_rows(open_block))
        or "~~DS-" in open_block
        or "## Progress / work log" in md
        or "### Open phases" not in order_sec
    )
    changed = new_md != md or new_completed != completed_md or needs_layout
    result.changed = changed

    if dry_run or not changed:
        result.message = "dry-run, no write" if dry_run else "already normalized"
        return result

    input_path.write_text(new_md, encoding="utf-8", newline="\n")
    if new_completed != completed_md:
        completed_path.write_text(new_completed, encoding="utf-8", newline="\n")
    n = len(result.archived_ds)
    result.message = f"archived {n} DS row(s); normalized input layout"
    return result


def _append_completed_wave_from_active(completed_md: str, line: str, date: str) -> str:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    ids = cells[1] if len(cells) > 1 else "—"
    short = cells[2] if len(cells) > 2 else "Active progress archived"
    new_line = f"| {date} | {ids} | {short} | — | — | — | — |"
    marker = "## Completed waves"
    if marker not in completed_md:
        return completed_md
    lines = completed_md.splitlines()
    insert_at = None
    for i, line_h in enumerate(lines):
        if line_h.strip().startswith("| date | ID(s) |"):
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("|------"):
                    insert_at = j + 1
                    break
            break
    if insert_at is None:
        return completed_md
    lines.insert(insert_at, new_line)
    return "\n".join(lines) + ("\n" if completed_md.endswith("\n") else "")
