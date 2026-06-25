"""Project root resolution helpers shared by fy suites."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence


def _marker_match(path: Path, marker_text: str | None) -> bool:
    """Marker match.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        path: Filesystem path to the file or directory being processed.
        marker_text: Primary marker text used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    # Branch on marker_text is None so _marker_match only continues along the matching
    # state path.
    if marker_text is None:
        return True
    # Protect the critical _marker_match work so failures can be turned into a
    # controlled result or cleanup path.
    try:
        return marker_text in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def resolve_project_root(
    *,
    start: Path | None = None,
    env_var: str | None = None,
    marker_file: str = "pyproject.toml",
    marker_text: str | None = None,
    manifest_names: Sequence[str] = ("fy-manifest.yaml", "fy-manifest.yml"),
) -> Path:
    """Resolve project root from environment override or ancestor
    traversal.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        start: Primary start used by this step.
        env_var: Primary env var used by this step.
        marker_file: Filesystem path to the file or directory being
            processed.
        marker_text: Primary marker text used by this step.
        manifest_names: Primary manifest names used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    if env_var:
        forced = os.environ.get(env_var, "").strip()
        if forced:
            forced_path = Path(forced).expanduser().resolve()
            if forced_path.is_dir():
                marker = forced_path / marker_file
                if marker.is_file() and _marker_match(marker, marker_text):
                    return forced_path
                for mf in manifest_names:
                    if (forced_path / mf).is_file():
                        return forced_path

    probe = (start or Path(__file__)).resolve()
    candidates = [probe] if probe.is_dir() else [probe.parent]
    candidates.extend(probe.parents)
    seen: set[Path] = set()
    for ancestor in candidates:
        if ancestor in seen:
            continue
        seen.add(ancestor)
        marker = ancestor / marker_file
        if marker.is_file() and _marker_match(marker, marker_text):
            return ancestor
        if any((ancestor / name).is_file() for name in manifest_names):
            return ancestor
    msg = f"Could not resolve project root from {probe}"
    raise RuntimeError(msg)
