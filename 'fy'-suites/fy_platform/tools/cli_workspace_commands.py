"""Cli workspace commands for fy_platform.tools.

"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from fy_platform.ai.backup_manager import create_workspace_backup, rollback_workspace_backup
from fy_platform.ai.observability import ObservabilityStore
from fy_platform.ai.production_readiness import workspace_production_readiness, write_workspace_production_site
from fy_platform.ai.release_readiness import workspace_release_readiness, write_workspace_release_site
from fy_platform.ai.workspace_status_site import build_workspace_status_site, write_workspace_status_site
from fy_platform.core.manifest import load_manifest, manifest_path
from fy_platform.core.project_resolver import resolve_project_root


def detect_roots(repo: Path) -> dict[str, list[str]]:
    """Detect roots.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        dict[str, list[str]]:
            Structured payload describing the outcome of the
            operation.
    """
    buckets = {
        'source': ['backend', 'world-engine', 'ai_stack', 'story_runtime_core', 'frontend', 'writers-room', 'src'],
        'docs': ['docs'],
        'tests': ['tests'],
        'templates': ['templates', 'frontend/templates', 'administration-tool/templates'],
    }
    out: dict[str, list[str]] = {key: [] for key in buckets}
    # Process (bucket, candidates) one item at a time so detect_roots applies the same
    # rule across the full collection.
    for bucket, candidates in buckets.items():
        # Process rel one item at a time so detect_roots applies the same rule across
        # the full collection.
        for rel in candidates:
            # Branch on (repo / rel).exists() so detect_roots only continues along the
            # matching state path.
            if (repo / rel).exists():
                out[bucket].append(rel)
    return out


def build_manifest_payload(repo: Path) -> dict:
    """Build manifest payload.

    Args:
        repo: Primary repo used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    roots = detect_roots(repo)
    project_id = repo.name.lower().replace(' ', '-')
    payload = {
        'manifestVersion': 1,
        'platformVersion': '1.0',
        'compat': 'autark-outbound',
        'generatedBy': {'tool': 'fy-platform bootstrap', 'generated_at': datetime.now(timezone.utc).isoformat()},
        'project': {'id': project_id, 'name': repo.name, 'repository_type': 'python-project'},
        'roots': roots,
        'docsStrategy': {
            'tracks': ['easy', 'technical', 'role-admin', 'role-developer', 'role-operator', 'role-writer', 'ai-read', 'status'],
            'status_pages': True,
            'outbound_only': True,
        },
        'suites': {},
    }
    source_roots = roots['source'] or ['src']
    payload['suites']['contractify'] = {'roots': roots['docs'] + source_roots, 'openapi': 'docs/api/openapi.yaml'}
    payload['suites']['testify'] = {'roots': roots['tests'] or ['tests'], 'ci_workflows': ['.github/workflows']}
    payload['suites']['documentify'] = {'roots': roots['docs'] + source_roots, 'tracks': payload['docsStrategy']['tracks']}
    payload['suites']['docify'] = {'roots': source_roots}
    payload['suites']['despaghettify'] = {'scan_roots': source_roots, 'spike_policy': 'local-and-global'}
    payload['suites']['templatify'] = {'template_roots': roots['templates'] or ['templates']}
    payload['suites']['usabilify'] = {'ui_roots': roots['templates'] or roots['docs']}
    payload['suites']['observifyfy'] = {'internal_roots': ['docs', 'docs/ADR'], 'role': 'internal-fy-observability'}
    payload['suites']['metrify'] = {'ledger_root': 'metrify/state', 'role': 'ai-usage-observer'}
    payload['suites']['dockerify'] = {'enabled': True, 'compose_roots': ['docker-compose.yml', 'compose.yml']}
    payload['suites']['postmanify'] = {'enabled': True, 'openapi': 'docs/api/openapi.yaml'}
    return payload


def resolve_repo(project_root: str) -> Path:
    """Resolve repo.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        project_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    if project_root:
        return Path(project_root).expanduser().resolve()
    return resolve_project_root(start=Path(__file__), env_var='FY_PLATFORM_PROJECT_ROOT', marker_text=None)


def cmd_bootstrap(args: argparse.Namespace) -> int:
    """Cmd bootstrap.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    path = manifest_path(repo)
    if path.is_file() and not args.force:
        print(json.dumps({'ok': False, 'reason': 'manifest_exists', 'path': str(path.relative_to(repo))}, indent=2))
        return 2
    payload = build_manifest_payload(repo)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding='utf-8')
    print(json.dumps({'ok': True, 'manifest': str(path.relative_to(repo)), 'suite_count': len(payload['suites'])}, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Cmd validate.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    manifest, warnings = load_manifest(repo)
    if manifest is None:
        print(json.dumps({'ok': False, 'warnings': warnings or ['manifest_missing']}, indent=2))
        return 2
    suite_names = sorted((manifest.get('suites') or {}).keys()) if isinstance(manifest, dict) else []
    payload = {'ok': not warnings, 'manifest': 'fy-manifest.yaml', 'warnings': warnings, 'suite_count': len(suite_names), 'suites': suite_names}
    print(json.dumps(payload, indent=2))
    return 0 if not warnings else 2


def cmd_workspace_status(args: argparse.Namespace) -> int:
    """Cmd workspace status.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = build_workspace_status_site(repo)
    payload.update(write_workspace_status_site(repo, payload))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_release_readiness(args: argparse.Namespace) -> int:
    """Cmd release readiness.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = workspace_release_readiness(repo)
    payload.update(write_workspace_release_site(repo, payload))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload['ok'] else 3


def cmd_production_readiness(args: argparse.Namespace) -> int:
    """Cmd production readiness.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = workspace_production_readiness(repo)
    payload.update(write_workspace_production_site(repo, payload))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload['ok'] else 4


def cmd_create_backup(args: argparse.Namespace) -> int:
    """Cmd create backup.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = create_workspace_backup(repo, reason=args.reason or 'manual')
    print(json.dumps({'ok': True, **payload}, indent=2, ensure_ascii=False))
    return 0


def cmd_rollback_backup(args: argparse.Namespace) -> int:
    """Cmd rollback backup.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    payload = rollback_workspace_backup(repo, backup_id=args.backup_id or None)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get('ok') else 2


def cmd_observability_status(args: argparse.Namespace) -> int:
    """Cmd observability status.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = resolve_repo(args.project_root)
    print(json.dumps(ObservabilityStore(repo).summarize(), indent=2, ensure_ascii=False))
    return 0
