"""Mock for fy_platform.providers.

"""
from __future__ import annotations


class MockProvider:
    """Coordinate mock provider behavior.
    """
    name = 'mock'

    def run(self, prompt: str) -> dict[str, str]:
        """Run the requested operation.

        Args:
            prompt: Free-text input that shapes this operation.

        Returns:
            dict[str, str]:
                Structured payload describing the
                outcome of the operation.
        """
        return {'ok': True, 'content': prompt[:120]}
