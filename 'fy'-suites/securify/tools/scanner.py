"""Scanner for securify.tools.

"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

EXCLUDED_DIRS = {'.git', '.venv', '__pycache__', 'node_modules', '.mypy_cache'}
TEXT_SUFFIXES = {'.py', '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.rst', '.html', '.js', '.ts'}
SECRET_FILE_NAMES = {'.env', '.env.local', '.env.production', '.env.development', 'id_rsa', 'id_ed25519', 'secrets.yml', 'secrets.yaml'}
SECRET_SUFFIXES = {'.pem', '.key', '.p12', '.pfx'}
SECURITY_DOC_CANDIDATES = [
    'SECURITY.md',
    'docs/SECURITY.md',
    'docs/security/README.md',
    'docs/security.md',
]
SECURITY_REVIEW_EXCLUDED_PREFIXES = [('docs', 'mvps', 'imports'), ('mvpify', 'imports')]

SECRET_PATTERNS = [
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    re.compile(r"(OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|SECRET_KEY)\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r'ghp_[A-Za-z0-9]{20,}'),
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


def _iter_files(target: Path):
    """Yield files.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        target: Primary target used by this step.
    """
    for path in target.rglob('*'):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def inspect_target_security(target: Path) -> dict[str, Any]:
    """Inspect target security.

    Args:
        target: Primary target used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    docs = [cand for cand in SECURITY_DOC_CANDIDATES if (target / cand).is_file()]
    gitignore = target / '.gitignore'
    ignore_rules = gitignore.read_text(encoding='utf-8', errors='replace').splitlines() if gitignore.is_file() else []
    normalized = {item.strip() for item in ignore_rules if item.strip() and not item.strip().startswith('#')}
    ignore_has_secret_rules = all(item in normalized for item in {'.env', '.env.*', '*.pem', '*.key', 'secrets.yml', 'secrets.yaml'})
    file_count = sum(1 for _ in _iter_files(target))
    return {
        'target_repo_root': str(target),
        'file_count': file_count,
        'security_docs': docs,
        'security_doc_count': len(docs),
        'has_gitignore': gitignore.is_file(),
        'ignore_has_secret_rules': ignore_has_secret_rules,
    }


def scan_target_security(target: Path) -> dict[str, Any]:
    """Scan target security.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        target: Primary target used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    inventory = inspect_target_security(target)
    risky_files: list[str] = []
    secret_hits: list[dict[str, str]] = []
    for path in _iter_files(target):
        rel = path.relative_to(target).as_posix()
        if path.name in SECRET_FILE_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
            risky_files.append(rel)
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel_tuple = tuple(part.lower() for part in path.relative_to(target).parts)
        rel_parts = set(rel_tuple)
        if 'tests' in rel_parts or 'fixtures' in rel_parts or _is_security_review_excluded(rel_tuple):
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                secret_hits.append({'path': rel, 'pattern': pattern.pattern[:48]})
                break

    next_steps: list[str] = []
    if inventory['security_doc_count'] == 0:
        next_steps.append('Add a SECURITY.md or docs/security guide so security expectations are discoverable.')
    if not inventory['has_gitignore'] or not inventory['ignore_has_secret_rules']:
        next_steps.append('Add secret-related ignore rules such as .env, *.pem, and *.key to .gitignore.')
    if risky_files:
        next_steps.append('Remove or relocate secret-like files from the tracked repository surface.')
    if secret_hits:
        next_steps.append('Replace embedded secret-looking values with environment-based or secret-store based configuration.')
    if not next_steps:
        next_steps.append('Keep security surfaces stable and rerun securify after meaningful repository changes.')

    ok = inventory['security_doc_count'] > 0 and inventory['ignore_has_secret_rules'] and not risky_files and not secret_hits
    return {
        'schema_version': 'fy.securify.audit.v1',
        'inventory': inventory,
        'security_ok': ok,
        'risky_file_count': len(risky_files),
        'secret_hit_count': len(secret_hits),
        'risky_files': risky_files[:20],
        'secret_hits': secret_hits[:20],
        'next_steps': next_steps,
        'summary': _summary(ok, inventory, risky_files, secret_hits),
    }


def _summary(ok: bool, inventory: dict[str, Any], risky_files: list[str], secret_hits: list[dict[str, str]]) -> str:
    """Summary the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        ok: Whether to enable this optional behavior.
        inventory: Primary inventory used by this step.
        risky_files: Primary risky files used by this step.
        secret_hits: Primary secret hits used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    if ok:
        return 'Securify did not find tracked secret-like files or embedded secret patterns, and basic security guidance is present.'
    reasons = []
    if inventory['security_doc_count'] == 0:
        reasons.append('no discoverable security documentation')
    if not inventory['ignore_has_secret_rules']:
        reasons.append('secret-related ignore rules are missing')
    if risky_files:
        reasons.append(f'{len(risky_files)} secret-like file surfaces')
    if secret_hits:
        reasons.append(f'{len(secret_hits)} embedded secret pattern hits')
    joined = ', '.join(reasons)
    return f'Securify found security follow-up work: {joined}. Start with the most direct exposure and the missing guidance surfaces.'


def render_markdown(payload: dict[str, Any]) -> str:
    """Render markdown.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    inv = payload['inventory']
    lines = [
        '# Securify Audit',
        '',
        payload['summary'],
        '',
        f"- security_ok: `{str(payload['security_ok']).lower()}`",
        f"- security_doc_count: `{inv['security_doc_count']}`",
        f"- has_gitignore: `{str(inv['has_gitignore']).lower()}`",
        f"- ignore_has_secret_rules: `{str(inv['ignore_has_secret_rules']).lower()}`",
        f"- risky_file_count: `{payload['risky_file_count']}`",
        f"- secret_hit_count: `{payload['secret_hit_count']}`",
        '',
        '## Most-Recent-Next-Steps',
        '',
    ]
    lines.extend(f'- {step}' for step in payload['next_steps'])
    if payload['risky_files']:
        lines.extend(['', '## Risky files', ''])
        lines.extend(f'- `{item}`' for item in payload['risky_files'])
    if payload['secret_hits']:
        lines.extend(['', '## Secret hits', ''])
        lines.extend(f"- `{item['path']}`" for item in payload['secret_hits'])
    return "\n".join(lines).strip() + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line entry point.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    parser = argparse.ArgumentParser(description='Securify security scan CLI.')
    parser.add_argument('command', choices=['inspect', 'audit', 'full'])
    parser.add_argument('--target-repo', required=True)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(list(argv) if argv is not None else None)

    target = Path(args.target_repo).resolve()
    if args.command == 'inspect':
        payload = inspect_target_security(target)
    else:
        payload = scan_target_security(target)
    if args.command == 'full':
        payload = {'inventory': inspect_target_security(target), 'audit': scan_target_security(target)}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if args.command == 'inspect':
            print(f"Securify inspected {payload['file_count']} files and found {payload['security_doc_count']} security-doc surfaces.")
        elif args.command == 'full':
            print(render_markdown(payload['audit']), end='')
        else:
            print(render_markdown(payload), end='')
    return 0
