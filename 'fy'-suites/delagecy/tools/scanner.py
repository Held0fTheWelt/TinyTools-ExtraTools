"""Legacy surface scanner for delagecy."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_PATTERNS = (
    r"\blegacy\b",
    r"\blegacy_",
    r"_legacy\b",
    r"\bdeprecated\b",
    r"\bcompatibility\b",
)

TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_PARTS = {
    ".claude",
    ".cursor",
    ".idea",
    ".project",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".pytest_tmp",
    ".ruff_cache",
    ".scripts",
    ".state_tmp",
    ".tmp_goc_pdf",
    ".venv",
    ".vscode",
    ".worktrees",
    ".wos",
    "__pycache__",
    ".fydata",
    "generated",
    "htmlcov",
    "imports",
    "node_modules",
    "normalized",
    "reports",
    "site-packages",
    "tmp",
    "tmp_coauth_dbg",
    "venv",
}


@dataclass(frozen=True)
class LegacyHit:
    """One scanner hit."""

    fingerprint: str
    path: str
    line: int
    kind: str
    pattern: str
    text: str

    def to_dict(self) -> dict[str, object]:
        """Convert hit to JSON-safe data."""
        return {
            "fingerprint": self.fingerprint,
            "path": self.path,
            "line": self.line,
            "kind": self.kind,
            "pattern": self.pattern,
            "text": self.text,
        }


def classify_path(path: Path) -> str:
    """Classify the surface where a hit was found."""
    parts = set(path.parts)
    suffix = path.suffix.lower()
    if "templates" in parts or suffix in {".html", ".css"}:
        return "ui"
    if "static" in parts or suffix in {".js", ".ts", ".tsx"}:
        return "ui"
    if "tests" in parts or path.name.startswith("test_"):
        return "test"
    if "docs" in parts or suffix == ".md":
        return "docs"
    if suffix == ".py":
        return "code"
    if suffix in {".json", ".yaml", ".yml", ".toml"}:
        return "config"
    return "unknown"


def should_scan(path: Path) -> bool:
    """Return whether a file should be scanned."""
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if path.name == "CHANGELOG.md":
        return False
    if path.name.startswith("audit_") and path.suffix.lower() in {".json", ".md"}:
        return False
    if "delagecy" in path.parts and "reports" in path.parts:
        return False
    if "delagecy" in path.parts and path.name in {
        "delagecy_registry.json",
        "legacy_removal_tracker.md",
    }:
        return False
    return path.is_file() and path.suffix.lower() in TEXT_SUFFIXES


def fingerprint_for(path: str, line: int, pattern: str, text: str) -> str:
    """Build a stable finding fingerprint."""
    body = f"{path}:{line}:{pattern}:{text.strip().lower()}".encode("utf-8")
    return hashlib.sha256(body).hexdigest()[:16]


def iter_files(root: Path, include: Iterable[str] | None = None) -> Iterable[Path]:
    """Yield candidate files."""
    includes = [root / item for item in include or ()]
    bases = includes or [root]
    for base in bases:
        if base.is_file():
            if should_scan(base):
                yield base
            continue
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            current = Path(dirpath)
            dirnames[:] = [
                name
                for name in dirnames
                if name not in EXCLUDED_PARTS
                and not (name == "reports" and "delagecy" in (current / name).parts)
                and not (name == "var" and current.name == "backend")
                and not (name == "archive" and current.name == "docs")
                and not (name == "MVPs" and current.name == "docs")
                and not (name == "source" and current.name == "world-engine")
            ]
            for filename in filenames:
                path = current / filename
                if should_scan(path):
                    yield path


def scan(root: Path, *, include: Iterable[str] | None = None, patterns: Iterable[str] | None = None) -> dict[str, object]:
    """Scan for legacy hits."""
    compiled = [(pattern, re.compile(pattern, re.IGNORECASE)) for pattern in (patterns or DEFAULT_PATTERNS)]
    hits: list[LegacyHit] = []
    scanned = 0
    for path in iter_files(root, include):
        scanned += 1
        rel = path.resolve().relative_to(root.resolve()).as_posix()
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line in enumerate(lines, start=1):
            for pattern, regex in compiled:
                if not regex.search(line):
                    continue
                text = line.strip()[:240]
                hits.append(
                    LegacyHit(
                        fingerprint=fingerprint_for(rel, lineno, pattern, text),
                        path=rel,
                        line=lineno,
                        kind=classify_path(path),
                        pattern=pattern,
                        text=text,
                    )
                )
                break
    return {
        "schema_version": "delagecy.scan.v1",
        "scanned_file_count": scanned,
        "hit_count": len(hits),
        "hits": [hit.to_dict() for hit in hits],
    }
