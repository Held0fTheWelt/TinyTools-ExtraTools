"""
Write frozen discover/audit JSON under ``reports/committed/`` from the
hermetic minimal repo.

Run from repository root after ``pip install -e .``:

python -m contractify.tools.freeze_committed_reports

Re-run whenever discovery, drift, conflict, or audit payload shape
changes materially.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from contractify.tools.audit_pipeline import build_discover_payload, run_audit
from contractify.tools.minimal_repo import build_minimal_contractify_test_repo

# Stable timestamp so diffs stay reviewable (not "current time").
FROZEN_GENERATED_AT = "2026-04-13T18:00:00+00:00"
# Avoid machine-specific temp paths in committed JSON (reviewable diffs).
SYNTHETIC_REPO_ROOT_LABEL = "<synthetic-minimal-repo-contractify-fixtures>"


def _contractify_dir() -> Path:
    """Contractify dir.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    return Path(__file__).resolve().parent.parent


def main() -> int:
    """Run the command-line entry point.

    This callable writes or records artifacts as part of its workflow.

    Returns:
        int:
            Process exit status code for the invoked
            command.
    """
    # Build filesystem locations and shared state that the rest of main reuses.
    out_dir = _contractify_dir() / "reports" / "committed"
    out_dir.mkdir(parents=True, exist_ok=True)
    # Enter a managed resource scope for this phase and rely on the context manager to
    # clean up when main leaves it.
    with tempfile.TemporaryDirectory(prefix="contractify-freeze-") as td:
        root = Path(td)
        build_minimal_contractify_test_repo(root)
        # Read and normalize the input data before main branches on or transforms it
        # further.
        audit = run_audit(root, max_contracts=40, frozen_generated_at=FROZEN_GENERATED_AT)
        discover = build_discover_payload(root, max_contracts=40, frozen_generated_at=FROZEN_GENERATED_AT)
    audit["repo_root"] = SYNTHETIC_REPO_ROOT_LABEL
    discover["repo_root"] = SYNTHETIC_REPO_ROOT_LABEL
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (out_dir / "audit.hermetic-fixture.json").write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (out_dir / "discover.hermetic-fixture.json").write_text(
        json.dumps(discover, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {out_dir / 'audit.hermetic-fixture.json'}")
    print(f"Wrote {out_dir / 'discover.hermetic-fixture.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
