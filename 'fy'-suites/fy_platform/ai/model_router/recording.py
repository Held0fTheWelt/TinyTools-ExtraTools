"""Recording for fy_platform.ai.model_router.

"""
from __future__ import annotations

from fy_platform.ai.workspace import utc_now
from fy_platform.ir.models import ProviderCallRecord
from metrify.tools.ledger import append_event, ensure_ledger
from metrify.tools.models import UsageEvent


def record_governed_route(router, *, task_type: str, model: str, budget_class: str, expected_utility: float, prompt_hash: str, context_hash: str, decision) -> None:
    """Record governed route.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        router: Primary router used by this step.
        task_type: Primary task type used by this step.
        model: Primary model used by this step.
        budget_class: Primary budget class used by this step.
        expected_utility: Primary expected utility used by this step.
        prompt_hash: Primary prompt hash used by this step.
        context_hash: Primary context hash used by this step.
        decision: Primary decision used by this step.
    """
    # Branch on router.root is None or router.ir_catalog is N... so
    # record_governed_route only continues along the matching state path.
    if router.root is None or router.ir_catalog is None or router.ledger_path is None:
        return
    ensure_ledger(router.ledger_path)
    provider_call_id = router.ir_catalog.new_id('providercall')
    lane_execution_id = router.ir_catalog.new_id('lanehint')
    router.ir_catalog.write_provider_call(
        ProviderCallRecord(
            provider_call_id=provider_call_id,
            run_id='route-only',
            lane_execution_id=lane_execution_id,
            task_type=task_type,
            provider='policy-only',
            model=model,
            budget_class=budget_class,
            prompt_hash=prompt_hash,
            context_hash=context_hash,
            cache_key=decision.cache_key,
            cache_hit=decision.cache_hit,
            guard_allowed=decision.allowed,
            allow_reason=decision.reason if decision.allowed else '',
            deny_reason='' if decision.allowed else decision.reason,
            expected_utility=expected_utility,
            result_status='authorized' if decision.allowed else 'blocked',
            created_at=utc_now(),
        )
    )
    append_event(
        router.ledger_path,
        UsageEvent(
            timestamp_utc=utc_now(),
            suite='metrify',
            run_id='route-only',
            model=model,
            service_tier=budget_class,
            input_tokens=0,
            cached_input_tokens=0,
            output_tokens=0,
            reasoning_tokens=0,
            cost_usd=0.0,
            notes=f'router:{task_type}',
            source='model_router',
            prompt_hash=prompt_hash,
            context_hash=context_hash,
            cache_key=decision.cache_key,
            cache_hit=decision.cache_hit,
            guard_allowed=decision.allowed,
            guard_reason=decision.reason,
            expected_utility=expected_utility,
            policy_lane=decision.policy_lane,
        ),
    )
    # Branch on decision.allowed and router.cache is not None so record_governed_route
    # only continues along the matching state path.
    if decision.allowed and router.cache is not None:
        router.cache.remember(decision.cache_key)
