"""Cache for fy_platform.providers.

"""
from __future__ import annotations

import json
from pathlib import Path

from fy_platform.ai.workspace import workspace_root


class ProviderCache:
    """Coordinate provider cache behavior.
    """
    def __init__(self, root: Path | None = None) -> None:
        """Initialize ProviderCache.

        This callable writes or records artifacts as part of its
        workflow. Control flow branches on the parsed state rather than
        relying on one linear path.

        Args:
            root: Root directory used to resolve repository-local paths.
        """
        self.root = workspace_root(root)
        self.path = self.root / '.fydata' / 'cache' / 'provider_cache.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Branch on not self.path.exists() so __init__ only continues along the matching
        # state path.
        if not self.path.exists():
            self.path.write_text('{}\n', encoding='utf-8')

    def _load(self) -> dict[str, bool]:
        """Load the requested operation.

        Exceptions are normalized inside the implementation before
        control returns to callers.

        Returns:
            dict[str, bool]:
                Structured payload describing the
                outcome of the operation.
        """
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return {}

    def has(self, cache_key: str) -> bool:
        """Return whether the requested condition.

        Args:
            cache_key: Primary cache key used by this step.

        Returns:
            bool:
                Boolean outcome for the requested
                condition check.
        """
        return bool(self._load().get(cache_key))

    def remember(self, cache_key: str) -> None:
        """Remember the requested operation.

        This callable writes or records artifacts as part of its
        workflow.

        Args:
            cache_key: Primary cache key used by this step.
        """
        payload = self._load()
        payload[cache_key] = True
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
