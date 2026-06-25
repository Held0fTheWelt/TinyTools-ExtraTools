"""Evolution contract pack for fy_platform.ai.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import workspace_root

CONTRACT_PACK_VERSION = 'fy.evolution-wave1.contract-pack.v1'
META_DIRS = {'docs', 'internal', 'MVPs', "'fy'-suites", '.git', '.github', '.pytest_cache', '.fydata', '__pycache__'}


def canonical_schema_source_dir(root: Path | None = None) -> Path:
    """Canonical schema source dir.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    workspace = workspace_root(root)
    return workspace / 'fy_platform' / 'contracts' / 'evolution_wave1' / 'schemas'


def canonical_schema_payloads(root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Canonical schema payloads.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    source_dir = canonical_schema_source_dir(root)
    payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(source_dir.glob('*.json')):
        payloads[path.name] = json.loads(path.read_text(encoding='utf-8'))
    return payloads


def suite_dirs_for_ownership(root: Path | None = None) -> list[Path]:
    """Suite dirs for ownership.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        list[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    workspace = workspace_root(root)
    out: list[Path] = []
    for path in sorted(workspace.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_dir() or path.name.startswith('.') or path.name in META_DIRS:
            continue
        if path.name == 'fy_platform' or (path / 'adapter' / 'service.py').is_file() or path.name in {'brokenify', 'observifyfy'}:
            out.append(path)
    return out


def suite_names_for_ownership(root: Path | None = None) -> list[str]:
    """Suite names for ownership.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    return [path.name for path in suite_dirs_for_ownership(root)]
