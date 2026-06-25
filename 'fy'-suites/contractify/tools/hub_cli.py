"""Contractify hub CLI — discover, audit (discovery + drift), JSON reports."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from fy_platform.core.artifact_envelope import build_envelope, write_envelope
from fy_platform.core.manifest import load_manifest, suite_config
from contractify.tools.audit_pipeline import build_discover_payload, run_audit
from contractify.tools.investigation_suite import DEFAULT_ADR_INVESTIGATION_DIR, write_adr_investigation_suite
from contractify.tools.repo_paths import repo_root

SUITE_VERSION = "0.1.0"




def _configured_max_contracts(root: Path, manifest: dict | None, cli_value: int | None) -> int:
    """Resolve discovery ceiling from explicit CLI arg first, else
    manifest, else phase-1 default.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        root: Root directory used to resolve repository-local paths.
        manifest: Primary manifest used by this step.
        cli_value: Primary cli value used by this step.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    # Branch on cli_value is not None so _configured_max_contracts only continues along
    # the matching state path.
    if cli_value is not None:
        return int(cli_value)
    cfg = suite_config(manifest, "contractify")
    raw = cfg.get("max_contracts") if cfg else None
    # Branch on isinstance(raw, int) and raw > 0 so _configured_max_contracts only
    # continues along the matching state path.
    if isinstance(raw, int) and raw > 0:
        return raw
    return 30

def _base_findings_from_payload(payload: dict) -> tuple[list[dict], list[dict]]:
    """Project contractify-specific payload into suite-neutral
    finding/evidence summaries.

    The implementation iterates over intermediate items before it
    returns. Control flow branches on the parsed state rather than
    relying on one linear path.

    Args:
        payload: Structured data carried through this workflow.

    Returns:
        tuple[list[dict], list[dict]]:
            Structured payload describing the outcome of the
            operation.
    """
    findings: list[dict] = []
    evidence: list[dict] = []
    for d in payload.get("drift_findings", []):
        summary = str(d.get("summary", "")).strip()
        if not summary:
            continue
        findings.append(
            {
                "id": d.get("id", "unknown"),
                "suite": "contractify",
                "category": d.get("drift_class", "drift"),
                "severity": d.get("severity", "medium"),
                "confidence": float(d.get("confidence", 0.0)),
                "summary": summary,
                "scope": "repository",
                "references": d.get("evidence_sources", []),
            }
        )
        for src in d.get("evidence_sources", []):
            evidence.append({"kind": "source", "source_path": str(src), "deterministic": bool(d.get("deterministic", False))})
    for c in payload.get("conflicts", []):
        summary = str(c.get("summary", "")).strip()
        if not summary:
            continue
        findings.append(
            {
                "id": c.get("id", "unknown"),
                "suite": "contractify",
                "category": c.get("classification", "conflict"),
                "severity": c.get("severity", "medium"),
                "confidence": float(c.get("confidence", 0.0)),
                "summary": summary,
                "scope": "repository",
                "references": c.get("sources", []),
            }
        )
        for src in c.get("sources", []):
            evidence.append({"kind": "source", "source_path": str(src), "deterministic": not bool(c.get("requires_human_review", True))})
    return findings, evidence


def _write_deprecation_markdown(path: Path, deprecations: list[dict[str, str]]) -> None:
    """Write deprecation markdown.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        path: Filesystem path to the file or directory being processed.
        deprecations: Primary deprecations used by this step.
    """
    if not deprecations:
        return
    lines = ["# Deprecations", ""]
    for item in deprecations:
        lines.append(f"- `{item.get('id', 'unknown')}`: {item.get('message', '')}")
        repl = item.get("replacement", "").strip()
        if repl:
            lines.append(f"  - replacement: `{repl}`")
        target = item.get("removal_target", "").strip()
        if target:
            lines.append(f"  - removal_target: `{target}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_global_help() -> None:
    """Print global help.
    """
    print(
        "Contractify hub CLI\n\n"
        "Commands:\n"
        "  discover   Emit discovered contracts/projections/relations (JSON).\n"
        "  audit      Full audit: discovery + drift + conflicts + actionable units (JSON).\n"
        "  self-check Run audit scoped to fy-suite integration sanity (same as audit for now).\n"
        "  adr-investigation Refresh ADR investigation markdown and Mermaid maps.\n\n"
        "Examples:\n"
        "  python -m contractify.tools discover --json --out \"'fy'-suites/contractify/reports/_local_contract_discovery.json\"\n"
        "  python -m contractify.tools audit --json --out \"'fy'-suites/contractify/reports/_local_contract_audit.json\"\n"
        "  python -m contractify.tools adr-investigation --out-dir \"'fy'-suites/contractify/investigations/adr\"\n"
    )


def cmd_discover(args: argparse.Namespace) -> int:
    """Cmd discover.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = repo_root()
    manifest, _warnings = load_manifest(root)
    deprecations: list[dict[str, str]] = []
    if manifest is None:
        msg = "No fy-manifest.yaml detected; Contractify is running in legacy fallback mode."
        print(f"DEPRECATION: {msg}", file=sys.stderr)
        deprecations.append(
            {
                "id": "CONTRACTIFY-LEGACY-FALLBACK-001",
                "message": msg,
                "replacement": "Run fy-platform bootstrap and configure suites.contractify.openapi",
                "removal_target": "wave-2",
            }
        )
    max_contracts = _configured_max_contracts(root, manifest, args.max_contracts)
    payload = build_discover_payload(root, max_contracts=max_contracts)
    text = json.dumps(payload, indent=2)
    if args.out:
        out = (root / args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        out.write_text(text, encoding="utf-8")
        _write_deprecation_markdown(out.with_suffix(out.suffix + ".deprecations.md"), deprecations)
    if not args.quiet:
        print(text)
    if args.envelope_out:
        findings, evidence = _base_findings_from_payload(payload)
        env = build_envelope(
            suite="contractify",
            suite_version=SUITE_VERSION,
            payload=payload,
            manifest_ref="fy-manifest.yaml",
            deprecations=deprecations,
            findings=findings,
            evidence=evidence,
            stats=payload.get("stats", {}),
        )
        env_out = Path(args.envelope_out)
        if not env_out.is_absolute():
            env_out = root / env_out
        write_envelope(env_out, env)
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Cmd audit.

    This callable writes or records artifacts as part of its workflow.
    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = repo_root()
    manifest, _warnings = load_manifest(root)
    deprecations: list[dict[str, str]] = []
    if manifest is None:
        msg = "No fy-manifest.yaml detected; Contractify is running in legacy fallback mode."
        print(f"DEPRECATION: {msg}", file=sys.stderr)
        deprecations.append(
            {
                "id": "CONTRACTIFY-LEGACY-FALLBACK-001",
                "message": msg,
                "replacement": "Run fy-platform bootstrap and configure suites.contractify.openapi",
                "removal_target": "wave-2",
            }
        )
    max_contracts = _configured_max_contracts(root, manifest, args.max_contracts)
    payload = run_audit(root, max_contracts=max_contracts)
    text = json.dumps(payload, indent=2)
    if args.out:
        out = (root / args.out).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        out.write_text(text, encoding="utf-8")
        _write_deprecation_markdown(out.with_suffix(out.suffix + ".deprecations.md"), deprecations)
    if not args.quiet or not args.out:
        print(text)
    if args.envelope_out:
        findings, evidence = _base_findings_from_payload(payload)
        env = build_envelope(
            suite="contractify",
            suite_version=SUITE_VERSION,
            payload=payload,
            manifest_ref="fy-manifest.yaml",
            deprecations=deprecations,
            findings=findings,
            evidence=evidence,
            stats=payload.get("stats", {}),
        )
        env_out = Path(args.envelope_out)
        if not env_out.is_absolute():
            env_out = root / env_out
        write_envelope(env_out, env)
    return 0


def cmd_self_check(args: argparse.Namespace) -> int:
    """Narrow pass: reuse full audit (suite is small); consumers grep
    actionable_units.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    return cmd_audit(args)




def cmd_adr_investigation(args: argparse.Namespace) -> int:
    """Cmd adr investigation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = repo_root()
    bundle = write_adr_investigation_suite(root, out_dir_rel=args.out_dir)
    if not args.quiet:
        print(json.dumps(bundle, indent=2))
    return 0
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
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        _print_global_help()
        return 0

    parser = argparse.ArgumentParser(description="Contractify repository contract governance CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_disc = sub.add_parser("discover", help="Discovery-only JSON")
    p_disc.add_argument("--json", action="store_true", help="Emit JSON (always on for discover)")
    p_disc.add_argument("--out", default="", help="Repo-relative JSON output path")
    p_disc.add_argument("--max-contracts", type=int, default=None, help="Optional explicit discovery ceiling; defaults to suites.contractify.max_contracts or 30")
    p_disc.add_argument("--quiet", action="store_true", help="When --out set, skip stdout")
    p_disc.add_argument("--envelope-out", default="", help="Optional path for shared envelope output JSON")
    p_disc.set_defaults(func=cmd_discover)

    p_audit = sub.add_parser("audit", help="Discovery + drift + conflicts")
    p_audit.add_argument("--json", action="store_true", help="Emit JSON")
    p_audit.add_argument("--out", default="", help="Repo-relative JSON output path")
    p_audit.add_argument("--max-contracts", type=int, default=None, help="Optional explicit discovery ceiling; defaults to suites.contractify.max_contracts or 30")
    p_audit.add_argument("--quiet", action="store_true", help="When --out set, skip stdout")
    p_audit.add_argument("--envelope-out", default="", help="Optional path for shared envelope output JSON")
    p_audit.set_defaults(func=cmd_audit)

    p_self = sub.add_parser("self-check", help="Integration sanity audit")
    p_self.add_argument("--json", action="store_true", help="Emit JSON")
    p_self.add_argument("--out", default="")
    p_self.add_argument("--max-contracts", type=int, default=None, help="Optional explicit discovery ceiling; defaults to suites.contractify.max_contracts or 30")
    p_self.add_argument("--quiet", action="store_true")
    p_self.add_argument("--envelope-out", default="", help="Optional path for shared envelope output JSON")
    p_self.set_defaults(func=cmd_self_check)

    p_adr = sub.add_parser("adr-investigation", help="Refresh ADR investigation markdown + Mermaid maps")
    p_adr.add_argument("--out-dir", default=DEFAULT_ADR_INVESTIGATION_DIR, help="Repo-relative output directory for ADR investigation artifacts")
    p_adr.add_argument("--quiet", action="store_true", help="When set, skip stdout JSON bundle")
    p_adr.set_defaults(func=cmd_adr_investigation)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
