"""Status page analysis for fy_platform.ai.

"""
from __future__ import annotations

from typing import Any

from fy_platform.ai.decision_policy import DECISION_LANES


def simple_governance_lines(governance: dict[str, Any] | None) -> list[str]:
    """Simple governance lines.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        governance: Primary governance used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    # Branch on not governance so simple_governance_lines only continues along the
    # matching state path.
    if not governance:
        return []
    failures = governance.get('failures', []) or []
    warnings = governance.get('warnings', []) or []
    lines: list[str] = []
    # Branch on failures so simple_governance_lines only continues along the matching
    # state path.
    if failures:
        lines.append('There are still governance problems inside the suite workspace.')
        lines.extend(f'- {item}' for item in failures)
    # Branch on warnings so simple_governance_lines only continues along the matching
    # state path.
    elif warnings:
        lines.append('The suite is usable, but there are warnings you should look at soon.')
        lines.extend(f'- {item}' for item in warnings)
    else:
        lines.append('The suite workspace currently looks healthy.')
    return lines


def decision_summary(payload: dict[str, Any]) -> tuple[str, list[str]]:
    """Decision summary.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        tuple[str, list[str]]:
            Collection produced from the parsed or
            accumulated input data.
    """
    decision = payload.get('decision') or {}
    lane = str(decision.get('lane', '') or '')
    if not lane:
        return '', []
    lines = [f"Decision lane: `{lane}`", DECISION_LANES.get(lane, '')]
    if decision.get('recommended_action'):
        lines.append(str(decision['recommended_action']))
    return '\n\n'.join(item for item in lines if item), list(decision.get('uncertainty_flags', []))


def derive_next_steps(suite: str, command: str, payload: dict[str, Any]) -> list[str]:
    """Derive next steps.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        suite: Primary suite used by this step.
        command: Named command for this operation.
        payload: Structured data carried through this workflow.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    steps: list[str] = []
    reason = str(payload.get('reason', '') or payload.get('error_code', '') or '')
    lane = str((payload.get('decision') or {}).get('lane', '') or '')
    if payload.get('ok') is False:
        if reason.startswith('governance_gate_failed'):
            steps.append('Repair the missing governance files or rules shown below before running the suite again.')
        elif reason == 'target_repo_not_found':
            steps.append('Check the target repository path and run the command again.')
        elif reason == 'no_runs':
            steps.append('Run an audit first so the suite has a real result to explain.')
        elif reason == 'consolidate_not_supported':
            steps.append('Use a suite that supports consolidate, or run a normal audit first.')
        else:
            steps.append('Read the error details and rerun the command after the blocking issue is fixed.')
    else:
        if lane == 'abstain':
            steps.append('Do not act automatically. Collect more evidence first.')
        elif lane == 'user_input_required':
            steps.append('Provide the missing instruction or mapping before any outward change is applied.')
        elif lane == 'ambiguous':
            steps.append('Review the top candidate options manually. The system found more than one plausible path.')
        elif lane == 'likely_but_review':
            steps.append('The likely next move is visible, but it still needs human review before outward use.')
        elif lane == 'safe_to_apply':
            steps.append('The strongest evidence looks safe enough for automatic application in this narrow case.')
        if payload.get('finding_count', 0):
            steps.append(f"Review the {payload.get('finding_count')} finding(s) and decide which one should be fixed first.")
        if payload.get('drift_count', 0):
            steps.append(f"Inspect the {payload.get('drift_count')} drift item(s) before applying generated outputs.")
        if payload.get('local_spike_count', 0):
            steps.append('Open the local spike workstream first, even if the global category still looks low.')
        unmapped = payload.get('unmapped_blocks') or []
        if unmapped:
            steps.append(f"Map the remaining template blocks first: {', '.join(unmapped[:5])}.")
    if not steps:
        steps.append(f'Read the latest {suite} output and choose the narrowest next move based on the current evidence.')
    return steps[:6]
