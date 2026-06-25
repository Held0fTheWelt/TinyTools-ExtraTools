"""Minimal CLI for Diagnosta."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from diagnosta.adapter.service import DiagnostaAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="diagnosta")
    sub = parser.add_subparsers(dest="command", required=False)
    for name in [
        "inspect",
        "audit",
        "prepare-context-pack",
        "compare-runs",
        "triage",
        "diagnose",
        "readiness-case",
        "blocker-graph",
    ]:
        cmd = sub.add_parser(name)
        if name in {"audit", "diagnose", "readiness-case", "blocker-graph"}:
            cmd.add_argument("target", nargs="?", default=".")
        elif name == "compare-runs":
            cmd.add_argument("left_run_id")
            cmd.add_argument("right_run_id")
        else:
            cmd.add_argument("query", nargs="?", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    adapter = DiagnostaAdapter(root=Path.cwd())
    command = args.command or "inspect"
    if command in {"audit", "diagnose", "readiness-case", "blocker-graph"}:
        payload = adapter.audit(args.target)
    elif command == "compare-runs":
        payload = adapter.compare_runs(args.left_run_id, args.right_run_id)
    elif command == "prepare-context-pack":
        payload = adapter.prepare_context_pack(args.query or "diagnosta")
    elif command == "triage":
        payload = adapter.triage(args.query)
    else:
        payload = adapter.inspect(args.query)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get("ok", True) else 1
