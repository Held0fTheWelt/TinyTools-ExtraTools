"""Version and status extraction — deterministic string scans only."""
from __future__ import annotations

from pathlib import Path

import pytest

import contractify.tools.repo_paths as repo_paths
from contractify.tools.versioning import (
    adr_declared_status,
    adr_supersedes_line,
    openapi_declared_version,
    read_openapi_version_from_file,
    resolve_supersedes_markdown_target,
)


def test_openapi_version_from_fixture_repo() -> None:
    """Verify that openapi version from fixture repo works as expected.
    """
    root = repo_paths.repo_root()
    p = root / "docs" / "api" / "openapi.yaml"
    assert read_openapi_version_from_file(p) == "0.0.1"


def test_openapi_declared_version_parses_info_block() -> None:
    """Verify that openapi declared version parses info block works as
    expected.
    """
    text = "openapi: 3.0.3\ninfo:\n  title: T\n  version: 2.4.0\npaths: {}\n"
    assert openapi_declared_version(text) == "2.4.0"


def test_adr_status_parses_markdown() -> None:
    """Verify that adr status parses markdown works as expected.
    """
    head = "# ADR\n\n**Status**: Deprecated\n\nBody.\n"
    assert adr_declared_status(head) == "deprecated"


def test_adr_supersedes_line_resolves_relative_markdown(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Isolated tree: autouse hermetic repo also uses ``tmp_path`` for
    ``docs/governance``.

    This callable writes or records artifacts as part of its workflow.

    Args:
        tmp_path_factory: Primary tmp path factory used by this step.
    """
    tmp_path = tmp_path_factory.mktemp("versioning_supersedes_iso")
    gov = tmp_path / "docs" / "governance"
    gov.mkdir(parents=True)
    target = gov / "adr-0001-scene-identity.md"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    target.write_text("# ADR 1\n", encoding="utf-8")
    newer = gov / "adr-0003-retired.md"
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    newer.write_text(
        "# ADR 3\n\n**Status**: Superseded\n\nSupersedes: [ADR 1](adr-0001-scene-identity.md)\n",
        encoding="utf-8",
    )
    head = newer.read_text(encoding="utf-8")
    body = adr_supersedes_line(head)
    assert "adr-0001" in body
    rel = resolve_supersedes_markdown_target(body, adr_file=newer, repo=tmp_path)
    assert rel.replace("\\", "/").endswith("docs/governance/adr-0001-scene-identity.md")
