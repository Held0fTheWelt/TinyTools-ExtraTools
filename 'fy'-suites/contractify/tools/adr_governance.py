"""
ADR governance inventory, migration planning, and canonicalization
support.

This module does not rewrite repository ADR files. It provides: -
deterministic ADR inventory across canonical and bounded legacy
locations, - proposed canonical IDs / paths under ``docs/ADR``, -
duplicate / legacy / navigation gap findings, - bounded migration
planning inputs for Contractify audits and investigation docs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from pathlib import Path
from typing import Iterable

from contractify.tools.models import serialise
from contractify.tools.versioning import adr_declared_status, adr_supersedes_line

ADR_CANONICAL_DIR = "docs/ADR"
ADR_LEGACY_DIRS = (
    "docs/architecture/adr",
    "docs/adr",
)
_ADR_FILE_RE = re.compile(r"(?i)^adr[-._A-Za-z0-9]+\.md$")
_TITLE_RE = re.compile(r"(?im)^#\s+(.+?)\s*$")
_DATE_RE = re.compile(r"(?im)^\s*\*{0,2}date\*{0,2}\s*:?[\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}[^\n]*)$")
_DATE_SECTION_RE = re.compile(
    r"(?is)^\s*#{2,6}\s+date\s*$\s*([\r\n]+)(.+?)(?=^\s*#{1,6}\s+|\Z)",
)
_ID_RE = re.compile(r"(?i)\bADR[-._ ]?((?:[A-Z]+[-._ ])*[0-9]{1,4})\b")


@dataclass
class ADRGovernanceRecord:
    """Structured data container for adrgovernance record.
    """
    current_path: str
    title: str
    declared_id: str
    status: str
    date: str
    family: str
    family_reason: str
    proposed_canonical_id: str
    proposed_canonical_path: str
    supersedes: list[str]
    current_location_class: str
    issues: list[str]
    duplicate_keys: list[str]


@dataclass
class ADRGovernanceFinding:
    """Coordinate adrgovernance finding behavior.
    """
    id: str
    kind: str
    severity: str
    summary: str
    sources: list[str]
    recommended_action: str


def _safe_rel(path: Path, repo: Path) -> str:
    """Safe rel.

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        path: Filesystem path to the file or directory being processed.
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    # Protect the critical _safe_rel work so failures can be turned into a controlled
    # result or cleanup path.
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def _read(path: Path, *, max_bytes: int = 24000) -> str:
    """Read the requested operation.

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        path: Filesystem path to the file or directory being processed.
        max_bytes: Primary max bytes used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    try:
        return path.read_bytes()[:max_bytes].decode("utf-8", errors="replace")
    except OSError:
        return ""


def _slugify(text: str) -> str:
    """Slugify the requested operation.

    Args:
        text: Text content to inspect or rewrite.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


def _heading_title(head: str, path: Path) -> str:
    """Heading title.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        head: Primary head used by this step.
        path: Filesystem path to the file or directory being processed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    m = _TITLE_RE.search(head)
    if not m:
        return path.stem
    title = m.group(1).strip()
    title = re.sub(r"^\s*ADR[-._ ]?[A-Za-z0-9.\-_ ]+\s*:?\s*", "", title, flags=re.IGNORECASE)
    return title.strip() or path.stem


def _declared_id(head: str, path: Path) -> str:
    """Declared id.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        head: Primary head used by this step.
        path: Filesystem path to the file or directory being processed.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    m = _ID_RE.search(head[:1000])
    if m:
        raw = m.group(0).upper().replace("_", "-").replace(" ", "-").replace(".", "-")
        raw = re.sub(r"-{2,}", "-", raw)
        num = re.search(r"([0-9]{1,4})(?!.*[0-9])", raw)
        if num:
            return f"ADR-{int(num.group(1)):04d}"
        return raw
    stem = path.stem.upper().replace("_", "-")
    m2 = re.search(r"ADR[-._ ]?([0-9]{1,4})", stem, re.IGNORECASE)
    if m2:
        return f"ADR-{int(m2.group(1)):04d}"
    return f"ADR-{abs(hash(path.stem)) % 10000:04d}"


def _extract_sequence(declared_id: str) -> int:
    """Extract sequence.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        declared_id: Identifier used to select an existing run or
            record.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    m = re.search(r"([0-9]{1,4})(?!.*[0-9])", declared_id)
    if not m:
        return 0
    return int(m.group(1))


def _date_value(head: str) -> str:
    """Date value.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        head: Primary head used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    sample = head[:12000]
    m = _DATE_RE.search(sample)
    if m:
        return m.group(1).strip()
    lines = sample.splitlines()
    for idx, line in enumerate(lines):
        if line.strip().lower() != "## date":
            continue
        for nxt in lines[idx + 1 :]:
            stripped = nxt.strip()
            if not stripped:
                continue
            return stripped
    return ""


def iter_adr_markdown_paths(repo: Path) -> list[Path]:
    """Yield adr markdown paths.

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
    seen: set[str] = set()
    out: list[Path] = []
    for rel_dir in (ADR_CANONICAL_DIR, *ADR_LEGACY_DIRS):
        d = repo / rel_dir
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            if "template" in path.stem.lower():
                continue
            if not _ADR_FILE_RE.match(path.name):
                continue
            rel = _safe_rel(path, repo)
            if rel in seen:
                continue
            seen.add(rel)
            out.append(path)
    return out


def first_existing_relative(repo: Path, *rel_paths: str) -> str:
    """First existing relative.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.
        *rel_paths: Primary rel paths used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    repo = repo.resolve()
    for rel in rel_paths:
        if not rel:
            continue
        if (repo / rel).is_file():
            return rel.replace("\\", "/")
    return ""


def _family_for(path: Path, title: str, head: str) -> tuple[str, str]:
    """Family for.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        path: Filesystem path to the file or directory being processed.
        title: Primary title used by this step.
        head: Primary head used by this step.

    Returns:
        tuple[str, str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    title_low = f"{path.as_posix()} {title}".lower()
    body_low = head[:12000].lower()
    rules: list[tuple[tuple[str, ...], str, str, int]] = [
        (("runtime authority", "world-engine", "play service", "authoritative runtime"), "RUNTIME", "keywords: runtime authority", 0),
        (("backend session", "session surface", "quarantine", "session routes", "transitional runtime"), "BACKEND.SESSION", "keywords: backend session/quarantine", 0),
        (("scene identity", "guidance phase", "god of carnage", "goc"), "SLICE.GOC", "keywords: scene identity / goc", 0),
        (("writers' room", "writers room", "publishing flow", "publish governance"), "CONTENT.PUBLISHING", "keywords: writers-room/publishing", 0),
        (("rag", "retrieval", "retrieved context", "langgraph", "langchain"), "AI.RAG", "keywords: rag/retrieval", 0),
    ]
    scored: list[tuple[int, str, str]] = []
    for keywords, family, reason, _base in rules:
        title_hits = sum(1 for k in keywords if k in title_low)
        body_hits = sum(1 for k in keywords if k in body_low)
        score = title_hits * 5 + body_hits
        if score:
            scored.append((score, family, reason))
    if not scored:
        return "GENERAL", "default family"
    scored.sort(reverse=True)
    _score, family, reason = scored[0]
    return family, reason


def _proposed_canonical_id(family: str, seq: int) -> str:
    """Proposed canonical id.

    Args:
        family: Primary family used by this step.
        seq: Primary seq used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    return f"ADR.{family}.{seq:04d}"


def _proposed_canonical_path(family: str, seq: int, title: str) -> str:
    """Proposed canonical path.

    Args:
        family: Primary family used by this step.
        seq: Primary seq used by this step.
        title: Primary title used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    slug = _slugify(title)
    return f"{ADR_CANONICAL_DIR}/{_proposed_canonical_id(family, seq)}-{slug}.md"


def discover_adr_governance(repo: Path) -> dict:
    """Discover adr governance.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    repo = repo.resolve()
    records: list[ADRGovernanceRecord] = []
    by_declared_id: dict[str, list[str]] = {}
    by_proposed_path: dict[str, list[str]] = {}
    by_title_slug: dict[str, list[str]] = {}

    for path in iter_adr_markdown_paths(repo):
        rel = _safe_rel(path, repo)
        head = _read(path)
        title = _heading_title(head, path)
        declared_id = _declared_id(head, path)
        status = adr_declared_status(head)
        date = _date_value(head)
        family, family_reason = _family_for(path, title, head)
        seq = _extract_sequence(declared_id)
        proposed_path = _proposed_canonical_path(family, seq, title)
        supersedes = []
        raw_sup = adr_supersedes_line(head)
        if raw_sup:
            supersedes.append(raw_sup.strip())
        current_location_class = "canonical" if rel.startswith(f"{ADR_CANONICAL_DIR}/") else "legacy"

        issues: list[str] = []
        if current_location_class != "canonical":
            issues.append("not_in_canonical_adr_directory")
        if not date:
            issues.append("missing_explicit_date")
        if status == "unknown":
            issues.append("missing_explicit_status")
        if status == "superseded" and not raw_sup:
            issues.append("superseded_without_navigation")
        if status == "deprecated" and not raw_sup:
            issues.append("deprecated_without_navigation")

        record = ADRGovernanceRecord(
            current_path=rel,
            title=title,
            declared_id=declared_id,
            status=status,
            date=date,
            family=family,
            family_reason=family_reason,
            proposed_canonical_id=_proposed_canonical_id(family, seq),
            proposed_canonical_path=proposed_path,
            supersedes=supersedes,
            current_location_class=current_location_class,
            issues=issues,
            duplicate_keys=[],
        )
        records.append(record)
        by_declared_id.setdefault(declared_id, []).append(rel)
        by_proposed_path.setdefault(proposed_path, []).append(rel)
        by_title_slug.setdefault(_slugify(title), []).append(rel)

    findings: list[ADRGovernanceFinding] = []
    for declared_id, paths in sorted(by_declared_id.items()):
        if len(paths) < 2:
            continue
        findings.append(
            ADRGovernanceFinding(
                id=f"ADR-GOV-DUP-ID-{hashlib.sha256(declared_id.encode()).hexdigest()[:8]}",
                kind="duplicate_declared_id",
                severity="high",
                summary=f"Multiple ADR files declare the same id {declared_id}.",
                sources=paths,
                recommended_action="Keep one canonical ADR under docs/ADR and remove or redirect legacy duplicates.",
            )
        )
        for rec in records:
            if rec.current_path in paths:
                rec.duplicate_keys.append(f"declared_id:{declared_id}")

    for proposed_path, paths in sorted(by_proposed_path.items()):
        if len(paths) < 2:
            continue
        findings.append(
            ADRGovernanceFinding(
                id=f"ADR-GOV-DUP-CANON-{hashlib.sha256(proposed_path.encode()).hexdigest()[:8]}",
                kind="canonical_path_collision",
                severity="high",
                summary=f"More than one ADR resolves to the same proposed canonical path {proposed_path}.",
                sources=paths,
                recommended_action="Rename, merge, or deepen the family sequence so one canonical path maps to one decision record.",
            )
        )
        for rec in records:
            if rec.current_path in paths:
                rec.duplicate_keys.append(f"canonical_path:{proposed_path}")

    for title_slug, paths in sorted(by_title_slug.items()):
        if len(paths) < 2:
            continue
        findings.append(
            ADRGovernanceFinding(
                id=f"ADR-GOV-DUP-TITLE-{hashlib.sha256(title_slug.encode()).hexdigest()[:8]}",
                kind="similar_title_overlap",
                severity="medium",
                summary=f"Multiple ADR files share a materially similar normalized title {title_slug!r}.",
                sources=paths,
                recommended_action="Review whether these are true siblings, staged revisions, or stale duplicates.",
            )
        )
        for rec in records:
            if rec.current_path in paths:
                rec.duplicate_keys.append(f"title_slug:{title_slug}")

    for rec in records:
        if rec.current_location_class != "canonical":
            findings.append(
                ADRGovernanceFinding(
                    id=f"ADR-GOV-LEGACY-{hashlib.sha256(rec.current_path.encode()).hexdigest()[:8]}",
                    kind="legacy_adr_location",
                    severity="medium",
                    summary=f"ADR still lives outside the canonical docs/ADR directory: {rec.current_path}",
                    sources=[rec.current_path],
                    recommended_action=f"Migrate to {rec.proposed_canonical_path} and remove the legacy duplicate once links are updated.",
                )
            )
        for issue in rec.issues:
            if issue.startswith("missing_explicit_"):
                findings.append(
                    ADRGovernanceFinding(
                        id=f"ADR-GOV-META-{hashlib.sha256((rec.current_path + issue).encode()).hexdigest()[:8]}",
                        kind=issue,
                        severity="medium",
                        summary=f"ADR metadata gap in {rec.current_path}: {issue.replace('_', ' ')}.",
                        sources=[rec.current_path],
                        recommended_action="Add an explicit header field instead of relying on historical knowledge.",
                    )
                )
            elif issue.endswith("_without_navigation"):
                findings.append(
                    ADRGovernanceFinding(
                        id=f"ADR-GOV-SUP-{hashlib.sha256((rec.current_path + issue).encode()).hexdigest()[:8]}",
                        kind=issue,
                        severity="medium",
                        summary=f"ADR lifecycle says retired but no explicit supersession navigation is present: {rec.current_path}",
                        sources=[rec.current_path],
                        recommended_action="Add a Supersedes / Replaced by line or record the unresolved state explicitly.",
                    )
                )

    records_sorted = sorted(records, key=lambda r: (r.family, r.proposed_canonical_id, r.current_path))
    findings_sorted = sorted(findings, key=lambda f: (f.severity, f.kind, f.id))

    return {
        "canonical_dir": ADR_CANONICAL_DIR,
        "legacy_dirs": list(ADR_LEGACY_DIRS),
        "records": [serialise(r) for r in records_sorted],
        "findings": [serialise(f) for f in findings_sorted],
        "stats": {
            "n_adrs": len(records_sorted),
            "n_canonical_adrs": sum(1 for r in records_sorted if r.current_location_class == "canonical"),
            "n_legacy_adrs": sum(1 for r in records_sorted if r.current_location_class != "canonical"),
            "n_findings": len(findings_sorted),
        },
    }
