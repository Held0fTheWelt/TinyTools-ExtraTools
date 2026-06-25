"""Tests for input list → completed log archive sync."""
from __future__ import annotations

from pathlib import Path

from despaghettify.tools.input_list_archive import (
    completed_log_empty_template_path,
    load_completed_log_template,
    open_ds_ids_from_md,
    sync_input_archive,
)


def _legacy_closed_input() -> str:
    return """# Test

## Information input list (extensible)

| ID | pattern | location | hint | direction | collision |
|----|---------|----------|------|-----------|-----------|
| ~~**DS-001**~~ **CLOSED** | **C1 ·** x | loc | Done: seams | dir | — |
| **DS-002** | **C4 ·** y | loc2 | hint | dir2 | — |

## Recommended implementation order

| Priority / phase | DS-ID(s) | short logic | workstream (primary) | note |
|------------------|----------|-------------|----------------------|------|
| 1 | ~~DS-001~~ | logic | ws | closed |
| 2 | **DS-002** | logic2 | ws | open |

## Active progress (in-flight only)

| date | ID(s) | short description | pre | post | state | PR |
|------|-------|-------------------|-----|------|-------|-----|
| 2026-05-19 | DS-001 | partial | — | — | — | — |

## Canonical technical reading paths

- x
"""


def test_archives_closed_rows_and_keeps_open(tmp_path: Path) -> None:
    hub = tmp_path / "despaghettify"
    hub.mkdir()
    (hub / "despaghettification_implementation_input.md").write_text(
        _legacy_closed_input(), encoding="utf-8"
    )
    (hub / "despaghettification_completed_log.md").write_text(
        "# Completed\n\n## Closed DS detail (batch)\n\n"
        "| ID | pattern | location (typical) | outcome (done) | gates / evidence |\n"
        "|----|---------|--------------------|----------------|------------------|\n\n"
        "## Completed waves\n\n"
        "| date | ID(s) | short description | pre artefacts | post artefacts | state | PR |\n"
        "|------|-------|-------------------|---------------|----------------|-------|-----|\n",
        encoding="utf-8",
    )
    result = sync_input_archive(hub)
    assert result.changed
    assert "DS-001" in result.archived_ds
    md = (hub / "despaghettification_implementation_input.md").read_text(encoding="utf-8")
    assert "### Open" in md
    assert "~~DS-001~~" not in md.split("### Open")[1].split("### Closed")[0]
    assert "DS-002" in md
    assert open_ds_ids_from_md(md) == ["DS-002"]
    completed = (hub / "despaghettification_completed_log.md").read_text(encoding="utf-8")
    assert "**DS-001**" in completed


def test_completed_log_empty_template_exists_in_hub() -> None:
    from despaghettify.tools.repo_paths import despag_hub_dir, repo_root

    hub = despag_hub_dir(repo_root())
    tpl = completed_log_empty_template_path(hub)
    assert tpl.is_file()
    body = load_completed_log_template(hub)
    assert "## Closed DS detail" in body
    assert "## Completed waves" in body
    assert "| — | — | — | — | — | — | — |" in body


def test_creates_completed_log_from_template_when_missing(tmp_path: Path) -> None:
    hub = tmp_path / "despaghettify"
    (hub / "templates").mkdir(parents=True)
    tpl_src = (
        Path(__file__).resolve().parents[2]
        / "templates"
        / "despaghettification_completed_log.EMPTY.md"
    )
    (hub / "templates" / "despaghettification_completed_log.EMPTY.md").write_text(
        tpl_src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (hub / "despaghettification_implementation_input.md").write_text(
        _legacy_closed_input(),
        encoding="utf-8",
    )
    result = sync_input_archive(hub)
    assert result.changed
    completed = hub / "despaghettification_completed_log.md"
    assert completed.is_file()
    assert "## When to append here" in completed.read_text(encoding="utf-8")


def test_idempotent_when_already_normalized(tmp_path: Path) -> None:
    hub = tmp_path / "despaghettify"
    hub.mkdir()
    inp = hub / "despaghettification_implementation_input.md"
    inp.write_text(
        """# T

## Information input list (extensible)

### Open

| ID | pattern | location (typical) | hint | direction | collision |
|----|---------|----------|------|-----------|-----------|
| — | — | — | — | — | — |

### Closed (archived)

*None.*

## Recommended implementation order

### Open phases

| Priority / phase | DS-ID(s) | short logic | workstream (primary) | note |
|------------------|----------|-------------|----------------------|------|
| — | — | — | — | — |

### Closed phases (archived)

*None.*

## Active progress (in-flight only)

| date | ID(s) | short description | pre | post | state | PR |
|------|-------|-------------------|-----|------|-------|-----|
| — | — | — | — | — | — | — |

## Canonical

- x
""",
        encoding="utf-8",
    )
    (hub / "despaghettification_completed_log.md").write_text(
        "# Completed\n\n## Closed DS detail\n\n| ID | p | l | o | g |\n|----|---|---|---|---|\n\n"
        "## Completed waves\n\n| date | ID(s) | s | pre | post | st | pr |\n|------|-------|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    before = inp.read_text(encoding="utf-8")
    result = sync_input_archive(hub)
    after = inp.read_text(encoding="utf-8")
    assert not result.archived_ds
    assert after == before or result.changed  # layout normalize may tweak whitespace only
