"""Tests for conftest.

"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


def build_minimal_documentify_repo(tmp_path: Path) -> Path:
    """Build minimal documentify repo.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        tmp_path: Filesystem path to the file or directory being
            processed.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    root = tmp_path / 'repo'
    (root / "'fy'-suites" / 'documentify' / 'reports').mkdir(parents=True, exist_ok=True)
    (root / '.github' / 'workflows').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'start-here').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'technical').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'testing').mkdir(parents=True, exist_ok=True)
    (root / 'docs' / 'operations').mkdir(parents=True, exist_ok=True)
    # Process svc one item at a time so build_minimal_documentify_repo applies the same
    # rule across the full collection.
    for svc in ('frontend', 'administration-tool', 'backend', 'world-engine', 'ai_stack', 'story_runtime_core', 'writers-room'):
        (root / svc).mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'pyproject.toml').write_text('[project]\nname="fixture"\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'README.md').write_text('# Fixture\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'docs' / 'start-here' / 'README.md').write_text('# Start\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'docs' / 'technical' / 'README.md').write_text('# Technical\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'docs' / 'testing' / 'README.md').write_text('# Testing\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'docs' / 'operations' / 'RUNBOOK.md').write_text('# Runbook\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / '.github' / 'workflows' / 'backend-tests.yml').write_text('name: x\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'docker-up.py').write_text('print()\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'docker-compose.yml').write_text('services: {}\n', encoding='utf-8')
    (root / 'tests').mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'tests' / 'TESTING.md').write_text('# Testing\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'tests' / 'run_tests.py').write_text('print()\n', encoding='utf-8')
    return root


@pytest.fixture(autouse=True)
def _patch_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Patch repo root.

    Args:
        monkeypatch: Primary monkeypatch used by this step.
        tmp_path: Filesystem path to the file or directory being
            processed.

    Returns:
        Iterator[None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    fake = build_minimal_documentify_repo(tmp_path)
    monkeypatch.setenv('DOCUMENTIFY_REPO_ROOT', str(fake))
    monkeypatch.setattr('documentify.tools.repo_paths.repo_root', lambda start=None: fake)
    monkeypatch.setattr('documentify.tools.hub_cli.repo_root', lambda start=None: fake)
    yield
