#!/usr/bin/env python3
"""
Postmanify — generate Postman collections from OpenAPI (master + per-tag
sub-suites).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from fy_platform.core.artifact_envelope import build_envelope, write_envelope
from fy_platform.core.manifest import load_manifest, suite_config
from postmanify.tools.openapi_postman import build_collections, load_openapi_dict, write_json
from postmanify.tools.repo_paths import repo_root

SUITE_VERSION = "0.1.0"


def _default_openapi(repo: Path) -> Path:
    """Default openapi.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        repo: Primary repo used by this step.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    # Read and normalize the input data before _default_openapi branches on or
    # transforms it further.
    manifest, _warnings = load_manifest(repo)
    cfg = suite_config(manifest, "postmanify")
    rel = str(cfg.get("openapi", "")).strip() if cfg else ""
    # Branch on rel so _default_openapi only continues along the matching state path.
    if rel:
        return (repo / rel).resolve()
    return repo / "docs" / "api" / "openapi.yaml"


def _default_out_master(repo: Path) -> str:
    """Default out master.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    manifest, _warnings = load_manifest(repo)
    cfg = suite_config(manifest, "postmanify")
    rel = str(cfg.get("out_master", "")).strip() if cfg else ""
    return rel or "postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json"


def _default_suites_dir(repo: Path) -> str:
    """Default suites dir.

    Args:
        repo: Primary repo used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    manifest, _warnings = load_manifest(repo)
    cfg = suite_config(manifest, "postmanify")
    rel = str(cfg.get("suites_dir", "")).strip() if cfg else ""
    return rel or "postman/suites"


def _cmd_plan(args: argparse.Namespace) -> int:
    """Cmd plan.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = repo_root()
    openapi_path = Path(args.openapi).resolve() if args.openapi else _default_openapi(repo)
    if not openapi_path.is_file():
        print(f"Missing OpenAPI file: {openapi_path}", file=sys.stderr)
        return 2
    spec = load_openapi_dict(openapi_path)
    master, subs = build_collections(spec, backend_api_prefix=args.backend_api_prefix.strip() or "/api/v1")
    n_folders = len(master.get("item", []))
    n_reqs = sum(len(f.get("item", [])) for f in master.get("item", []) if isinstance(f, dict))
    report = {"openapi": str(openapi_path), "tag_folders": n_folders, "requests": n_reqs, "sub_suites": len(subs)}
    print(json.dumps(report, indent=2))
    if args.envelope_out:
        env = build_envelope(
            suite="postmanify",
            suite_version=SUITE_VERSION,
            payload=report,
            manifest_ref="fy-manifest.yaml",
            findings=[],
            evidence=[{"kind": "openapi", "source_path": str(openapi_path.relative_to(repo)), "deterministic": True}],
            stats={"requests": n_reqs, "tag_folders": n_folders, "sub_suites": len(subs)},
        )
        out = Path(args.envelope_out)
        if not out.is_absolute():
            out = repo / out
        write_envelope(out, env)
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    """Cmd generate.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    repo = repo_root()
    openapi_path = Path(args.openapi).resolve() if args.openapi else _default_openapi(repo)
    if not openapi_path.is_file():
        print(f"Missing OpenAPI file: {openapi_path}", file=sys.stderr)
        return 2

    spec = load_openapi_dict(openapi_path)
    master, subs = build_collections(spec, backend_api_prefix=args.backend_api_prefix.strip() or "/api/v1")

    out_master = (repo / args.out_master).resolve()
    suites_dir = (repo / args.suites_dir).resolve()

    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(out_master, master)
    for slug, coll in subs.items():
        write_json(suites_dir / f"WorldOfShadows_Suite_{slug}.postman_collection.json", coll)

    raw = openapi_path.read_bytes()
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "openapi_path": str(openapi_path.relative_to(repo)),
        "openapi_sha256": hashlib.sha256(raw).hexdigest(),
        "backend_api_prefix": args.backend_api_prefix.strip() or "/api/v1",
        "master_collection": str(out_master.relative_to(repo)),
        "suites_dir": str(suites_dir.relative_to(repo)),
        "sub_suite_files": sorted(f"WorldOfShadows_Suite_{slug}.postman_collection.json" for slug in subs),
    }
    # Persist the structured JSON representation so automated tooling can consume the
    # result without reparsing prose.
    write_json(suites_dir.parent / "postmanify-manifest.json", manifest)

    report = {"ok": True, "manifest": str((suites_dir.parent / "postmanify-manifest.json").relative_to(repo))}
    deprecations: list[dict[str, str]] = []
    if "WorldOfShadows_" in args.out_master:
        msg = "Legacy default collection naming detected; prefer manifest-driven generic naming."
        print(f"DEPRECATION: {msg}", file=sys.stderr)
        deprecations.append(
            {
                "id": "POSTMANIFY-LEGACY-NAME-001",
                "message": msg,
                "replacement": "Configure suites.postmanify.out_master in fy-manifest.yaml",
                "removal_target": "wave-2",
            }
        )
    print(json.dumps(report, indent=2))
    if args.envelope_out:
        env = build_envelope(
            suite="postmanify",
            suite_version=SUITE_VERSION,
            payload=report | {"postmanify_manifest": manifest},
            manifest_ref="fy-manifest.yaml",
            deprecations=deprecations,
            findings=[],
            evidence=[{"kind": "manifest", "source_path": "postman/postmanify-manifest.json", "deterministic": True}],
            stats={"sub_suites": len(subs)},
        )
        out = Path(args.envelope_out)
        if not out.is_absolute():
            out = repo / out
        write_envelope(out, env)
    if deprecations:
        dep_path = suites_dir.parent / "postmanify.deprecations.md"
        dep_lines = ["# Deprecations", ""]
        for item in deprecations:
            dep_lines.append(f"- `{item['id']}`: {item['message']}")
            dep_lines.append(f"  - replacement: `{item['replacement']}`")
            dep_lines.append(f"  - removal_target: `{item['removal_target']}`")
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        dep_path.write_text("\n".join(dep_lines) + "\n", encoding="utf-8")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Implement ``main`` for the surrounding module workflow.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    repo = repo_root()
    ap = argparse.ArgumentParser(
        description="Generate Postman Collection v2.1 JSON from OpenAPI (master tree + per-tag sub-suites).",
    )
    ap.add_argument(
        "--openapi",
        default="",
        help=f"OpenAPI 3 YAML path (default: { _default_openapi(repo).as_posix() } relative to repo).",
    )
    ap.add_argument(
        "--backend-api-prefix",
        default="/api/v1",
        help="Path prefix stripped when building {{backendBaseUrl}}{{backendApiPrefix}}/… URLs.",
    )

    sub = ap.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Print counts only (no writes).")
    p_plan.add_argument(
        "--envelope-out",
        default="",
        help="Optional path for versioned shared envelope JSON (repo-relative).",
    )
    p_plan.set_defaults(func=_cmd_plan)

    p_gen = sub.add_parser("generate", help="Write master collection, per-tag suites, and manifest under postman/.")
    p_gen.add_argument(
        "--out-master",
        default=_default_out_master(repo),
        help="Repo-relative output path for the combined collection.",
    )
    p_gen.add_argument(
        "--suites-dir",
        default=_default_suites_dir(repo),
        help="Repo-relative directory for per-tag `WorldOfShadows_Suite_<tag>.postman_collection.json` files.",
    )
    p_gen.add_argument(
        "--envelope-out",
        default="",
        help="Optional path for versioned shared envelope JSON (repo-relative).",
    )
    p_gen.set_defaults(func=_cmd_generate)

    args = ap.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
