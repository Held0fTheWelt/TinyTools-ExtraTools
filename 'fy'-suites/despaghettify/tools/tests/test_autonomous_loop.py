"""Tests for autonomous loop state machine (isolated paths via patch)."""
from __future__ import annotations

import json
import unittest
import shutil
from pathlib import Path
from unittest.mock import patch

from despaghettify.tools import autonomous_loop as al


def _minimal_input(open_ds: str | None) -> str:
    """Minimal input.

    Args:
        open_ds: Primary open ds used by this step.

    Returns:
        str:
            Rendered text produced for downstream callers or
            writers.
    """
    open_row = f"| **{open_ds}** | x | y | z | w | status |\n" if open_ds else ""
    return f"""# x

## Information input list

{open_row}
## Recommended implementation order

| Phase | Note |
|-------|------|
"""


class AutonomousLoopTests(unittest.TestCase):
    """Coordinate autonomous loop tests behavior.
    """
    def setUp(self) -> None:
        """Set up.

        This callable writes or records artifacts as part of its
        workflow. Control flow branches on the parsed state rather than
        relying on one linear path.
        """
        self._tmp = Path(__file__).resolve().parent / "_autonomous_test_state"
        self._tmp.mkdir(exist_ok=True)
        self._state_file = self._tmp / "autonomous_state.json"
        self._input = self._tmp / "input.md"
        if self._state_file.exists():
            self._state_file.unlink()

    def tearDown(self) -> None:
        """Tear down.

        Control flow branches on the parsed state rather than relying on
        one linear path.
        """
        if self._state_file.exists():
            self._state_file.unlink()
        if self._tmp.exists():
            shutil.rmtree(self._tmp, ignore_errors=True)

    def test_init_backlog_then_main_check(self) -> None:
        """Verify that init backlog then main check works as expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        self._input.write_text(_minimal_input("DS-099"), encoding="utf-8")
        with patch.object(al, "INPUT_LIST", self._input), patch.object(al, "STATE_DIR", self._tmp), patch.object(
            al, "STATE_FILE", self._state_file
        ):
            code, msg, st = al.init_session(force=True)
            self.assertEqual(code, 0, msg)
            self.assertEqual(st["phase"], "backlog")
            open_now = al.collect_open_ds_ids()
            self.assertIn("DS-099", open_now)
            r = al.advance("backlog_solve", ds="DS-099", check_json=None)
            self.assertFalse(r.ok)
            self.assertEqual(r.exit_code, 2)
            slice_json = self._tmp / "slice_check.json"
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            slice_json.write_text(
                json.dumps({"kind": "despaghettify_check", "ast": {"total_functions": 2}}),
                encoding="utf-8",
            )
            rel_slice = slice_json.relative_to(al.ROOT).as_posix()
            r_impl = al.advance("backlog_implement", ds="DS-099", check_json=rel_slice)
            self.assertTrue(r_impl.ok, r_impl.message)
            st_mid = al.load_state()
            assert st_mid is not None
            self.assertEqual(st_mid["last_kind"], "backlog_implement")
            r_impl_bad = al.advance("backlog_implement", ds="DS-099", check_json=None)
            self.assertFalse(r_impl_bad.ok)
            self.assertEqual(r_impl_bad.exit_code, 2)
            # Close DS in markdown (no bold open row)
            self._input.write_text(_minimal_input(None), encoding="utf-8")
            r2 = al.advance("backlog_solve", ds="DS-099", check_json=None)
            self.assertTrue(r2.ok, r2.message)
            st2 = al.load_state()
            assert st2 is not None
            self.assertEqual(st2["phase"], "main")
            chk = self._tmp / "chk.json"
            # Write the human-readable companion text so reviewers can inspect the
            # result without opening raw structured data.
            chk.write_text(
                json.dumps(
                    {"kind": "despaghettify_check", "ast": {"total_functions": 1, "count_over_100_lines": 0, "count_over_50_lines": 0, "count_nesting_ge_6": 0}}
                ),
                encoding="utf-8",
            )
            rel = chk.relative_to(al.ROOT).as_posix()
            r3 = al.advance("main_check", ds=None, check_json=rel)
            self.assertTrue(r3.ok, r3.message)

    def test_init_main_when_no_open_ds(self) -> None:
        """Verify that init main when no open ds works as expected.

        This callable writes or records artifacts as part of its
        workflow.
        """
        # Write the human-readable companion text so reviewers can inspect the result
        # without opening raw structured data.
        self._input.write_text(_minimal_input(None), encoding="utf-8")
        with patch.object(al, "INPUT_LIST", self._input), patch.object(al, "STATE_DIR", self._tmp), patch.object(
            al, "STATE_FILE", self._state_file
        ):
            code, _, st = al.init_session(force=True)
            self.assertEqual(code, 0)
            self.assertEqual(st["phase"], "main")
            self.assertEqual(st["last_kind"], "init")


class MetricsBundleTests(unittest.TestCase):
    """Coordinate metrics bundle tests behavior.
    """
    def test_build_bundle_shape(self) -> None:
        """Verify that build bundle shape works as expected.
        """
        from despaghettify.tools.metrics_bundle import build_metrics_bundle

        setup = {
            "schema_version": 1,
            "trigger_bars": {f"C{i}": 50.0 for i in range(1, 8)},
            "weights": {f"C{i}": 1.0 / 7 for i in range(1, 8)},
            "m7_ref": 50.0,
        }
        chk = {"ast": {"total_functions": 100, "count_over_100_lines": 0, "count_over_50_lines": 0, "count_nesting_ge_6": 0}}
        b = build_metrics_bundle(check_payload=chk, setup=setup)
        self.assertIn("m7", b)
        self.assertIn("per_category_trigger_fires", b)
        self.assertFalse(b["trigger_policy_fires"])


if __name__ == "__main__":
    unittest.main()
