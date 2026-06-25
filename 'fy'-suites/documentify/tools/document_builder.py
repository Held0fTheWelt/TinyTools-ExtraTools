"""Document builder for documentify.tools.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SERVICE_DIRS = ('frontend', 'administration-tool', 'backend', 'world-engine', 'ai_stack', 'story_runtime_core', 'writers-room')
ROLE_MAP = {
    'admin': {
        'summary': 'Operate the administration interface and content governance surfaces.',
        'paths': ('administration-tool/', 'backend/app/api/v1/', 'docs/admin/', 'docs/governance/'),
    },
    'developer': {
        'summary': 'Implement and debug the repository across backend, engine, frontend, and AI stack surfaces.',
        'paths': ('backend/', 'world-engine/', 'frontend/', 'ai_stack/', 'story_runtime_core/', 'tests/'),
    },
    'operator': {
        'summary': 'Start, monitor, and troubleshoot the local stack and runtime-facing services.',
        'paths': ('docker-up.py', 'docker-compose.yml', 'docs/operations/', 'docs/testing/', '.github/workflows/'),
    },
    'writer': {
        'summary': 'Work with narrative content, Writers-Room flow, and module governance.',
        'paths': ('writers-room/', 'content/modules/', 'docs/MVPs/', 'docs/start-here/', 'backend/app/api/v1/writers_room_routes.py'),
    },
    'player': {
        'summary': 'Understand the player-facing experience and where the live runtime begins.',
        'paths': ('frontend/', 'docs/user/', 'docs/start-here/', 'world-engine/'),
    },
}


def _existing(paths: list[str], root: Path) -> list[str]:
    """Existing the requested operation.

    Args:
        paths: Primary paths used by this step.
        root: Root directory used to resolve repository-local paths.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    return [p for p in paths if (root / p).exists()]


def collect_repository_context(root: Path) -> dict[str, Any]:
    """Collect repository context.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    # Build filesystem locations and shared state that the rest of
    # collect_repository_context reuses.
    docs_root = root / 'docs'
    docs_dirs = sorted(p.name for p in docs_root.iterdir() if p.is_dir()) if docs_root.is_dir() else []
    services = [name for name in SERVICE_DIRS if (root / name).exists()]
    workflows = sorted(p.name for p in (root / '.github/workflows').glob('*.yml')) if (root / '.github/workflows').is_dir() else []
    key_docs = [
        'README.md',
        'docs/start-here/README.md',
        'docs/technical/README.md',
        'docs/testing/README.md',
        'docs/operations/RUNBOOK.md',
        'tests/TESTING.md',
        'docker-up.py',
        'tests/run_tests.py',
    ]
    return {
        'services': services,
        'docs_dirs': docs_dirs,
        'workflows': workflows,
        'key_docs': _existing(key_docs, root),
    }


def _simple_overview(context: dict[str, Any]) -> str:
    """Simple overview.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        context: Primary context used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    services = ', '.join(context['services']) if context['services'] else 'no primary service roots detected yet'
    graph_nodes = []
    for service in context['services']:
        node = service.replace('-', '_').replace(' ', '_')
        graph_nodes.append(f'    core --> {node}["{service}"]')
    if not graph_nodes:
        graph_nodes.append('    core --> pending["repository surfaces"]')

    lines = [
        '# fy-suites — What, Why, and How',
        '',
        '## What is it?',
        '',
        'The **fy-suites** are a family of internal tools that work together inside one shared workspace.',
        '',
        'They are not one single tool. They are a **tool system**.',
        '',
        'Each suite has its own responsibility, but all suites share the same platform foundations.',
        '',
        f'The repository currently exposes these major service or package areas: **{services}**.',
        '',
        '```mermaid',
        'flowchart TD',
        '    core["fy-suites"]',
        *graph_nodes,
        '```',
        '',
        '## Why does it exist?',
        '',
        'The fy-suites exist because complex work becomes hard to manage when everything is mixed together.',
        '',
        'Without a system like this, useful information spreads across many places, documentation drifts, tests lose context, and support tools start contaminating the real target work.',
        '',
        'The fy-suites solve this by creating one internal system with clear lanes, shared rules, and readable outputs.',
        '',
        'They exist to make work:',
        '',
        '- more organized',
        '- more explainable',
        '- more governable',
        '- more reusable',
        '- safer to review',
        '- easier to continue later',
        '',
        '## How does it work?',
        '',
        'At a simple level, the fy-suites work like this:',
        '',
        '1. there is one shared platform',
        '2. each suite has its own job',
        '3. the suites share a common lifecycle',
        '4. work stays internal before it becomes outward',
        '5. results are tracked, explained, and turned into next steps',
        '',
        '### Shared platform',
        '',
        'The shared platform provides workspace handling, evidence tracking, run tracking, context building, model routing, status pages, release readiness, and production readiness.',
        '',
        '### Common lifecycle',
        '',
        'Most suites follow common actions such as initialize, inspect, audit, explain, prepare context, compare runs, prepare fixes, self-audit, and readiness checks.',
        '',
        '### Start reading here',
        '',
    ]
    lines.extend(f'- `{item}`' for item in context['key_docs'])
    lines.extend([
        '',
        '## Quick recap',
        '',
        '### What?',
        'A modular family of internal suites for governed support work.',
        '',
        '### Why?',
        'To reduce chaos, improve clarity, keep work explainable, and avoid uncontrolled changes.',
        '',
        '### How?',
        'Through a shared platform, specialized suites, a common lifecycle, internal tracking, and controlled outward action.',
    ])
    return '\n'.join(lines) + '\n'


def _technical_reference(context: dict[str, Any]) -> str:
    """Technical reference.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        context: Primary context used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    services = context['services'] or ['(none detected)']
    lines = [
        '# World of Shadows — technical reference',
        '',
        '## Repository service map',
        '',
        '```mermaid',
        'flowchart LR',
        '    repo["repository"]',
    ]
    for svc in services:
        node = svc.replace('-', '_').replace(' ', '_').replace('(', '').replace(')', '')
        lines.append(f'    repo --> {node}["{svc}"]')
    lines.extend([
        '```',
        '',
        '## Documentation domains',
        '',
        ', '.join(context['docs_dirs']) if context['docs_dirs'] else '(none detected)',
        '',
        '## Automation and gates',
        '',
        ', '.join(context['workflows']) if context['workflows'] else '(no workflows detected)',
        '',
        '## Canonical operational entrypoints',
        '',
        '- `docker-up.py` — local Docker lifecycle',
        '- `docker-compose.yml` — stack declaration',
        '- `tests/run_tests.py` — multi-suite test runner',
        '- `.github/workflows/` — GitHub Actions CI gates',
    ])
    return '\n'.join(lines) + '\n'


def _role_doc(role: str, root: Path) -> str:
    """Role doc.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        role: Primary role used by this step.
        root: Root directory used to resolve repository-local paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    info = ROLE_MAP[role]
    existing_paths = _existing(list(info['paths']), root)
    lines = [
        f'# {role.capitalize()} documentation',
        '',
        info['summary'],
        '',
        '## What this role needs',
        '',
        f'This role mainly needs the parts of the repository that best support **{role}** work without forcing a full-system deep dive.',
        '',
        '## Recommended reading order',
        '',
    ]
    if existing_paths:
        lines.extend(f'- `{p}`' for p in existing_paths)
    else:
        lines.append('- no matching paths detected in the current repository snapshot')
    lines.extend([
        '',
        '## How to use this role doc',
        '',
        'Start with the first relevant path, use the simple overview to orient yourself, then move into technical or suite-specific material only when you need more detail.',
    ])
    return '\n'.join(lines) + '\n'


def generate_documentation(root: Path, out_dir: Path) -> dict[str, Any]:
    """Generate documentation.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        root: Root directory used to resolve repository-local paths.
        out_dir: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    context = collect_repository_context(root)
    generated: list[str] = []
    simple = out_dir / 'simple' / 'PLATFORM_OVERVIEW.md'
    technical = out_dir / 'technical' / 'SYSTEM_REFERENCE.md'
    simple.parent.mkdir(parents=True, exist_ok=True)
    technical.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    simple.write_text(_simple_overview(context), encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    technical.write_text(_technical_reference(context), encoding='utf-8')
    generated.extend([simple.relative_to(root).as_posix(), technical.relative_to(root).as_posix()])
    roles_root = out_dir / 'roles'
    for role in ROLE_MAP:
        role_path = roles_root / role / 'README.md'
        role_path.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        role_path.write_text(_role_doc(role, root), encoding='utf-8')
        generated.append(role_path.relative_to(root).as_posix())
    return {
        'suite': 'documentify',
        'generated_count': len(generated),
        'services': context['services'],
        'docs_dirs': context['docs_dirs'],
        'workflows': context['workflows'],
        'generated_files': generated,
        'simple_style': 'what-why-how',
        'uses_mermaid': True,
    }


def render_markdown(summary: dict[str, Any], out_dir: Path, root: Path) -> str:
    """Render markdown.

    Args:
        summary: Structured data carried through this workflow.
        out_dir: Root directory used to resolve repository-local paths.
        root: Root directory used to resolve repository-local paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = ['# Documentify generation report', '', '## Summary', '']
    lines.append(f"- **generated_count**: `{summary['generated_count']}`")
    lines.append(f"- **output_root**: `{out_dir.relative_to(root).as_posix()}`")
    lines.append(f"- **simple_style**: `{summary.get('simple_style', 'default')}`")
    lines.append(f"- **uses_mermaid**: `{str(summary.get('uses_mermaid', False)).lower()}`")
    lines.extend(['', '## Services', ''])
    lines.extend(f'- `{svc}`' for svc in summary.get('services', []))
    lines.extend(['', '## Generated files', ''])
    lines.extend(f'- `{path}`' for path in summary.get('generated_files', []))
    return '\n'.join(lines) + '\n'


def write_generation_bundle(root: Path, out_dir_rel: str, json_rel: str, md_rel: str) -> dict[str, Any]:
    """Write generation bundle.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.
        out_dir_rel: Primary out dir rel used by this step.
        json_rel: Primary json rel used by this step.
        md_rel: Primary md rel used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    out_dir = root / out_dir_rel
    summary = generate_documentation(root, out_dir)
    json_path = root / json_rel
    md_path = root / md_rel
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    json_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    md_path.write_text(render_markdown(summary, out_dir, root), encoding='utf-8')
    return summary
