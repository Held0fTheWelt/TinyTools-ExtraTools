"""Regression tests for the DS-005 runtime import gate."""

from __future__ import annotations

import importlib

from despaghettify.tools import ds005_runtime_import_check as ds005


def test_frozen_runtime_modules_resolve_to_current_package_paths() -> None:
    """The gate must follow the current app.runtime package layout."""
    import_paths = [
        ds005.runtime_module_import_path(name)
        for name in ds005.FROZEN_RUNTIME_MODULES
    ]

    assert "app.runtime.turn_executor" not in import_paths
    assert "app.runtime.turn.turn_executor" in import_paths
    assert "app.runtime.validation.validators" in import_paths
    assert "app.runtime.ai_turn.ai_turn_executor" in import_paths
    assert "app.runtime.supervisor.supervisor_orchestrator" in import_paths


def test_frozen_runtime_modules_import_in_gate_order() -> None:
    """The same ordered module set imported by the scan remains importable."""
    for name in ds005.FROZEN_RUNTIME_MODULES:
        import_path = ds005.runtime_module_import_path(name)
        module = importlib.import_module(import_path)
        assert module.__name__ == import_path
