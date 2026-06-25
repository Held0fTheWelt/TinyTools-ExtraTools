"""Manifest loading and suite-specific config extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def manifest_path(project_root: Path) -> Path:
    """Return canonical manifest path under project root.

    Args:
        project_root: Root directory used to resolve repository-local
            paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return project_root / "fy-manifest.yaml"


def load_manifest(project_root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load manifest if present; return (manifest, warnings).

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        project_root: Root directory used to resolve repository-local
            paths.

    Returns:
        tuple[dict[str, Any] | None, list[str]]:
            Structured payload describing the outcome of the
            operation.
    """
    path = manifest_path(project_root)
    # Branch on not path.is_file() so load_manifest only continues along the matching
    # state path.
    if not path.is_file():
        alt = project_root / "fy-manifest.yml"
        # Branch on not alt.is_file() so load_manifest only continues along the matching
        # state path.
        if not alt.is_file():
            return None, []
        path = alt
    # Protect the critical load_manifest work so failures can be turned into a
    # controlled result or cleanup path.
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, [f"manifest_load_error: {exc}"]
    # Branch on raw is None so load_manifest only continues along the matching state
    # path.
    if raw is None:
        return None, ["manifest_empty"]
    # Branch on not isinstance(raw, dict) so load_manifest only continues along the
    # matching state path.
    if not isinstance(raw, dict):
        return None, ["manifest_not_object"]
    warnings: list[str] = []
    # Branch on 'manifestVersion' not in raw so load_manifest only continues along the
    # matching state path.
    if "manifestVersion" not in raw:
        warnings.append("manifest_missing_manifestVersion")
    return raw, warnings


def suite_config(manifest: dict[str, Any] | None, suite_name: str) -> dict[str, Any]:
    """Return suite-specific config map from manifest.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        manifest: Primary manifest used by this step.
        suite_name: Primary suite name used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    if not manifest:
        return {}
    suites = manifest.get("suites")
    if not isinstance(suites, dict):
        return {}
    cfg = suites.get(suite_name)
    return cfg if isinstance(cfg, dict) else {}


def roots_for_suite(
    *,
    manifest: dict[str, Any] | None,
    suite_name: str,
    key: str = "roots",
) -> list[str]:
    """Read suite root list from manifest config if present.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        manifest: Primary manifest used by this step.
        suite_name: Primary suite name used by this step.
        key: Primary key used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    cfg = suite_config(manifest, suite_name)
    raw = cfg.get(key)
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for value in raw:
        if isinstance(value, str) and value.strip():
            out.append(value.strip())
    return out
