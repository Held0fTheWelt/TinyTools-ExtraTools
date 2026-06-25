#!/usr/bin/env python3
"""
DS-005: import frozen runtime modules in fixed order (cycle regression
check).

Run from repository root: python
"./'fy'-suites/despaghettify/tools/ds005_runtime_import_check.py"

Prepends ``backend/`` on sys.path so ``app.*`` resolves without
installing the package.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_tools = Path(__file__).resolve().parent
_hub = _tools.parent
_grand = _hub.parent
_ins = str(_grand if _grand.name == "'fy'-suites" else _hub.parent)
if _ins not in sys.path:
    sys.path.insert(0, _ins)

from despaghettify.tools.repo_paths import repo_root

try:
    _REPO_ROOT = repo_root()
except RuntimeError:
    _REPO_ROOT = Path.cwd()
BACKEND_ROOT = _REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.runtime.package_classification import runtime_module_import_path

# Frozen order for cycle regression; names resolve through package_classification
# so the gate follows the current runtime package layout.
FROZEN_RUNTIME_MODULES = [
    "turn_executor",
    "turn_executor_validated_pipeline_apply",
    "turn_executor_validated_pipeline_narrative_log",
    "turn_executor_validated_pipeline",
    "validators",
    "role_structured_decision",
    "ai_decision",
    "ai_failure_recovery",
    "ai_turn_executor",
    "turn_dispatcher",
    # DS-015: supervisor entry seam (after dispatcher; must import clean in this order)
    "supervisor_orchestrate_execute",
    "supervisor_orchestrator",
]


def main() -> int:
    """Implement ``main`` for the surrounding module workflow.

    The implementation iterates over intermediate items before it
    returns.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    # Process name one item at a time so main applies the same rule across the full
    # collection.
    for name in FROZEN_RUNTIME_MODULES:
        import_path = runtime_module_import_path(name)
        importlib.import_module(import_path)
        print(f"import_ok\t{import_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
