"""Tests for metrics_bundle ast_heuristic_v2."""
from __future__ import annotations

import unittest


class AstHeuristicV2Tests(unittest.TestCase):
    """Coordinate ast heuristic v2 tests behavior.
    """
    def test_zero_ast_all_below_cap(self) -> None:
        """Verify that zero ast all below cap works as expected.

        The implementation iterates over intermediate items before it
        returns.
        """
        from despaghettify.tools.metrics_bundle import ast_heuristic_category_scores

        s = ast_heuristic_category_scores(
            {"total_functions": 100, "count_over_100_lines": 0, "count_over_50_lines": 0, "count_nesting_ge_6": 0}
        )
        # Process (k, v) one item at a time so test_zero_ast_all_below_cap applies the
        # same rule across the full collection.
        for k, v in s.items():
            self.assertLess(v, 100.0, f"{k} must stay strictly below 100 for finite inputs")
        self.assertEqual(s["C2"], 0.0)

    def test_realistic_counts_no_flat_100(self) -> None:
        """Verify that realistic counts no flat 100 works as expected.
        """
        from despaghettify.tools.metrics_bundle import ast_heuristic_category_scores

        s = ast_heuristic_category_scores(
            {
                "total_functions": 4365,
                "count_over_100_lines": 39,
                "count_over_50_lines": 276,
                "count_nesting_ge_6": 0,
            }
        )
        self.assertLess(s["C4"], 100.0)
        self.assertLess(s["C6"], 100.0)
        self.assertNotAlmostEqual(s["C4"], s["C6"], places=1)

    def test_literal_rates_are_true_percentages(self) -> None:
        """Verify that literal rates are true percentages works as
        expected.
        """
        from despaghettify.tools.metrics_bundle import build_metrics_bundle

        setup = {
            "schema_version": 1,
            "trigger_bars": {f"C{i}": 50.0 for i in range(1, 8)},
            "weights": {f"C{i}": 1.0 / 7 for i in range(1, 8)},
            "m7_ref": 50.0,
        }
        ast = {
            "total_functions": 100,
            "count_over_100_lines": 10,
            "count_over_50_lines": 20,
            "count_nesting_ge_6": 2,
            "count_nesting_ge_4": 2,
            "count_functions_magic_int_literals_ge_5": 5,
            "count_functions_duplicate_name_across_files": 3,
            "count_functions_control_flow_heavy": 7,
            "c1_files_in_import_cycles_pct": 1.5,
            "c1_import_graph_files": 200,
            "c1_files_in_cycles": 3,
        }
        b = build_metrics_bundle(check_payload={"ast": ast}, setup=setup)
        lr = b["literal_rates"]
        self.assertAlmostEqual(lr["functions_over_100_lines_pct"], 10.0, places=4)
        self.assertAlmostEqual(lr["functions_over_50_lines_pct"], 20.0, places=4)
        self.assertAlmostEqual(lr["functions_nesting_ge_6_pct"], 2.0, places=4)
        self.assertAlmostEqual(lr["over_100_lines_among_over_50_lines_pct"], 50.0, places=4)
        cs = lr["condition_shares_pct"]
        self.assertAlmostEqual(cs["C3"], 10.0, places=4)
        self.assertAlmostEqual(cs["C5"], 5.0, places=4)
        self.assertIn("10.00", b["plain_language_de"]["C3"])
        ma = b["metric_a"]
        self.assertEqual(ma["id"], "share_weighted_m7")
        # Equal 1/7 weights: sum(condition_shares) / 7
        expected = (1.5 + 2 + 10 + 20 + 5 + 3 + 7) / 7.0
        self.assertAlmostEqual(ma["m7"], expected, places=3)
        self.assertAlmostEqual(ma["category_scores"]["C3"], 10.0, places=4)
        sc = b["score"]
        self.assertIn("trigger_v2", sc["categories"]["C1"])
        self.assertIn("anteil_pct", sc["categories"]["C1"])
        self.assertAlmostEqual(sc["categories"]["C1"]["anteil_pct"], 1.5, places=4)
        self.assertAlmostEqual(sc["categories"]["C3"]["anteil_pct"], 10.0, places=4)
        self.assertAlmostEqual(sc["m7_anteil_pct_gewichtet"], ma["m7"], places=3)
        self.assertAlmostEqual(sc["m7_trigger_v2"], b["m7"], places=4)

    def test_trigger_policy_compares_anteil_to_bars_not_heuristic_trigger(self) -> None:
        """Bars apply to operational %-shares; high trigger_v2 alone must not fire."""
        from despaghettify.tools.metrics_bundle import build_metrics_bundle

        setup = {
            "schema_version": 1,
            "trigger_bars": {"C1": 50, "C2": 50, "C3": 50, "C4": 50, "C5": 50, "C6": 50, "C7": 50},
            "weights": {"C1": 0.2, "C2": 0.1, "C3": 0.2, "C4": 0.15, "C5": 0.1, "C6": 0.15, "C7": 0.1},
            "m7_ref": 50.0,
        }
        ast = {
            "total_functions": 100,
            "count_over_100_lines": 10,
            "count_over_50_lines": 20,
            "count_nesting_ge_6": 2,
            "count_nesting_ge_4": 2,
            "count_functions_magic_int_literals_ge_5": 5,
            "count_functions_duplicate_name_across_files": 3,
            "count_functions_control_flow_heavy": 7,
            "c1_files_in_import_cycles_pct": 1.5,
            "c1_import_graph_files": 200,
            "c1_files_in_cycles": 3,
        }
        b = build_metrics_bundle(check_payload={"ast": ast}, setup=setup)
        self.assertEqual(b.get("trigger_policy_basis"), "anteil_pct")
        # Heuristic C3 is high, but bar 50 is compared to true share 10% → no fire on C3
        self.assertFalse(b["per_category_trigger_fires"]["C3"])
        self.assertFalse(b["per_category_trigger_fires"]["C4"])
        self.assertFalse(b["trigger_policy_fires"])
        # Heuristic C3 still high vs modest true share (policy uses anteil, not this column)
        self.assertGreater(b["category_scores"]["C3"], b["score"]["categories"]["C3"]["anteil_pct"])

    def test_trigger_policy_fires_when_anteil_exceeds_bar(self) -> None:
        """Verify that trigger policy fires when anteil exceeds bar works
        as expected.
        """
        from despaghettify.tools.metrics_bundle import build_metrics_bundle

        setup = {
            "schema_version": 1,
            "trigger_bars": {"C1": 50, "C2": 50, "C3": 50, "C4": 5.0, "C5": 50, "C6": 50, "C7": 50},
            "weights": {f"C{i}": 1.0 / 7 for i in range(1, 8)},
            "m7_ref": 100.0,
        }
        ast = {
            "total_functions": 100,
            "count_over_100_lines": 0,
            "count_over_50_lines": 10,
            "count_nesting_ge_6": 0,
            "count_nesting_ge_4": 0,
            "c1_files_in_import_cycles_pct": 0.0,
        }
        b = build_metrics_bundle(check_payload={"ast": ast}, setup=setup)
        self.assertTrue(b["per_category_trigger_fires"]["C4"])  # 10% > 5

    def test_build_bundle_source_v2(self) -> None:
        """Verify that build bundle source v2 works as expected.
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
        self.assertEqual(b["source"], "ast_heuristic_v2")
        self.assertFalse(b["trigger_policy_fires"])
        self.assertIn("score", b)
        self.assertEqual(len(b["score"]["categories"]), 7)
        self.assertIn("literal_rates", b)
        self.assertIn("plain_language_de", b)
        self.assertEqual(b["literal_rates"]["functions_over_100_lines_pct"], 0.0)
        self.assertEqual(b["literal_rates"]["condition_shares_pct"]["C3"], 0.0)
        self.assertIn("100 AST-Zeilen", b["plain_language_de"]["C3"])


if __name__ == "__main__":
    unittest.main()
