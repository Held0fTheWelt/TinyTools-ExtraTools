"""Platform dispatch emit for fy_platform.surfaces.

"""
from __future__ import annotations

import json

from fy_platform.surfaces.platform_dispatch import platform_mode_payload


def emit_payload(command: str, mode_name: str, args) -> int:
    """Emit payload.

    Args:
        command: Named command for this operation.
        mode_name: Primary mode name used by this step.
        args: Command-line arguments to parse for this invocation.

    Returns:
        int:
            Value produced by this callable as ``int``.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # emit_payload.
    payload = platform_mode_payload(command, mode_name, args)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get('ok', True) else 2
