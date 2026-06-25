
"""Memory bridge for mvpify.tools.

"""
from __future__ import annotations

import json
from pathlib import Path


def write_memory_snapshot(path: Path, import_payload: dict, plan: dict) -> dict:
    """Write memory snapshot.

    This callable writes or records artifacts as part of its workflow.

    Args:
        path: Filesystem path to the file or directory being processed.
        import_payload: Primary import payload used by this step.
        plan: Primary plan used by this step.

    Returns:
        dict:
            Structured payload describing the outcome of the
            operation.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Assemble the structured result data before later steps enrich or return it from
    # write_memory_snapshot.
    payload = {
        'kind': 'mvpify_operations_memory',
        'source': import_payload.get('source'),
        'artifact_count': import_payload.get('artifact_count', 0),
        'highest_value_next_step': plan.get('highest_value_next_step'),
        'step_count': len(plan.get('steps', [])),
    }
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return payload
