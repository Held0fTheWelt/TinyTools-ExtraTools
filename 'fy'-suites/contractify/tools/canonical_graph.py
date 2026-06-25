"""Canonical graph for contractify.tools.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fy_platform.ai.workspace import target_repo_id, utc_now
from fy_platform.evolution.graph_store import (
    CanonicalGraphStore,
    stable_artifact_id,
    stable_relation_id,
    stable_unit_id,
)


def _family_of_contract(item: dict[str, Any]) -> str:
    """Family of contract.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        item: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    anchor = item.get('anchor_location', '') or ''
    # Branch on item.get('anchor_kind') == 'workflow_definition' so _family_of_contract
    # only continues along the matching state path.
    if item.get('anchor_kind') == 'workflow_definition':
        return 'workflow_definition'
    # Branch on anchor.startswith('docs/ADR/') or 'adr' in ' ... so _family_of_contract
    # only continues along the matching state path.
    if anchor.startswith('docs/ADR/') or 'adr' in ' '.join(item.get('tags', [])).lower():
        return 'adr_governance'
    return item.get('contract_type', 'contract') or 'contract'


def _make_unit(*, unit_id: str, title: str, entity_type: str, source_paths: list[str], summary: str, why_it_exists: str, commands: list[str], roles: list[str], tags: list[str], maturity: str = 'cross-linked', stability: str = 'observed', last_verified: str, dependencies: list[str] | None = None, outputs: list[str] | None = None, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    """Make unit.

    Args:
        unit_id: Identifier used to select an existing run or record.
        title: Primary title used by this step.
        entity_type: Primary entity type used by this step.
        source_paths: Primary source paths used by this step.
        summary: Structured data carried through this workflow.
        why_it_exists: Primary why it exists used by this step.
        commands: Primary commands used by this step.
        roles: Primary roles used by this step.
        tags: Primary tags used by this step.
        maturity: Primary maturity used by this step.
        stability: Primary stability used by this step.
        last_verified: Primary last verified used by this step.
        dependencies: Primary dependencies used by this step.
        outputs: Primary outputs used by this step.
        evidence_refs: Primary evidence refs used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return {
        'unit_id': unit_id,
        'title': title,
        'entity_type': entity_type,
        'owner_suite': 'contractify',
        'source_paths': source_paths,
        'summary': summary,
        'why_it_exists': why_it_exists,
        'contracts': [],
        'dependencies': dependencies or [],
        'consumers': roles,
        'commands': commands,
        'inputs': [],
        'outputs': outputs or [],
        'failure_modes': [],
        'evidence_refs': evidence_refs or [f'source:{p}' for p in source_paths],
        'roles': roles,
        'layer_status': {'technical': 'observed', 'ai': 'available-for-projection'},
        'maturity': maturity,
        'last_verified': last_verified,
        'stability': stability,
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
        'relation_id': stable_relation_id('contractify', from_id, relation_type, to_id),
        'from_id': from_id,
        'to_id': to_id,
        'relation_type': relation_type,
        'owner_suite': 'contractify',
        'evidence_refs': [f'source:{p}' for p in source_paths if p],
        'confidence': 'high',
        'created_at': now,
        'last_verified': now,
    })


def _build_public_command_family(repo_root: Path, now: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build public command family.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        now: Primary now used by this step.

    Returns:
        tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str,...:
            Structured payload describing the outcome of the
            operation.
    """
    mode_registry = repo_root / 'fy_platform' / 'runtime' / 'mode_registry.py'
    cli_parser = repo_root / 'fy_platform' / 'tools' / 'cli_parser.py'
    pyproject = repo_root / 'pyproject.toml'
    if not (mode_registry.is_file() and cli_parser.is_file() and pyproject.is_file()):
        return [], [], {}
    family = 'public_command_surface'
    source_paths = ['fy_platform/runtime/mode_registry.py', 'fy_platform/tools/cli_parser.py', 'pyproject.toml']
    roles = ['developer', 'operator']
    commands = ['analyze --mode contract', 'analyze --mode quality', 'analyze --mode code_docs', 'analyze --mode docs', 'export-schemas']
    contract_id = stable_unit_id('contractify', 'contract', 'public-command-surface-contract')
    claim_id = stable_unit_id('contractify', 'claim', 'public-command-surface-claim')
    units = [
        _make_unit(
            unit_id=contract_id,
            title='Public command surface contract',
            entity_type='contract',
            source_paths=source_paths,
            summary='The platform public surfaces must continue to expose the governed analyze and schema-export entrypoints.',
            why_it_exists='Contractify elevates the platform command surface into a normative family because other suites depend on these outward commands.',
            commands=commands,
            roles=roles,
            tags=[f'family:{family}', 'contract-family', 'cli'],
            last_verified=now,
        ),
        _make_unit(
            unit_id=claim_id,
            title='Claim: public command surfaces remain governed',
            entity_type='claim',
            source_paths=source_paths,
            summary='The public command registry and parser continue to expose the bounded platform entrypoints required by the current evolution slice.',
            why_it_exists='This claim is the thin normative claim that Testify can validate against the real command registry and parser surfaces.',
            commands=commands,
            roles=roles,
            tags=[f'family:{family}', 'claim', 'cli'],
            dependencies=[contract_id],
            last_verified=now,
        ),
    ]
    relations: list[dict[str, Any]] = []
    _add_relation(relations, from_id=contract_id, relation_type='defines', to_id=claim_id, source_paths=source_paths, now=now)
    _add_relation(relations, from_id=claim_id, relation_type='derives-from', to_id=contract_id, source_paths=source_paths, now=now)
    command_unit_ids: list[str] = []
    for command in commands:
        cmd_id = stable_unit_id('contractify', 'cli-command', command)
        command_unit_ids.append(cmd_id)
        units.append(
            _make_unit(
                unit_id=cmd_id,
                title=command,
                entity_type='cli-command',
                source_paths=source_paths,
                summary=f'Governed public command surface: {command}.',
                why_it_exists='The command exists as a public-surface obligation under the current fy platform evolution slice.',
                commands=[command],
                roles=roles,
                tags=[f'family:{family}', 'governed-surface', 'cli-command'],
                last_verified=now,
            )
        )
        _add_relation(relations, from_id=contract_id, relation_type='governs', to_id=cmd_id, source_paths=source_paths, now=now)
    return units, relations, {'family': family, 'contract_count': 1, 'claim_count': 1, 'surface_count': len(command_unit_ids), 'source_paths': source_paths}


def _build_schema_export_family(repo_root: Path, now: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build schema export family.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        now: Primary now used by this step.

    Returns:
        tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str,...:
            Structured payload describing the outcome of the
            operation.
    """
    export_impl = repo_root / 'fy_platform' / 'ai' / 'final_product_schemas.py'
    source_dir = repo_root / 'fy_platform' / 'contracts' / 'evolution_wave1' / 'schemas'
    export_dir = repo_root / 'docs' / 'platform' / 'schemas'
    if not (export_impl.is_file() and source_dir.is_dir() and export_dir.is_dir()):
        return [], [], {}
    family = 'schema_export'
    source_paths = ['fy_platform/ai/final_product_schemas.py', 'fy_platform/contracts/evolution_wave1/schemas/fy_unit.schema.json', 'docs/platform/schemas/fy_unit.schema.json']
    roles = ['developer', 'operator']
    commands = ['export-schemas']
    contract_id = stable_unit_id('contractify', 'contract', 'canonical-schema-export-contract')
    claim_id = stable_unit_id('contractify', 'claim', 'canonical-schema-export-claim')
    source_surface_id = stable_unit_id('contractify', 'artifact-type', 'canonical-schema-source-pack')
    export_surface_id = stable_unit_id('contractify', 'artifact-type', 'canonical-schema-export-bundle')
    units = [
        _make_unit(
            unit_id=contract_id,
            title='Canonical schema export contract',
            entity_type='contract',
            source_paths=source_paths,
            summary='The canonical schema source pack must remain exportable into the public docs/platform/schemas surface.',
            why_it_exists='The evolution substrate depends on a real schema-export contract, not only static schema files.',
            commands=commands,
            roles=roles,
            tags=[f'family:{family}', 'contract-family', 'schema-export'],
            last_verified=now,
        ),
        _make_unit(
            unit_id=claim_id,
            title='Claim: canonical schema export remains complete',
            entity_type='claim',
            source_paths=source_paths,
            summary='The exported schema bundle still carries both the legacy platform schemas and the canonical evolution schemas.',
            why_it_exists='This is the thin canonical claim that Testify can verify against the exported schema surface.',
            commands=commands,
            roles=roles,
            tags=[f'family:{family}', 'claim', 'schema-export'],
            dependencies=[contract_id],
            last_verified=now,
        ),
        _make_unit(
            unit_id=source_surface_id,
            title='Canonical schema source pack',
            entity_type='artifact-type',
            source_paths=['fy_platform/contracts/evolution_wave1/schemas/fy_unit.schema.json'],
            summary='Tracked schema source-of-truth inputs for the evolution substrate.',
            why_it_exists='The source pack is the normative input surface governed by the export contract.',
            commands=commands,
            roles=roles,
            tags=[f'family:{family}', 'governed-surface', 'schema-source'],
            last_verified=now,
        ),
        _make_unit(
            unit_id=export_surface_id,
            title='Canonical schema export bundle',
            entity_type='artifact-type',
            source_paths=['docs/platform/schemas/fy_unit.schema.json'],
            summary='Public exported schema bundle written by the platform export-schemas surface.',
            why_it_exists='The export bundle is the public-facing artifact surface governed by the schema export contract.',
            commands=commands,
            roles=roles,
            tags=[f'family:{family}', 'governed-surface', 'schema-export'],
            last_verified=now,
        ),
    ]
    relations: list[dict[str, Any]] = []
    _add_relation(relations, from_id=contract_id, relation_type='defines', to_id=claim_id, source_paths=source_paths, now=now)
    _add_relation(relations, from_id=claim_id, relation_type='derives-from', to_id=contract_id, source_paths=source_paths, now=now)
    _add_relation(relations, from_id=contract_id, relation_type='governs', to_id=source_surface_id, source_paths=source_paths, now=now)
    _add_relation(relations, from_id=contract_id, relation_type='governs', to_id=export_surface_id, source_paths=source_paths, now=now)
    return units, relations, {'family': family, 'contract_count': 1, 'claim_count': 1, 'surface_count': 2, 'source_paths': source_paths}


def build_contractify_graph(repo_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Build contractify graph.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo_root: Root directory used to resolve repository-local
            paths.
        payload: Structured data carried through this workflow.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    now = utc_now()
    units: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    contract_units: list[str] = []
    claim_units: list[str] = []
    claim_by_anchor: dict[str, str] = {}
    claim_by_family: dict[str, list[str]] = {}
    contract_by_family: dict[str, list[str]] = {}
    family_breakdown: dict[str, dict[str, Any]] = {}
    contracts = payload.get('contracts', []) or []

    for item in contracts:
        cid = item.get('id', '')
        anchor = item.get('anchor_location', '')
        family = _family_of_contract(item)
        source_paths = [anchor] if anchor else []
        family_tag = f'family:{family}'
        contract_id = stable_unit_id('contractify', 'contract', cid or item.get('title', 'contract'))
        contract_units.append(contract_id)
        contract_by_family.setdefault(family, []).append(contract_id)
        units.append({
            'unit_id': contract_id,
            'title': item.get('title', cid),
            'entity_type': 'contract',
            'owner_suite': 'contractify',
            'source_paths': source_paths,
            'summary': item.get('summary', ''),
            'why_it_exists': 'Normative contract discovered by Contractify from accepted repository truth anchors.',
            'contracts': [],
            'dependencies': item.get('derived_from', []),
            'consumers': item.get('audiences', []),
            'commands': ['analyze --mode contract'],
            'inputs': [],
            'outputs': item.get('validated_by', []),
            'failure_modes': item.get('drift_signals', []),
            'evidence_refs': [f'source:{anchor}'] if anchor else [],
            'roles': item.get('audiences', []) or ['developer'],
            'layer_status': {'technical': 'observed', 'ai': 'available-for-projection'},
            'maturity': 'cross-linked' if item.get('validated_by') else 'evidence-fill',
            'last_verified': now,
            'stability': item.get('status', 'observed'),
            'tags': list(item.get('tags', [])) + [family_tag, item.get('contract_type', 'contract')],
        })

        claim_id = stable_unit_id('contractify', 'claim', f"{cid}-claim")
        claim_units.append(claim_id)
        claim_by_family.setdefault(family, []).append(claim_id)
        if anchor:
            claim_by_anchor[anchor] = claim_id
        units.append({
            'unit_id': claim_id,
            'title': f"Claim: {item.get('title', cid)}",
            'entity_type': 'claim',
            'owner_suite': 'contractify',
            'source_paths': source_paths,
            'summary': item.get('summary', ''),
            'why_it_exists': 'Canonical claim distilled directly from the governing Contractify contract anchor.',
            'contracts': [cid],
            'dependencies': [contract_id],
            'consumers': item.get('audiences', []),
            'commands': ['analyze --mode contract'],
            'inputs': [],
            'outputs': item.get('validated_by', []),
            'failure_modes': item.get('drift_signals', []),
            'evidence_refs': [f'source:{anchor}'] if anchor else [],
            'roles': item.get('audiences', []) or ['developer'],
            'layer_status': {'technical': 'observed', 'ai': 'available-for-projection'},
            'maturity': 'cross-linked' if item.get('validated_by') else 'evidence-fill',
            'last_verified': now,
            'stability': item.get('status', 'observed'),
            'tags': list(item.get('tags', [])) + [family_tag, 'claim'],
        })
        _add_relation(relations, from_id=contract_id, relation_type='defines', to_id=claim_id, source_paths=source_paths, now=now)
        _add_relation(relations, from_id=claim_id, relation_type='derives-from', to_id=contract_id, source_paths=source_paths, now=now)
        if family == 'workflow_definition' and anchor:
            workflow_surface_id = stable_unit_id('contractify', 'workflow', anchor)
            units.append(_make_unit(
                unit_id=workflow_surface_id,
                title=anchor.split('/')[-1],
                entity_type='workflow',
                source_paths=[anchor],
                summary='Governed workflow definition surface tied to a Contractify contract family.',
                why_it_exists='Workflow definitions are a real normative family in the current repository state.',
                commands=['analyze --mode contract'],
                roles=item.get('audiences', []) or ['developer', 'operator'],
                tags=[family_tag, 'governed-surface', 'workflow'],
                last_verified=now,
            ))
            _add_relation(relations, from_id=contract_id, relation_type='governs', to_id=workflow_surface_id, source_paths=[anchor], now=now)
            family_breakdown.setdefault(family, {'family': family, 'contract_count': 0, 'claim_count': 0, 'surface_count': 0, 'source_paths': []})
            family_breakdown[family]['surface_count'] += 1
            family_breakdown[family]['source_paths'].append(anchor)
        family_breakdown.setdefault(family, {'family': family, 'contract_count': 0, 'claim_count': 0, 'surface_count': 0, 'source_paths': []})
        family_breakdown[family]['contract_count'] += 1
        family_breakdown[family]['claim_count'] += 1
        if anchor:
            family_breakdown[family]['source_paths'].append(anchor)

    for extra_units, extra_relations, meta in (_build_public_command_family(repo_root, now), _build_schema_export_family(repo_root, now)):
        if not meta:
            continue
        units.extend(extra_units)
        relations.extend(extra_relations)
        family = meta['family']
        family_breakdown[family] = meta
        for unit in extra_units:
            if unit['entity_type'] == 'contract':
                contract_units.append(unit['unit_id'])
                contract_by_family.setdefault(family, []).append(unit['unit_id'])
            elif unit['entity_type'] == 'claim':
                claim_units.append(unit['unit_id'])
                claim_by_family.setdefault(family, []).append(unit['unit_id'])

    family_counts = {
        family: {
            'contract_count': meta['contract_count'],
            'claim_count': meta['claim_count'],
            'surface_count': meta.get('surface_count', 0),
        }
        for family, meta in sorted(family_breakdown.items())
    }
    workflow_claims = []
    for item in contracts:
        if item.get('anchor_kind') == 'workflow_definition' and item.get('anchor_location'):
            workflow_claims.append({'path': item['anchor_location'], 'claim_id': claim_by_anchor.get(item['anchor_location'], ''), 'contract_title': item.get('title', '')})

    normative_inventory = {
        'contract_count': len(contract_units),
        'claim_count': len(claim_units),
        'workflow_claims': workflow_claims,
        'family_counts': family_counts,
        'claim_ids_by_family': {k: v for k, v in sorted(claim_by_family.items())},
        'contract_ids_by_family': {k: v for k, v in sorted(contract_by_family.items())},
        'stats': payload.get('stats', {}),
    }
    contract_map = {
        'contracts': contracts,
        'workflow_claims': workflow_claims,
        'family_breakdown': family_breakdown,
        'adr_governance': payload.get('adr_governance', {}),
        'manual_unresolved_areas': payload.get('manual_unresolved_areas', [])[:20],
    }
    return {
        'generated_at': now,
        'target_repo_id': target_repo_id(repo_root),
        'units': units,
        'relations': relations,
        'normative_inventory': normative_inventory,
        'contract_map': contract_map,
    }


def persist_contractify_graph(*, workspace: Path, repo_root: Path, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist contractify graph.

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
    bundle = build_contractify_graph(repo_root, payload)
    now = utc_now()
    target_id = target_repo_id(repo_root)
    export_dir = workspace / 'contractify' / 'generated' / target_id / run_id / 'evolution_graph'
    export_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    def add_artifact(name: str, artifact_type: str, data: dict[str, Any], *, source_units: list[str] | None = None, maturity: str = 'cross-linked') -> None:
        """Add artifact.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            name: Primary name used by this step.
            artifact_type: Primary artifact type used by this step.
            data: Primary data used by this step.
            source_units: Primary source units used by this step.
            maturity: Primary maturity used by this step.
        """
        path = export_dir / name
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        artifacts.append({
            'artifact_id': stable_artifact_id('contractify', artifact_type, str(path.relative_to(workspace)), run_id),
            'artifact_type': artifact_type,
            'producer_suite': 'contractify',
            'source_units': source_units or [],
            'source_artifacts': [],
            'run_id': run_id,
            'created_at': now,
            'source_revision': '',
            'maturity': maturity,
            'evidence_mode': 'deterministic-audit',
            'tracked_or_generated': 'generated',
            'render_family': 'json',
            'path': str(path.relative_to(workspace)),
            'status': 'complete',
        })

    contract_claim_units = [u['unit_id'] for u in bundle['units'] if u['entity_type'] in {'contract', 'claim'}]
    add_artifact('normative_inventory.json', 'normative-inventory', bundle['normative_inventory'], source_units=contract_claim_units)
    add_artifact('contract_map.json', 'contract-map', bundle['contract_map'], source_units=[u['unit_id'] for u in bundle['units'] if u['entity_type'] == 'contract'])
    add_artifact('family_coverage.json', 'coverage-report', {'families': bundle['normative_inventory']['family_counts']}, source_units=contract_claim_units)

    store = CanonicalGraphStore(workspace)
    graph_result = store.persist_bundle(
        suite='contractify',
        run_id=run_id,
        command='analyze',
        mode='contract',
        lane='generate',
        target_repo_root=repo_root,
        units=bundle['units'],
        relations=bundle['relations'],
        artifacts=artifacts,
        validation_summary={
            'unit_count': len(bundle['units']),
            'relation_count': len(bundle['relations']),
            'artifact_count': len(artifacts) + 3,
            'contract_count': bundle['normative_inventory']['contract_count'],
            'claim_count': bundle['normative_inventory']['claim_count'],
            'family_count': len(bundle['normative_inventory']['family_counts']),
        },
        residual_notes=['This canonical normative slice now covers several truthful families, but it still does not represent full repository-wide contract graphing.'],
        tool_chain=['fy_platform', 'contractify'],
    )

    unit_artifact_id = stable_artifact_id('contractify', 'unit-index', graph_result['written_paths']['unit_index'][1], run_id)
    relation_artifact_id = stable_artifact_id('contractify', 'relation-graph', graph_result['written_paths']['relation_graph'][1], run_id)
    manifest_artifact_id = stable_artifact_id('contractify', 'run-manifest', graph_result['written_paths']['run_manifest'][1], run_id)
    artifacts.extend([
        {
            'artifact_id': unit_artifact_id,
            'artifact_type': 'unit-index',
            'producer_suite': 'contractify',
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
            'producer_suite': 'contractify',
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
            'producer_suite': 'contractify',
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
    graph_result['run_manifest']['validation_summary']['family_count'] = len(bundle['normative_inventory']['family_counts'])
    for relpath in graph_result['written_paths']['run_manifest']:
        (workspace / relpath).write_text(json.dumps(graph_result['run_manifest'], indent=2) + '\n', encoding='utf-8')
    return {**bundle, **graph_result, 'artifact_index': artifact_index}
