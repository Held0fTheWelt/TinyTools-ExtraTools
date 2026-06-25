"""Execution for fy_platform.providers.

"""
from __future__ import annotations

from fy_platform.providers.contracts import ProviderCallRequest
from fy_platform.providers.governor import ProviderGovernor


class ProviderExecutor:
    """Coordinate provider executor behavior.
    """
    def __init__(self, governor: ProviderGovernor) -> None:
        """Initialize ProviderExecutor.

        Args:
            governor: Primary governor used by this step.
        """
        self.governor = governor

    def authorize(self, request: ProviderCallRequest):
        """Authorize the requested operation.

        Args:
            request: Primary request used by this step.
        """
        return self.governor.decide(request)
