"""Memory bridge for observifyfy.tools.

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_memory_snapshot(path: Path, inventory: dict[str, Any], next_steps: dict[str, Any]) -> dict[str, Any]:
    """Write memory snapshot.

    This callable writes or records artifacts as part of its workflow.

    Args:
        path: Filesystem path to the file or directory being processed.
        inventory: Primary inventory used by this step.
        next_steps: Primary next steps used by this step.

    Returns:
        dict[str, Any]:
            Structured payload describing the outcome of the
            operation.
    """
    # Assemble the structured result data before later steps enrich or return it from
    # write_memory_snapshot.
    payload = {
        'memory_kind': 'fy_suite_operations',
        'suite_count': inventory.get('suite_count', 0),
        'existing_suite_count': inventory.get('existing_suite_count', 0),
        'internal_roots': inventory.get('internal_roots', {}),
        'highest_value_next_step': next_steps.get('highest_value_next_step'),
        'recommended_next_steps': next_steps.get('recommended_next_steps', [])[:5],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return payload
