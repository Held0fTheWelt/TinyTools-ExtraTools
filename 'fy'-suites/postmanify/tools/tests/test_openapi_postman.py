"""Tests for OpenAPI → Postman URL mapping and grouping."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from postmanify.tools import cli as postmanify_cli
from postmanify.tools.cli import _default_out_master
from postmanify.tools.openapi_postman import backend_postman_url_raw, group_operations_by_tag, iter_operations


class UrlMappingTests(unittest.TestCase):
    """Coordinate url mapping tests behavior.
    """
    def test_backend_prefix_tail(self) -> None:
        """Verify that backend prefix tail works as expected.
        """
        self.assertEqual(
            backend_postman_url_raw("/api/v1/languages", backend_api_prefix="/api/v1"),
            "{{backendBaseUrl}}{{backendApiPrefix}}/languages",
        )
        self.assertEqual(
            backend_postman_url_raw("/api/v1", backend_api_prefix="/api/v1"),
            "{{backendBaseUrl}}{{backendApiPrefix}}",
        )

    def test_non_prefixed_path_uses_literal(self) -> None:
        """Verify that non prefixed path uses literal works as expected.
        """
        self.assertEqual(
            backend_postman_url_raw("/other/path", backend_api_prefix="/api/v1"),
            "{{backendBaseUrl}}/other/path",
        )


class IterOperationsTests(unittest.TestCase):
    """Coordinate iter operations tests behavior.
    """
    def test_iter_skips_non_operations(self) -> None:
        """Verify that iter skips non operations works as expected.
        """
        spec = {
            "paths": {
                "/api/v1/health": {
                    "get": {"tags": ["System"], "summary": "Health"},
                    "parameters": [],
                }
            }
        }
        ops = iter_operations(spec)
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0].method, "GET")
        self.assertEqual(ops[0].path, "/api/v1/health")

    def test_group_by_primary_tag(self) -> None:
        """Verify that group by primary tag works as expected.
        """
        spec = {
            "paths": {
                "/api/v1/a": {"get": {"tags": ["Auth"], "summary": "A"}},
                "/api/v1/b": {"post": {"tags": ["Forum", "Auth"], "summary": "B"}},
            }
        }
        ops = iter_operations(spec)
        g = group_operations_by_tag(ops)
        self.assertIn("Auth", g)
        self.assertIn("Forum", g)
        self.assertEqual(len(g["Auth"]), 1)
        self.assertEqual(len(g["Forum"]), 1)

    def test_manifest_can_override_default_output_master(self) -> None:
        """Verify that manifest can override default output master works as
        expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            (repo / "fy-manifest.yaml").write_text(
                "manifestVersion: 1\n"
                "suites:\n"
                "  postmanify:\n"
                "    out_master: postman/custom_master.json\n",
                encoding="utf-8",
            )
            self.assertEqual(_default_out_master(repo), "postman/custom_master.json")

    def test_plan_can_emit_envelope(self) -> None:
        """Verify that plan can emit envelope works as expected.

        This callable writes or records artifacts as part of its
        workflow. Exceptions are normalized inside the implementation
        before control returns to callers.
        """
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs" / "api").mkdir(parents=True)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            (repo / "docs" / "api" / "openapi.yaml").write_text(
                "openapi: 3.0.0\ninfo:\n  title: T\n  version: '1.0.0'\npaths: {}\n",
                encoding="utf-8",
            )
            old = postmanify_cli.repo_root
            postmanify_cli.repo_root = lambda: repo
            try:
                env = repo / "out.envelope.json"
                code = postmanify_cli.main(["plan", "--envelope-out", str(env)])
                self.assertEqual(code, 0)
                self.assertTrue(env.is_file())
                payload = json.loads(env.read_text(encoding="utf-8"))
                self.assertEqual(payload["envelopeVersion"], "1")
                self.assertIn("stats", payload)
            finally:
                postmanify_cli.repo_root = old

    def test_generate_emits_deprecation_sidecar_for_legacy_naming(self) -> None:
        """Verify that generate emits deprecation sidecar for legacy naming
        works as expected.

        This callable writes or records artifacts as part of its
        workflow. Exceptions are normalized inside the implementation
        before control returns to callers.
        """
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs" / "api").mkdir(parents=True)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            (repo / "docs" / "api" / "openapi.yaml").write_text(
                "openapi: 3.0.0\ninfo:\n  title: T\n  version: '1.0.0'\npaths: {}\n",
                encoding="utf-8",
            )
            old = postmanify_cli.repo_root
            postmanify_cli.repo_root = lambda: repo
            try:
                code = postmanify_cli.main(["generate"])
                self.assertEqual(code, 0)
                dep = repo / "postman" / "postmanify.deprecations.md"
                self.assertTrue(dep.is_file())
            finally:
                postmanify_cli.repo_root = old


if __name__ == "__main__":
    unittest.main()
