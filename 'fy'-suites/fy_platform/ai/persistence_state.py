"""Persistence state for fy_platform.ai.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.contracts import STORAGE_SCHEMA_VERSIONS
from fy_platform.ai.workspace import utc_now, workspace_root, write_json

SCHEMA_STATE_REL = Path('.fydata/registry/schema_versions.json')
MIGRATION_LOG_REL = Path('.fydata/registry/migration_log.jsonl')


def _default_state() -> dict[str, Any]:
    """Default state.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return {
        'schema_version': 'fy.storage-schema-state.v1',
        'generated_at': utc_now(),
        'components': {k: {'current_version': v, 'last_migrated_at': utc_now(), 'status': 'ok'} for k, v in STORAGE_SCHEMA_VERSIONS.items()},
    }


def load_schema_state(root: Path | None = None) -> dict[str, Any]:
    """Load schema state.

    This callable writes or records artifacts as part of its workflow.
    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    path = workspace / SCHEMA_STATE_REL
    # Branch on not path.is_file() so load_schema_state only continues along the
    # matching state path.
    if not path.is_file():
        state = _default_state()
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(path, state)
        return state
    # Protect the critical load_schema_state work so failures can be turned into a
    # controlled result or cleanup path.
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        state = _default_state()
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(path, state)
        return state


def ensure_schema_state(root: Path | None = None) -> dict[str, Any]:
    """Ensure schema state.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    state = load_schema_state(workspace)
    changed = False
    components = state.setdefault('components', {})
    for name, version in STORAGE_SCHEMA_VERSIONS.items():
        entry = components.get(name)
        if not isinstance(entry, dict) or entry.get('current_version') != version:
            components[name] = {
                'current_version': version,
                'last_migrated_at': utc_now(),
                'status': 'ok',
            }
            changed = True
    if changed:
        state['generated_at'] = utc_now()
        # Persist the structured JSON representation so automated tooling can consume
        # the result without reparsing prose.
        write_json(workspace / SCHEMA_STATE_REL, state)
    return state


def plan_storage_migrations(root: Path | None = None) -> dict[str, Any]:
    """Plan storage migrations.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    state = load_schema_state(workspace)
    plans: list[dict[str, Any]] = []
    for name, version in STORAGE_SCHEMA_VERSIONS.items():
        current = int((state.get('components', {}).get(name, {}) or {}).get('current_version', 0) or 0)
        if current < version:
            plans.append({'component': name, 'from_version': current, 'to_version': version, 'action': 'migrate'})
    return {
        'schema_version': 'fy.storage-migration-plan.v1',
        'workspace_root': str(workspace),
        'required': bool(plans),
        'plans': plans,
    }


def record_migration_event(root: Path | None, *, component: str, from_version: int, to_version: int, action: str, status: str = 'ok') -> None:
    """Record migration event.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.
        component: Primary component used by this step.
        from_version: Primary from version used by this step.
        to_version: Primary to version used by this step.
        action: Primary action used by this step.
        status: Named status for this operation.
    """
    workspace = workspace_root(root)
    path = workspace / MIGRATION_LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        'ts': utc_now(),
        'component': component,
        'from_version': from_version,
        'to_version': to_version,
        'action': action,
        'status': status,
    }
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + '\n')
