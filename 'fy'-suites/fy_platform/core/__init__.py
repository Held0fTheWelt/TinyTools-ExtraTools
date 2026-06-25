"""Core shared modules for the Fy platform."""

from fy_platform.core.artifact_envelope import build_envelope, dump_envelope_json
from fy_platform.core.manifest import load_manifest
from fy_platform.core.project_resolver import resolve_project_root

__all__ = [
    "build_envelope",
    "dump_envelope_json",
    "load_manifest",
    "resolve_project_root",
]
