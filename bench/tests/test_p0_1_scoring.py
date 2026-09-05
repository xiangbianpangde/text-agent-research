"""P0.1 regression tests for coverage and certification safety."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from bench.evaluator import ScenarioResult, evaluate_benchmark


class EvaluatorSafetyTests(unittest.TestCase):
    def test_empty_metrics_are_na_not_perfect(self) -> None:
        metrics = evaluate_benchmark(
            [],
            required_tracks=["Track-A"],
            required_scenario_ids=["S01"],
        )

        self.assertIsNone(metrics.composite_score)
        self.assertIsNone(metrics.pgem)
        self.assertIsNone(metrics.vlp)
        self.assertIsNone(metrics.sf1)
        self.assertIsNone(metrics.if1)
        self.assertIsNone(metrics.fcaa)
        self.assertIsNone(metrics.zhr)
        self.assertFalse(metrics.certification_eligible)
        self.assertFalse(metrics.iqg_passed)
        self.assertEqual(metrics.tier, "N/A")
        self.assertIn("NO_RESULTS", metrics.ineligible_reasons)

    def test_partial_run_cannot_receive_tier(self) -> None:
        result = ScenarioResult(
            scenario_id="S01",
            track="Track-A",
            name="single diagnostic",
            passed=True,
            score=1.0,
            version_correct=True,
            graph_exact_match=True,
            stale_tp=1,
            impact_tp=1,
            is_fail_closed_expected=True,
            fail_closed_satisfied=True,
        )
        metrics = evaluate_benchmark(
            [result],
            evaluation_mode="diagnostic_partial",
            required_tracks=["Track-A"],
            required_scenario_ids=["S01"],
        )

        self.assertEqual(metrics.composite_score, 100.0)
        self.assertTrue(metrics.integrity_gate_passed)
        self.assertFalse(metrics.certification_eligible)
        self.assertFalse(metrics.iqg_passed)
        self.assertEqual(metrics.tier, "N/A")
        self.assertIn("PARTIAL_EVALUATION", metrics.ineligible_reasons)

    def test_missing_metric_blocks_integrity_gate(self) -> None:
        result = ScenarioResult(
            scenario_id="S01",
            track="Track-A",
            name="coverage without integrity evidence",
            passed=True,
            score=1.0,
        )
        metrics = evaluate_benchmark(
            [result],
            required_tracks=["Track-A"],
            required_scenario_ids=["S01"],
        )

        self.assertTrue(metrics.certification_eligible)
        self.assertFalse(metrics.integrity_gate_passed)
        self.assertFalse(metrics.iqg_passed)
        self.assertEqual(metrics.tier, "CONFORMANCE-FAIL")

    def test_complete_internal_suite_can_only_conformance_pass(self) -> None:
        result = ScenarioResult(
            scenario_id="S01",
            track="Track-A",
            name="complete synthetic contract",
            passed=True,
            score=1.0,
            version_correct=True,
            graph_exact_match=True,
            stale_tp=1,
            impact_tp=1,
            is_fail_closed_expected=True,
            fail_closed_satisfied=True,
        )
        metrics = evaluate_benchmark(
            [result],
            required_tracks=["Track-A"],
            required_scenario_ids=["S01"],
        )

        self.assertTrue(metrics.certification_eligible)
        self.assertTrue(metrics.iqg_passed)
        self.assertEqual(metrics.tier, "CONFORMANCE-PASS")
        self.assertNotIn("S-Tier", metrics.tier_name)


class CliSafetyTests(unittest.TestCase):
    @staticmethod
    def _run_json(*args: str) -> dict:
        completed = subprocess.run(
            [sys.executable, "-m", "bench", *args, "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def test_single_hardcoded_scenario_is_diagnostic_only(self) -> None:
        report = self._run_json("--scenario", "S03")

        self.assertEqual(report["total_scenarios"], 1)
        self.assertEqual(report["composite_score"], 100.0)
        self.assertEqual(report["evaluation_mode"], "diagnostic_partial")
        self.assertFalse(report["certification_eligible"])
        self.assertFalse(report["iqg_passed"])
        self.assertEqual(report["tier"], "N/A")
        self.assertIsNone(report["metrics"]["pgem"])

    def test_track_filter_runs_only_the_selected_track(self) -> None:
        report = self._run_json("--track", "Track1_DefinitionProvenance")

        self.assertEqual(report["total_scenarios"], 6)
        self.assertEqual(
            {scenario["track"] for scenario in report["scenarios"]},
            {"Track1_DefinitionProvenance"},
        )
        self.assertEqual(report["evaluation_mode"], "diagnostic_partial")
        self.assertEqual(report["tier"], "N/A")
        self.assertFalse(report["certification_eligible"])

    def test_researchctl_wrapper_emits_one_json_document(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "researchctl.cli",
                "--root",
                "fixture",
                "bench",
                "--scenario",
                "S03",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(completed.stdout)

        self.assertEqual(report["evaluation_mode"], "diagnostic_partial")
        self.assertEqual(report["tier"], "N/A")


if __name__ == "__main__":
    unittest.main()
