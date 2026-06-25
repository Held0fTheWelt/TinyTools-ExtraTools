"""Tests for spaghetti_setup_audit (canonical md vs json mirror)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


_FIXTURE_MD = """# x

## Per-category trigger bars

| Category | Symbol | Bar |
| -------- | ------ | --- |
| a | **C1** | **10** |
| b | **C2** | **10** |
| c | **C3** | **10** |
| d | **C4** | **10** |
| e | **C5** | **10** |
| f | **C6** | **10** |
| g | **C7** | **10** |

## M7 category weights

| Symbol | Weight |
| ------ | ------ |
| **C1** | 0.2 |
| **C2** | 0.1 |
| **C3** | 0.2 |
| **C4** | 0.15 |
| **C5** | 0.1 |
| **C6** | 0.15 |
| **C7** | 0.1 |

## Composite reference

| Field | Value |
| ----- | ----- |
| **M7_ref** | **10** |
"""


class SpaghettiSetupAuditTests(unittest.TestCase):
    """Coordinate spaghetti setup audit tests behavior.
    """
    def test_parse_current_repo_setup_md(self) -> None:
        """Verify that parse current repo setup md works as expected.
        """
        from despaghettify.tools.repo_paths import despag_hub_dir, repo_root
        from despaghettify.tools.spaghetti_setup_audit import compute_m7_ref, parse_spaghetti_setup_md

        # Build filesystem locations and shared state that the rest of
        # test_parse_current_repo_setup_md reuses.
        hub = despag_hub_dir(repo_root())
        md_path = hub / "spaghetti-setup.md"
        p = parse_spaghetti_setup_md(md_path.read_text(encoding="utf-8"))
        self.assertEqual(p["trigger_bars"]["C1"], 2.0)
        self.assertEqual(p["trigger_bars"]["C3"], 12.0)
        self.assertEqual(p["trigger_bars"]["C4"], 5.0)
        self.assertEqual(p["weights"]["C1"], 0.25)
        self.assertAlmostEqual(p["m7_ref"], 4.24, places=3)
        self.assertAlmostEqual(compute_m7_ref(p["trigger_bars"], p["weights"]), 4.24, places=3)

    def test_audit_json_matches_md(self) -> None:
        """Verify that audit json matches md works as expected.
        """
        from despaghettify.tools.repo_paths import despag_hub_dir, repo_root
        from despaghettify.tools.spaghetti_setup_audit import audit_setup

        hub = despag_hub_dir(repo_root())
        rep = audit_setup(
            md_path=hub / "spaghetti-setup.md",
            json_path=hub / "spaghetti-setup.json",
            check_json_path=None,
        )
        self.assertTrue(rep["derived_json_matches_md"], rep["drift_issues"])
        self.assertTrue(rep["json_mirror_ok"], rep["drift_issues"])
        self.assertEqual(rep["audit_status"], "PASS")
        self.assertEqual(rep["audit_exit_code"], 0)

    def test_parse_accepts_plain_and_bold_and_backtick_c(self) -> None:
        """Verify that parse accepts plain and bold and backtick c works as
        expected.
        """
        from despaghettify.tools.spaghetti_setup_audit import parse_spaghetti_setup_md

        md = _FIXTURE_MD.replace("| c | **C3** | **10** |", "| c | `C3` | 12.0 |")
        p = parse_spaghetti_setup_md(md)
        self.assertEqual(p["trigger_bars"]["C3"], 12.0)

    def test_parse_rejects_duplicate_bar(self) -> None:
        """Verify that parse rejects duplicate bar works as expected.
        """
        from despaghettify.tools.spaghetti_setup_audit import parse_spaghetti_setup_md

        dup_row = "\n| dup | **C1** | 1 |\n"
        insert_at = _FIXTURE_MD.find("## M7 category weights")
        self.assertGreater(insert_at, 0)
        md = _FIXTURE_MD[:insert_at] + dup_row + _FIXTURE_MD[insert_at:]
        with self.assertRaises(ValueError) as ctx:
            parse_spaghetti_setup_md(md)
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_parse_rejects_non_numeric_bar(self) -> None:
        """Verify that parse rejects non numeric bar works as expected.
        """
        from despaghettify.tools.spaghetti_setup_audit import parse_spaghetti_setup_md

        bad = _FIXTURE_MD.replace("| a | **C1** | **10** |", "| a | **C1** | high |")
        with self.assertRaises(ValueError) as ctx:
            parse_spaghetti_setup_md(bad)
        self.assertIn("non-numeric", str(ctx.exception).lower())

    def test_audit_fail_json_stale(self) -> None:
        """Verify that audit fail json stale works as expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        from despaghettify.tools import spaghetti_setup_audit as ssa

        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "spaghetti-setup.json"
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            md_p.write_text(_FIXTURE_MD, encoding="utf-8")
            ssa.sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=False)
            doc = ssa.load_setup_json(js_p)
            doc["trigger_bars"]["C1"] = 999
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            js_p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            rep = ssa.audit_setup(md_path=md_p, json_path=js_p, check_json_path=None)
            self.assertEqual(rep["audit_status"], "FAIL_JSON_STALE")
            self.assertEqual(rep["audit_exit_code"], 1)

    def test_audit_fail_md_inconsistent(self) -> None:
        """Verify that audit fail md inconsistent works as expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        from despaghettify.tools import spaghetti_setup_audit as ssa

        bad = _FIXTURE_MD.replace("| **M7_ref** | **10** |", "| **M7_ref** | **99** |")
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "spaghetti-setup.json"
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            md_p.write_text(_FIXTURE_MD, encoding="utf-8")
            ssa.sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=False)
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            md_p.write_text(bad, encoding="utf-8")
            rep = ssa.audit_setup(md_path=md_p, json_path=js_p, check_json_path=None)
            self.assertEqual(rep["audit_status"], "FAIL_MD_INCONSISTENT")
            self.assertEqual(rep["audit_exit_code"], 2)

    def test_sync_dry_run_matches_written_json(self) -> None:
        """Verify that sync dry run matches written json works as expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        from despaghettify.tools import spaghetti_setup_audit as ssa

        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "out.json"
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            md_p.write_text(_FIXTURE_MD, encoding="utf-8")
            _c, _m, doc_dry = ssa.sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=True)
            ssa.sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=False)
            doc_disk = ssa.load_setup_json(js_p)
            self.assertEqual(doc_dry, doc_disk)

    def test_sync_writes_json_matching_fixture_md(self) -> None:
        """Verify that sync writes json matching fixture md works as
        expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        from despaghettify.tools.spaghetti_setup_audit import audit_setup, sync_setup_json_from_md

        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "spaghetti-setup.json"
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            md_p.write_text(_FIXTURE_MD, encoding="utf-8")
            code, msgs, doc = sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=False)
            self.assertEqual(code, 0, msgs)
            self.assertEqual(doc["m7_ref"], 10)
            rep = audit_setup(md_path=md_p, json_path=js_p, check_json_path=None)
            self.assertTrue(rep["derived_json_matches_md"], rep["drift_issues"])
            self.assertTrue(rep["json_mirror_ok"], rep["drift_issues"])

    def test_sync_rejects_inconsistent_m7_ref(self) -> None:
        """Verify that sync rejects inconsistent m7 ref works as expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        from despaghettify.tools.spaghetti_setup_audit import sync_setup_json_from_md

        bad = _FIXTURE_MD.replace("| **M7_ref** | **10** |", "| **M7_ref** | **99** |")
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "out.json"
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            md_p.write_text(bad, encoding="utf-8")
            code, msgs, _doc = sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=False)
            self.assertEqual(code, 2)
            self.assertTrue(msgs)
            self.assertFalse(js_p.is_file())

    def test_sync_dry_run_does_not_create_file(self) -> None:
        """Verify that sync dry run does not create file works as expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        from despaghettify.tools.spaghetti_setup_audit import sync_setup_json_from_md

        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "missing.json"
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            md_p.write_text(_FIXTURE_MD, encoding="utf-8")
            code, _msgs, doc = sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=True)
            self.assertEqual(code, 0)
            self.assertFalse(js_p.is_file())
            self.assertEqual(doc["trigger_bars"]["C1"], 10)


if __name__ == "__main__":
    unittest.main()
