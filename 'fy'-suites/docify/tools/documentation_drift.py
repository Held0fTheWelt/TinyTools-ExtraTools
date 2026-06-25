"""
Heuristic documentation drift hints from changed repository paths.

This module does **not** perform semantic analysis of diffs. It
classifies **paths** (and optional ``git diff`` name lists) into coarse
**change classes** and suggests **documentation layers** that often need
a follow-up pass after similar edits.

House assumptions are documented in
``DOCUMENTATION_QUALITY_STANDARD.md`` at the Docify hub root. Treat
every inference as **advisory** evidence for humans and agents, not as
proof of missing documentation.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from docify.tools.repo_paths import docify_hub_rel_posix, repo_root


@dataclass(frozen=True)
class DriftHint:
    """Single-file drift classification output."""

    path: str
    change_classes: tuple[str, ...]
    inventory_categories: tuple[str, ...]
    recommended_documentation_layers: tuple[str, ...]
    note: str


def _uniq(seq: Iterable[str]) -> tuple[str, ...]:
    """Uniq the requested operation.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        seq: Primary seq used by this step.

    Returns:
        tuple[str, ...]:
            Collection produced from the parsed or
            accumulated input data.
    """
    seen: set[str] = set()
    out: list[str] = []
    # Process item one item at a time so _uniq applies the same rule across the full
    # collection.
    for item in seq:
        # Branch on not item or item in seen so _uniq only continues along the matching
        # state path.
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return tuple(out)


def classify_repository_path(rel_posix: str) -> DriftHint:
    """Classify one repo-relative POSIX path and return drift hints.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        rel_posix: Primary rel posix used by this step.

    Returns:
        DriftHint:
            Value produced by this callable as
            ``DriftHint``.
    """
    lower = rel_posix.lower()
    parts = rel_posix.split("/")

    change_classes: list[str] = []
    inventory: list[str] = []
    layers: list[str] = []
    notes: list[str] = []

    if not rel_posix.endswith((".py", ".md", ".yml", ".yaml", ".toml", ".json")):
        notes.append("non_primary_source_suffix")

    if "migrations" in parts:
        change_classes.append("database_migration")
        inventory.append("operational_runbook_drift")
        layers.extend(["OPERATIONAL_RUNBOOK", "CHANGELOG_OR_RELEASE_NOTES"])

    if any(
        token in lower
        for token in (
            "docker-compose",
            "compose.yml",
            "compose.yaml",
            "dockerfile",
            "k8s",
            "kubernetes",
            "helm",
        )
    ):
        change_classes.append("container_or_deploy_layout")
        inventory.append("operational_runbook_drift")
        layers.extend(["OPERATIONAL_RUNBOOK", "README_OR_FEATURE_DOC"])

    if any(
        name in lower
        for name in (
            "config.py",
            "settings.py",
            "runtime_config",
            "pyproject.toml",
            ".env.example",
            "application.yml",
            "appsettings",
        )
    ) or "config" in parts:
        change_classes.append("config_or_settings")
        inventory.append("stale_documentation_after_behavior_change")
        layers.extend(["LOCAL_DOCSTRINGS", "README_OR_FEATURE_DOC", "OPERATIONAL_RUNBOOK"])

    if any(
        frag in lower
        for frag in (
            "routes",
            "_routes.py",
            "router",
            "/api/",
            "blueprint",
            "fastapi",
            "flask",
        )
    ):
        change_classes.append("http_or_public_api_surface")
        inventory.append("missing_or_stale_public_contract_docs")
        layers.extend(
            [
                "LOCAL_DOCSTRINGS",
                "README_OR_FEATURE_DOC",
                "ARCHITECTURE_DOC",
                "OPENAPI_OR_API_CATALOG",
            ]
        )

    if any(lower.endswith(suffix) for suffix in ("cli.py", "hub_cli.py", "__main__.py")):
        change_classes.append("cli_entrypoint")
        inventory.append("tool_inventory_readme_mismatch_risk")
        layers.extend(["SUITE_README_OR_TOOL_DOCS", "LOCAL_DOCSTRINGS"])

    if "governance" in parts or "policy" in parts:
        change_classes.append("policy_or_governance_logic")
        inventory.append("unreadable_internal_logic_or_policy_docs")
        layers.extend(["LOCAL_DOCSTRINGS", "ARCHITECTURE_DOC", "OPERATIONAL_RUNBOOK"])

    if rel_posix.startswith("docs/") or "/docs/" in rel_posix:
        change_classes.append("repository_markdown_doc")
        inventory.append("readme_or_architecture_doc_drift")
        layers.extend(["REPOSITORY_MARKDOWN"])

    if "tests" in parts and rel_posix.endswith(".py"):
        change_classes.append("tests_python")
        inventory.append("test_docstring_noise_risk")
        layers.extend(["LOCAL_DOCSTRINGS_LIGHT_TOUCH"])

    if rel_posix.startswith("'fy'-suites/docify/"):
        change_classes.append("docify_suite_self")
        inventory.append("suite_self_documentation_gap")
        layers.extend(["SUITE_README_OR_TOOL_DOCS", "LOCAL_DOCSTRINGS"])

    if not change_classes:
        change_classes.append("general_code_or_config")
        inventory.append("stale_documentation_after_behavior_change")
        layers.append("LOCAL_DOCSTRINGS")

    note = "; ".join(notes) if notes else "heuristic_path_only"

    return DriftHint(
        path=rel_posix,
        change_classes=_uniq(change_classes),
        inventory_categories=_uniq(inventory),
        recommended_documentation_layers=_uniq(layers) or ("LOCAL_DOCSTRINGS",),
        note=note,
    )


def changed_paths_from_git(*, repo: Path, base: str, head: str) -> list[str]:
    """Return changed repo-relative POSIX paths from ``git diff
    --name-only``.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.

    Args:
        repo: Primary repo used by this step.
        base: Primary base used by this step.
        head: Primary head used by this step.

    Returns:
        list[str]:
            Collection produced from the parsed or
            accumulated input data.
    """
    cmd = [
        "git",
        "-C",
        str(repo),
        "diff",
        "--name-only",
        f"{base}...{head}",
    ]
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        msg = "git executable not found on PATH"
        raise RuntimeError(msg) from exc
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        msg = f"git diff failed ({proc.returncode}): {err}"
        raise RuntimeError(msg)
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines:
        p = (repo / ln).resolve()
        try:
            rel = p.relative_to(repo.resolve()).as_posix()
        except ValueError:
            continue
        out.append(rel)
    return sorted(set(out))


def infer_hints(paths: Sequence[str]) -> list[DriftHint]:
    """Return drift hints for each path (deduplicated, stable sort).

    Args:
        paths: Primary paths used by this step.

    Returns:
        list[DriftHint]:
            Collection produced from the parsed or
            accumulated input data.
    """
    unique = sorted({p.replace("\\", "/").strip() for p in paths if p.strip()})
    return [classify_repository_path(p) for p in unique]


def _default_git_base(repo: Path) -> str:
    """Pick a reasonable default base ref without requiring network access.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    for candidate in ("origin/main", "origin/master", "main", "master"):
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", candidate],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and (proc.stdout or "").strip():
            return candidate
    return "HEAD~1"


def emit_json_payload(
    *,
    repo: Path,
    base: str,
    head: str,
    hints: Sequence[DriftHint],
) -> str:
    """Serialize drift output for reports and CI artifacts.

    Args:
        repo: Primary repo used by this step.
        base: Primary base used by this step.
        head: Primary head used by this step.
        hints: Primary hints used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    payload = {
        "repo_root": str(repo),
        "git": {"base": base, "head": head},
        "summary": {
            "files": len(hints),
            "change_classes": sorted({c for h in hints for c in h.change_classes}),
        },
        "files": [asdict(h) for h in hints],
        "disclaimer": (
            "Heuristic path-only classification; verify with code review and the suite "
            "documentation standard. Not semantic drift detection."
        ),
    }
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def drift_cli_main(argv: Sequence[str] | None = None) -> int:
    """CLI entry for ``docify drift``.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    parser = argparse.ArgumentParser(
        description="Heuristic documentation follow-up hints from git-changed paths.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (defaults via docify.tools.repo_paths.repo_root()).",
    )
    parser.add_argument(
        "--base",
        default="",
        help="Git base ref for diff (default: first existing among origin/main, main, HEAD~1).",
    )
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Git head ref for diff (default: HEAD).",
    )
    parser.add_argument(
        "--paths-file",
        type=Path,
        default=None,
        help="Optional newline-separated repo-relative paths instead of git diff.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write JSON output to this file (implies --json).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = (args.repo_root or repo_root()).resolve()
    if not (root / "pyproject.toml").is_file():
        print(f"Not a repository root: {root}", file=sys.stderr)
        return 2

    if args.paths_file is not None:
        if not args.paths_file.is_file():
            print(f"Missing --paths-file: {args.paths_file}", file=sys.stderr)
            return 2
        raw_paths = [
            ln.strip()
            for ln in args.paths_file.read_text(encoding="utf-8", errors="replace").splitlines()
            if ln.strip()
        ]
        base = "paths-file"
        head = "paths-file"
    else:
        base = (args.base or "").strip() or _default_git_base(root)
        head = (args.head or "").strip() or "HEAD"
        try:
            raw_paths = changed_paths_from_git(repo=root, base=base, head=head)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 3

    hints = infer_hints(raw_paths)

    if args.out is not None:
        args.json = True

    if args.json:
        text = emit_json_payload(repo=root, base=base, head=head, hints=hints)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            args.out.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    hub = docify_hub_rel_posix(root)
    print(f"Repo root: {root}")
    print(f"Docify hub: {hub}")
    print(f"Git diff: {base}...{head}  ({len(hints)} paths)")
    for hint in hints:
        print(f"- {hint.path}")
        print(f"    change_classes: {', '.join(hint.change_classes)}")
        print(f"    inventory:      {', '.join(hint.inventory_categories)}")
        print(f"    layers:         {', '.join(hint.recommended_documentation_layers)}")
        print(f"    note:           {hint.note}")
    return 0
