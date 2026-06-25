"""Adr reflection for fy_platform.ai.

"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from textwrap import dedent
from typing import Any

ADR_DIRS = (
    'docs/ADR',
    'docs/adr',
    'docs/architecture/adr',
)
ADR_ID_RE = re.compile(r'(?i)\bADR[-._ ]?(\d{1,4})\b')
TITLE_RE = re.compile(r'(?m)^#\s+(.+)$')
SUPERCEDES_RE = re.compile(r'(?im)^\s*supersedes\s*:\s*(.+)$')
CONSOLIDATION_HINT_RE = re.compile(r'(?i)\b(consolidat(?:ed|ion)?|merge(?:d)?|unified|supersedes?)\b')
WORD_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{2,}')
STOPWORDS = {
    'the', 'and', 'for', 'with', 'from', 'into', 'this', 'that', 'these', 'those',
    'adr', 'architecture', 'decision', 'record', 'consolidated', 'consolidation',
    'merged', 'merge', 'unified', 'system', 'service', 'repo', 'repository', 'test',
}
MATRIX_ASSIGN_RE = re.compile(r'ADR_TEST_MATRIX\s*=\s*(\{.*\})', re.DOTALL)
INSTRUCTION_ASSIGN_RE = re.compile(r'(?i)\b(ADR[-._ ]?\d{1,4})\s*=\s*([^;\n]+)')


def _safe_read(path: Path) -> str:
    """Safe read.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return path.read_text(encoding='utf-8', errors='replace') if path.is_file() else ''


def _normalize_adr_id(raw: str) -> str:
    """Normalize adr id.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        raw: Primary raw used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    m = ADR_ID_RE.search(raw)
    # Branch on not m so _normalize_adr_id only continues along the matching state path.
    if not m:
        return raw.strip().upper().replace('_', '-').replace('.', '-')
    return f"ADR-{int(m.group(1)):04d}"


def _extract_title(text: str, path: Path) -> str:
    """Extract title.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        text: Text content to inspect or rewrite.
        path: Filesystem path to the file or directory being processed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    m = TITLE_RE.search(text[:4000])
    if m:
        title = m.group(1).strip()
        title = re.sub(r'(?i)^ADR[-._ ]?\d{1,4}\s*[:\-]?\s*', '', title).strip()
        return title or path.stem
    return path.stem


def _extract_keywords(title: str, path: Path, text: str) -> list[str]:
    """Extract keywords.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        title: Primary title used by this step.
        path: Filesystem path to the file or directory being processed.
        text: Text content to inspect or rewrite.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    raw = ' '.join([title, path.stem.replace('-', ' '), text[:2000]])
    words: list[str] = []
    seen: set[str] = set()
    for match in WORD_RE.findall(raw):
        token = match.lower().replace('_', '-').strip('-')
        if token in STOPWORDS or token.isdigit() or len(token) < 3:
            continue
        if token not in seen:
            seen.add(token)
            words.append(token)
    return words[:8]


def list_adr_paths(repo: Path) -> list[Path]:
    """List adr paths.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        list[Path]:
            Filesystem path produced or resolved by this
            callable.
    """
    repo = repo.resolve()
    out: list[Path] = []
    seen: set[str] = set()
    for rel_dir in ADR_DIRS:
        base = repo / rel_dir
        if not base.is_dir():
            continue
        for path in sorted(base.glob('*.md')):
            if 'template' in path.stem.lower():
                continue
            rel = str(path.resolve())
            if rel in seen:
                continue
            seen.add(rel)
            out.append(path)
    return out


def discover_consolidated_adrs(repo: Path) -> list[dict[str, Any]]:
    """Discover consolidated adrs.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        list[dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    records: list[dict[str, Any]] = []
    for path in list_adr_paths(repo):
        text = _safe_read(path)
        title = _extract_title(text, path)
        adr_id = _normalize_adr_id(path.stem)
        match = ADR_ID_RE.search(text[:2000])
        if match:
            adr_id = f"ADR-{int(match.group(1)):04d}"
        supersedes: list[str] = []
        sup = SUPERCEDES_RE.search(text[:4000])
        if sup:
            supersedes = [_normalize_adr_id(x) for x in re.split(r'[, ]+', sup.group(1).strip()) if x.strip()]
        consolidated = bool(supersedes) or bool(CONSOLIDATION_HINT_RE.search(text[:4000]))
        if not consolidated:
            continue
        records.append({
            'adr_id': adr_id,
            'title': title,
            'path': str(path.relative_to(repo).as_posix()),
            'keywords': _extract_keywords(title, path, text),
            'supersedes': supersedes,
        })
    return records


def find_candidate_test_matches(repo: Path, adr: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    """Find candidate test matches.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.
        adr: Primary adr used by this step.
        limit: Primary limit used by this step.

    Returns:
        list[dict[str, Any]]:
            Structured payload describing the outcome of the
            operation.
    """
    repo = repo.resolve()
    tests_dir = repo / 'tests'
    if not tests_dir.is_dir():
        return []
    adr_id = adr.get('adr_id', '')
    title = adr.get('title', '')
    keywords = list(adr.get('keywords', []))
    hits: list[dict[str, Any]] = []
    for path in sorted(tests_dir.rglob('test_*.py')):
        if path.name == 'test_adr_consolidation_alignment.py':
            continue
        text = _safe_read(path)
        rel = path.relative_to(repo).as_posix()
        name_l = path.name.lower()
        text_l = text.lower()
        score = 0
        reasons: list[str] = []
        if adr_id and adr_id.lower() in text_l:
            score += 6
            reasons.append('adr-id-in-body')
        if adr_id and adr_id.lower().replace('-', '_') in text_l:
            score += 4
            reasons.append('adr-id-variant-in-body')
        for token in list(dict.fromkeys(keywords + _extract_keywords(title, path, title)[:4])):
            if token in name_l:
                score += 3
                reasons.append(f'filename:{token}')
            elif token in text_l:
                score += 1
                reasons.append(f'content:{token}')
        if score > 0:
            hits.append({'path': rel, 'score': score, 'reasons': reasons[:6]})
    hits.sort(key=lambda item: (-item['score'], item['path']))
    return hits[:limit]


def parse_instruction_mapping(instruction: str | None) -> dict[str, list[str]]:
    """Parse instruction mapping.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        instruction: Free-text input that shapes this operation.

    Returns:
        dict[str, list[str]]:
            Structured payload describing the outcome of the
            operation.
    """
    if not instruction:
        return {}
    mapping: dict[str, list[str]] = {}
    for raw_adr, raw_paths in INSTRUCTION_ASSIGN_RE.findall(instruction):
        adr_id = _normalize_adr_id(raw_adr)
        paths = [p.strip() for p in raw_paths.split(',') if p.strip()]
        if paths:
            mapping[adr_id] = paths
    return mapping


def render_contract_matrix_module(entries: list[dict[str, Any]]) -> str:
    """Render contract matrix module.

    The implementation iterates over intermediate items before it
    returns.

    Args:
        entries: Primary entries used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    lines = [
        '"""Generated by contractify consolidate. Edit with care; rerun consolidate after manual changes."""',
        '',
        'ADR_TEST_MATRIX = {',
    ]
    for entry in entries:
        lines.append(f"    {entry['adr_id']!r}: {{")
        lines.append(f"        'title': {entry.get('title', '')!r},")
        lines.append(f"        'source_path': {entry.get('source_path', '')!r},")
        lines.append(f"        'keywords': {entry.get('keywords', [])!r},")
        lines.append(f"        'required_test_paths': {entry.get('required_test_paths', [])!r},")
        lines.append('    },')
    lines.append('}')
    lines.append('')
    return '\n'.join(lines)


def render_alignment_test_module() -> str:
    """Render alignment test module.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return dedent(
        """
        from __future__ import annotations

        from pathlib import Path

        from tests.adr_contract_matrix import ADR_TEST_MATRIX


        def test_consolidated_adr_matrix_is_not_empty() -> None:
            assert ADR_TEST_MATRIX, "ADR_TEST_MATRIX must contain at least one consolidated ADR mapping"


        def test_consolidated_adrs_are_reflected_in_named_tests() -> None:
            repo_root = Path(__file__).resolve().parents[1]
            missing: list[str] = []
            for adr_id, entry in ADR_TEST_MATRIX.items():
                required_paths = list(entry.get('required_test_paths', []))
                if not required_paths:
                    missing.append(f"{adr_id}: no required_test_paths declared")
                    continue
                existing = [p for p in required_paths if (repo_root / p).is_file()]
                if not existing:
                    missing.append(f"{adr_id}: none of {required_paths!r} exist")
            assert not missing, "\\n".join(missing)
        """
    ).lstrip()


def load_adr_test_matrix(repo: Path) -> dict[str, Any]:
    """Load adr test matrix.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    matrix_path = repo / 'tests' / 'adr_contract_matrix.py'
    if not matrix_path.is_file():
        return {}
    text = _safe_read(matrix_path)
    match = MATRIX_ASSIGN_RE.search(text)
    if not match:
        return {}
    try:
        return ast.literal_eval(match.group(1))
    except Exception:
        return {}


def compute_reflection_status(repo: Path, consolidated_adrs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute reflection status.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.
        consolidated_adrs: Primary consolidated adrs used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    matrix = load_adr_test_matrix(repo)
    alignment_test_present = (repo / 'tests' / 'test_adr_consolidation_alignment.py').is_file()
    mirrored: list[str] = []
    weakly_mapped: list[str] = []
    unmapped: list[str] = []
    direct_refs: dict[str, list[str]] = {}
    for adr in consolidated_adrs:
        adr_id = adr['adr_id']
        matches = find_candidate_test_matches(repo, adr)
        direct_refs[adr_id] = [item['path'] for item in matches]
        entry = matrix.get(adr_id) if isinstance(matrix, dict) else None
        declared_paths = list(entry.get('required_test_paths', [])) if isinstance(entry, dict) else []
        existing_paths = [p for p in declared_paths if (repo / p).is_file()]
        if existing_paths and alignment_test_present:
            mirrored.append(adr_id)
        elif entry or matches:
            weakly_mapped.append(adr_id)
        else:
            unmapped.append(adr_id)
    return {
        'consolidated_adr_count': len(consolidated_adrs),
        'matrix_present': bool(matrix),
        'alignment_test_present': alignment_test_present,
        'mirrored_adr_ids': mirrored,
        'weakly_mapped_adr_ids': weakly_mapped,
        'unmapped_adr_ids': unmapped,
        'direct_ref_candidates': direct_refs,
    }
