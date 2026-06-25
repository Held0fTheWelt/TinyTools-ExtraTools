"""Suite quality policy for fy_platform.ai.policy.

"""
from __future__ import annotations

from pathlib import Path

REQUIRED_LIFECYCLE_COMMANDS = (
    'init', 'inspect', 'audit', 'explain', 'prepare-context-pack', 'compare-runs', 'clean', 'reset'
)
CORE_SUITES = {'contractify', 'testify', 'documentify', 'docify', 'despaghettify', 'templatify', 'usabilify', 'securify', 'observifyfy', 'mvpify', 'metrify', 'diagnosta', 'coda'}
OPTIONAL_SUITES = {'dockerify', 'postmanify'}


def evaluate_workspace_quality(workspace_root: Path) -> dict:
    """Evaluate workspace quality.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    required_root_files = ['README.md', 'pyproject.toml', 'requirements.txt', 'requirements-dev.txt', 'requirements-test.txt']
    missing = [rel for rel in required_root_files if not (workspace_root / rel).exists()]
    warnings: list[str] = []
    # Branch on not (workspace_root / 'fy_governance_enforcem... so
    # evaluate_workspace_quality only continues along the matching state path.
    if not (workspace_root / 'fy_governance_enforcement.yaml').exists():
        warnings.append('missing:fy_governance_enforcement.yaml')
    return {
        'ok': not missing,
        'missing': missing,
        'warnings': warnings,
    }


def evaluate_suite_quality(workspace_root: Path, suite: str) -> dict:
    """Evaluate suite quality.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.
        suite: Primary suite used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    suite_root = workspace_root / suite
    required = [
        'README.md',
        'adapter/service.py',
        'adapter/cli.py',
        'tools',
        'reports',
        'state',
    ]
    if suite in CORE_SUITES:
        required.append('templates')
    missing: list[str] = []
    for rel in required:
        if not (suite_root / rel).exists():
            missing.append(rel)
    warnings: list[str] = []
    if not (suite_root / 'docs').exists():
        warnings.append('missing_optional:docs')
    if not any((suite_root / rel).exists() for rel in ['tests', 'adapter/tests', 'tools/tests']):
        warnings.append('missing_optional:tests')
    if not (suite_root / '__init__.py').exists():
        warnings.append('missing_optional:__init__.py')
    return {
        'ok': not missing,
        'suite': suite,
        'missing': missing,
        'warnings': warnings,
    }
