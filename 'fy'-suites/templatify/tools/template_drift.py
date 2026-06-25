"""Template drift for templatify.tools.

"""
from __future__ import annotations

from pathlib import Path
import re

from templatify.tools.template_registry import template_map

HEADER_RE = re.compile(r'templify:template_id=([^\s]+) template_hash=([0-9a-f]{64})')


def scan_generated_drift(workspace_root: Path, generated_dir: Path) -> dict:
    """Scan generated drift.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        workspace_root: Root directory used to resolve repository-local
            paths.
        generated_dir: Root directory used to resolve repository-local
            paths.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    records = template_map(workspace_root)
    drifted = []
    scanned = 0
    # Branch on not generated_dir.exists() so scan_generated_drift only continues along
    # the matching state path.
    if not generated_dir.exists():
        return {'ok': True, 'scanned_files': 0, 'drift_count': 0, 'drifted': []}
    # Process path one item at a time so scan_generated_drift applies the same rule
    # across the full collection.
    for path in generated_dir.rglob('*.md'):
        scanned += 1
        first = path.read_text(encoding='utf-8', errors='replace').splitlines()[:1]
        # Branch on not first so scan_generated_drift only continues along the matching
        # state path.
        if not first:
            continue
        match = HEADER_RE.search(first[0])
        # Branch on not match so scan_generated_drift only continues along the matching
        # state path.
        if not match:
            continue
        template_id, used_hash = match.group(1), match.group(2)
        current = records.get(template_id)
        # Branch on current and current.sha256 != used_hash so scan_generated_drift only
        # continues along the matching state path.
        if current and current.sha256 != used_hash:
            drifted.append({'path': path.as_posix(), 'template_id': template_id, 'used_hash': used_hash, 'current_hash': current.sha256})
    return {'ok': True, 'scanned_files': scanned, 'drift_count': len(drifted), 'drifted': drifted}
