"""Hub cli for metrify.tools.

"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .ai_support import write_ai_pack
from .ledger import append_event, compute_cost, ensure_ledger, ingest_jsonl
from .models import UsageEvent
from .observify_bridge import write_observify_summary
from .pricing_catalog import catalog_payload
from .repo_paths import repo_root, suite_dir
from .reporting import build_summary, write_report_bundle


def _ledger_path(root: Path) -> Path:
    """Ledger path.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return suite_dir(root) / 'state' / 'ledger.jsonl'


def _print_help() -> None:
    """Print help.
    """
    print(
        'Metrify hub CLI\n\n'
        'Commands:\n'
        '  pricing     Show the bundled pricing catalog.\n'
        '  record      Record one usage event.\n'
        '  ingest      Import events from a JSONL file.\n'
        '  report      Compute reports from the internal ledger.\n'
        '  ai-pack     Write AI-friendly summaries and llms.txt.\n'
        '  full        Run report + ai-pack + observify summary.\n'
    )


def _record(args: argparse.Namespace) -> int:
    """Record the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = repo_root()
    ledger = _ledger_path(root)
    event = UsageEvent(
        timestamp_utc=args.timestamp_utc,
        suite=args.suite,
        run_id=args.run_id,
        model=args.model,
        service_tier=args.service_tier,
        input_tokens=args.input_tokens,
        cached_input_tokens=args.cached_input_tokens,
        output_tokens=args.output_tokens,
        reasoning_tokens=args.reasoning_tokens,
        cost_usd=args.cost_usd if args.cost_usd is not None else compute_cost(args.model, args.service_tier, args.input_tokens, args.cached_input_tokens, args.output_tokens),
        technique_tags=[item for item in (args.technique_tags or '').split(',') if item],
        utility_score=args.utility_score,
        resolved_findings=args.resolved_findings,
        notes=args.notes or '',
        source='manual',
    )
    append_event(ledger, event)
    # Branch on not args.quiet so _record only continues along the matching state path.
    if not args.quiet:
        print(json.dumps(event.to_dict(), indent=2))
    return 0


def _ingest(args: argparse.Namespace) -> int:
    """Ingest the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = repo_root()
    ledger = _ledger_path(root)
    count = ingest_jsonl(ledger, Path(args.source).resolve())
    if not args.quiet:
        print(json.dumps({'ok': True, 'imported': count, 'ledger_path': str(ledger)}, indent=2))
    return 0


def _report(args: argparse.Namespace) -> int:
    """Report the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = repo_root()
    ledger = _ledger_path(root)
    ensure_ledger(ledger)
    summary = build_summary(ledger)
    paths = write_report_bundle(root, summary)
    if not args.quiet:
        print(json.dumps({'ok': True, 'summary': summary, 'paths': paths}, indent=2))
    return 0


def _ai_pack(args: argparse.Namespace) -> int:
    """Ai pack.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = repo_root()
    ledger = _ledger_path(root)
    summary = build_summary(ledger)
    paths = write_ai_pack(root, summary)
    if not args.quiet:
        print(json.dumps({'ok': True, 'paths': paths}, indent=2))
    return 0


def _full(args: argparse.Namespace) -> int:
    """Full the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    root = repo_root()
    ledger = _ledger_path(root)
    ensure_ledger(ledger)
    summary = build_summary(ledger)
    paths = {}
    paths.update(write_report_bundle(root, summary))
    paths.update(write_ai_pack(root, summary))
    paths.update(write_observify_summary(root, summary))
    if not args.quiet:
        print(json.dumps({'ok': True, 'summary': summary, 'paths': paths}, indent=2))
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
    if not argv or argv[0] in ('-h', '--help', 'help'):
        _print_help()
        return 0
    parser = argparse.ArgumentParser(description='Metrify AI cost observability CLI')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('pricing', help='Print bundled pricing catalog')

    p_record = sub.add_parser('record', help='Record one usage event')
    p_record.add_argument('--timestamp-utc', default='1970-01-01T00:00:00+00:00')
    p_record.add_argument('--suite', required=True)
    p_record.add_argument('--run-id', required=True)
    p_record.add_argument('--model', required=True)
    p_record.add_argument('--service-tier', default='standard')
    p_record.add_argument('--input-tokens', type=int, default=0)
    p_record.add_argument('--cached-input-tokens', type=int, default=0)
    p_record.add_argument('--output-tokens', type=int, default=0)
    p_record.add_argument('--reasoning-tokens', type=int, default=0)
    p_record.add_argument('--cost-usd', type=float, default=None)
    p_record.add_argument('--technique-tags', default='')
    p_record.add_argument('--utility-score', type=float, default=None)
    p_record.add_argument('--resolved-findings', type=int, default=0)
    p_record.add_argument('--notes', default='')
    p_record.add_argument('--quiet', action='store_true')

    p_ingest = sub.add_parser('ingest', help='Import events from JSONL')
    p_ingest.add_argument('--source', required=True)
    p_ingest.add_argument('--quiet', action='store_true')

    p_report = sub.add_parser('report', help='Build cost reports')
    p_report.add_argument('--quiet', action='store_true')

    p_ai = sub.add_parser('ai-pack', help='Build AI context outputs')
    p_ai.add_argument('--quiet', action='store_true')

    p_full = sub.add_parser('full', help='Build all metrify outputs')
    p_full.add_argument('--quiet', action='store_true')

    ns = parser.parse_args(argv)
    if ns.command == 'pricing':
        print(json.dumps(catalog_payload(), indent=2))
        return 0
    if ns.command == 'record':
        return _record(ns)
    if ns.command == 'ingest':
        return _ingest(ns)
    if ns.command == 'report':
        return _report(ns)
    if ns.command == 'ai-pack':
        return _ai_pack(ns)
    if ns.command == 'full':
        return _full(ns)
    return 2
