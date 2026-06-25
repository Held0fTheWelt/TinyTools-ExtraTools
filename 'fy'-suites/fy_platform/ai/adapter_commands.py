"""Adapter commands for fy_platform.ai.

"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fy_platform.ai.cross_suite_intelligence import collect_cross_suite_signals
from fy_platform.ai.governance_checks import build_self_governance_status
from fy_platform.ai.readiness_facade import build_production_readiness, build_release_readiness
from fy_platform.ai.status_page import build_status_payload, write_status_page
from fy_platform.ai.workspace import binding_path, ensure_workspace_layout, target_repo_id, utc_now, write_json
from fy_platform.ai.semantic_index.index_manager import SemanticIndex
from fy_platform.ai.decision_policy import DECISION_LANES
from fy_platform.ai.strategy_profiles import strategy_runtime_metadata


def cross_suite(adapter, query: str | None = None) -> dict[str, Any]:
    """Cross suite.

    Args:
        adapter: Primary adapter used by this step.
        query: Free-text input that shapes this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return collect_cross_suite_signals(adapter.root, adapter.suite, query=query)


def attach_status_page(adapter, command: str, payload: dict[str, Any], latest_run: dict[str, Any] | None = None, governance: dict[str, Any] | None = None) -> dict[str, Any]:
    """Attach status page.

    Args:
        adapter: Primary adapter used by this step.
        command: Named command for this operation.
        payload: Structured data carried through this workflow.
        latest_run: Primary latest run used by this step.
        governance: Primary governance used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    latest = latest_run if latest_run is not None else adapter.registry.latest_run(adapter.suite)
    gov = governance if governance is not None else payload.get('governance')
    payload.setdefault('active_strategy_profile', strategy_runtime_metadata(adapter.root))
    payload.setdefault('cross_suite', cross_suite(adapter, payload.get('query') or payload.get('summary') or ''))
    # Read and normalize the input data before attach_status_page branches on or
    # transforms it further.
    status = build_status_payload(suite=adapter.suite, command=command, payload=payload, latest_run=latest, governance=gov)
    payload.update(write_status_page(adapter.root, adapter.suite, status))
    return payload


def self_governance_status(adapter) -> dict[str, Any]:
    """Self governance status.

    Args:
        adapter: Primary adapter used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return build_self_governance_status(adapter.root, adapter.suite)


def init_suite(adapter, target_repo_root: str | None = None) -> dict[str, Any]:
    """Init suite.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        target_repo_root: Root directory used to resolve
            repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    ensure_workspace_layout(adapter.root)
    target = Path(target_repo_root).resolve() if target_repo_root else None
    governance = self_governance_status(adapter)
    if target_repo_root and (not target or not target.exists() or not target.is_dir()):
        return attach_status_page(adapter, 'init', {'ok': False, 'suite': adapter.suite, 'reason': 'target_repo_not_found', 'target_repo_root': target_repo_root, 'governance': governance}, governance=governance)
    if not governance['ok']:
        return attach_status_page(adapter, 'init', {'ok': False, 'suite': adapter.suite, 'reason': 'governance_gate_failed:init', 'governance': governance}, governance=governance)
    binding = {'suite': adapter.suite, 'workspace_root': str(adapter.root), 'target_repo_root': str(target) if target else None, 'target_repo_id': target_repo_id(target) if target else None, 'bound_at': utc_now()}
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(binding_path(adapter.root, adapter.suite), binding)
    payload = {'ok': True, 'suite': adapter.suite, 'binding': binding, 'governance': governance, 'warnings': governance['warnings'], 'summary': f'{adapter.suite} is initialized and bound for outward work. Internal state stays in the fy workspace.'}
    return attach_status_page(adapter, 'init', payload, governance=governance)


def inspect_suite(adapter, query: str | None = None) -> dict[str, Any]:
    """Inspect suite.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        query: Free-text input that shapes this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    latest = adapter.registry.latest_run(adapter.suite)
    governance = self_governance_status(adapter)
    route = adapter.router.route('summarize', evidence_strength='moderate', audience='developer', reproducibility='strict')
    out = {'ok': True, 'suite': adapter.suite, 'latest_run': latest, 'governance': governance, 'warnings': governance['warnings'], 'route': route.__dict__, 'summary': f'{adapter.suite} is ready for inspection. Read the latest summary first and then only open detailed artifacts where you still need proof.', 'uncertainty': []}
    if query:
        pack = adapter.index.build_context_pack(query, suite_scope=[adapter.suite], audience='developer')
        out.update({'query': query, 'hit_count': len(pack.hits), 'summary': pack.summary, 'artifact_paths': pack.artifact_paths, 'evidence_confidence': pack.evidence_confidence, 'priorities': pack.priorities, 'next_steps': pack.next_steps, 'uncertainty': pack.uncertainty})
    return attach_status_page(adapter, 'inspect', out, governance=governance)


def explain_suite(adapter, audience: str = 'developer') -> dict[str, Any]:
    """Explain suite.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        audience: Free-text input that shapes this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    latest = adapter.registry.latest_run(adapter.suite)
    governance = self_governance_status(adapter)
    if not latest:
        return attach_status_page(adapter, 'explain', {'ok': False, 'reason': 'no_runs', 'suite': adapter.suite, 'governance': governance}, governance=governance)
    artifacts = adapter.registry.artifacts_for_run(latest['run_id'])
    journal_summary = adapter.journal.summarize(adapter.suite, latest['run_id'])
    route = adapter.router.route('explain', audience=audience, evidence_strength='moderate')
    base = f"Suite {adapter.suite} last ran in mode {latest['mode']} with status {latest['status']}."
    if artifacts:
        base += f' Produced {len(artifacts)} artifacts.'
    if audience == 'manager':
        summary = f'{adapter.suite} has a fresh result. Start with the simple summary and only open deeper artifacts where the summary still feels incomplete.'
    elif audience == 'operator':
        summary = base + ' Review the journal and generated artifacts before outward application.'
    else:
        summary = base + ' Start with the top artifacts and validate the next action against the latest evidence.'
    payload = {'ok': True, 'suite': adapter.suite, 'run_id': latest['run_id'], 'summary': summary, 'artifacts': artifacts, 'journal_summary': journal_summary, 'governance': governance, 'warnings': governance['warnings'], 'route': route.__dict__}
    return attach_status_page(adapter, 'explain', payload, latest_run=latest, governance=governance)


def prepare_context_pack(adapter, query: str, audience: str = 'developer') -> dict[str, Any]:
    """Prepare context pack.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        query: Free-text input that shapes this operation.
        audience: Free-text input that shapes this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    latest = adapter.registry.latest_run(adapter.suite)
    if latest and latest.get('target_repo_root'):
        target = Path(latest['target_repo_root'])
        if target.is_dir():
            adapter.index.clear_scope(adapter.suite, 'target', latest.get('target_repo_id'))
            adapter.index.index_directory(suite=adapter.suite, directory=target, scope='target', target_repo_id=latest.get('target_repo_id'))
    adapter.index.clear_scope(adapter.suite, 'suite')
    adapter.index.index_directory(suite=adapter.suite, directory=adapter.hub_dir, scope='suite')
    out_dir = adapter.hub_dir / 'generated' / 'context_packs'
    out_dir.mkdir(parents=True, exist_ok=True)
    route = adapter.router.route('prepare_context_pack', audience=audience, evidence_strength='moderate', reproducibility='strict')
    payload = adapter.context_packs.build_and_write(suite=adapter.suite, query=query, suite_scope=[adapter.suite], audience=audience, out_dir=out_dir)
    payload.update({'ok': True, 'suite': adapter.suite, 'query': query, 'audience': audience, 'route': route.__dict__})
    return attach_status_page(adapter, 'prepare-context-pack', payload, latest_run=latest)


def compare_runs(adapter, left_run_id: str, right_run_id: str) -> dict[str, Any]:
    """Compare runs.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        left_run_id: Identifier used to select an existing run or
            record.
        right_run_id: Identifier used to select an existing run or
            record.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    delta = adapter.registry.compare_runs(left_run_id, right_run_id)
    if not delta:
        return attach_status_page(adapter, 'compare-runs', {'ok': False, 'reason': 'run_not_found', 'suite': adapter.suite})
    warnings: list[str] = []
    if delta.target_repo_changed or delta.target_repo_id_changed:
        warnings.append('target_repo_changed_between_runs')
    if delta.mode_changed:
        warnings.append('mode_changed_between_runs')
    route = adapter.router.route('compare', evidence_strength='moderate')
    payload = {'ok': True, 'suite': adapter.suite, **delta.__dict__, 'warnings': warnings, 'route': route.__dict__, 'summary': f'Compared {left_run_id} with {right_run_id}. Focus first on changed artifacts, review-state changes, and any target or mode differences.'}
    return attach_status_page(adapter, 'compare-runs', payload)


def clean_suite(adapter, mode: str = 'standard') -> dict[str, Any]:
    """Clean suite.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        mode: Named mode for this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    removed = []
    cache_dir = adapter.root / '.fydata' / 'cache'
    if cache_dir.is_dir():
        shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        removed.append(str(cache_dir.relative_to(adapter.root)))
    if mode in {'aggressive', 'generated'}:
        gen_dir = adapter.hub_dir / 'generated'
        if gen_dir.is_dir():
            shutil.rmtree(gen_dir)
            gen_dir.mkdir(parents=True, exist_ok=True)
            removed.append(str(gen_dir.relative_to(adapter.root)))
    if mode == 'aggressive':
        run_dir = adapter.root / '.fydata' / 'runs' / adapter.suite
        if run_dir.is_dir():
            shutil.rmtree(run_dir)
            run_dir.mkdir(parents=True, exist_ok=True)
            removed.append(str(run_dir.relative_to(adapter.root)))
    return attach_status_page(adapter, 'clean', {'ok': True, 'suite': adapter.suite, 'mode': mode, 'removed': removed})


def reset_suite(adapter, mode: str = 'soft') -> dict[str, Any]:
    """Reset suite.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        adapter: Primary adapter used by this step.
        mode: Named mode for this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    removed = []
    if mode in {'soft', 'hard'}:
        state_dir = adapter.hub_dir / 'state'
        if state_dir.is_dir():
            shutil.rmtree(state_dir)
            state_dir.mkdir(parents=True, exist_ok=True)
            removed.append(str(state_dir.relative_to(adapter.root)))
    if mode in {'hard', 'reindex-reset'}:
        index_db = adapter.root / '.fydata' / 'index' / 'semantic_index.db'
        if index_db.exists():
            index_db.unlink()
            removed.append(str(index_db.relative_to(adapter.root)))
            adapter.index = SemanticIndex(adapter.root)
    if mode == 'hard':
        bind = binding_path(adapter.root, adapter.suite)
        if bind.exists():
            bind.unlink()
            removed.append(str(bind.relative_to(adapter.root)))
    return attach_status_page(adapter, 'reset', {'ok': True, 'suite': adapter.suite, 'mode': mode, 'removed': removed})


def triage_suite(adapter, query: str | None = None) -> dict[str, Any]:
    """Triage suite.

    Args:
        adapter: Primary adapter used by this step.
        query: Free-text input that shapes this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    route = adapter.router.route('triage', ambiguity='high' if query else 'low', evidence_strength='weak' if not query else 'moderate')
    latest = adapter.registry.latest_run(adapter.suite)
    hints = [item['path'] for item in adapter.registry.artifacts_for_run(latest['run_id'])[:5]] if latest else []
    flags = [] if query else ['query_missing']
    payload = {
        'ok': True,
        'suite': adapter.suite,
        'route': route.__dict__,
        'query': query or '',
        'latest_hints': hints,
        'summary': 'Triage is for ranking problems before action. It should help you decide what to inspect next, not silently fix risky issues.',
        'decision': {'lane': 'likely_but_review' if query else 'abstain', 'recommended_action': 'Use triage to rank evidence first. Do not treat it as proof on its own.', 'uncertainty_flags': flags},
        'uncertainty': flags,
    }
    return attach_status_page(adapter, 'triage', payload)


def prepare_fix_suite(adapter, finding_ids: list[str]) -> dict[str, Any]:
    """Prepare fix suite.

    Args:
        adapter: Primary adapter used by this step.
        finding_ids: Primary finding ids used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    route = adapter.router.route('prepare_fix', ambiguity='high' if not finding_ids else 'low', evidence_strength='weak' if not finding_ids else 'moderate')
    flags = [] if finding_ids else ['no_finding_ids']
    payload = {
        'ok': True,
        'suite': adapter.suite,
        'route': route.__dict__,
        'finding_ids': finding_ids,
        'advisory_only': True,
        'decision': {'lane': 'abstain' if not finding_ids else 'likely_but_review', 'recommended_action': 'Prepare the fix plan, then review it before any outward application.', 'uncertainty_flags': flags},
        'uncertainty': flags,
    }
    return attach_status_page(adapter, 'prepare-fix', payload)


def self_audit_suite(adapter) -> dict[str, Any]:
    """Self audit suite.

    Args:
        adapter: Primary adapter used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    governance = self_governance_status(adapter)
    latest = adapter.registry.latest_run(adapter.suite)
    latest_artifacts = adapter.registry.artifacts_for_run(latest['run_id']) if latest else []
    payload = {'ok': governance['ok'], 'suite': adapter.suite, 'summary': 'Self-audit checks whether this suite is internally well formed, documented, and ready for outward work.', 'governance': governance, 'latest_run': latest, 'latest_artifact_count': len(latest_artifacts), 'warnings': governance['warnings'], 'blocking_reasons': governance['failures']}
    return attach_status_page(adapter, 'self-audit', payload, latest_run=latest, governance=governance)


def release_readiness_suite(adapter) -> dict[str, Any]:
    """Release readiness suite.

    Args:
        adapter: Primary adapter used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    payload = build_release_readiness(adapter.root, adapter.suite)
    return attach_status_page(adapter, 'release-readiness', payload, latest_run=payload.get('latest_run'))


def production_readiness_suite(adapter) -> dict[str, Any]:
    """Production readiness suite.

    Args:
        adapter: Primary adapter used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    payload = build_production_readiness(adapter.root, adapter.suite)
    return attach_status_page(adapter, 'production-readiness', payload, latest_run=payload.get('suite_release', {}).get('latest_run'))


def import_bundle_unsupported(adapter, bundle_path: str, *, legacy: bool = False) -> dict[str, Any]:
    """Import bundle unsupported.

    Args:
        adapter: Primary adapter used by this step.
        bundle_path: Filesystem path to the file or directory being
            processed.
        legacy: Whether to enable this optional behavior.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return attach_status_page(adapter, 'legacy-import' if legacy else 'import', {'ok': False, 'suite': adapter.suite, 'reason': 'import_not_supported', 'bundle_path': bundle_path, 'legacy': legacy})


def consolidate_unsupported(adapter, target_repo_root: str, *, apply_safe: bool = False, instruction: str | None = None) -> dict[str, Any]:
    """Consolidate unsupported.

    Args:
        adapter: Primary adapter used by this step.
        target_repo_root: Root directory used to resolve
            repository-local paths.
        apply_safe: Whether to enable this optional behavior.
        instruction: Free-text input that shapes this operation.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    return attach_status_page(adapter, 'consolidate', {'ok': False, 'suite': adapter.suite, 'reason': 'consolidate_not_supported', 'apply_safe': apply_safe, 'instruction': instruction or ''})
