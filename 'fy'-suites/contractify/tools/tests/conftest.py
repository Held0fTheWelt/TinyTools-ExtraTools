"""
Hermetic test defaults: Contractify unit tests must not depend on a full
World of Shadows checkout.

ZIP extracts and partial trees still run ``pytest`` here when
``repo_root()`` is patched to a synthetic layout that satisfies
``discovery`` / ``drift_analysis`` / ``hub_cli`` expectations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from contractify.tools.minimal_repo import build_minimal_contractify_test_repo


_MODULES_WITHOUT_REPO_PATCH = frozenset(
    {
        "contractify.tools.tests.test_models",
        "contractify.tools.tests.test_example_artifacts",
        "contractify.tools.tests.test_runtime_mvp_spine",
        "contractify.tools.tests.test_manifest_first_profile",
        "contractify.tools.tests.test_projection_governance_closure",
    }
)


@pytest.fixture(autouse=True)
def _hermetic_contractify_repo(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Patch ``repo_root()`` for every test module except pure unit tests.

    Control flow branches on the parsed state rather than relying on one
    linear path.

    Args:
        request: Primary request used by this step.
        monkeypatch: Primary monkeypatch used by this step.
        tmp_path: Filesystem path to the file or directory being
            processed.

    Returns:
        Iterator[None]:
            Collection produced from the parsed or
            accumulated input data.
    """
    # Branch on request.module.__name__ in _MODULES_WITHOUT_R... so
    # _hermetic_contractify_repo only continues along the matching state path.
    if request.module.__name__ in _MODULES_WITHOUT_REPO_PATCH:
        yield
        return
    fake = build_minimal_contractify_test_repo(tmp_path)
    monkeypatch.setattr("contractify.tools.repo_paths.repo_root", lambda start=None: fake)
    monkeypatch.setattr("contractify.tools.hub_cli.repo_root", lambda start=None: fake)
    yield
