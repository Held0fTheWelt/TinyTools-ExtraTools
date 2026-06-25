"""
Workspace security-hygiene review helpers.

These helpers intentionally sit below the public security and production
readiness surfaces so both can share the same bounded understanding of
secret-risk scanning, security documentation expectations, and
ignore-rule hygiene.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fy_platform.ai.policy.indexing_policy import DEFAULT_EXCLUDED_DIRS, DEFAULT_EXCLUDED_FILES
from fy_platform.ai.workspace import read_text_safe, workspace_root

SECRET_FILE_NAMES = {'.env', '.env.local', '.env.production', '.env.development', 'secrets.yml', 'secrets.yaml', 'id_rsa', 'id_ed25519'}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r'''(OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|SECRET_KEY)\s*[:=]\s*['"][^'"]+['"]'''),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
]
TEXT_SUFFIXES = {'.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.rst'}
SECURITY_DOC_CANDIDATES = ['SECURITY.md', 'docs/SECURITY.md', 'docs/security/README.md', 'docs/security.md']
SECRET_IGNORE_RULES = {'.env', '.env.*', '*.pem', '*.key', 'secrets.yml', 'secrets.yaml'}
SECURITY_REVIEW_EXCLUDED_PREFIXES = [
    ('docs', 'mvps', 'imports'),
    ('mvpify', 'imports'),
]


def _is_security_review_excluded(rel_parts: tuple[str, ...]) -> bool:
    """Return whether security review excluded.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        rel_parts: Primary rel parts used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    # Process prefix one item at a time so _is_security_review_excluded applies the same
    # rule across the full collection.
    for prefix in SECURITY_REVIEW_EXCLUDED_PREFIXES:
        # Branch on rel_parts[:len(prefix)] == prefix so _is_security_review_excluded
        # only continues along the matching state path.
        if rel_parts[: len(prefix)] == prefix:
            return True
    return False


def _workspace_security_inventory(workspace: Path) -> dict[str, Any]:
    """Workspace security inventory.

    Args:
        workspace: Primary workspace used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    docs = [cand for cand in SECURITY_DOC_CANDIDATES if (workspace / cand).is_file()]
    gitignore = workspace / '.gitignore'
    ignore_rules = gitignore.read_text(encoding='utf-8', errors='replace').splitlines() if gitignore.is_file() else []
    normalized_rules = {line.strip() for line in ignore_rules if line.strip() and not line.strip().startswith('#')}
    ignore_has_secret_rules = all(rule in normalized_rules for rule in SECRET_IGNORE_RULES)
    return {
        'security_docs': docs,
        'security_doc_count': len(docs),
        'has_gitignore': gitignore.is_file(),
        'ignore_has_secret_rules': ignore_has_secret_rules,
    }


def scan_workspace_security(root: Path | None = None) -> dict[str, Any]:
    """Scan workspace security.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    workspace = workspace_root(root)
    inventory = _workspace_security_inventory(workspace)
    risky_files: list[str] = []
    secret_hits: list[dict[str, str]] = []
    for path in workspace.rglob('*'):
        if any(part in DEFAULT_EXCLUDED_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.name in SECRET_FILE_NAMES:
            risky_files.append(path.relative_to(workspace).as_posix())
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel_tuple = tuple(part.lower() for part in path.relative_to(workspace).parts)
        rel_parts = set(rel_tuple)
        if 'tests' in rel_parts or 'fixtures' in rel_parts:
            continue
        if _is_security_review_excluded(rel_tuple):
            continue
        try:
            text = read_text_safe(path)
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                secret_hits.append({'path': path.relative_to(workspace).as_posix(), 'pattern': pattern.pattern[:48]})
                break
    indexing_policy_ok = '.env' in DEFAULT_EXCLUDED_FILES and '.fydata' in DEFAULT_EXCLUDED_DIRS
    next_steps: list[str] = []
    if inventory['security_doc_count'] == 0:
        next_steps.append('Add a SECURITY.md or docs/security guide so security expectations are discoverable.')
    if not inventory['has_gitignore'] or not inventory['ignore_has_secret_rules']:
        next_steps.append('Add secret-related ignore rules such as .env, .env.*, *.pem, *.key, secrets.yml, and secrets.yaml to .gitignore.')
    if risky_files:
        next_steps.append('Remove or relocate secret-like files from the tracked repository surface.')
    if secret_hits:
        next_steps.append('Replace embedded secret-looking values with environment-based or secret-store based configuration.')
    if not next_steps:
        next_steps.append('Security hygiene checks are green. Keep imported reference exclusions bounded and rerun after meaningful changes.')
    ok = indexing_policy_ok and inventory['security_doc_count'] > 0 and inventory['has_gitignore'] and inventory['ignore_has_secret_rules'] and not risky_files and not secret_hits
    if ok:
        summary = 'Workspace security hygiene checks are green and bounded import-reference exclusions remain active.'
    else:
        reasons = []
        if inventory['security_doc_count'] == 0:
            reasons.append('no discoverable security documentation')
        if not inventory['ignore_has_secret_rules']:
            reasons.append('secret-related ignore rules are missing')
        if risky_files:
            reasons.append(f'{len(risky_files)} risky file surfaces')
        if secret_hits:
            reasons.append(f'{len(secret_hits)} embedded secret pattern hits')
        summary = 'Workspace security review found follow-up work: ' + ', '.join(reasons) + '.'
    return {
        'schema_version': 'fy.security-review.v2',
        'workspace_root': str(workspace),
        'indexing_policy_ok': indexing_policy_ok,
        **inventory,
        'risky_file_count': len(risky_files),
        'secret_hit_count': len(secret_hits),
        'risky_files': risky_files[:20],
        'secret_hits': secret_hits[:20],
        'next_steps': next_steps,
        'summary': summary,
        'ok': ok,
    }
