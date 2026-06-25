"""Canonical graph for testify.tools.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import target_repo_id, utc_now
from fy_platform.evolution.bundle_loader import load_bundle_artifact_payload, load_latest_suite_graph_bundle
from fy_platform.evolution.graph_store import (
    CanonicalGraphStore,
    stable_artifact_id,
    stable_relation_id,
    stable_unit_id,
)


def _unit_family(unit: dict[str, Any]) -> str | None:
    """Unit family.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        unit: Primary unit used by this step.

    Returns:
        str | None:
            Value produced by this callable as ``str |
            None``.
    """
    # Process tag one item at a time so _unit_family applies the same rule across the
    # full collection.
    for tag in unit.get('tags', []):
        # Branch on isinstance(tag, str) and tag.startswith('fami... so _unit_family
        # only continues along the matching state path.
        if isinstance(tag, str) and tag.startswith('family:'):
            return tag.split(':', 1)[1]
    return None


def _make_unit(*, unit_id: str, title: str, entity_type: str, source_paths: list[str], summary: str, why_it_exists: str, roles: list[str], tags: list[str], now: str, commands: list[str] | None = None, dependencies: list[str] | None = None, outputs: list[str] | None = None) -> dict[str, Any]:
    """Make unit.

    Args:
        unit_id: Identifier used to select an existing run or record.
        title: Primary title used by this step.
        entity_type: Primary entity type used by this step.
        source_paths: Primary source paths used by this step.
        summary: Structured data carried through this workflow.
        why_it_exists: Primary why it exists used by this step.
        roles: Primary roles used by this step.
        tags: Primary tags used by this step.
        now: Primary now used by this step.
        commands: Primary commands used by this step.
        dependencies: Primary dependencies used by this step.
        outputs: Primary outputs used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return {
        'unit_id': unit_id,
        'title': title,
        'entity_type': entity_type,
        'owner_suite': 'testify',
        'source_paths': source_paths,
        'summary': summary,
        'why_it_exists': why_it_exists,
        'contracts': [],
        'dependencies': dependencies or [],
        'consumers': roles,
        'commands': commands or ['analyze --mode quality'],
        'inputs': [],
        'outputs': outputs or ['proof-report'],
        'failure_modes': [],
        'evidence_refs': [f'source:{p}' for p in source_paths if p],
        'roles': roles,
        'layer_status': {'technical': 'observed', 'ai': 'available-for-projection'},
        'maturity': 'cross-linked',
        'last_verified': now,
        'stability': 'observed',
        'tags': tags,
    }


def _add_relation(relations: list[dict[str, Any]], *, from_id: str, relation_type: str, to_id: str, source_paths: list[str], now: str) -> None:
    """Add relation.

    Args:
        relations: Primary relations used by this step.
        from_id: Identifier used to select an existing run or record.
        relation_type: Primary relation type used by this step.
        to_id: Identifier used to select an existing run or record.
        source_paths: Primary source paths used by this step.
        now: Primary now used by this step.
    """
    relations.append({
        'relation_id': stable_relation_id('testify', from_id, relation_type, to_id),
        'from_id': from_id,
        'to_id': to_id,
        'relation_type': relation_type,
        'owner_suite': 'testify',
        'evidence_refs': [f'source:{p}' for p in source_paths if p],
        'confidence': 'high',
        'created_at': now,
        'last_verified': now,
    })


def _contract_lookup(contractify_bundle: dict[str, Any] | None) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]], dict[str, list[str]]]:
    """Contract lookup.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        contractify_bundle: Primary contractify bundle used by this
            step.

    Returns:
        tuple[dict[str, str], dict[str, str], dict[str, list[str]],...:
            Structured payload describing the outcome of the
            operation.
    """
    contract_claims_by_path: dict[str, str] = {}
    contract_units_by_path: dict[str, str] = {}
    claim_ids_by_family: dict[str, list[str]] = {}
    contract_ids_by_family: dict[str, list[str]] = {}
    if not contractify_bundle:
        return contract_claims_by_path, contract_units_by_path, claim_ids_by_family, contract_ids_by_family
    for unit in contractify_bundle['unit_index.json'].get('units', []):
        family = _unit_family(unit)
        if unit.get('entity_type') == 'claim':
            if unit.get('source_paths'):
                contract_claims_by_path[unit['source_paths'][0]] = unit['unit_id']
            if family:
                claim_ids_by_family.setdefault(family, []).append(unit['unit_id'])
        if unit.get('entity_type') == 'contract':
            if unit.get('source_paths'):
                contract_units_by_path[unit['source_paths'][0]] = unit['unit_id']
            if family:
                contract_ids_by_family.setdefault(family, []).append(unit['unit_id'])
    return contract_claims_by_path, contract_units_by_path, claim_ids_by_family, contract_ids_by_family


def _link_proof(relations: list[dict[str, Any]], claim_links: list[dict[str, str]], *, proof_id: str, family: str, source_paths: list[str], claim_id: str | None, contract_id: str | None, now: str) -> int:
    """Link proof.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        relations: Primary relations used by this step.
        claim_links: Primary claim links used by this step.
        proof_id: Identifier used to select an existing run or record.
        family: Primary family used by this step.
        source_paths: Primary source paths used by this step.
        claim_id: Identifier used to select an existing run or record.
        contract_id: Identifier used to select an existing run or
            record.
        now: Primary now used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    linked = 0
    if claim_id:
        linked += 1
        claim_links.append({'family': family, 'claim_id': claim_id, 'proof_id': proof_id})
        _add_relation(relations, from_id=proof_id, relation_type='validates', to_id=claim_id, source_paths=source_paths, now=now)
    if contract_id:
        _add_relation(relations, from_id=proof_id, relation_type='proves', to_id=contract_id, source_paths=source_paths, now=now)
    return linked


def build_testify_graph(repo_root: Path, payload: dict[str, Any], *, contractify_bundle: dict[str, Any] | None) -> dict[str, Any]:
    """Build testify graph.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        payload: Structured data carried through this workflow.
        contractify_bundle: Primary contractify bundle used by this
            step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    now = utc_now()
    units: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    proof_units: list[str] = []
    linked_claims = 0
    claim_links: list[dict[str, str]] = []
    proof_family_counts: dict[str, int] = {}
    linked_claims_by_family: dict[str, int] = {}

    contract_claims_by_path, contract_units_by_path, claim_ids_by_family, contract_ids_by_family = _contract_lookup(contractify_bundle)

    for wf_name, wf_data in sorted((payload.get('workflows') or {}).items()):
        wf_path = f'.github/workflows/{wf_name}'
        family = 'workflow_definition'
        surface_id = stable_unit_id('testify', 'test-surface', wf_path)
        units.append(_make_unit(
            unit_id=surface_id,
            title=wf_name,
            entity_type='test-surface',
            source_paths=[wf_path],
            summary='Observed workflow governance surface from Testify audit.',
            why_it_exists='Workflow files are executable proof surfaces for the evolution graph.',
            roles=['developer', 'operator'],
            tags=[f'family:{family}', 'workflow', 'test-surface'],
            now=now,
        ))
        proof_id = stable_unit_id('testify', 'proof', f'workflow-proof:{wf_name}')
        proof_units.append(proof_id)
        proof_family_counts[family] = proof_family_counts.get(family, 0) + 1
        units.append(_make_unit(
            unit_id=proof_id,
            title=f'Proof: {wf_name}',
            entity_type='proof',
            source_paths=[wf_path],
            summary=f"Workflow `{wf_name}` exists with {wf_data.get('job_count', 0)} jobs and workflow_dispatch={wf_data.get('workflow_dispatch')}.",
            why_it_exists='Workflow proof slices validate workflow-definition claims and contracts when present.',
            roles=['developer', 'operator'],
            tags=[f'family:{family}', 'proof', 'workflow'],
            now=now,
            dependencies=[surface_id],
            outputs=['claim-proof-status'],
        ))
        _add_relation(relations, from_id=proof_id, relation_type='derives-from', to_id=surface_id, source_paths=[wf_path], now=now)
        claim_id = contract_claims_by_path.get(wf_path) or next(iter(claim_ids_by_family.get(family, [])), None)
        contract_id = contract_units_by_path.get(wf_path) or next(iter(contract_ids_by_family.get(family, [])), None)
        added = _link_proof(relations, claim_links, proof_id=proof_id, family=family, source_paths=[wf_path], claim_id=claim_id, contract_id=contract_id, now=now)
        linked_claims += added
        if added:
            linked_claims_by_family[family] = linked_claims_by_family.get(family, 0) + added

    runner_surface_id = stable_unit_id('testify', 'test-surface', 'tests/run_tests.py')
    units.append(_make_unit(
        unit_id=runner_surface_id,
        title='tests/run_tests.py',
        entity_type='test-surface',
        source_paths=['tests/run_tests.py'],
        summary='Observed test runner governance surface.',
        why_it_exists='Central runner governance remains an explicit proof surface.',
        roles=['developer'],
        tags=['family:runner_governance', 'runner', 'test-surface'],
        now=now,
    ))
    runner_proof_id = stable_unit_id('testify', 'proof', 'runner-governance-proof')
    proof_units.append(runner_proof_id)
    proof_family_counts['runner_governance'] = proof_family_counts.get('runner_governance', 0) + 1
    units.append(_make_unit(
        unit_id=runner_proof_id,
        title='Proof: runner governance',
        entity_type='proof',
        source_paths=['tests/run_tests.py'],
        summary=f"Runner exposes {len((payload.get('runner') or {}).get('suite_targets', []))} suite targets.",
        why_it_exists='Central runner governance is a secondary proof family in the shared graph.',
        roles=['developer'],
        tags=['family:runner_governance', 'proof', 'runner'],
        now=now,
        dependencies=[runner_surface_id],
    ))
    _add_relation(relations, from_id=runner_proof_id, relation_type='derives-from', to_id=runner_surface_id, source_paths=['tests/run_tests.py'], now=now)

    public_modes = payload.get('public_modes', {}) or {}
    if public_modes.get('surface_paths'):
        family = 'public_command_surface'
        surface_paths = public_modes['surface_paths']
        surface_id = stable_unit_id('testify', 'test-surface', 'public-command-surface')
        units.append(_make_unit(
            unit_id=surface_id,
            title='public command registry surface',
            entity_type='test-surface',
            source_paths=surface_paths,
            summary='Observed public command registry and parser surface.',
            why_it_exists='The public command family is a real proof surface because the mode registry and parser are tracked code surfaces.',
            roles=['developer', 'operator'],
            tags=[f'family:{family}', 'cli', 'test-surface'],
            now=now,
        ))
        proof_id = stable_unit_id('testify', 'proof', 'public-command-surface-proof')
        proof_units.append(proof_id)
        proof_family_counts[family] = proof_family_counts.get(family, 0) + 1
        missing_modes = public_modes.get('missing_analyze_modes', [])
        units.append(_make_unit(
            unit_id=proof_id,
            title='Proof: public command surface',
            entity_type='proof',
            source_paths=surface_paths,
            summary=f"Required analyze modes missing={missing_modes}; mode_count={len(public_modes.get('mode_keys', []))}.",
            why_it_exists='This proof family validates the bounded public analyze surfaces that Contractify now treats as a governed command family.',
            roles=['developer', 'operator'],
            tags=[f'family:{family}', 'proof', 'cli'],
            now=now,
            dependencies=[surface_id],
        ))
        _add_relation(relations, from_id=proof_id, relation_type='derives-from', to_id=surface_id, source_paths=surface_paths, now=now)
        claim_id = next(iter(claim_ids_by_family.get(family, [])), None)
        contract_id = next(iter(contract_ids_by_family.get(family, [])), None)
        added = _link_proof(relations, claim_links, proof_id=proof_id, family=family, source_paths=surface_paths, claim_id=claim_id, contract_id=contract_id, now=now)
        linked_claims += added
        if added:
            linked_claims_by_family[family] = linked_claims_by_family.get(family, 0) + added

    schema_export = payload.get('schema_export', {}) or {}
    if schema_export.get('surface_paths'):
        family = 'schema_export'
        surface_paths = schema_export['surface_paths']
        surface_id = stable_unit_id('testify', 'test-surface', 'canonical-schema-export-surface')
        units.append(_make_unit(
            unit_id=surface_id,
            title='canonical schema export surface',
            entity_type='test-surface',
            source_paths=surface_paths,
            summary='Observed schema source and export bundle surface.',
            why_it_exists='The schema export surface is a real proof surface because it exposes both tracked sources and exported schema outputs.',
            roles=['developer', 'operator'],
            tags=[f'family:{family}', 'schema-export', 'test-surface'],
            now=now,
        ))
        proof_id = stable_unit_id('testify', 'proof', 'canonical-schema-export-proof')
        proof_units.append(proof_id)
        proof_family_counts[family] = proof_family_counts.get(family, 0) + 1
        units.append(_make_unit(
            unit_id=proof_id,
            title='Proof: canonical schema export',
            entity_type='proof',
            source_paths=surface_paths,
            summary=f"canonical_source_complete={schema_export.get('canonical_source_complete')} canonical_export_complete={schema_export.get('canonical_export_complete')} export_count={schema_export.get('export_count', 0)}.",
            why_it_exists='This proof family verifies the canonical schema export slice against the real exported files.',
            roles=['developer', 'operator'],
            tags=[f'family:{family}', 'proof', 'schema-export'],
            now=now,
            dependencies=[surface_id],
        ))
        _add_relation(relations, from_id=proof_id, relation_type='derives-from', to_id=surface_id, source_paths=surface_paths, now=now)
        claim_id = next(iter(claim_ids_by_family.get(family, [])), None)
        contract_id = next(iter(contract_ids_by_family.get(family, [])), None)
        added = _link_proof(relations, claim_links, proof_id=proof_id, family=family, source_paths=surface_paths, claim_id=claim_id, contract_id=contract_id, now=now)
        linked_claims += added
        if added:
            linked_claims_by_family[family] = linked_claims_by_family.get(family, 0) + added

    proof_report = {
        'summary': payload.get('summary', {}),
        'findings': payload.get('findings', []),
        'warnings': payload.get('warnings', []),
        'workflows': payload.get('workflows', {}),
        'public_modes': public_modes,
        'schema_export': schema_export,
        'claim_links': claim_links,
        'proof_family_counts': proof_family_counts,
        'linked_claims_by_family': linked_claims_by_family,
        'contractify_graph_available': bool(contractify_bundle),
    }
    claim_proof_status = {
        'linked_claim_count': linked_claims,
        'linked_claims': claim_links,
        'proof_unit_count': len(proof_units),
        'workflow_proof_count': len(payload.get('workflows', {})),
        'proof_family_counts': proof_family_counts,
        'linked_claims_by_family': linked_claims_by_family,
        'family_gap_count': len([family for family, count in proof_family_counts.items() if linked_claims_by_family.get(family, 0) == 0]),
    }
    return {
        'generated_at': now,
        'target_repo_id': target_repo_id(repo_root),
        'units': units,
        'relations': relations,
        'proof_report': proof_report,
        'claim_proof_status': claim_proof_status,
    }


def persist_testify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist testify graph.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        workspace: Primary workspace used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.
        run_id: Identifier used to select an existing run or record.
        payload: Structured data carried through this workflow.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    contractify_bundle = load_latest_suite_graph_bundle(workspace, suite='contractify', target_repo_root=repo_root)
    bundle = build_testify_graph(repo_root, payload, contractify_bundle=contractify_bundle)
    now = utc_now()
    target_id = target_repo_id(repo_root)
    export_dir = workspace / 'testify' / 'generated' / target_id / run_id / 'evolution_graph'
    export_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    def add_artifact(name: str, artifact_type: str, data: dict[str, Any], *, source_units: list[str] | None = None) -> None:
        """Add artifact.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            name: Primary name used by this step.
            artifact_type: Primary artifact type used by this step.
            data: Primary data used by this step.
            source_units: Primary source units used by this step.
        """
        path = export_dir / name
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        artifacts.append({
            'artifact_id': stable_artifact_id('testify', artifact_type, str(path.relative_to(workspace)), run_id),
            'artifact_type': artifact_type,
            'producer_suite': 'testify',
            'source_units': source_units or [],
            'source_artifacts': [],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': 'cross-linked',
            'evidence_mode': 'deterministic-audit',
            'tracked_or_generated': 'generated',
            'render_family': 'json',
            'path': str(path.relative_to(workspace)),
            'status': 'complete',
        })

    proof_unit_ids = [u['unit_id'] for u in bundle['units'] if u['entity_type'] == 'proof']
    add_artifact('proof_report.json', 'proof-report', bundle['proof_report'], source_units=proof_unit_ids)
    add_artifact('claim_proof_status.json', 'claim-proof-status', bundle['claim_proof_status'], source_units=proof_unit_ids)
    add_artifact('family_coverage.json', 'coverage-report', {'proof_family_counts': bundle['claim_proof_status']['proof_family_counts'], 'linked_claims_by_family': bundle['claim_proof_status']['linked_claims_by_family']}, source_units=proof_unit_ids)

    store = CanonicalGraphStore(workspace)
    graph_result = store.persist_bundle(
        suite='testify',
        run_id=run_id,
        command='analyze',
        mode='quality',
        lane='generate',
        target_repo_root=repo_root,
        units=bundle['units'],
        relations=bundle['relations'],
        artifacts=artifacts,
        validation_summary={
            'unit_count': len(bundle['units']),
            'relation_count': len(bundle['relations']),
            'artifact_count': len(artifacts) + 3,
            'linked_claim_count': bundle['claim_proof_status']['linked_claim_count'],
            'linked_family_count': sum(1 for c in bundle['claim_proof_status']['linked_claims_by_family'].values() if c > 0),
        },
        residual_notes=['This proof slice now covers multiple truthful families, but it is still not full repository-wide proof graphing.'],
        tool_chain=['fy_platform', 'testify', 'contractify'],
    )

    unit_artifact_id = stable_artifact_id('testify', 'unit-index', graph_result['written_paths']['unit_index'][1], run_id)
    relation_artifact_id = stable_artifact_id('testify', 'relation-graph', graph_result['written_paths']['relation_graph'][1], run_id)
    manifest_artifact_id = stable_artifact_id('testify', 'run-manifest', graph_result['written_paths']['run_manifest'][1], run_id)
    artifacts.extend([
        {
            'artifact_id': unit_artifact_id,
            'artifact_type': 'unit-index',
            'producer_suite': 'testify',
            'source_units': [u['unit_id'] for u in bundle['units']],
            'source_artifacts': [],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': 'cross-linked',
            'evidence_mode': 'deterministic-audit',
            'tracked_or_generated': 'generated',
            'render_family': 'json',
            'path': graph_result['written_paths']['unit_index'][1],
            'status': 'complete',
        },
        {
            'artifact_id': relation_artifact_id,
            'artifact_type': 'relation-graph',
            'producer_suite': 'testify',
            'source_units': [u['unit_id'] for u in bundle['units']],
            'source_artifacts': [unit_artifact_id],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': 'cross-linked',
            'evidence_mode': 'deterministic-audit',
            'tracked_or_generated': 'generated',
            'render_family': 'json',
            'path': graph_result['written_paths']['relation_graph'][1],
            'status': 'complete',
        },
        {
            'artifact_id': manifest_artifact_id,
            'artifact_type': 'run-manifest',
            'producer_suite': 'testify',
            'source_units': [],
            'source_artifacts': [item['artifact_id'] for item in artifacts],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': 'cross-linked',
            'evidence_mode': 'deterministic-audit',
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
    graph_result['run_manifest']['validation_summary']['linked_family_count'] = sum(1 for c in bundle['claim_proof_status']['linked_claims_by_family'].values() if c > 0)
    for relpath in graph_result['written_paths']['run_manifest']:
        (workspace / relpath).write_text(json.dumps(graph_result['run_manifest'], indent=2) + '\n', encoding='utf-8')
    return {**bundle, **graph_result, 'artifact_index': artifact_index}
