"""Shared deprecation notice helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DeprecationNotice:
    """Machine-readable and human-readable deprecation record."""

    id: str
    message: str
    replacement: str = ""
    removal_target: str = ""

    def as_payload(self) -> dict[str, str]:
        """As payload.

        Returns:
            dict[str, str]:
                Structured payload describing the
                outcome of the operation.
        """
        return asdict(self)
