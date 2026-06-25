"""Final product catalog data for fy_platform.ai.

"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.contracts import COMMAND_ENVELOPE_COMPATIBILITY, COMMAND_ENVELOPE_SCHEMA_VERSION, MANIFEST_COMPATIBILITY
from fy_platform.ai.policy.suite_quality_policy import CORE_SUITES, OPTIONAL_SUITES, evaluate_suite_quality
from fy_platform.ai.release_readiness import suite_release_readiness
from fy_platform.ai.strategy_profiles import strategy_runtime_metadata
from fy_platform.ai.workspace import utc_now, workspace_root

GENERIC_LIFECYCLE_COMMANDS = [
    'init', 'inspect', 'audit', 'explain', 'prepare-context-pack', 'compare-runs', 'clean', 'reset', 'triage', 'prepare-fix', 'self-audit', 'release-readiness', 'production-readiness',
]
PLATFORM_NATIVE_COMMANDS = ['strategy show', 'strategy set <A|B|C|D|E>']

SUITE_NATIVE_COMMANDS = {
    'contractify': ['consolidate', 'import', 'legacy-import'],
    'testify': [],
    'documentify': ['generate-track'],
    'docify': ['inline-explain'],
    'despaghettify': ['wave-plan'],
    'dockerify': ['stack-audit'],
    'postmanify': ['sync'],
    'templatify': ['list-templates', 'validate', 'render', 'check-drift'],
    'usabilify': ['inspect', 'evaluate', 'full'],
    'securify': ['scan', 'evaluate', 'autofix'],
    'observifyfy': ['inspect', 'audit', 'ai-pack', 'full'],
    'mvpify': ['inspect', 'plan', 'ai-pack', 'full'],
    'metrify': ['pricing', 'record', 'ingest', 'report', 'ai-pack', 'full'],
    'diagnosta': ['diagnose', 'readiness-case', 'blocker-graph'],
    'coda': ['assemble', 'closure-pack', 'residue-report', 'bundle'],
}

SUITE_SUMMARIES = {
    'contractify': 'Discovers, audits, explains, and consolidates contracts and projections.',
    'testify': 'Audits test governance and verifies ADR-to-test reflection, not just passing behavior.',
    'documentify': 'Builds and grows documentation tracks, including status and AI-readable exports.',
    'docify': 'Improves code documentation, docstrings, and dense inline explanations for Python code.',
    'despaghettify': 'Detects structural complexity and opens work for local spikes and broader cleanup.',
    'dockerify': 'Provides repo-serving Docker and compose governance when the target repository needs it.',
    'postmanify': 'Refreshes Postman surfaces from API evidence for repositories that use them.',
    'templatify': 'Owns and validates reusable templates for reports, docs, context packs, and suite outputs.',
    'usabilify': 'Surfaces human-usable status, UX guidance, and understandable next-step outputs.',
    'securify': 'Provides the security lane for scans, secret-risk review, and security-oriented guidance.',
    'observifyfy': 'Tracks internal fy-suite operations, internal docs roots, and non-contaminating cross-suite observability.',
    'mvpify': 'Imports prepared MVP bundles, mirrors their docs into the governed workspace, and orchestrates next-step implementation across suites.',
    'metrify': 'Measures AI usage, cost, model routing, and output volume across fy suites and summarizes the spending/utility picture.',
    'diagnosta': 'Owns bounded readiness diagnosis, blocker prioritization, and claim-honesty outputs across suites.',
    'coda': 'Owns bounded closure-pack assembly, review-first completion packaging, and explicit residue reporting.',
}


def suite_dirs(workspace: Path) -> list[str]:
    """Suite dirs.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    return sorted({p.name for p in workspace.iterdir() if p.is_dir() and (p / 'adapter').is_dir()})


def suite_catalog_payload(root: Path | None = None) -> dict[str, Any]:
    """Suite catalog payload.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    suites = sorted({*CORE_SUITES, *OPTIONAL_SUITES, *suite_dirs(workspace)})
    rows: list[dict[str, Any]] = []
    # Process suite one item at a time so suite_catalog_payload applies the same rule
    # across the full collection.
    for suite in suites:
        # Build filesystem locations and shared state that the rest of
        # suite_catalog_payload reuses.
        suite_root = workspace / suite
        quality = evaluate_suite_quality(workspace, suite)
        readiness = suite_release_readiness(workspace, suite) if suite_root.exists() else None
        rows.append({
            'suite': suite,
            'category': 'core' if suite in CORE_SUITES else 'optional',
            'summary': SUITE_SUMMARIES.get(suite, 'No catalog summary recorded yet.'),
            'has_adapter': (suite_root / 'adapter' / 'service.py').is_file(),
            'has_tools': (suite_root / 'tools').is_dir(),
            'has_docs': (suite_root / 'docs').is_dir() or (suite_root / 'README.md').is_file(),
            'has_templates': (suite_root / 'templates').is_dir(),
            'has_status': (suite_root / 'reports' / 'status' / 'most_recent_next_steps.json').is_file(),
            'lifecycle_commands': GENERIC_LIFECYCLE_COMMANDS,
            'native_commands': SUITE_NATIVE_COMMANDS.get(suite, []),
            'quality_ok': quality['ok'],
            'quality_missing': quality['missing'],
            'quality_warnings': quality['warnings'],
            'release_ready': bool(readiness and readiness.get('ready')),
            'latest_run_id': ((readiness or {}).get('latest_run') or {}).get('run_id'),
        })
    return {
        'schema_version': 'fy.suite-catalog.v1',
        'generated_at': utc_now(),
        'suite_count': len(rows),
        'core_count': sum(1 for row in rows if row['category'] == 'core'),
        'optional_count': sum(1 for row in rows if row['category'] == 'optional'),
        'suites': rows,
    }


def command_reference_payload(root: Path | None = None) -> dict[str, Any]:
    """Command reference payload.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    catalog = suite_catalog_payload(workspace)
    strategy = strategy_runtime_metadata(workspace)
    return {
        'schema_version': 'fy.command-reference.v1',
        'generated_at': utc_now(),
        'command_envelope_current': COMMAND_ENVELOPE_SCHEMA_VERSION,
        'command_envelope_compatibility': COMMAND_ENVELOPE_COMPATIBILITY,
        'manifest_compatibility': MANIFEST_COMPATIBILITY,
        'generic_lifecycle_commands': GENERIC_LIFECYCLE_COMMANDS,
        'platform_native_commands': PLATFORM_NATIVE_COMMANDS,
        'active_strategy_profile': strategy,
        'suite_native_commands': {row['suite']: row['native_commands'] for row in catalog['suites']},
    }
