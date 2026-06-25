from __future__ import annotations

import argparse
import time
from typing import Sequence

from fy_platform.ai.adapter_cli_helper import build_command_envelope, update_status_page
from fy_platform.ai.observability import ObservabilityStore
from fy_platform.tools.ai_suite_cli_emit import emit
from fy_platform.tools.ai_suite_cli_execution import execute_command
from fy_platform.tools.ai_suite_cli_registry import COMMAND_CHOICES, SUITES


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run autark fy suite adapters against an outward target repository.")
    parser.add_argument("suite", choices=sorted(SUITES))
    parser.add_argument("command", choices=COMMAND_CHOICES)
    parser.add_argument("--target-repo", default="")
    parser.add_argument("--query", default="")
    parser.add_argument("--audience", default="developer")
    parser.add_argument("--left-run-id", default="")
    parser.add_argument("--right-run-id", default="")
    parser.add_argument("--mode", default="standard")
    parser.add_argument("--finding-id", action="append", default=[])
    parser.add_argument("--apply-safe", action="store_true")
    parser.add_argument("--instruction", default="")
    parser.add_argument("--bundle", default="")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--strict", action="store_true")
    return parser


def _error_payload(args, exc: Exception) -> dict:
    return {
        "ok": False,
        "suite": args.suite,
        "reason": "command_exception",
        "error": str(exc),
        "exception_type": type(exc).__name__,
        "recovery_hints": [
            "Inspect workspace status and production readiness before retrying.",
            "Retry with --format markdown if you need a simpler summary while debugging.",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    adapter = SUITES[args.suite]()
    metrics = ObservabilityStore(adapter.root)
    started = time.perf_counter()
    try:
        out = execute_command(adapter, args)
    except Exception as exc:
        out = _error_payload(args, exc)
    out = update_status_page(adapter, args.command, out)
    emit(out, args.suite, args.command, args.format)
    envelope = build_command_envelope(args.suite, args.command, out)
    duration_ms = int((time.perf_counter() - started) * 1000)
    metrics.record_command(
        suite=args.suite,
        command=args.command,
        exit_code=envelope.exit_code,
        duration_ms=duration_ms,
        ok=envelope.ok,
        warnings_count=len(envelope.warnings),
        errors_count=len(envelope.errors),
        target_repo_id=(out.get("binding") or {}).get("target_repo_id") or out.get("target_repo_id"),
        active_profile=((out.get("active_strategy_profile") or {}).get("active_profile", "")),
    )
    metrics.record_route(suite=args.suite, command=args.command, route=out.get("route"))
    return envelope.exit_code
