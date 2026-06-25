"""Ai suite cli emit for fy_platform.tools.

"""
from __future__ import annotations

import json

from fy_platform.ai.adapter_cli_helper import build_command_envelope, render_markdown_output


def emit(payload: dict, suite: str, command: str, fmt: str) -> None:
    """Emit the requested operation.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        payload: Structured data carried through this workflow.
        suite: Primary suite used by this step.
        command: Named command for this operation.
        fmt: Primary fmt used by this step.
    """
    envelope = build_command_envelope(suite, command, payload)
    # Branch on fmt == 'markdown' so emit only continues along the matching state path.
    if fmt == 'markdown':
        print(render_markdown_output(suite, command, payload), end='')
        return
    print(json.dumps({
        'ok': envelope.ok,
        'suite': envelope.suite,
        'command': envelope.command,
        'schema_version': envelope.schema_version,
        'exit_code': envelope.exit_code,
        'error_code': envelope.error_code,
        'warnings': envelope.warnings,
        'errors': envelope.errors,
        'timestamp': envelope.timestamp,
        'contract_version': envelope.contract_version,
        'compatibility_mode': envelope.compatibility_mode,
        'recovery_hints': envelope.recovery_hints,
        'payload': envelope.payload,
    }, indent=2, ensure_ascii=False))
