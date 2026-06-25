"""Models for observifyfy.tools.

"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SuiteObservation:
    """Coordinate suite observation behavior.
    """
    name: str
    hub_path: str
    exists: bool
    has_readme: bool = False
    has_reports: bool = False
    has_state: bool = False
    has_tools: bool = False
    has_adapter: bool = False
    run_count: int = 0
    journal_count: int = 0
    workflow_count: int = 0
    status_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """To dict.

        Returns:
            dict[str, Any]:
                Structured payload describing the
                outcome of the operation.
        """
        return asdict(self)
