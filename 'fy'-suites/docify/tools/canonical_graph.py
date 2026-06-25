"""Canonical graph for docify.tools.

"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import target_repo_id, utc_now, workspace_root
from fy_platform.evolution.graph_store import (
    CanonicalGraphStore,
    infer_owner_suite_for_path,
    stable_artifact_id,
    stable_relation_id,
    stable_unit_id,
)

DOCIFY_PUBLIC_COMMANDS = [
    ('docify', 'workflow', 'docify/hub_cli'),
    ('docify', 'cli-command', 'docify audit'),
    ('docify', 'cli-command', 'docify drift'),
    ('docify', 'cli-command', 'docify inline-explain'),
    ('docify', 'cli-command', 'docify open-doc'),
]
COMMAND_EXAMPLE_RE = re.compile(r'^\s*(docify\s+[A-Za-z0-9_-]+.*)$')


def _doc_summary(text: str, *, fallback: str) -> str:
    """Doc summary.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        text: Text content to inspect or rewrite.
        fallback: Primary fallback used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = (text or '').strip().splitlines()
    # Branch on not lines so _doc_summary only continues along the matching state path.
    if not lines:
        return fallback
    first = lines[0].strip()
    return first[:240] if first else fallback


def _public_name(name: str) -> bool:
    """Public name.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        name: Primary name used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    if name.startswith('__') and name.endswith('__'):
        return True
    return not name.startswith('_')


def _readme_examples(repo_root: Path) -> list[str]:
    """Readme examples.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    readme = repo_root / 'docify' / 'README.md'
    if not readme.is_file():
        return []
    found: list[str] = []
    for line in readme.read_text(encoding='utf-8', errors='replace').splitlines():
        match = COMMAND_EXAMPLE_RE.match(line)
        if match:
            cmd = match.group(1).strip()
            if cmd not in found:
                found.append(cmd)
    return found


def build_docify_graph(repo_root: Path) -> dict[str, Any]:
    """Build docify graph.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(repo_root)
    units: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    now = utc_now()
    owned_python_files = 0
    python_units_by_module: dict[str, list[str]] = {}
    module_units: list[str] = []
    function_units: list[str] = []
    class_units: list[str] = []
    import_counts: dict[str, int] = {}

    for path in sorted(repo_root.rglob('*.py')):
        parts = set(path.parts)
        if '__pycache__' in parts or '.venv' in parts or '.git' in parts:
            continue
        owner_suite = infer_owner_suite_for_path(path, workspace=workspace)
        if not owner_suite:
            continue
        owned_python_files += 1
        rel = path.resolve().relative_to(workspace.resolve()).as_posix()
        python_units_by_module.setdefault(rel, [])
        parse_note = ''
        try:
            module = ast.parse(path.read_text(encoding='utf-8', errors='replace'))
            syntax_ok = True
        except SyntaxError as exc:
            module = ast.Module(body=[], type_ignores=[])
            syntax_ok = False
            parse_note = f'syntax-error:{exc.lineno or 1}'
        module_id = stable_unit_id(owner_suite, 'module', rel)
        module_unit = {
            'unit_id': module_id,
            'title': path.name,
            'entity_type': 'module',
            'owner_suite': owner_suite,
            'source_paths': [rel],
            'summary': _doc_summary(ast.get_docstring(module) or '', fallback=f'Python module at {rel}.'),
            'why_it_exists': f'Module owned by {owner_suite} and scanned by docify for code-near documentation quality.',
            'contracts': [],
            'dependencies': [],
            'consumers': [],
            'commands': [],
            'inputs': [],
            'outputs': [],
            'failure_modes': ([] if syntax_ok else [parse_note]),
            'evidence_refs': [f'source:{rel}'],
            'roles': ['developer'],
            'layer_status': {'technical': 'observed', 'ai': 'available-for-projection'},
            'maturity': 'evidence-fill',
            'last_verified': now,
            'stability': 'observed',
            'tags': ['python', owner_suite],
        }
        units.append(module_unit)
        module_units.append(module_id)

        imports: list[str] = []
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names if alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        if imports:
            module_unit['dependencies'] = sorted(set(imports))[:40]
            import_counts[rel] = len(module_unit['dependencies'])

        for node in module.body:
            if isinstance(node, ast.ClassDef) and _public_name(node.name):
                class_id = stable_unit_id(owner_suite, 'class', f'{rel}::{node.name}')
                units.append({
                    'unit_id': class_id,
                    'title': node.name,
                    'entity_type': 'class',
                    'owner_suite': owner_suite,
                    'source_paths': [rel],
                    'summary': _doc_summary(ast.get_docstring(node) or '', fallback=f'Public class {node.name} in {rel}.'),
                    'why_it_exists': 'Public class captured for code-near documentation and API inventory.',
                    'contracts': [], 'dependencies': [], 'consumers': [], 'commands': [], 'inputs': [], 'outputs': [], 'failure_modes': [],
                    'evidence_refs': [f'source:{rel}'], 'roles': ['developer'], 'layer_status': {'technical': 'observed'},
                    'maturity': 'evidence-fill', 'last_verified': now, 'stability': 'observed', 'tags': ['python-class', owner_suite],
                })
                class_units.append(class_id)
                python_units_by_module[rel].append(class_id)
                relations.append({'relation_id': stable_relation_id('docify', module_id, 'contains', class_id), 'from_id': module_id, 'to_id': class_id, 'relation_type': 'contains', 'owner_suite': 'docify', 'evidence_refs': [f'source:{rel}'], 'confidence': 'high', 'created_at': now, 'last_verified': now})
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _public_name(node.name):
                fn_id = stable_unit_id(owner_suite, 'function', f'{rel}::{node.name}')
                units.append({
                    'unit_id': fn_id,
                    'title': node.name,
                    'entity_type': 'function',
                    'owner_suite': owner_suite,
                    'source_paths': [rel],
                    'summary': _doc_summary(ast.get_docstring(node) or '', fallback=f'Public function {node.name} in {rel}.'),
                    'why_it_exists': 'Public callable captured for code-near documentation and API inventory.',
                    'contracts': [], 'dependencies': [], 'consumers': [], 'commands': [], 'inputs': [a.arg for a in getattr(node.args, 'args', []) if a.arg != 'self'], 'outputs': [], 'failure_modes': [],
                    'evidence_refs': [f'source:{rel}'], 'roles': ['developer'], 'layer_status': {'technical': 'observed'},
                    'maturity': 'evidence-fill', 'last_verified': now, 'stability': 'observed', 'tags': ['python-function', owner_suite],
                })
                function_units.append(fn_id)
                python_units_by_module[rel].append(fn_id)
                relations.append({'relation_id': stable_relation_id('docify', module_id, 'contains', fn_id), 'from_id': module_id, 'to_id': fn_id, 'relation_type': 'contains', 'owner_suite': 'docify', 'evidence_refs': [f'source:{rel}'], 'confidence': 'high', 'created_at': now, 'last_verified': now})

    cli_units: list[str] = []
    for owner_suite, entity_type, norm_name in DOCIFY_PUBLIC_COMMANDS:
        unit_id = stable_unit_id(owner_suite, entity_type, norm_name)
        cli_units.append(unit_id)
        units.append({
            'unit_id': unit_id,
            'title': norm_name,
            'entity_type': entity_type,
            'owner_suite': owner_suite,
            'source_paths': ['docify/tools/hub_cli.py', 'docify/README.md'],
            'summary': f'Public Docify command surface: {norm_name}.',
            'why_it_exists': 'CLI capture for the pilot code-near documentation slice.',
            'contracts': [], 'dependencies': [], 'consumers': ['developer', 'operator'],
            'commands': [norm_name] if entity_type == 'cli-command' else ['docify'],
            'inputs': [], 'outputs': ['documentation guidance', 'audit output'], 'failure_modes': [],
            'evidence_refs': ['source:docify/tools/hub_cli.py', 'source:docify/README.md'], 'roles': ['developer', 'operator'],
            'layer_status': {'technical': 'observed', 'role': 'relevant'}, 'maturity': 'cross-linked' if entity_type == 'cli-command' else 'evidence-fill',
            'last_verified': now, 'stability': 'observed', 'tags': ['cli', 'docify'],
        })
    workflow_id = stable_unit_id('docify', 'workflow', 'docify-audit')
    units.append({
        'unit_id': workflow_id,
        'title': 'docify audit',
        'entity_type': 'workflow',
        'owner_suite': 'docify',
        'source_paths': ['docify/adapter/service.py', 'docify/tools/hub_cli.py'],
        'summary': 'Audit workflow that scans Python code for missing docstrings and code-near documentation gaps.',
        'why_it_exists': 'Primary code-near documentation audit entry flow.',
        'contracts': [], 'dependencies': ['docify.tools.canonical_graph'], 'consumers': ['developer'],
        'commands': ['docify audit', 'analyze --mode code_docs'], 'inputs': ['target_repo_root'],
        'outputs': ['coverage-report', 'drift-report', 'unit-index', 'relation-graph'],
        'failure_modes': ['governance_gate_failed', 'syntax-error-in-target-module'],
        'evidence_refs': ['source:docify/adapter/service.py', 'source:docify/tools/hub_cli.py'],
        'roles': ['developer'], 'layer_status': {'technical': 'observed'}, 'maturity': 'cross-linked',
        'last_verified': now, 'stability': 'observed', 'tags': ['workflow', 'docify'],
    })
    for cli_id in cli_units:
        relations.append({'relation_id': stable_relation_id('docify', workflow_id, 'contains', cli_id), 'from_id': workflow_id, 'to_id': cli_id, 'relation_type': 'contains', 'owner_suite': 'docify', 'evidence_refs': ['source:docify/tools/hub_cli.py'], 'confidence': 'high', 'created_at': now, 'last_verified': now})

    for item in _readme_examples(repo_root):
        unit_id = stable_unit_id('docify', 'documentation-unit', item)
        units.append({
            'unit_id': unit_id,
            'title': item,
            'entity_type': 'documentation-unit',
            'owner_suite': 'docify',
            'source_paths': ['docify/README.md'],
            'summary': f'Readme example command: {item}.',
            'why_it_exists': 'Example linkage for public Docify commands.',
            'contracts': [], 'dependencies': [], 'consumers': ['developer'], 'commands': [item],
            'inputs': [], 'outputs': [], 'failure_modes': [], 'evidence_refs': ['source:docify/README.md'],
            'roles': ['developer'], 'layer_status': {'technical': 'observed'}, 'maturity': 'cross-linked',
            'last_verified': now, 'stability': 'observed', 'tags': ['example', 'docify'],
        })
        parts = item.split()
        cli_target = parts[1] if len(parts) > 1 else ''
        for cli_id in cli_units:
            if cli_target and cli_id.endswith(cli_target.replace('-', '_')):
                relations.append({'relation_id': stable_relation_id('docify', unit_id, 'documents', cli_id), 'from_id': unit_id, 'to_id': cli_id, 'relation_type': 'documents', 'owner_suite': 'docify', 'evidence_refs': ['source:docify/README.md'], 'confidence': 'moderate', 'created_at': now, 'last_verified': now})

    coverage = {
        'owned_python_file_count': owned_python_files,
        'module_unit_count': len(module_units),
        'class_unit_count': len(class_units),
        'function_unit_count': len(function_units),
        'cli_command_count': sum(1 for item in units if item['entity_type'] == 'cli-command'),
        'workflow_count': sum(1 for item in units if item['entity_type'] == 'workflow'),
    }
    api_inventory = {
        'module_units': len(module_units),
        'class_units': len(class_units),
        'function_units': len(function_units),
        'public_functions_by_module': {k: len([u for u in v if ':function:' in u]) for k, v in python_units_by_module.items()},
        'import_density': import_counts,
    }
    drift_report = {'mode': 'heuristic', 'summary': 'Doc drift candidates are derived conservatively from missing code-near documentation findings.', 'candidate_unit_count': 0, 'candidate_units': []}
    cli_inventory = {'commands': _readme_examples(repo_root) or [item[2] for item in DOCIFY_PUBLIC_COMMANDS if item[1] == 'cli-command']}
    example_index = {'examples': _readme_examples(repo_root)}
    return {'generated_at': now, 'target_repo_id': target_repo_id(repo_root), 'units': units, 'relations': relations, 'coverage_report': coverage, 'api_inventory': api_inventory, 'drift_report': drift_report, 'cli_inventory': cli_inventory, 'example_index': example_index}


def persist_docify_graph(*, workspace: Path, repo_root: Path, run_id: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Persist docify graph.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        workspace: Primary workspace used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.
        run_id: Identifier used to select an existing run or record.
        findings: Primary findings used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    bundle = build_docify_graph(repo_root)
    now = utc_now()
    finding_units: list[str] = []
    for finding in findings:
        rel = finding.get('path', '')
        owner_suite = infer_owner_suite_for_path(workspace / rel, workspace=workspace) if rel else None
        if not owner_suite:
            continue
        if finding.get('kind') == 'module':
            unit_id = stable_unit_id(owner_suite, 'module', rel)
        elif finding.get('kind') == 'classdef':
            unit_id = stable_unit_id(owner_suite, 'class', f"{rel}::{finding.get('name', '')}")
        else:
            unit_id = stable_unit_id(owner_suite, 'function', f"{rel}::{finding.get('name', '')}")
        finding_units.append(unit_id)
    bundle['coverage_report']['missing_docstring_finding_count'] = len(findings)
    bundle['coverage_report']['finding_unit_refs'] = sorted(set(finding_units))
    bundle['drift_report']['candidate_unit_count'] = len(findings)
    bundle['drift_report']['candidate_units'] = sorted(set(finding_units))[:200]

    target_id = target_repo_id(repo_root)
    export_dir = workspace / 'docify' / 'generated' / target_id / run_id / 'evolution_graph'
    export_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    def add_artifact(name: str, artifact_type: str, payload: dict[str, Any], *, source_units: list[str] | None = None, evidence_mode: str = 'deterministic-scan') -> None:
        """Add artifact.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            name: Primary name used by this step.
            artifact_type: Primary artifact type used by this step.
            payload: Structured data carried through this workflow.
            source_units: Primary source units used by this step.
            evidence_mode: Primary evidence mode used by this step.
        """
        path = export_dir / name
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
        artifacts.append({
            'artifact_id': stable_artifact_id('docify', artifact_type, str(path.relative_to(workspace)), run_id),
            'artifact_type': artifact_type,
            'producer_suite': 'docify',
            'source_units': source_units or [],
            'source_artifacts': [],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': 'evidence-fill',
            'evidence_mode': evidence_mode,
            'tracked_or_generated': 'generated',
            'render_family': 'json',
            'path': str(path.relative_to(workspace)),
            'status': 'complete',
        })

    all_unit_ids = [item['unit_id'] for item in bundle['units']]
    add_artifact('coverage_report.json', 'coverage-report', bundle['coverage_report'], source_units=bundle['drift_report']['candidate_units'])
    add_artifact('api_inventory.json', 'api-inventory', bundle['api_inventory'], source_units=all_unit_ids)
    add_artifact('drift_report.json', 'drift-report', bundle['drift_report'], source_units=bundle['drift_report']['candidate_units'], evidence_mode='heuristic')
    add_artifact('cli_inventory.json', 'cli-inventory', bundle['cli_inventory'], source_units=[u['unit_id'] for u in bundle['units'] if u['entity_type'] == 'cli-command'], evidence_mode='tracked-plus-scan')
    add_artifact('example_index.json', 'example-index', bundle['example_index'], source_units=[u['unit_id'] for u in bundle['units'] if u['entity_type'] == 'documentation-unit'], evidence_mode='tracked-plus-scan')

    store = CanonicalGraphStore(workspace)
    graph_result = store.persist_bundle(
        suite='docify',
        run_id=run_id,
        command='analyze',
        mode='code_docs',
        lane='generate',
        target_repo_root=repo_root,
        units=bundle['units'],
        relations=bundle['relations'],
        artifacts=artifacts,
        validation_summary={'unit_count': len(bundle['units']), 'relation_count': len(bundle['relations']), 'artifact_count': len(artifacts) + 3, 'missing_docstring_finding_count': len(findings)},
        residual_notes=['Relation semantics remain conservative and are not yet a full repository-wide graph compiler.', 'Doc drift reporting remains heuristic and should not be treated as semantic proof.'],
        tool_chain=['fy_platform', 'docify'],
    )

    unit_artifact_id = stable_artifact_id('docify', 'unit-index', graph_result['written_paths']['unit_index'][1], run_id)
    relation_artifact_id = stable_artifact_id('docify', 'relation-graph', graph_result['written_paths']['relation_graph'][1], run_id)
    manifest_artifact_id = stable_artifact_id('docify', 'run-manifest', graph_result['written_paths']['run_manifest'][1], run_id)
    artifacts.extend([
        {
            'artifact_id': unit_artifact_id,
            'artifact_type': 'unit-index',
            'producer_suite': 'docify',
            'source_units': all_unit_ids,
            'source_artifacts': [],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': 'evidence-fill',
            'evidence_mode': 'deterministic-scan',
            'tracked_or_generated': 'generated',
            'render_family': 'json',
            'path': graph_result['written_paths']['unit_index'][1],
            'status': 'complete',
        },
        {
            'artifact_id': relation_artifact_id,
            'artifact_type': 'relation-graph',
            'producer_suite': 'docify',
            'source_units': all_unit_ids,
            'source_artifacts': [unit_artifact_id],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': 'cross-linked',
            'evidence_mode': 'deterministic-scan',
            'tracked_or_generated': 'generated',
            'render_family': 'json',
            'path': graph_result['written_paths']['relation_graph'][1],
            'status': 'complete',
        },
        {
            'artifact_id': manifest_artifact_id,
            'artifact_type': 'run-manifest',
            'producer_suite': 'docify',
            'source_units': [],
            'source_artifacts': [item['artifact_id'] for item in artifacts],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': 'cross-linked',
            'evidence_mode': 'deterministic-scan',
            'tracked_or_generated': 'generated',
            'render_family': 'json',
            'path': graph_result['written_paths']['run_manifest'][1],
            'status': 'complete',
        },
    ])

    artifact_index = {'schema_name': 'artifact.schema.json', 'artifact_count': len(artifacts), 'generated_at': now, 'artifacts': artifacts}
    for relpath in graph_result['written_paths']['artifact_index']:
        (workspace / relpath).write_text(json.dumps(artifact_index, indent=2) + '\n', encoding='utf-8')
    graph_result['artifact_index'] = artifact_index
    graph_result['run_manifest']['emitted_artifacts'] = [item['artifact_id'] for item in artifacts]
    for relpath in graph_result['written_paths']['run_manifest']:
        (workspace / relpath).write_text(json.dumps(graph_result['run_manifest'], indent=2) + '\n', encoding='utf-8')
    return {**bundle, **graph_result, 'artifact_index': artifact_index}
