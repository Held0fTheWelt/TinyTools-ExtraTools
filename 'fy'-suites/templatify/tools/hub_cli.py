"""Hub cli for templatify.tools.

"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from fy_platform.ai.workspace import workspace_root
from templatify.tools.template_drift import scan_generated_drift
from templatify.tools.template_inventory import inspect_areas
from templatify.tools.template_registry import discover_templates
from templatify.tools.template_render import render_with_header
from templatify.tools.template_validator import validate_templates
from templatify.tools.templating_engine import apply_plan, build_plan


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line entry point.

    This callable writes or records artifacts as part of its workflow.
    The implementation iterates over intermediate items before it
    returns.

    Args:
        argv: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    # Read and normalize the input data before main branches on or transforms it
    # further.
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description='Templatify template governance CLI')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list-templates')
    sub.add_parser('validate')
    sub.add_parser('inspect')
    # Read and normalize the input data before main branches on or transforms it
    # further.
    p_render = sub.add_parser('render')
    p_render.add_argument('--family', required=True)
    p_render.add_argument('--name', required=True)
    p_render.add_argument('--var', action='append', default=[])
    p_render.add_argument('--out', default='')
    # Read and normalize the input data before main branches on or transforms it
    # further.
    p_drift = sub.add_parser('check-drift')
    p_drift.add_argument('--generated-dir', required=True)
    # Read and normalize the input data before main branches on or transforms it
    # further.
    p_plan = sub.add_parser('plan')
    p_plan.add_argument('--source-dir', required=True)
    p_plan.add_argument('--areas', nargs='*', default=[])
    p_plan.add_argument('--out', default='templatify/reports/templatify_plan.json')
    p_plan.add_argument('--md-out', default='templatify/reports/templatify_plan_report.md')
    p_plan.add_argument('--quiet', action='store_true')
    # Read and normalize the input data before main branches on or transforms it
    # further.
    p_apply = sub.add_parser('apply')
    p_apply.add_argument('--source-dir', required=True)
    p_apply.add_argument('--areas', nargs='*', default=[])
    p_apply.add_argument('--preview', action='store_true')
    p_apply.add_argument('--out', default='templatify/reports/templatify_apply.json')
    p_apply.add_argument('--md-out', default='templatify/reports/templatify_apply_report.md')
    p_apply.add_argument('--quiet', action='store_true')
    # Read and normalize the input data before main branches on or transforms it
    # further.
    args = parser.parse_args(argv)

    root = workspace_root(Path(__file__))
    # Branch on args.command == 'list-templates' so main only continues along the
    # matching state path.
    if args.command == 'list-templates':
        # Assemble the structured result data before later steps enrich or return it
        # from main.
        payload = {'ok': True, 'templates': [item.__dict__ for item in discover_templates(root)]}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    # Branch on args.command == 'validate' so main only continues along the matching
    # state path.
    if args.command == 'validate':
        # Assemble the structured result data before later steps enrich or return it
        # from main.
        payload = validate_templates(root)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload.get('ok') else 1
    # Branch on args.command == 'inspect' so main only continues along the matching
    # state path.
    if args.command == 'inspect':
        # Assemble the structured result data before later steps enrich or return it
        # from main.
        payload = inspect_areas(root)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    # Branch on args.command == 'render' so main only continues along the matching state
    # path.
    if args.command == 'render':
        # Wire together the shared services that main depends on for the rest of its
        # workflow.
        context = {}
        # Process raw one item at a time so main applies the same rule across the full
        # collection.
        for raw in args.var:
            # Branch on '=' not in raw so main only continues along the matching state
            # path.
            if '=' not in raw:
                raise SystemExit(f'Invalid --var {raw!r}, expected key=value')
            key, value = raw.split('=', 1)
            context[key] = value
        rendered, record = render_with_header(root, args.family, args.name, context)
        # Branch on args.out so main only continues along the matching state path.
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            out.write_text(rendered, encoding='utf-8')
            print(json.dumps({'ok': True, 'path': str(out), 'template_id': record.template_id}, indent=2))
        else:
            print(rendered, end='')
        return 0
    # Branch on args.command == 'check-drift' so main only continues along the matching
    # state path.
    if args.command == 'check-drift':
        # Assemble the structured result data before later steps enrich or return it
        # from main.
        payload = scan_generated_drift(root, Path(args.generated_dir).resolve())
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if payload.get('drift_count', 0) == 0 else 1
    # Branch on args.command == 'plan' so main only continues along the matching state
    # path.
    if args.command == 'plan':
        # Assemble the structured result data before later steps enrich or return it
        # from main.
        payload = build_plan(root, Path(args.source_dir).resolve(), areas=args.areas or None)
        out = root / args.out
        md = root / args.md_out
        out.parent.mkdir(parents=True, exist_ok=True)
        md.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        lines = ['# Templatify plan report', '']
        # Process (area, info) one item at a time so main applies the same rule across
        # the full collection.
        for area, info in payload.get('areas', {}).items():
            lines.extend([
                f'## {area}',
                '',
                f"- status: `{info.get('status', 'unknown')}`",
                f"- target_root: `{info.get('target_root', '')}`",
            ])
            unmapped = info.get('unmapped_base_blocks', [])
            # Branch on unmapped so main only continues along the matching state path.
            if unmapped:
                lines.append(f"- unmapped_base_blocks: `{', '.join(unmapped)}`")
            lines.append('')
        # Branch on payload.get('warnings') so main only continues along the matching
        # state path.
        if payload.get('warnings'):
            lines.extend(['## Warnings', ''])
            lines.extend(f'- {item}' for item in payload['warnings'])
            lines.append('')
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        md.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        # Branch on not args.quiet so main only continues along the matching state path.
        if not args.quiet:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    # Branch on args.command == 'apply' so main only continues along the matching state
    # path.
    if args.command == 'apply':
        # Assemble the structured result data before later steps enrich or return it
        # from main.
        plan = build_plan(root, Path(args.source_dir).resolve(), areas=args.areas or None)
        written = apply_plan(root, plan, write_under_generated=args.preview)
        payload = {'ok': True, 'suite': 'templatify', 'written': written, 'preview': bool(args.preview), 'areas': sorted(plan.get('areas', {}).keys())}
        out = root / args.out
        md = root / args.md_out
        out.parent.mkdir(parents=True, exist_ok=True)
        md.parent.mkdir(parents=True, exist_ok=True)
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        md.write_text('# Templatify apply report\n\n' + '\n'.join(f'- `{item}`' for item in written) + '\n', encoding='utf-8')
        # Branch on not args.quiet so main only continues along the matching state path.
        if not args.quiet:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    return 2
