"""Policies for fy_platform.ai.model_router.

"""
from __future__ import annotations

DEFAULT_TASK_POLICY = {
    'tier': 'slm',
    'model': 'local-slim-default',
    'budget': 'cheap',
    'repro': 'strict',
    'safety': 'advisory',
}

TASK_POLICIES = {
    'classify': {'tier': 'slm', 'model': 'local-slim-classifier', 'budget': 'cheap', 'repro': 'strict', 'safety': 'advisory'},
    'extract': {'tier': 'slm', 'model': 'local-slim-extractor', 'budget': 'cheap', 'repro': 'strict', 'safety': 'advisory'},
    'cluster': {'tier': 'slm', 'model': 'local-slim-cluster', 'budget': 'cheap', 'repro': 'stable', 'safety': 'advisory'},
    'summarize': {'tier': 'slm', 'model': 'local-slim-summarizer', 'budget': 'cheap', 'repro': 'stable', 'safety': 'advisory'},
    'explain': {'tier': 'llm', 'model': 'local-general-llm', 'budget': 'moderate', 'repro': 'stable', 'safety': 'advisory'},
    'triage': {'tier': 'llm', 'model': 'local-general-llm', 'budget': 'moderate', 'repro': 'stable', 'safety': 'review-first'},
    'compare': {'tier': 'llm', 'model': 'local-general-llm', 'budget': 'moderate', 'repro': 'stable', 'safety': 'advisory'},
    'prepare_fix': {'tier': 'llm', 'model': 'local-code-llm', 'budget': 'expensive', 'repro': 'stable', 'safety': 'review-first'},
    'prepare_context_pack': {'tier': 'slm', 'model': 'local-slim-retrieval-helper', 'budget': 'cheap', 'repro': 'strict', 'safety': 'advisory'},
    'decision': {'tier': 'slm', 'model': 'local-slim-policy-helper', 'budget': 'cheap', 'repro': 'strict', 'safety': 'advisory'},
    'cross_suite_synthesis': {'tier': 'llm', 'model': 'local-general-llm', 'budget': 'moderate', 'repro': 'stable', 'safety': 'advisory'},
}


def build_policy(task_type: str) -> dict[str, str]:
    """Build policy.

    Args:
        task_type: Primary task type used by this step.

    Returns:
        dict[str, str]:
            Structured payload describing the outcome of the
            operation.
    """
    return dict(TASK_POLICIES.get(task_type, DEFAULT_TASK_POLICY))


def apply_policy_adjustments(
    policy: dict[str, str],
    *,
    task_type: str,
    ambiguity: str,
    evidence_strength: str,
    audience: str,
    reproducibility: str,
) -> tuple[dict[str, str], list[str]]:
    """Apply policy adjustments.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        policy: Primary policy used by this step.
        task_type: Primary task type used by this step.
        ambiguity: Primary ambiguity used by this step.
        evidence_strength: Primary evidence strength used by this step.
        audience: Free-text input that shapes this operation.
        reproducibility: Primary reproducibility used by this step.

    Returns:
        tuple[dict[str, str], list[str]]:
            Structured payload describing the outcome of the
            operation.
    """
    reasons = [f'policy_route:{task_type}']
    # Branch on ambiguity in {'high', 'user-input'} and task_... so
    # apply_policy_adjustments only continues along the matching state path.
    if ambiguity in {'high', 'user-input'} and task_type in {'triage', 'explain', 'decision'}:
        policy['tier'] = 'llm'
        policy['model'] = 'local-general-llm'
        policy['budget'] = 'moderate'
        reasons.append('ambiguity_escalation')
    # Branch on evidence_strength == 'weak' and task_type in ... so
    # apply_policy_adjustments only continues along the matching state path.
    if evidence_strength == 'weak' and task_type in {'prepare_fix', 'decision'}:
        policy['tier'] = 'slm'
        policy['model'] = 'local-slim-policy-helper'
        policy['budget'] = 'cheap'
        policy['safety'] = 'abstain-first'
        reasons.append('weak_evidence_downgrade')
    # Branch on audience in {'manager', 'operator'} and task_... so
    # apply_policy_adjustments only continues along the matching state path.
    if audience in {'manager', 'operator'} and task_type == 'explain':
        reasons.append(f'audience:{audience}')
    # Branch on reproducibility == 'strict' so apply_policy_adjustments only continues
    # along the matching state path.
    if reproducibility == 'strict':
        policy['repro'] = 'strict'
        reasons.append('strict_reproducibility')
    return policy, reasons


def fallback_chain_for(policy: dict[str, str]) -> list[str]:
    """Fallback chain for.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        policy: Primary policy used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    if policy['tier'] == 'llm':
        return ['local-slim-default', 'deterministic-fallback']
    if policy['model'] != 'local-slim-default':
        return ['local-slim-default', 'deterministic-fallback']
    return ['deterministic-fallback']


def expected_utility_for(task_type: str, tier: str) -> float:
    """Expected utility for.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        task_type: Primary task type used by this step.
        tier: Primary tier used by this step.

    Returns:
        float:
            Value produced by this callable as ``float``.
    """
    expected_utility = 0.65 if tier == 'llm' else 0.25
    if task_type in {'triage', 'explain', 'prepare_fix', 'compare'}:
        expected_utility = max(expected_utility, 0.45)
    return expected_utility
