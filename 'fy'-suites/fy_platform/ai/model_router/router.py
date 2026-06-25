from __future__ import annotations

from pathlib import Path

from fy_platform.ai.model_router.policies import apply_policy_adjustments, build_policy, expected_utility_for, fallback_chain_for
from fy_platform.ai.model_router.recording import record_governed_route
from fy_platform.ai.schemas.common import ModelRouteDecision
from fy_platform.ai.workspace import sha256_text, workspace_root
from fy_platform.ir.catalog import IRCatalog
from fy_platform.providers.cache import ProviderCache
from fy_platform.providers.contracts import ProviderCallRequest
from fy_platform.providers.governor import ProviderGovernor


class ModelRouter:
    def __init__(self, root: Path | None = None) -> None:
        self.root = workspace_root(root) if root is not None else None
        self.cache = ProviderCache(self.root) if self.root is not None else None
        self.ir_catalog = IRCatalog(self.root) if self.root is not None else None
        self.ledger_path = (self.root / "metrify" / "state" / "ledger.jsonl") if self.root is not None else None
        self.governor = ProviderGovernor(
            cache_lookup=(self.cache.has if self.cache is not None else (lambda key: False)),
            budget_checker=self._budget_checker,
        )

    def _budget_checker(self, request: ProviderCallRequest) -> bool:
        return not (request.budget_class == "expensive" and request.expected_utility < 0.5)

    def route(
        self,
        task_type: str,
        *,
        ambiguity: str = "low",
        evidence_strength: str = "moderate",
        audience: str = "developer",
        reproducibility: str = "stable",
    ) -> ModelRouteDecision:
        policy, reasons = apply_policy_adjustments(
            build_policy(task_type),
            task_type=task_type,
            ambiguity=ambiguity,
            evidence_strength=evidence_strength,
            audience=audience,
            reproducibility=reproducibility,
        )
        expected_utility = expected_utility_for(task_type, policy["tier"])
        request = ProviderCallRequest(
            task_type=task_type,
            suite_or_mode=task_type,
            run_id="route-only",
            lane_execution_id="route-only",
            provider="policy-only",
            model=policy["model"],
            prompt_hash=sha256_text(f"{task_type}:{audience}:{ambiguity}"),
            context_hash=sha256_text(f'{evidence_strength}:{reproducibility}:{policy["tier"]}'),
            estimated_tokens=0,
            expected_utility=expected_utility,
            budget_class=policy["budget"],
            allow_provider=policy["tier"] == "llm",
            metadata={"evidence_strength": evidence_strength, "reproducibility": reproducibility},
        )
        governor = self.governor.decide(request)
        record_governed_route(
            self,
            task_type=task_type,
            model=policy["model"],
            budget_class=policy["budget"],
            expected_utility=expected_utility,
            prompt_hash=request.prompt_hash,
            context_hash=request.context_hash,
            decision=governor,
        )
        return ModelRouteDecision(
            task_type=task_type,
            selected_tier=policy["tier"],
            selected_model=policy["model"],
            reason=";".join(reasons),
            budget_class=policy["budget"],
            fallback_chain=fallback_chain_for(policy),
            reproducibility_mode=policy["repro"],
            safety_mode=policy["safety"],
            estimated_cost_class=policy["budget"],
            governor_allowed=governor.allowed,
            governor_reason=governor.reason,
            governor_policy_lane=governor.policy_lane,
            governor_cache_key=governor.cache_key,
            governor_cache_hit=governor.cache_hit,
        )
