"""Tests for conftest.

"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest


def build_minimal_dockerify_repo(tmp_path: Path) -> Path:
    """Build minimal dockerify repo.

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
    (root / "'fy'-suites" / 'dockerify' / 'reports').mkdir(parents=True, exist_ok=True)
    (root / 'backend' / 'migrations').mkdir(parents=True, exist_ok=True)
    (root / 'database' / 'tests').mkdir(parents=True, exist_ok=True)
    (root / 'tests' / 'smoke').mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'pyproject.toml').write_text('[project]\nname="fixture"\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'docker-compose.yml').write_text(
        'services:\n'
        '  backend:\n'
        '    depends_on:\n'
        '      play-service:\n'
        '        condition: service_healthy\n'
        '  frontend: {}\n'
        '  administration-tool: {}\n'
        '  play-service:\n'
        '    healthcheck:\n'
        '      test: ["CMD", "true"]\n',
        encoding='utf-8',
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'docker-up.py').write_text('init-env ensure-env up build restart stop down reset health .env', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / '.env.example').write_text('SECRET_KEY=\n', encoding='utf-8')
    # Process rel one item at a time so build_minimal_dockerify_repo applies the same
    # rule across the full collection.
    for rel in ('backend/Dockerfile', 'world-engine/Dockerfile', 'frontend/Dockerfile', 'administration-tool/Dockerfile'):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        p.write_text('FROM scratch\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'backend' / 'docker-entrypoint.sh').write_text('flask db upgrade\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'database' / 'tests' / 'test_database_migrations_and_files.py').write_text('def test_ok():\n    assert True\n', encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / 'database' / 'tests' / 'test_database_upgrades.py').write_text('def test_ok():\n    assert True\n', encoding='utf-8')
    # Process rel one item at a time so build_minimal_dockerify_repo applies the same
    # rule across the full collection.
    for rel in ('test_backend_startup.py', 'test_admin_startup.py', 'test_engine_startup.py'):
        (root / 'tests' / 'smoke' / rel).write_text('def test_ok():\n    assert True\n', encoding='utf-8')
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
    fake = build_minimal_dockerify_repo(tmp_path)
    monkeypatch.setenv('DOCKERIFY_REPO_ROOT', str(fake))
    monkeypatch.setattr('dockerify.tools.repo_paths.repo_root', lambda start=None: fake)
    monkeypatch.setattr('dockerify.tools.hub_cli.repo_root', lambda start=None: fake)
    yield
