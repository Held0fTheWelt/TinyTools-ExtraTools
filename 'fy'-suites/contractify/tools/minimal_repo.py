"""
Synthetic minimal repository layout for hermetic tests and frozen report
generation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _write_minimal_openapi(root: Path) -> str:
    """Write minimal openapi.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    body = (
        "openapi: 3.0.0\n"
        "info:\n"
        "  title: ContractifyTestAPI\n"
        "  version: '0.0.1'\n"
        "paths: {}\n"
    )
    p = root / "docs" / "api" / "openapi.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = body.encode("utf-8")
    p.write_bytes(raw)
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_minimal_contractify_test_repo(root: Path) -> Path:
    """Create a tiny repo tree that mirrors the discovery anchors
    Contractify expects.

    This callable writes or records artifacts as part of its workflow.

    Args:
        root: Root directory used to resolve repository-local paths.

    Returns:
        Path:
            Filesystem path produced or resolved by this
            callable.
    """
    root = root.resolve()
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "pyproject.toml").write_text(
        '[project]\nname = "world-of-shadows-hub"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    sha = _write_minimal_openapi(root)
    (root / "docs" / "dev" / "contracts").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "technical").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "docs" / "technical" / "shared-runtime.md").write_text("# Shared\n", encoding="utf-8")
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "docs" / "dev" / "contracts" / "normative-contracts-index.md").write_text(
        "# Normative contracts index\n\n**binding scope** test fixture. See also `openapi.yaml`.\n\n"
        "## Duplicate navigation stress (deterministic conflict fixture)\n"
        "| A | [one](../../technical/shared-runtime.md) |\n"
        "| B | [two](../../technical/shared-runtime.md) |\n"
        "## Active row stress (retired ADR linked with Active label)\n"
        "| Active | [retired ADR](../../ADR/adr-0003-retired.md) |\n",
        encoding="utf-8",
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "docs" / "dev" / "README.md").write_text(
        "See [Normative contracts index](contracts/normative-contracts-index.md).\n",
        encoding="utf-8",
    )
    manifest = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "openapi_path": "docs/api/openapi.yaml",
        "openapi_sha256": sha,
        "backend_api_prefix": "/api/v1",
        "master_collection": "postman/Master.postman_collection.json",
        "suites_dir": "postman/suites",
        "sub_suite_files": [],
    }
    (root / "postman").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "postman" / "postmanify-manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    fy = root / "'fy'-suites"
    (fy / "contractify").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (fy / "contractify" / "README.md").write_text(
        "# Contractify\n\n**Normative** suite charter for tests.\n",
        encoding="utf-8",
    )
    (fy / "contractify" / "reports").mkdir(parents=True, exist_ok=True)
    (fy / "despaghettify").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (fy / "despaghettify" / "spaghetti-setup.md").write_text(
        "## Normative specification\n\nCanonical contract for tooling.\n",
        encoding="utf-8",
    )
    (fy / "docify").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (fy / "docify" / "README.md").write_text(
        "Default roots include `'fy'-suites/contractify` for self-governance.\n",
        encoding="utf-8",
    )
    (fy / "docify" / "tools").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (fy / "docify" / "tools" / "python_documentation_audit.py").write_text(
        "DEFAULT_RELATIVE_ROOTS = (\n    \"'fy'-suites/contractify\",\n)\n",
        encoding="utf-8",
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (fy / "docify" / "documentation-check-task.md").write_text(
        "# Documentation check task\n\n**Normative** procedure; default roots include **'fy'-suites/contractify**.\n",
        encoding="utf-8",
    )
    (fy / "postmanify").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (fy / "postmanify" / "postmanify-sync-task.md").write_text(
        "# Postmanify sync\n\nRegenerate Postman collections from **docs/api/openapi.yaml** after each OpenAPI edit.\n",
        encoding="utf-8",
    )
    wf = root / ".github" / "workflows"
    wf.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (wf / "ci_openapi_hint.yml").write_text(
        "name: ci\non: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: cat docs/api/openapi.yaml\n",
        encoding="utf-8",
    )
    adr = root / "docs" / "ADR"
    adr.mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (adr / "adr-0001-scene-identity.md").write_text(
        "# ADR 1\n\n**Status**: Accepted\n\nDecision about **scene identity** surface.\n",
        encoding="utf-8",
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (adr / "adr-0002-runtime-authority.md").write_text(
        "# ADR 2\n\n**Status**: Accepted\n\n**Runtime authority** overlaps **scene identity** vocabulary.\n",
        encoding="utf-8",
    )
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (adr / "adr-0003-retired.md").write_text(
        "# ADR 3 retired\n\n**Status**: Superseded\n\n"
        "Supersedes: [ADR 1](adr-0001-scene-identity.md)\n\n"
        "Retained for history only.\n",
        encoding="utf-8",
    )
    (root / "docs" / "operations").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "docs" / "operations" / "OPERATIONAL_GOVERNANCE_RUNTIME.md").write_text(
        "# Ops\n\n**Normative** alignment with governance runtime controls.\n",
        encoding="utf-8",
    )
    (root / "schemas").mkdir(parents=True, exist_ok=True)
    # Write the human-readable companion text so reviewers can inspect the result
    # without opening raw structured data.
    (root / "schemas" / "sample_payload.json").write_text('{"type": "object"}\n', encoding="utf-8")
    return root
