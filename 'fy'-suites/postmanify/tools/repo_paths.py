"""Resolve monorepo root and Postmanify hub directory."""
from __future__ import annotations

from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root

FY_SUITES_DIRNAME = "'fy'-suites"


def _current_or_legacy_suite_dir(repo: Path, suite: str) -> Path:
    """Current or legacy suite dir.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        repo: Primary repo used by this step.
        suite: Primary suite used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    direct = repo / suite
    # Branch on direct.is_dir() or (repo / 'fy_platform').is_... so
    # _current_or_legacy_suite_dir only continues along the matching state path.
    if direct.is_dir() or (repo / 'fy_platform').is_dir():
        return direct
    nested = repo / FY_SUITES_DIRNAME / suite
    return nested


def repo_root(*, start: Path | None = None) -> Path:
    """Resolve the current workspace root with shared project resolution.

    When Postmanify is loaded from the monorehub layout (``'fy'-suites/postmanify/…``),
    ``resolve_project_root`` can stop at ``'fy'-suites/`` because that directory has its
    own ``pyproject.toml``. Prefer the nearest ancestor that contains
    ``docs/api/openapi.yaml`` (the canonical WoS spec).
    """
    r = resolve_project_root(
        start=start or Path(__file__),
        env_var="FY_PLATFORM_PROJECT_ROOT",
        marker_text=None,
    )
    cand = r.resolve()
    for _ in range(6):
        if (cand / "docs" / "api" / "openapi.yaml").is_file():
            return cand
        parent = cand.parent
        if parent == cand:
            break
        cand = parent
    return r.resolve()


def postmanify_hub_dir(repo: Path | None = None) -> Path:
    """Return the current Postmanify hub, with legacy nested fallback.

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    r = repo or repo_root()
    return _current_or_legacy_suite_dir(r, 'postmanify')
