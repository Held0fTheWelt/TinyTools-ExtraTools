#!/usr/bin/env python3
"""
Validate repo-relative paths referenced from Despaghettify hub skills
markdown.

Scans ``<hub>/superpowers/**/*.md`` for: - Markdown link targets
``[text](path)`` / ``![alt](path)`` (skips http(s), mailto, bare
fragments) - Inline repo paths in backticks:
``'fy'-suites/despaghettify/...``, hub-relative alias
``despaghettify/...``, or ``tools/...`` with a file suffix

Run from repository root: python
"./'fy'-suites/despaghettify/tools/validate_despag_skill_paths.py"

Exit 1 if any path is missing. Optional CI / pre-push hook.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_tools = Path(__file__).resolve().parent
_hub = _tools.parent
_grand = _hub.parent
_ins = str(_grand if _grand.name == "'fy'-suites" else _hub.parent)
if _ins not in sys.path:
    sys.path.insert(0, _ins)

from despaghettify.tools.repo_paths import FY_SUITES_DIRNAME, despag_hub_dir, repo_root

ROOT = repo_root()
SCAN_ROOT = despag_hub_dir(ROOT) / "superpowers"


def _resolve_repo_relpath(raw: str) -> Path:
    """Resolve ``despaghettify/…`` backticks to
    ``'fy'-suites/despaghettify/…`` when the repo-root path is absent.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        raw: Primary raw used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    p = (ROOT / raw).resolve()
    # Branch on p.exists() so _resolve_repo_relpath only continues along the matching
    # state path.
    if p.exists():
        return p
    # Branch on raw == 'despaghettify' or raw.startswith('des... so
    # _resolve_repo_relpath only continues along the matching state path.
    if raw == "despaghettify" or raw.startswith("despaghettify/"):
        alt = (ROOT / FY_SUITES_DIRNAME / raw).resolve()
        # Branch on alt.exists() so _resolve_repo_relpath only continues along the
        # matching state path.
        if alt.exists():
            return alt
    return p

# Require a proper ``[...](...)`` / ``![...](...)`` so prose like `` `](...)` `` in VALIDATION.md
# does not yield a bogus ``...`` path target.
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
# Repo-like path inside backticks (file or trailing slash dir)
BACKTICK_REPO_RE = re.compile(
    r"`((?:'fy'-suites/despaghettify|despaghettify|despaghettify/tools|tools)/[a-zA-Z0-9_./-]+(?:\.(?:md|py|yaml|yml)|/))`"
)


def _should_skip_target(raw: str) -> bool:
    """Return whether skip target.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        raw: Primary raw used by this step.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    t = raw.strip()
    if not t or t.startswith("#"):
        return True
    if t.startswith(("http://", "https://", "mailto:", "vscode:", "data:")):
        return True
    return False


def _resolve(base_file: Path, target: str) -> Path:
    """Resolve the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        base_file: Filesystem path to the file or directory being
            processed.
        target: Primary target used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    t = target.strip().split("#", 1)[0].strip()
    p = Path(t)
    if p.is_absolute():
        return p
    return (base_file.parent / t).resolve()


def _under_repo(path: Path) -> bool:
    """Under repo.

    Exceptions are normalized inside the implementation before control
    returns to callers.

    Args:
        path: Filesystem path to the file or directory being processed.

    Returns:
        bool:
            Boolean outcome for the requested condition
            check.
    """
    try:
        path.relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def collect_paths(md_path: Path, text: str) -> list[tuple[str, str]]:
    """Return list of (kind, path_str_for_display) needing validation.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        md_path: Filesystem path to the file or directory being
            processed.
        text: Text content to inspect or rewrite.

    Returns:
        list[tuple[str, str]]:
            Collection produced from the parsed or
            accumulated input data.
    """
    out: list[tuple[str, str]] = []
    for m in LINK_RE.finditer(text):
        raw = m.group(1)
        if _should_skip_target(raw):
            continue
        resolved = _resolve(md_path, raw)
        if not _under_repo(resolved):
            out.append(("link_escape", f"{md_path.relative_to(ROOT)}: {raw!r} -> {resolved}"))
            continue
        out.append(("link", str(resolved)))
    for m in BACKTICK_REPO_RE.finditer(text):
        raw = m.group(1).rstrip("/")
        if not raw:
            continue
        resolved = _resolve_repo_relpath(raw)
        if not _under_repo(resolved):
            out.append(("backtick_escape", f"{md_path.relative_to(ROOT)}: {raw!r}"))
            continue
        out.append(("backtick", str(resolved)))
    return out


def main() -> int:
    """Implement ``main`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    if not SCAN_ROOT.is_dir():
        print(f"Missing {SCAN_ROOT}", file=sys.stderr)
        return 2

    errors: list[str] = []
    scanned = 0
    for md_path in sorted(SCAN_ROOT.rglob("*.md")):
        scanned += 1
        text = md_path.read_text(encoding="utf-8", errors="replace")
        for kind, ref in collect_paths(md_path, text):
            if kind.endswith("_escape"):
                errors.append(ref)
                continue
            p = Path(ref)
            if not p.exists():
                rel = md_path.relative_to(ROOT)
                errors.append(f"{rel}: missing {kind} target {p.relative_to(ROOT)}")

    if errors:
        print("Despaghettify skill path validation failed:\n", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print(f"OK: validated paths in {scanned} markdown file(s) under {SCAN_ROOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
