"""Tests for governance.

"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import yaml

from testify.tools.repo_paths import FY_SUITES_DIRNAME

REQUIRED_WORKFLOWS = (
    'backend-tests.yml',
    'admin-tests.yml',
    'engine-tests.yml',
    'ai-stack-tests.yml',
    'quality-gate.yml',
    'pre-deployment.yml',
    'compose-smoke.yml',
)
REQUIRED_HUB_SCRIPTS = (
    'despag-check',
    'wos-despag',
    'postmanify',
    'docify',
    'contractify',
    'fy-platform',
    'dockerify',
    'testify',
    'documentify',
)
REQUIRED_ANALYZE_MODES = ('analyze.contract', 'analyze.quality', 'analyze.code_docs', 'analyze.docs')
REQUIRED_CANONICAL_SCHEMA_FILES = (
    'fy_unit.schema.json',
    'relation.schema.json',
    'artifact.schema.json',
    'run_manifest.schema.json',
    'suite_ownership.schema.json',
)


def _first_existing_path(root: Path, *rel_parts: str) -> Path | None:
    """Return the first existing file or directory under ``root`` or ``root / fy-suites``."""
    rel = Path(*rel_parts)
    for base in (root, root / FY_SUITES_DIRNAME):
        candidate = base / rel
        if candidate.is_file() or candidate.is_dir():
            return candidate
    return None


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


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load yaml.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    # Branch on not path.is_file() so _load_yaml only continues along the matching state
    # path.
    if not path.is_file():
        return {}
    # Read and normalize the input data before _load_yaml branches on or transforms it
    # further.
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    return data if isinstance(data, dict) else {}


def _module_ast(path: Path) -> ast.Module | None:
    """Module ast.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        ast.Module | None:
            Value produced by this callable as ``ast.Module
            | None``.
    """
    source = _read(path)
    if not source:
        return None
    return ast.parse(source)


def _find_named_value(module: ast.Module | None, variable_name: str) -> ast.AST | None:
    """Find named value.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        module: Primary module used by this step.
        variable_name: Primary variable name used by this step.

    Returns:
        ast.AST | None:
            Value produced by this callable as ``ast.AST |
            None``.
    """
    if module is None:
        return None
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    return node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == variable_name:
            return node.value
    return None


def _literal_from_module(path: Path, variable_name: str) -> Any:
    """Literal from module.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        path: Filesystem path to the file or directory being processed.
        variable_name: Primary variable name used by this step.

    Returns:
        Any:
            Value produced by this callable as ``Any``.
    """
    module = _module_ast(path)
    value_node = _find_named_value(module, variable_name)
    if value_node is None:
        return None
    try:
        return ast.literal_eval(value_node)
    except Exception:
        return None


def _dict_keys_from_module(path: Path, variable_name: str) -> list[str]:
    """Dict keys from module.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        path: Filesystem path to the file or directory being processed.
        variable_name: Primary variable name used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    module = _module_ast(path)
    value_node = _find_named_value(module, variable_name)
    if not isinstance(value_node, ast.Dict):
        return []
    keys: list[str] = []
    for key_node in value_node.keys:
        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
            keys.append(key_node.value)
    return keys


def _workflow_on_payload(data: dict[str, Any]) -> Any:
    """Workflow on payload.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        data: Primary data used by this step.

    Returns:
        Any:
            Value produced by this callable as ``Any``.
    """
    if 'on' in data:
        return data['on']
    if True in data:
        return data[True]
    return {}


def audit_test_governance(root: Path) -> dict[str, Any]:
    """Audit test governance.

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
    pyproject_text = _read(root / 'pyproject.toml')
    run_tests_path = root / 'tests/run_tests.py'
    workflows_dir = root / '.github/workflows'
    workflow_files = sorted(p.name for p in workflows_dir.glob('*.yml')) if workflows_dir.is_dir() else []
    scripts: dict[str, str] = {}
    in_scripts = False
    for line in pyproject_text.splitlines():
        if line.strip() == '[project.scripts]':
            in_scripts = True
            continue
        if in_scripts and line.startswith('['):
            break
        if in_scripts and '=' in line:
            key, _, value = line.partition('=')
            scripts[key.strip()] = value.strip().strip('"')
    suite_targets = _dict_keys_from_module(run_tests_path, 'SUITE_PYTEST_TARGETS')
    all_sequence = list(_literal_from_module(run_tests_path, 'ALL_SUITE_SEQUENCE') or [])
    display_names = _literal_from_module(run_tests_path, 'SUITE_DISPLAY_NAMES') or {}
    workflow_summary = {}
    for wf in workflow_files:
        data = _load_yaml(workflows_dir / wf)
        jobs = data.get('jobs') if isinstance(data.get('jobs'), dict) else {}
        on_payload = json.dumps(_workflow_on_payload(data))
        workflow_summary[wf] = {
            'job_count': len(jobs),
            'has_path_filters': 'paths' in on_payload,
            'workflow_dispatch': 'workflow_dispatch' in on_payload,
        }

    mode_registry_path = _first_existing_path(root, 'fy_platform', 'runtime', 'mode_registry.py')
    mode_keys = _dict_keys_from_module(mode_registry_path, 'MODE_SPECS') if mode_registry_path else []
    public_modes = {
        'mode_keys': sorted(mode_keys),
        'required_analyze_modes': list(REQUIRED_ANALYZE_MODES),
        'missing_analyze_modes': [name for name in REQUIRED_ANALYZE_MODES if name not in mode_keys],
        'surface_paths': [
            p
            for p in ('fy_platform/runtime/mode_registry.py', 'fy_platform/tools/cli_parser.py', 'pyproject.toml')
            if _first_existing_path(root, *p.split('/')) is not None
        ],
    }

    source_schema_dir = _first_existing_path(root, 'fy_platform', 'contracts', 'evolution_wave1', 'schemas')
    if source_schema_dir is None:
        source_schema_dir = root / 'fy_platform' / 'contracts' / 'evolution_wave1' / 'schemas'
    export_schema_dir = _first_existing_path(root, 'docs', 'platform', 'schemas')
    if export_schema_dir is None:
        export_schema_dir = root / 'docs' / 'platform' / 'schemas'
    source_schema_files = sorted(p.name for p in source_schema_dir.glob('*.json')) if source_schema_dir.is_dir() else []
    export_schema_files = sorted(p.name for p in export_schema_dir.glob('*.json')) if export_schema_dir.is_dir() else []
    schema_export = {
        'source_schema_files': source_schema_files,
        'export_schema_files': export_schema_files,
        'canonical_source_complete': all(name in source_schema_files for name in REQUIRED_CANONICAL_SCHEMA_FILES),
        'canonical_export_complete': all(name in export_schema_files for name in REQUIRED_CANONICAL_SCHEMA_FILES),
        'source_count': len(source_schema_files),
        'export_count': len(export_schema_files),
        'surface_paths': [
            p
            for p in (
                'fy_platform/ai/final_product_schemas.py',
                'fy_platform/contracts/evolution_wave1/schemas/fy_unit.schema.json',
                'docs/platform/schemas/fy_unit.schema.json',
            )
            if _first_existing_path(root, *p.split('/')) is not None
        ],
    }

    findings = []
    missing_workflows = [wf for wf in REQUIRED_WORKFLOWS if wf not in workflow_files]
    if missing_workflows:
        findings.append({'id': 'TESTIFY-MISSING-WORKFLOWS', 'severity': 'high', 'summary': f"Missing workflows: {', '.join(missing_workflows)}"})
    missing_scripts = [name for name in REQUIRED_HUB_SCRIPTS if name not in scripts]
    if missing_scripts:
        findings.append({'id': 'TESTIFY-MISSING-HUB-SCRIPTS', 'severity': 'high', 'summary': f"Missing root pyproject suite scripts: {', '.join(missing_scripts)}"})
    if 'backend' not in suite_targets or 'ai_stack' not in suite_targets:
        findings.append({'id': 'TESTIFY-RUNNER-DRIFT', 'severity': 'medium', 'summary': 'tests/run_tests.py no longer exposes the expected multi-suite targets.'})
    if public_modes['missing_analyze_modes']:
        findings.append({'id': 'TESTIFY-MISSING-PUBLIC-MODES', 'severity': 'medium', 'summary': f"Missing required analyze modes: {', '.join(public_modes['missing_analyze_modes'])}"})
    if source_schema_files and not schema_export['canonical_export_complete']:
        findings.append({'id': 'TESTIFY-SCHEMA-EXPORT-INCOMPLETE', 'severity': 'medium', 'summary': 'Canonical schema source files exist but the exported docs/platform/schemas surface is incomplete.'})

    warnings = []
    if 'frontend-tests.yml' not in workflow_files:
        warnings.append('No standalone frontend-tests.yml workflow detected; frontend quality currently relies on broader gates or local runner usage.')
    strengths = []
    if not missing_workflows:
        strengths.append('Core GitHub Actions workflow set is present for backend, admin, engine, AI stack, quality gate, pre-deployment, and compose smoke.')
    if not missing_scripts:
        strengths.append('Root pyproject exports all fy-suite console scripts, including dockerify, testify, and documentify.')
    if all_sequence:
        strengths.append(f"tests/run_tests.py declares canonical --suite all order: {', '.join(all_sequence)}.")
    if suite_targets:
        strengths.append(f"tests/run_tests.py declares explicit suite targets for: {', '.join(sorted(suite_targets))}.")
    if not public_modes['missing_analyze_modes'] and public_modes['mode_keys']:
        strengths.append('Mode registry exposes the required public analyze modes for contract, quality, code_docs, and docs.')
    if schema_export['canonical_source_complete'] and schema_export['canonical_export_complete']:
        strengths.append('Canonical schema source files and exported schema bundle are both complete for the current evolution slice.')

    component_pyprojects = []
    for rel in ('backend/pyproject.toml', 'frontend/pyproject.toml', 'administration-tool/pyproject.toml', 'world-engine/pyproject.toml', 'ai_stack/pyproject.toml', 'story_runtime_core/pyproject.toml'):
        p = root / rel
        component_pyprojects.append({'path': rel, 'exists': p.is_file()})
    return {
        'suite': 'testify',
        'summary': {
            'workflow_count': len(workflow_files),
            'runner_suite_count': len(suite_targets),
            'hub_script_count': len(scripts),
            'finding_count': len(findings),
            'warning_count': len(warnings),
            'analyze_mode_count': len(public_modes['mode_keys']),
            'canonical_schema_export_count': schema_export['export_count'],
        },
        'runner': {'suite_targets': sorted(suite_targets), 'all_sequence': all_sequence, 'display_names': display_names},
        'hub_pyproject': {'scripts': scripts, 'packages_where_clause_present': "where = [\"'fy'-suites\"]" in pyproject_text},
        'public_modes': public_modes,
        'schema_export': schema_export,
        'workflows': workflow_summary,
        'component_pyprojects': component_pyprojects,
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
    lines = ['# Testify audit report', '', '## Summary', '']
    for key, value in payload.get('summary', {}).items():
        lines.append(f'- **{key}**: `{value}`')
    lines.extend(['', '## Runner coverage', ''])
    lines.append(f"- `tests/run_tests.py` suites: `{payload.get('runner', {}).get('suite_targets', [])}`")
    lines.append(f"- `--suite all` order: `{payload.get('runner', {}).get('all_sequence', [])}`")
    lines.extend(['', '## Workflow coverage', ''])
    for name, data in sorted(payload.get('workflows', {}).items()):
        lines.append(f"- **{name}** — jobs: `{data.get('job_count')}`, path filters: `{data.get('has_path_filters')}`, workflow_dispatch: `{data.get('workflow_dispatch')}`")
    lines.extend(['', '## Public modes', ''])
    lines.append(f"- mode keys: `{payload.get('public_modes', {}).get('mode_keys', [])}`")
    lines.append(f"- missing analyze modes: `{payload.get('public_modes', {}).get('missing_analyze_modes', [])}`")
    lines.extend(['', '## Schema export', ''])
    schema = payload.get('schema_export', {})
    lines.append(f"- canonical source complete: `{schema.get('canonical_source_complete')}`")
    lines.append(f"- canonical export complete: `{schema.get('canonical_export_complete')}`")
    lines.append(f"- export count: `{schema.get('export_count')}`")
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
    payload = audit_test_governance(root)
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
