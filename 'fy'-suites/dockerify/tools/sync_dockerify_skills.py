#!/usr/bin/env python3
"""
Copy Dockerify hub skills into ``.cursor/skills/`` for Cursor project
skill discovery.

Canonical sources:
``'fy'-suites/dockerify/superpowers/<skill-name>/SKILL.md`` Targets:
.cursor/skills/<skill-name>/SKILL.md

Run from repository root after editing any skill under
``'fy'-suites/dockerify/superpowers/``:

python "./'fy'-suites/dockerify/tools/sync_dockerify_skills.py"

Optional: pass --check to exit 1 if .cursor copies differ (CI guard).
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

from fy_platform.core.project_resolver import resolve_project_root

DOCKERIFY_ROOT = Path(__file__).resolve().parents[1]
# Resolve repo root: use environment variable for explicit control, or traverse
# up to find pyproject.toml with [project] name = "world-of-shadows-hub"
REPO_ROOT = resolve_project_root(start=Path(__file__), marker_text="world-of-shadows-hub")
SRC_ROOT = DOCKERIFY_ROOT / "superpowers"
DST_ROOT = REPO_ROOT / ".cursor" / "skills"


def sync(*, check_only: bool) -> int:
    """Copy Dockerify router skills to ``.cursor/skills`` or verify they
    match.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        check_only: Whether to enable this optional behavior.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    # Branch on not SRC_ROOT.is_dir() so sync only continues along the matching state
    # path.
    if not SRC_ROOT.is_dir():
        print(f"Missing source: {SRC_ROOT}", file=sys.stderr)
        return 2
    skill_dirs = [p for p in SRC_ROOT.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()]
    # Branch on not skill_dirs so sync only continues along the matching state path.
    if not skill_dirs:
        print(f"No */SKILL.md under {SRC_ROOT}", file=sys.stderr)
        return 2

    mismatches: list[str] = []
    # Process src_dir one item at a time so sync applies the same rule across the full
    # collection.
    for src_dir in sorted(skill_dirs, key=lambda p: p.name):
        name = src_dir.name
        src = src_dir / "SKILL.md"
        dst = DST_ROOT / name / "SKILL.md"
        # Branch on check_only so sync only continues along the matching state path.
        if check_only:
            # Branch on not dst.is_file() so sync only continues along the matching
            # state path.
            if not dst.is_file():
                mismatches.append(f"missing {dst.relative_to(REPO_ROOT)}")
            # Branch on not filecmp.cmp(src, dst, shallow=False) so sync only continues
            # along the matching state path.
            elif not filecmp.cmp(src, dst, shallow=False):
                mismatches.append(f"differ {dst.relative_to(REPO_ROOT)}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"synced {name} -> {dst.relative_to(REPO_ROOT)}")

    # Branch on check_only so sync only continues along the matching state path.
    if check_only:
        # Branch on mismatches so sync only continues along the matching state path.
        if mismatches:
            print("Dockerify skill sync drift:\n" + "\n".join(mismatches), file=sys.stderr)
            return 1
        print("OK: .cursor/skills matches 'fy'-suites/dockerify/superpowers")
        return 0
    return 0


def main() -> int:
    """CLI entry for skill sync / drift check.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if copies are missing or differ from canonical SKILL.md files.",
    )
    args = ap.parse_args()
    return sync(check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
