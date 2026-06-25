
"""Planner for mvpify.tools.

"""
from __future__ import annotations

from .models import OrchestrationStep


def build_plan(import_payload: dict, repo_root: str) -> dict:
    """Build plan.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        import_payload: Primary import payload used by this step.
        repo_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    counters = import_payload.get('counters', {})
    suites = {item['name']: item for item in import_payload.get('suite_signals', [])}
    steps: list[OrchestrationStep] = []
    source_label = import_payload.get('source', import_payload.get('root', 'mvp-source'))

    steps.append(OrchestrationStep(
        phase='import',
        suite='mvpify',
        objective='Normalize the prepared MVP bundle into a governed internal import inventory.',
        why_now='Prepared MVP information exists but must become explicit and restartable before implementation work starts.',
        inputs=[source_label],
        outputs=['mvpify/reports/mvpify_import_inventory.json', 'mvpify/reports/mvpify_import_inventory.md'],
    ))

    # Branch on suites.get('contractify', {}).get('present') so build_plan only
    # continues along the matching state path.
    if suites.get('contractify', {}).get('present'):
        steps.append(OrchestrationStep(
            phase='governance',
            suite='contractify',
            objective='Attach the imported MVP contracts, ADRs, and runtime/MVP spine to governed records.',
            why_now='The imported MVP already contains governance surfaces that must become first-class before implementation drift begins.',
            inputs=['mvpify import inventory', 'docs/ADR', 'runtime/MVP docs'],
            outputs=['contract audit update', 'attachment report', 'runtime/MVP spine state'],
            depends_on=['import:mvpify'],
        ))

    # Branch on suites.get('despaghettify', {}).get('present') so build_plan only
    # continues along the matching state path.
    if suites.get('despaghettify', {}).get('present'):
        steps.append(OrchestrationStep(
            phase='structure',
            suite='despaghettify',
            objective='Assess structural drift and pick the smallest safe implementation surface for the next coding pass.',
            why_now='Prepared MVP plans only help if the code insertion path is scoped and coherent.',
            inputs=['mvpify import inventory', 'current repo tree', 'existing despaghettify workstreams'],
            outputs=['workstream state update', 'next structural insertion target'],
            depends_on=['governance:contractify' if suites.get('contractify', {}).get('present') else 'import:mvpify'],
        ))

    # Branch on counters.get('artifact_count', 0) > 0 so build_plan only continues along
    # the matching state path.
    if counters.get('artifact_count', 0) > 0:
        steps.append(OrchestrationStep(
            phase='implementation_task',
            suite='mvpify',
            objective='Emit a concrete implementation task draft that folds the imported MVP content into the live repo.',
            why_now='The agent needs a direct handoff artifact, not only analysis.',
            inputs=['import inventory', 'orchestration plan', 'relevant suite findings'],
            outputs=['mvpify audit task', 'mvpify implementation task'],
            depends_on=['structure:despaghettify' if suites.get('despaghettify', {}).get('present') else 'import:mvpify'],
        ))

    # Branch on counters.get('test_files', 0) or suites.get('... so build_plan only
    # continues along the matching state path.
    if counters.get('test_files', 0) or suites.get('testify', {}).get('present'):
        steps.append(OrchestrationStep(
            phase='verification',
            suite='testify',
            objective='Align tests, CI gates, and suite execution metadata with the imported MVP change set.',
            why_now='Implementation cannot be trusted unless test and CI surfaces are ready to carry the change.',
            inputs=['implementation task draft', 'tests/run_tests.py', 'GitHub workflows', 'pyproject.toml'],
            outputs=['test audit update', 'recommended gate set'],
            depends_on=['implementation_task:mvpify'],
        ))

    # Branch on counters.get('docker_stack', 0) or suites.get... so build_plan only
    # continues along the matching state path.
    if counters.get('docker_stack', 0) or suites.get('dockerify', {}).get('present'):
        steps.append(OrchestrationStep(
            phase='runtime_validation',
            suite='dockerify',
            objective='Validate startup, compose topology, database readiness, and smoke paths for the MVP insertion.',
            why_now='The imported MVP targets runtime behavior, so stable boot evidence matters immediately after implementation.',
            inputs=['implementation task draft', 'docker-up.py', 'docker-compose.yml'],
            outputs=['docker audit update', 'startup/stability findings'],
            depends_on=['implementation_task:mvpify'],
        ))

    # Branch on suites.get('documentify', {}).get('present') ... so build_plan only
    # continues along the matching state path.
    if suites.get('documentify', {}).get('present') or counters.get('docs_files', 0):
        steps.append(OrchestrationStep(
            phase='documentation',
            suite='documentify',
            objective='Refresh easy, technical, role-based, and AI-facing docs after the MVP import is applied.',
            why_now='Imported MVP plans lose value if the resulting repository state is not explained and searchable.',
            inputs=['implementation task draft', 'current docs', 'technical docs', 'contract/docs findings'],
            outputs=['documentify generation update', 'AI context pack refresh'],
            depends_on=['verification:testify'],
        ))

    # Branch on suites.get('observifyfy', {}).get('present') so build_plan only
    # continues along the matching state path.
    if suites.get('observifyfy', {}).get('present'):
        steps.append(OrchestrationStep(
            phase='meta_tracking',
            suite='observifyfy',
            objective='Track the import cycle, resulting suite findings, and the best next step outside project truth surfaces.',
            why_now='The import should remain restartable and internally observable across multiple suite passes.',
            inputs=['all previous phase outputs'],
            outputs=['observifyfy next-step update', 'operations memory refresh'],
            depends_on=['documentation:documentify' if suites.get('documentify', {}).get('present') else 'implementation_task:mvpify'],
        ))

    # Wire together the shared services that build_plan depends on for the rest of its
    # workflow.
    records = [s.to_dict() for s in steps]
    phase_index = {f"{step['phase']}:{step['suite']}": i for i, step in enumerate(records, 1)}
    return {
        'ok': True,
        'repo_root': repo_root,
        'source': import_payload.get('source'),
        'steps': records,
        'highest_value_next_step': records[1] if len(records) > 1 else records[0],
        'phase_index': phase_index,
    }
