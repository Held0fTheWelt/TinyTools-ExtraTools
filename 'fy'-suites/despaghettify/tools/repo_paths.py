"""
Resolve monorepo root and Despaghettify hub directory (always under
``'fy'-suites/despaghettify``).
"""
from __future__ import annotations

import os
from pathlib import Path

from fy_platform.core.manifest import load_manifest, suite_config
from fy_platform.core.project_resolver import resolve_project_root

# Directory name at repo root (includes literal quote characters).
FY_SUITES_DIRNAME = "'fy'-suites"


def repo_root(*, start: Path | None = None) -> Path:
    """Resolve project root with optional override, then fallback to
    ancestor manifest detection.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        start: Primary start used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    env = os.environ.get("DESPAG_REPO_ROOT", "").strip()
    # Branch on env so repo_root only continues along the matching state path.
    if env:
        forced = Path(env).expanduser().resolve()
        # Branch on forced.is_dir() so repo_root only continues along the matching state
        # path.
        if forced.is_dir():
            return forced
    p = (start or Path.cwd()).resolve()
    return resolve_project_root(start=p, marker_text=None)


def despag_hub_dir(repo: Path | None = None) -> Path:
    """Absolute path to the Despaghettify hub (markdown, state, tools
    package).

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    r = repo or repo_root()
    manifest, _warnings = load_manifest(r)
    cfg = suite_config(manifest, "despaghettify")
    configured = str(cfg.get("hub_path", "")).strip() if cfg else ""
    if configured:
        custom = (r / configured).resolve()
        if custom.is_dir():
            return custom
    direct = r / 'despaghettify'
    if (direct / 'spaghetti-setup.md').is_file():
        return direct
    nested = r / FY_SUITES_DIRNAME / 'despaghettify'
    if (nested / 'spaghetti-setup.md').is_file():
        return nested
    local = Path(__file__).resolve().parents[1]
    if (local / "spaghetti-setup.md").is_file():
        return local
    msg = f"Despaghettify hub not found under {r / 'despaghettify'} or {r / FY_SUITES_DIRNAME / 'despaghettify'}"
    raise RuntimeError(msg)


def despag_hub_rel_posix(repo: Path | None = None) -> str:
    """Repo-relative POSIX path to the hub (for CLI defaults and docs).

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    hub = despag_hub_dir(repo)
    r = repo or repo_root()
    try:
        return hub.resolve().relative_to(r.resolve()).as_posix()
    except ValueError:
        return hub.resolve().as_posix()


def despag_import_parent(repo: Path | None = None) -> Path:
    """Directory that must be on ``sys.path`` so ``import despaghettify``
    resolves.

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return despag_hub_dir(repo).parent
