"""Docker audit for dockerify.tools.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED_SERVICES = ('backend', 'frontend', 'administration-tool', 'play-service')
REQUIRED_DOCKER_COMMANDS = ('init-env', 'ensure-env', 'up', 'build', 'restart', 'stop', 'down', 'reset')
STARTUP_SMOKE_TESTS = (
    'tests/smoke/test_backend_startup.py',
    'tests/smoke/test_admin_startup.py',
    'tests/smoke/test_engine_startup.py',
)
DATABASE_EVIDENCE = (
    'backend/docker-entrypoint.sh',
    'backend/migrations',
    'database/tests/test_database_migrations_and_files.py',
    'database/tests/test_database_upgrades.py',
)


def _read(path: Path) -> str:
    """Read the requested operation.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return path.read_text(encoding='utf-8', errors='replace') if path.is_file() else ''


def _path_status(root: Path, rel: str) -> dict[str, Any]:
    """Path status.

    Args:
        root: Root directory used to resolve repository-local paths.
        rel: Primary rel used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    p = root / rel
    kind = 'file' if p.is_file() else 'dir' if p.is_dir() else 'missing'
    return {'path': rel, 'exists': p.exists(), 'kind': kind}


def _parse_compose(path: Path) -> dict[str, Any]:
    """Parse compose.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    if not path.is_file():
        return {'services': {}, 'service_names': [], 'parse_error': 'missing'}
    try:
        raw = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except yaml.YAMLError as exc:
        return {'services': {}, 'service_names': [], 'parse_error': str(exc)}
    services = raw.get('services') if isinstance(raw, dict) else {}
    if not isinstance(services, dict):
        services = {}
    projected: dict[str, Any] = {}
    for name, cfg in services.items():
        cfg = cfg if isinstance(cfg, dict) else {}
        depends = cfg.get('depends_on')
        if isinstance(depends, dict):
            depends_on = sorted(depends.keys())
            dependency_conditions = {k: (v.get('condition') if isinstance(v, dict) else None) for k, v in depends.items()}
        elif isinstance(depends, list):
            depends_on = [str(v) for v in depends]
            dependency_conditions = {}
        else:
            depends_on = []
            dependency_conditions = {}
        projected[name] = {
            'ports': list(cfg.get('ports', [])) if isinstance(cfg.get('ports'), list) else [],
            'has_build': isinstance(cfg.get('build'), (dict, str)),
            'has_env_file': 'env_file' in cfg,
            'has_healthcheck': isinstance(cfg.get('healthcheck'), dict),
            'depends_on': depends_on,
            'dependency_conditions': dependency_conditions,
        }
    return {'services': projected, 'service_names': sorted(projected.keys()), 'parse_error': None}


def _collect_findings(root: Path, compose: dict[str, Any], docker_up_text: str) -> list[dict[str, Any]]:
    """Collect findings.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        compose: Primary compose used by this step.
        docker_up_text: Primary docker up text used by this step.

    Returns:
        list[dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    findings: list[dict[str, Any]] = []
    services = compose.get('service_names', [])
    missing_services = [svc for svc in REQUIRED_SERVICES if svc not in services]
    if missing_services:
        findings.append({
            'id': 'DOCKERIFY-MISSING-SERVICES',
            'severity': 'high',
            'summary': f"Missing compose services: {', '.join(missing_services)}",
        })
    if not all(cmd in docker_up_text for cmd in REQUIRED_DOCKER_COMMANDS):
        findings.append({
            'id': 'DOCKERIFY-COMMAND-DRIFT',
            'severity': 'medium',
            'summary': 'docker-up.py no longer exposes the full canonical lifecycle command set.',
        })
    play = compose.get('services', {}).get('play-service', {})
    if not play.get('has_healthcheck'):
        findings.append({
            'id': 'DOCKERIFY-PLAY-HEALTHCHECK-MISSING',
            'severity': 'high',
            'summary': 'play-service healthcheck missing from compose; stable startup posture weakened.',
        })
    backend_dep = compose.get('services', {}).get('backend', {}).get('dependency_conditions', {}).get('play-service')
    if backend_dep != 'service_healthy':
        findings.append({
            'id': 'DOCKERIFY-BACKEND-DEPENDENCY-DRIFT',
            'severity': 'medium',
            'summary': 'backend no longer waits for play-service health in compose.',
        })
    for rel in STARTUP_SMOKE_TESTS:
        if not (root / rel).is_file():
            findings.append({
                'id': f'DOCKERIFY-MISSING-SMOKE::{rel}',
                'severity': 'medium',
                'summary': f'Missing startup smoke evidence: {rel}',
            })
    entrypoint = root / 'backend/docker-entrypoint.sh'
    if not entrypoint.is_file():
        findings.append({
            'id': 'DOCKERIFY-ENTRYPOINT-MISSING',
            'severity': 'high',
            'summary': 'backend/docker-entrypoint.sh missing; migration-on-start contract not evidenced.',
        })
    elif 'flask db upgrade' not in _read(entrypoint):
        findings.append({
            'id': 'DOCKERIFY-MIGRATION-COMMAND-MISSING',
            'severity': 'high',
            'summary': 'backend/docker-entrypoint.sh no longer runs `flask db upgrade`.',
        })
    return findings


def audit_docker_surface(root: Path) -> dict[str, Any]:
    """Audit docker surface.

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
    compose = _parse_compose(root / 'docker-compose.yml')
    docker_up_text = _read(root / 'docker-up.py')
    entrypoint_text = _read(root / 'backend/docker-entrypoint.sh')
    smoke_evidence = [_path_status(root, rel) for rel in STARTUP_SMOKE_TESTS]
    db_evidence = [_path_status(root, rel) for rel in DATABASE_EVIDENCE]
    required_files = [
        'docker-up.py',
        'docker-compose.yml',
        '.env.example',
        'backend/Dockerfile',
        'world-engine/Dockerfile',
        'frontend/Dockerfile',
        'administration-tool/Dockerfile',
    ]
    file_checks = [_path_status(root, rel) for rel in required_files]
    findings = _collect_findings(root, compose, docker_up_text)
    strengths: list[str] = []
    if not findings:
        strengths.append('No deterministic Docker governance gaps were detected in the audited surfaces.')
    if compose.get('services', {}).get('play-service', {}).get('has_healthcheck'):
        strengths.append('play-service healthcheck is explicitly declared in compose.')
    if compose.get('services', {}).get('backend', {}).get('dependency_conditions', {}).get('play-service') == 'service_healthy':
        strengths.append('backend waits for play-service health before startup.')
    if 'flask db upgrade' in entrypoint_text:
        strengths.append('backend Docker entrypoint upgrades the database schema on startup.')
    if all(item['exists'] for item in smoke_evidence):
        strengths.append('Repository contains startup smoke tests for backend, admin tool, and engine.')
    warnings = []
    for service_name in ('backend', 'frontend', 'administration-tool'):
        if not compose.get('services', {}).get(service_name, {}).get('has_healthcheck'):
            warnings.append(f'{service_name} has no compose healthcheck; startup confidence relies on smoke tests and dependent service readiness.')
    warnings = sorted(set(warnings))
    return {
        'suite': 'dockerify',
        'summary': {
            'required_service_count': len(REQUIRED_SERVICES),
            'present_service_count': len(compose.get('service_names', [])),
            'finding_count': len(findings),
            'warning_count': len(warnings),
            'migration_on_start': 'flask db upgrade' in entrypoint_text,
        },
        'compose': compose,
        'docker_up': {
            'path': 'docker-up.py',
            'commands_present': [cmd for cmd in REQUIRED_DOCKER_COMMANDS if cmd in docker_up_text],
            'mentions_env_bootstrap': 'init-env' in docker_up_text and '.env' in docker_up_text,
            'mentions_health_wait': 'health' in docker_up_text.lower(),
        },
        'file_checks': file_checks,
        'smoke_evidence': smoke_evidence,
        'database_evidence': db_evidence,
        'strengths': strengths,
        'warnings': warnings,
        'findings': findings,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    """Render markdown.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = ['# Dockerify audit report', '', '## Summary', '']
    summary = payload.get('summary', {})
    for key in ('required_service_count', 'present_service_count', 'finding_count', 'warning_count', 'migration_on_start'):
        lines.append(f'- **{key}**: `{summary.get(key)}`')
    lines.extend(['', '## Compose services', ''])
    for name in payload.get('compose', {}).get('service_names', []):
        svc = payload['compose']['services'][name]
        lines.append(f"- **{name}** — ports: `{svc.get('ports', [])}`, healthcheck: `{svc.get('has_healthcheck')}`, depends_on: `{svc.get('depends_on', [])}`")
    lines.extend(['', '## Strengths', ''])
    for item in payload.get('strengths', []):
        lines.append(f'- {item}')
    lines.extend(['', '## Warnings', ''])
    if payload.get('warnings'):
        for item in payload['warnings']:
            lines.append(f'- {item}')
    else:
        lines.append('- None.')
    lines.extend(['', '## Findings', ''])
    if payload.get('findings'):
        for item in payload['findings']:
            lines.append(f"- `{item['id']}` ({item['severity']}): {item['summary']}")
    else:
        lines.append('- None.')
    lines.extend(['', '## Database evidence', ''])
    for item in payload.get('database_evidence', []):
        lines.append(f"- `{item['path']}` — exists: `{item['exists']}`")
    return "\n".join(lines) + "\n"


def write_audit_bundle(root: Path, json_rel: str, md_rel: str) -> dict[str, Any]:
    """Write audit bundle.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.
        json_rel: Primary json rel used by this step.
        md_rel: Primary md rel used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    payload = audit_docker_surface(root)
    json_path = root / json_rel
    md_path = root / md_rel
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    json_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    md_path.write_text(render_markdown(payload), encoding='utf-8')
    return payload
