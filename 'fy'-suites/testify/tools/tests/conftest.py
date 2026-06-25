"""Tests for conftest.

"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


def build_minimal_testify_repo(tmp_path: Path) -> Path:
    """Build minimal testify repo.

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
    (root / "'fy'-suites" / 'testify' / 'reports').mkdir(parents=True, exist_ok=True)
    (root / '.github' / 'workflows').mkdir(parents=True, exist_ok=True)
    (root / 'tests').mkdir(parents=True, exist_ok=True)
    # Process rel one item at a time so build_minimal_testify_repo applies the same rule
    # across the full collection.
    for rel in ('backend/pyproject.toml', 'frontend/pyproject.toml', 'administration-tool/pyproject.toml', 'world-engine/pyproject.toml', 'ai_stack/pyproject.toml', 'story_runtime_core/pyproject.toml'):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        p.write_text('[project]\nname="fixture"\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'pyproject.toml').write_text(
        '[project]\nname="fixture"\n\n[project.scripts]\n'
        'despag-check = "despaghettify.tools.hub_cli:main"\n'
        'wos-despag = "despaghettify.tools.hub_cli:main"\n'
        'postmanify = "postmanify.tools.cli:main"\n'
        'docify = "docify.tools.hub_cli:main"\n'
        'contractify = "contractify.tools.hub_cli:main"\n'
        'fy-platform = "fy_platform.tools.cli:main"\n'
        'dockerify = "dockerify.tools.hub_cli:main"\n'
        'testify = "testify.tools.hub_cli:main"\n'
        'documentify = "documentify.tools.hub_cli:main"\n\n'
        '[tool.setuptools.packages.find]\nwhere = ["\'fy\'-suites"]\n',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'tests' / 'run_tests.py').write_text(
        'SUITE_DISPLAY_NAMES = {"backend": "Backend", "ai_stack": "AI"}\n'
        'SUITE_PYTEST_TARGETS = {"backend": ("backend", "tests"), "ai_stack": (".", "ai_stack/tests")}\n'
        'ALL_SUITE_SEQUENCE = ("backend", "ai_stack")\n',
        encoding='utf-8',
    )
    required = ['backend-tests.yml','admin-tests.yml','engine-tests.yml','ai-stack-tests.yml','quality-gate.yml','pre-deployment.yml','compose-smoke.yml']
    # Process name one item at a time so build_minimal_testify_repo applies the same
    # rule across the full collection.
    for name in required:
        (root / '.github' / 'workflows' / name).write_text('name: x\non:\n  push: {}\njobs:\n  test:\n    runs-on: ubuntu-latest\n', encoding='utf-8')
    (root / 'fy_platform' / 'runtime').mkdir(parents=True, exist_ok=True)
    (root / 'fy_platform' / 'runtime' / 'mode_registry.py').write_text(
        'MODE_SPECS = {\n'
        '    "analyze.contract": None,\n'
        '    "analyze.quality": None,\n'
        '    "analyze.code_docs": None,\n'
        '    "analyze.docs": None,\n'
        '}\n',
        encoding='utf-8',
    )
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
    fake = build_minimal_testify_repo(tmp_path)
    monkeypatch.setenv('TESTIFY_REPO_ROOT', str(fake))
    monkeypatch.setattr('testify.tools.repo_paths.repo_root', lambda start=None: fake)
    monkeypatch.setattr('testify.tools.hub_cli.repo_root', lambda start=None: fake)
    yield
