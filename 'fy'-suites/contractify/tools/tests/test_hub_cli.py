"""Tests for hub cli.

"""
import json

import contractify.tools.hub_cli as hub_cli
import contractify.tools.repo_paths as repo_paths
from contractify.tools.hub_cli import main


def test_discover_writes_json() -> None:
    """Verify that discover writes json works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.
    """
    # Build filesystem locations and shared state that the rest of
    # test_discover_writes_json reuses.
    root = repo_paths.repo_root()
    out_path = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_contractify_discover.json"
    out_arg = out_path.relative_to(root).as_posix()
    # Protect the critical test_discover_writes_json work so failures can be turned into
    # a controlled result or cleanup path.
    try:
        code = main(["discover", "--out", out_arg, "--quiet", "--max-contracts", "15"])
        assert code == 0
        # Read and normalize the input data before test_discover_writes_json branches on
        # or transforms it further.
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert "contracts" in data
        assert len(data["contracts"]) >= 1
    finally:
        # Branch on out_path.is_file() so test_discover_writes_json only continues along
        # the matching state path.
        if out_path.is_file():
            out_path.unlink()


def test_discover_can_emit_shared_envelope() -> None:
    """Verify that discover can emit shared envelope works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.
    """
    root = repo_paths.repo_root()
    out_path = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_contractify_discover_envelope.json"
    out_arg = out_path.relative_to(root).as_posix()
    try:
        code = main(["discover", "--max-contracts", "10", "--quiet", "--envelope-out", out_arg])
        assert code == 0
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["envelopeVersion"] == "1"
        assert data["suite"] == "contractify"
        assert "findings" in data
        assert "evidence" in data
        assert "stats" in data
    finally:
        if out_path.is_file():
            out_path.unlink()


def test_discover_writes_deprecation_evidence_when_manifest_missing(monkeypatch) -> None:
    """Verify that discover writes deprecation evidence when manifest
    missing works as expected.

    Exceptions are normalized inside the implementation before control
    returns to callers. Control flow branches on the parsed state rather
    than relying on one linear path.

    Args:
        monkeypatch: Primary monkeypatch used by this step.
    """
    root = repo_paths.repo_root()
    out = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_contractify_discover_missing_manifest.json"
    env = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_contractify_discover_missing_manifest.envelope.json"
    out_arg = out.relative_to(root).as_posix()
    env_arg = env.relative_to(root).as_posix()
    monkeypatch.setattr(hub_cli, "load_manifest", lambda _root: (None, []))
    try:
        code = main(["discover", "--out", out_arg, "--quiet", "--envelope-out", env_arg, "--max-contracts", "5"])
        assert code == 0
        env_payload = json.loads(env.read_text(encoding="utf-8"))
        assert env_payload["deprecations"]
        dep_md = out.with_suffix(out.suffix + ".deprecations.md")
        assert dep_md.is_file()
    finally:
        if out.is_file():
            out.unlink()
        if env.is_file():
            env.unlink()


def test_adr_investigation_writes_bundle() -> None:
    """Verify that adr investigation writes bundle works as expected.

    The implementation iterates over intermediate items before it
    returns. Exceptions are normalized inside the implementation before
    control returns to callers.
    """
    root = repo_paths.repo_root()
    out_dir = root / "'fy'-suites" / "contractify" / "reports" / "_pytest_adr_investigation_cli"
    try:
        code = main(["adr-investigation", "--out-dir", out_dir.relative_to(root).as_posix(), "--quiet"])
        assert code == 0
        assert (out_dir / "ADR_GOVERNANCE_INVESTIGATION.md").is_file()
        assert (out_dir / "ADR_RELATION_MAP.mmd").is_file()
        assert (out_dir / "ADR_CONFLICT_MAP.mmd").is_file()
    finally:
        if out_dir.exists():
            for child in sorted(out_dir.glob("*"), reverse=True):
                child.unlink()
            out_dir.rmdir()
