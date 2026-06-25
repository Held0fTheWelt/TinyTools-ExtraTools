"""Contracts for fy_platform.ai.

"""
from __future__ import annotations

WORKSPACE_CONTRACT_VERSION = 'fy.workspace-contract.v2'
COMMAND_ENVELOPE_SCHEMA_VERSION = 'fy.command-envelope.v4'
COMMAND_ENVELOPE_COMPATIBILITY = {
    'current': COMMAND_ENVELOPE_SCHEMA_VERSION,
    'supported_read_versions': ['fy.command-envelope.v3', 'fy.command-envelope.v4'],
    'supported_write_versions': [COMMAND_ENVELOPE_SCHEMA_VERSION],
}
MANIFEST_COMPATIBILITY = {
    'current_manifest_version': 1,
    'supported_manifest_versions': [1],
    'compat_mode': 'autark-outbound',
}
STORAGE_SCHEMA_VERSIONS = {
    'registry': 3,
    'semantic_index': 2,
}
PRODUCTION_READINESS_SCHEMA_VERSION = 'fy.production-readiness.v2'
OBSERVABILITY_SCHEMA_VERSION = 'fy.observability.v3'
RELEASE_MANAGEMENT_FILES = [
    'CHANGELOG.md',
    'docs/platform/BACKWARD_COMPATIBILITY.md',
    'docs/platform/DEPRECATION_POLICY.md',
    'docs/platform/SUPPORT_POLICY.md',
    'docs/platform/RELEASE_POLICY.md',
    'docs/platform/UPGRADE_AND_ROLLBACK.md',
]
