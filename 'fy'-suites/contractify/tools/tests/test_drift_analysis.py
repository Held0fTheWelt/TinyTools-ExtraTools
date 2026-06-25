"""Tests for drift analysis.

"""
import hashlib
import json

import contractify.tools.repo_paths as repo_paths
from contractify.tools.drift_analysis import drift_postman_openapi_manifest


def test_postman_openapi_hash_match_is_clean() -> None:
    """Verify that postman openapi hash match is clean works as expected.
    """
    root = repo_paths.repo_root()
    mf = root / "postman" / "postmanify-manifest.json"
    assert mf.is_file()
    # Read and normalize the input data before test_postman_openapi_hash_match_is_clean
    # branches on or transforms it further.
    data = json.loads(mf.read_text(encoding="utf-8"))
    rel = str(data.get("openapi_path", "")).replace("\\", "/")
    openapi = root / rel if rel else root / "docs" / "api" / "openapi.yaml"
    assert openapi.is_file()
    # Assemble the structured result data before later steps enrich or return it from
    # test_postman_openapi_hash_match_is_clean.
    findings = drift_postman_openapi_manifest(root)
    declared = data.get("openapi_sha256", "")
    actual = hashlib.sha256(openapi.read_bytes()).hexdigest()
    assert declared == actual
    assert not any(f.id == "DRF-POSTMAN-OPENAPI-SHA-001" for f in findings)
