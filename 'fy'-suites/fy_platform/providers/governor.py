"""Governor for fy_platform.providers.

"""
from __future__ import annotations

from fy_platform.providers.contracts import GovernorDecision, ProviderCallRequest


class ProviderGovernor:
    """Coordinate provider governor behavior.
    """
    DETERMINISTIC_TASKS = {'classify', 'extract', 'cluster', 'summarize', 'prepare_context_pack'}

    def __init__(self, *, cache_lookup, budget_checker, deterministic_checker=None) -> None:
        """Initialize ProviderGovernor.

        Args:
            cache_lookup: Primary cache lookup used by this step.
            budget_checker: Primary budget checker used by this step.
            deterministic_checker: Primary deterministic checker used by
                this step.
        """
        self.cache_lookup = cache_lookup
        self.budget_checker = budget_checker
        self.deterministic_checker = deterministic_checker or self._default_deterministic_checker

    def _default_deterministic_checker(self, request: ProviderCallRequest) -> bool:
        """Default deterministic checker.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            request: Primary request used by this step.

        Returns:
            bool:
                Boolean outcome for the requested
                condition check.
        """
        if request.task_type in self.DETERMINISTIC_TASKS:
            return True
        if request.metadata.get('evidence_strength') == 'strong':
            return True
        if request.metadata.get('reproducibility') == 'strict' and request.task_type not in {'explain', 'triage', 'compare', 'prepare_fix'}:
            return True
        return False

    def decide(self, request: ProviderCallRequest) -> GovernorDecision:
        """Decide the requested operation.

        Control flow branches on the parsed state rather than relying on
        one linear path.

        Args:
            request: Primary request used by this step.

        Returns:
            GovernorDecision:
                Value produced by this callable as
                ``GovernorDecision``.
        """
        cache_key = f"{request.task_type}:{request.model}:{request.prompt_hash}:{request.context_hash}"
        cache_hit = self.cache_lookup(cache_key)
        if cache_hit:
            return GovernorDecision(False, 'cache_hit_available', 'abstain', cache_key, cache_hit=True)
        if not request.allow_provider:
            return GovernorDecision(False, 'lane_not_allowed', 'abstain', cache_key)
        if self.deterministic_checker(request):
            return GovernorDecision(False, 'deterministic_solution_available', 'abstain', cache_key)
        if not self.budget_checker(request):
            return GovernorDecision(False, 'budget_exhausted_run', 'abstain', cache_key, budget_state='blocked')
        if request.expected_utility < 0.35:
            return GovernorDecision(False, 'utility_too_low', 'abstain', cache_key)
        return GovernorDecision(True, 'governor_allowed', 'likely_but_review', cache_key)
