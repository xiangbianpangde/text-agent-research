"""P0.3A trust-boundary and anchor acceptance tests."""
from __future__ import annotations

import ast
import copy
import inspect
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bench.dsl.executor import ExecutionRecord, materialize_overlay
from bench.dsl.loader import ScenarioContractError, load_scenario, validate_prediction, validate_scenario
from bench.evaluator import ScenarioResult, evaluate_benchmark
from bench.evaluators.graph import graph_exact_match
from bench.evaluators.scenario import evaluate_scenario
from bench.evaluators.sets import set_confusion
from bench.oracle.compiler import compile_gold
from bench.oracle.manifest import load_manifest, validate_manifest
from bench.runner import ORACLE_ANCHOR_IDS, REQUIRED_SCENARIO_IDS, run_oracle_scenario
from bench.scenarios import TRACKS


ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "bench" / "packs" / "p0_seed_v1"


def prediction(capture_id: str, **updates):
    value = {
        "schema_version": "prediction/v1",
        "capture_id": capture_id,
        "status": "success",
        "error_semantic": None,
        "warnings": [],
        "errors": [],
        "results": [],
        "provenance_graph": None,
        "asserted_facts": [],
        "evidence": [],
        "retrieval_mode": None,
        "ranking_authority": None,
    }
    value.update(updates)
    return value


class ContractBoundaryTests(unittest.TestCase):
    def test_scenario_and_prediction_cannot_self_award(self) -> None:
        scenario = json.loads((PACK / "scenarios" / "S07.json").read_text())
        scenario["steps"][1]["score"] = 1.0
        with self.assertRaisesRegex(ScenarioContractError, "score"):
            validate_scenario(scenario)

        value = prediction("x")
        value["passed"] = True
        with self.assertRaisesRegex(ScenarioContractError, "passed"):
            validate_prediction(value)

    def test_compiler_api_has_only_manifest_and_actions(self) -> None:
        self.assertEqual(list(inspect.signature(compile_gold).parameters), ["manifest", "actions"])

    def test_gold_is_compiled_before_participant_process_starts(self) -> None:
        from bench.adapters.process import ProcessSUTAdapter
        from bench.oracle import compiler as compiler_module

        events = []
        original_compile = compiler_module.compile_gold
        original_start = ProcessSUTAdapter._start

        def compile_spy(*args, **kwargs):
            events.append("compile")
            return original_compile(*args, **kwargs)

        def start_spy(adapter):
            events.append("start")
            return original_start(adapter)

        with mock.patch.object(compiler_module, "compile_gold", side_effect=compile_spy), mock.patch.object(
            ProcessSUTAdapter, "_start", autospec=True, side_effect=start_spy
        ):
            run_oracle_scenario("S07")
        self.assertLess(events.index("compile"), events.index("start"))

    def test_oracle_and_evaluator_have_no_researchctl_import_or_scenario_branches(self) -> None:
        paths = [ROOT / "bench" / "runner.py"]
        for directory in ("oracle", "dsl", "evaluators"):
            paths.extend((ROOT / "bench" / directory).rglob("*.py"))
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(alias.name == "researchctl" or alias.name.startswith("researchctl.") for alias in node.names), path)
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "") == "researchctl" or (node.module or "").startswith("researchctl."), path)
        evaluator_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "bench" / "evaluators").rglob("*.py"))
        for scenario_id in ORACLE_ANCHOR_IDS:
            self.assertNotIn(f'"{scenario_id}"', evaluator_text)


class CompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(PACK / "oracle-manifest.json")

    def test_all_seven_anchor_gold_documents_are_byte_deterministic(self) -> None:
        self.assertEqual(len(ORACLE_ANCHOR_IDS), 7)
        for scenario_id in ORACLE_ANCHOR_IDS:
            actions = load_scenario(PACK / "scenarios" / f"{scenario_id}.json")
            first = compile_gold(self.manifest, actions)
            second = compile_gold(self.manifest, actions)
            self.assertEqual(first, second)
            self.assertEqual(first["manifest_digest"], self.manifest.digest)

    def test_manifest_metric_change_changes_s12_gold_without_scenario_edit(self) -> None:
        actions = load_scenario(PACK / "scenarios" / "S12.json")
        first = compile_gold(self.manifest, actions)
        changed = copy.deepcopy(self.manifest.document)
        changed["evidence_atoms"][0]["value"] = "0.701"
        second = compile_gold(validate_manifest(changed), actions)
        self.assertNotEqual(first["gold_digest"], second["gold_digest"])
        self.assertNotEqual(first["checkpoints"][0]["evidence"], second["checkpoints"][0]["evidence"])

    def test_topology_changes_impact_and_stale_gold_sets(self) -> None:
        s16 = load_scenario(PACK / "scenarios" / "S16.json")
        s17 = load_scenario(PACK / "scenarios" / "S17.json")
        first_impact = compile_gold(self.manifest, s16)["checkpoints"][0]["impact_set"]
        first_stale = compile_gold(self.manifest, s17)["checkpoints"][0]["stale_set"]
        changed = copy.deepcopy(self.manifest.document)
        changed["relations"] = [row for row in changed["relations"] if row["source_ref"] != "claim:CURRENT#accuracy"]
        changed_manifest = validate_manifest(changed)
        second_impact = compile_gold(changed_manifest, s16)["checkpoints"][0]["impact_set"]
        second_stale = compile_gold(changed_manifest, s17)["checkpoints"][0]["stale_set"]
        self.assertNotEqual(first_impact, second_impact)
        self.assertNotEqual(first_stale, second_stale)

    def test_materialized_seed_hash_is_verified_not_used_as_gold(self) -> None:
        actions = load_scenario(PACK / "scenarios" / "S12.json")
        gold = compile_gold(self.manifest, actions)
        with tempfile.TemporaryDirectory() as tmp:
            bad_pack = Path(tmp) / "pack"
            workspace = Path(tmp) / "workspace"
            shutil.copytree(PACK, bad_pack)
            workspace.mkdir()
            metric = bad_pack / "seed" / "raw" / "EXP-017" / "R052" / "metrics.csv"
            metric.write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ScenarioContractError, "hash mismatch"):
                materialize_overlay(bad_pack, workspace, self.manifest, actions)
        self.assertEqual(gold, compile_gold(self.manifest, actions))


class GenericEvaluatorTests(unittest.TestCase):
    def test_real_set_math_and_extra_graph_edge(self) -> None:
        self.assertEqual(set_confusion({"A", "B", "C"}, {"A", "B"})["fp"], 1)
        gold = {"nodes": [{"ref": "A"}], "edges": []}
        predicted = {"nodes": [{"ref": "A"}], "edges": [{"source_ref": "A", "relation": "fake", "target_ref": "B"}]}
        self.assertFalse(graph_exact_match(predicted, gold))

    def test_wrong_version_and_phantom_authoritative_prediction_fail(self) -> None:
        manifest = load_manifest(PACK / "oracle-manifest.json")
        actions = load_scenario(PACK / "scenarios" / "S07.json")
        gold = compile_gold(manifest, actions)
        capture = prediction(
            "run-binding",
            results=[{"entity_id": "R052"}, {"entity_id": "H003@v999"}],
            asserted_facts=[{"subject": "run:R052", "predicate": "bound_version", "value": "EXP-017@v4"}],
            ranking_authority="authoritative",
        )
        result = evaluate_scenario(gold, ExecutionRecord("S07", predictions={"run-binding": capture}), manifest)
        self.assertFalse(result.passed)
        self.assertFalse(result.version_correct)
        self.assertGreaterEqual(result.civ_count, 1)

    def test_oracle_shadow_forces_ineligible_until_all_33_are_cut_over(self) -> None:
        legacy = [ScenarioResult("S03", TRACKS[0], "legacy", True, 1.0)]
        fake = type("Evaluation", (), {"scenario_id": "S03", "to_dict": lambda self: {"scenario_id": "S03"}})()
        metrics = evaluate_benchmark(
            legacy,
            evaluation_mode="full",
            required_tracks=TRACKS,
            required_scenario_ids=REQUIRED_SCENARIO_IDS,
            oracle_evaluations=[fake],
        )
        self.assertFalse(metrics.certification_eligible)
        self.assertEqual(metrics.tier, "N/A")
        self.assertIn("P0_3_ORACLE_COVERAGE_INCOMPLETE", metrics.ineligible_reasons)


class CrashAnchorTests(unittest.TestCase):
    def test_s31_uses_external_sigkill_and_proves_fixed_point(self) -> None:
        evaluation, _metadata, _gold = run_oracle_scenario("S31")
        self.assertTrue(evaluation.passed, evaluation.to_dict())
        kinds = [row["kind"] for row in evaluation.checks if row["passed"]]
        self.assertIn("external_termination", kinds)
        self.assertGreaterEqual(kinds.count("canonical_state_exact"), 3)
        self.assertGreaterEqual(kinds.count("tx_residue_empty"), 2)


if __name__ == "__main__":
    unittest.main()
