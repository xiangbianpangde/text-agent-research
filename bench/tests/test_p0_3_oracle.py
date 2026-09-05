"""P0.3A/B trust-boundary, Gold coverage, and state-machine tests."""
from __future__ import annotations

import ast
import copy
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from bench.adapters import ProcessSUTAdapter
from bench.adapters.process import SUTAdapterError
from bench.dsl.command_codec import encode_operation
from bench.dsl.executor import ExecutionRecord
from bench.dsl.loader import ScenarioContractError, load_pack_registry, load_scenario, validate_prediction, validate_scenario
from bench.evaluator import ScenarioResult, evaluate_benchmark
from bench.evaluators.graph import graph_exact_match
from bench.evaluators.integrity import CIV_CODES, classify_civ
from bench.evaluators.scenario import evaluate_scenario
from bench.evaluators.sets import set_confusion
from bench.evaluators.state import CLE_PROFILE, canonical_index_digest
from bench.oracle.compiler import compile_gold
from bench.packs.p0_seed_v1.build_fixture import build_fixture_archive
from bench.oracle.manifest import ManifestError, load_manifest, validate_manifest
from bench.runner import ORACLE_ANCHOR_IDS, ORACLE_SCENARIO_IDS, REQUIRED_SCENARIO_IDS, run_oracle_scenario
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
        "route_sequence": [],
        "as_of": None,
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
        for scenario_id in ORACLE_SCENARIO_IDS:
            self.assertNotIn(f'"{scenario_id}"', evaluator_text)


class CompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(PACK / "oracle-manifest.json")

    def test_all_four_frozen_json_contracts_validate(self) -> None:
        import jsonschema

        action_schema = json.loads((ROOT / "bench" / "dsl" / "schemas" / "scenario-actions-v1.schema.json").read_text())
        manifest_schema = json.loads((ROOT / "bench" / "oracle" / "schemas" / "oracle-manifest-v1.schema.json").read_text())
        gold_schema = json.loads((ROOT / "bench" / "oracle" / "schemas" / "compiled-gold-v1.schema.json").read_text())
        prediction_schema = json.loads((ROOT / "bench" / "dsl" / "schemas" / "prediction-v1.schema.json").read_text())
        jsonschema.validate(self.manifest.document, manifest_schema)
        jsonschema.validate(prediction("schema-check"), prediction_schema)
        for scenario_id in ORACLE_SCENARIO_IDS:
            document = json.loads((PACK / "scenarios" / f"{scenario_id}.json").read_text())
            jsonschema.validate(document, action_schema)
            jsonschema.validate(
                compile_gold(self.manifest, load_scenario(PACK / "scenarios" / f"{scenario_id}.json")),
                gold_schema,
            )

    def test_pack_registry_is_complete_and_independent_of_legacy_functions(self) -> None:
        registry = load_pack_registry(PACK)
        self.assertEqual(tuple(registry["required_scenario_ids"]), ORACLE_SCENARIO_IDS)
        self.assertEqual(len(registry["required_scenario_ids"]), 33)

    def test_all_33_gold_documents_are_byte_deterministic(self) -> None:
        self.assertEqual(tuple(REQUIRED_SCENARIO_IDS), ORACLE_SCENARIO_IDS)
        self.assertEqual(len(ORACLE_SCENARIO_IDS), 33)
        self.assertEqual(
            {path.stem for path in (PACK / "scenarios").glob("*.json")},
            set(REQUIRED_SCENARIO_IDS),
        )
        for scenario_id in ORACLE_SCENARIO_IDS:
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

    def test_sealed_fixture_hash_is_verified_and_external_fixture_is_ignored(self) -> None:
        import hashlib

        archive = PACK / self.manifest.document["fixture"]["archive"]
        actual = "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(actual, self.manifest.document["fixture"]["content_hash"])
        actions = load_scenario(PACK / "scenarios" / "S12.json")
        gold = compile_gold(self.manifest, actions)
        with tempfile.TemporaryDirectory() as tmp:
            fake_fixture = Path(tmp) / "fixture"
            fake_fixture.mkdir()
            (fake_fixture / "poison.txt").write_text("must not be read", encoding="utf-8")
            evaluation, _metadata, rerun_gold = run_oracle_scenario("S12", str(fake_fixture))
        self.assertEqual(gold, rerun_gold)
        self.assertFalse(evaluation.passed)


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
        phantom = {
            "entity_id": "H003", "version_ref": "H003@v999", "path": None,
            "content_hash": None, "git_commit": None, "status": None,
            "is_stale": False, "relation_type": None, "section": None,
            "is_available": True,
        }
        capture = prediction(
            "run-binding",
            results=[gold["checkpoints"][0]["results"][0], phantom],
            asserted_facts=[{"subject": "run:R052", "predicate": "bound_version", "value": "EXP-017@v4"}],
            ranking_authority="authoritative",
            route_sequence=["current"],
        )
        result = evaluate_scenario(gold, ExecutionRecord("S07", predictions={"run-binding": capture}), manifest)
        self.assertFalse(result.passed)
        self.assertFalse(result.version_correct)
        self.assertGreaterEqual(result.civ_count, 1)

    def test_full_oracle_shadow_coverage_remains_ineligible_until_cutover(self) -> None:
        legacy = [
            ScenarioResult(scenario_id, TRACKS[index % len(TRACKS)], "legacy", True, 1.0)
            for index, scenario_id in enumerate(REQUIRED_SCENARIO_IDS)
        ]
        evaluations = [
            type("Evaluation", (), {"scenario_id": scenario_id, "to_dict": lambda self: {"scenario_id": self.scenario_id}})()
            for scenario_id in REQUIRED_SCENARIO_IDS
        ]
        metrics = evaluate_benchmark(
            legacy,
            evaluation_mode="full",
            required_tracks=TRACKS,
            required_scenario_ids=REQUIRED_SCENARIO_IDS,
            oracle_evaluations=evaluations,
        )
        self.assertEqual(metrics.p0_3_status, "incomplete_p0_3b")
        self.assertEqual(len(metrics.oracle_compiled_scenario_ids), 33)
        self.assertFalse(metrics.certification_eligible)
        self.assertEqual(metrics.tier, "N/A")
        self.assertIn("P0_3_SHADOW_MODE", metrics.ineligible_reasons)
        self.assertNotIn("P0_3_ORACLE_COVERAGE_INCOMPLETE", metrics.ineligible_reasons)
        self.assertIsNone(metrics.composite_score)
        self.assertIsNone(metrics.passed_scenarios)
        self.assertIsNone(metrics.integrity_gate_passed)
        self.assertEqual(metrics.legacy_diagnostic["passed_scenarios"], 33)

    def test_partial_oracle_shadow_reports_incomplete_coverage(self) -> None:
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


class SolAuditRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(PACK / "oracle-manifest.json")

    def _gold(self, scenario_id: str):
        return compile_gold(
            self.manifest,
            load_scenario(PACK / "scenarios" / f"{scenario_id}.json"),
        )

    def test_manifest_temporal_and_reference_authority_is_strict(self) -> None:
        for value in ("not-a-timestamp", "2026-08-01", "2026-08-01T00:00:00"):
            changed = copy.deepcopy(self.manifest.document)
            changed["facts"][0]["occurred_at"] = value
            with self.assertRaisesRegex(ManifestError, "RFC3339"):
                validate_manifest(changed)
        changed = copy.deepcopy(self.manifest.document)
        changed["facts"][1]["value"] = "EV-NOT-FOUND"
        with self.assertRaisesRegex(ManifestError, "unknown event"):
            validate_manifest(changed)
        changed = copy.deepcopy(self.manifest.document)
        changed["queries"] = [row for row in changed["queries"] if row["query_id"] != "Q-S15"] + [
            {**next(row for row in changed["queries"] if row["query_id"] == "Q-S15"), "as_of": "9999-01-01T00:00:00Z"}
        ]
        changed_manifest = validate_manifest(changed)
        with self.assertRaisesRegex(ManifestError, "cutoff"):
            compile_gold(changed_manifest, load_scenario(PACK / "scenarios" / "S15.json"))

    def test_hidden_gold_params_are_rejected_and_semantic_target_is_forbidden(self) -> None:
        scenario = json.loads((PACK / "scenarios" / "S25.json").read_text())
        scenario["steps"][1]["params"]["ref"] = "run:R052"
        with self.assertRaisesRegex(ScenarioContractError, "only query_id"):
            validate_scenario(scenario)

        changed = copy.deepcopy(self.manifest.document)
        query = next(row for row in changed["queries"] if row["query_id"] == "Q-S25")
        query["target_ref"] = "run:R052"
        with self.assertRaisesRegex(ManifestError, "cannot declare target_ref"):
            validate_manifest(changed)

        actions = load_scenario(PACK / "scenarios" / "S25.json")
        original_command = encode_operation("query_text_semantic", actions.steps[1]["params"], self.manifest)
        original_gold = compile_gold(self.manifest, actions)
        visible_change = copy.deepcopy(self.manifest.document)
        next(row for row in visible_change["queries"] if row["query_id"] == "Q-S25")["text"] = "unmatched visible query"
        changed_manifest = validate_manifest(visible_change)
        changed_command = encode_operation("query_text_semantic", actions.steps[1]["params"], changed_manifest)
        changed_gold = compile_gold(changed_manifest, actions)
        self.assertNotEqual(original_command, changed_command)
        self.assertNotEqual(original_gold["gold_digest"], changed_gold["gold_digest"])

    def test_reproducible_fixture_builder_is_root_independent(self) -> None:
        self.assertFalse((PACK / "source").exists())
        self.assertTrue((PACK / "source.tar").is_file())
        import hashlib
        import tarfile
        source_hash = "sha256:" + hashlib.sha256((PACK / "source.tar").read_bytes()).hexdigest()
        self.assertEqual(source_hash, self.manifest.document["fixture"]["source_hash"])
        with tarfile.open(PACK / "source.tar", "r") as archive:
            self.assertFalse(any(Path(member.name).name.startswith("._") for member in archive.getmembers()))
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            h1 = build_fixture_archive(PACK / "source.tar", Path(first) / "fixture.tar")
            h2 = build_fixture_archive(PACK / "source.tar", Path(second) / "fixture.tar")
            self.assertEqual(h1, h2)
            self.assertEqual(h1, self.manifest.document["fixture"]["content_hash"])
        with tempfile.TemporaryDirectory() as contaminated:
            root = Path(contaminated)
            (root / "._poison").write_bytes(b"metadata")
            with self.assertRaisesRegex(ValueError, "AppleDouble"):
                build_fixture_archive(root, root / "out.tar")

    def test_every_manifest_physical_path_is_in_rebuilt_fixture(self) -> None:
        import tarfile
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "fixture.tar"
            build_fixture_archive(PACK / "source.tar", archive)
            with tarfile.open(archive, "r") as handle:
                names = set(handle.getnames())
        for obj in (*self.manifest.document["entities"], *self.manifest.document["artifacts"]):
            path = obj.get("path")
            if path:
                self.assertTrue(path in names or any(name.startswith(path.rstrip("/") + "/") for name in names), obj["ref"])

    def test_correct_fail_closed_refusal_has_no_positive_gold_channels(self) -> None:
        for scenario_id, capture_id, error in (("S06", "ambiguous", "AMBIGUOUS_VERSION"), ("S19", "missing-source", "SOURCE_MISSING")):
            gold = self._gold(scenario_id)
            self.assertNotIn("results", gold["checkpoints"][0])
            capture = prediction(capture_id, status="fail_closed", error_semantic=error)
            result = evaluate_scenario(gold, ExecutionRecord(scenario_id, predictions={capture_id: capture}), self.manifest)
            self.assertTrue(result.passed, result.to_dict())

    def test_attached_answer_on_fail_closed_refusal_fails(self) -> None:
        gold = self._gold("S30")
        capture = prediction("writer-collision", status="error", error_semantic="TX_LOCKED", evidence=[{"fabricated": True}])
        result = evaluate_scenario(gold, ExecutionRecord("S30", predictions={"writer-collision": capture}), self.manifest)
        self.assertFalse(result.passed)

    def test_all_eight_civ_classes_are_computed(self) -> None:
        base = prediction(
            "civ",
            ranking_authority="authoritative",
            results=[
                {"entity_id": "PHANTOM"},
                {"entity_id": "R052", "version_ref": "R052@v999"},
                {"ref": "run:R052", "content_hash": "sha256:fake", "git_commit": "fake"},
            ],
            asserted_facts=[{"subject": "run:R052", "predicate": "invented", "value": True}],
            provenance_graph={"nodes": [], "edges": [{"source_ref": "run:R052", "relation": "fake", "target_ref": "metric:M001"}]},
        )
        checkpoint = {"expected_condition": {"error_semantic": None}}
        codes = {row["code"] for row in classify_civ(base, checkpoint, self.manifest)}

        ambiguity = prediction(
            "amb",
            ranking_authority="authoritative",
            status="success",
            results=[{"ref": "definition:H003@v1"}],
        )
        codes.update(row["code"] for row in classify_civ(
            ambiguity,
            {"expected_condition": {"error_semantic": "AMBIGUOUS_VERSION"}},
            self.manifest,
        ))
        historical = prediction(
            "hist",
            ranking_authority="authoritative",
            status="warning",
            results=[{
                "ref": "organized:EXP-017",
                "content_hash": "sha256:cb064f9775ce8463f9bdc7f4d793d686a15ab05f6979f148d18ffd6c29f49ee5",
                "git_commit": "17a61f69c2a31efdafca0953a6e9d8ee0bfee292",
            }],
        )
        gold = self._gold("S14")["checkpoints"][0]
        codes.update(row["code"] for row in classify_civ(historical, gold, self.manifest))
        self.assertEqual(codes, CIV_CODES)

    def test_dynamic_versions_are_valid_but_nonexistent_versions_are_civ(self) -> None:
        gold = self._gold("S05")
        checkpoint = gold["checkpoints"][0]
        results = []
        for ref in ("definition:H003@v1", "definition:H003@v2", "definition:H003@v3"):
            obj = checkpoint["oracle_state"]["objects"][ref]
            results.append({
                "ref": ref,
                "entity_id": obj["entity_id"], "version_ref": obj["version_ref"],
                "path": obj["path"], "content_hash": obj["content_hash"],
                "git_commit": obj["git_commit"], "status": None, "is_stale": False,
                "relation_type": None, "section": None, "is_available": True,
            })
        capture = prediction("lineage", route_sequence=["current"], results=results)
        result = evaluate_scenario(gold, ExecutionRecord("S05", predictions={"lineage": capture}), self.manifest)
        self.assertTrue(result.passed, result.to_dict())
        self.assertEqual(result.civ_count, 0)
        contradictory = copy.deepcopy(capture)
        contradictory["results"][0]["versioned_ref"] = "CONTRADICT@v999"
        with self.assertRaisesRegex(ScenarioContractError, "extra"):
            validate_prediction(contradictory, capture_id="lineage")

        phantom = prediction(
            "lineage",
            ranking_authority="authoritative",
            results=[{"entity_id": "H003", "version_ref": "H003@v4"}],
        )
        violations = classify_civ(phantom, {"expected_condition": {"error_semantic": None}}, self.manifest)
        self.assertIn("PHANTOM_VERSION_ASSERTED", {row["code"] for row in violations})

    def test_s15_as_of_gold_has_explicit_lifecycle_cutoff(self) -> None:
        from bench.oracle.model import OracleState
        state = OracleState.from_manifest(self.manifest)
        before = state.visible_refs("2026-08-05T00:00:00Z")
        exact = state.visible_refs("2026-08-10T00:00:00Z")
        self.assertNotIn("claim:REPORT-002#accuracy", before)
        self.assertNotIn("historical:REPORT-002:organized", before)
        self.assertIn("claim:REPORT-002#accuracy", exact)
        self.assertIn("historical:REPORT-002:organized", exact)
        changed = copy.deepcopy(self.manifest.document)
        changed["entities"][0]["lifecycle_start"] = "2026-08-15T00:30:00+01:00"
        offset_state = OracleState.from_manifest(validate_manifest(changed))
        self.assertIn("definition:H003@v1", offset_state.visible_refs("2026-08-15T00:00:00Z"))

        checkpoint = self._gold("S15")["checkpoints"][0]
        refs = {row["ref"] for row in checkpoint["results"]}
        self.assertIn("historical:REPORT-002:organized", refs)
        self.assertNotIn("run:R071", refs)
        self.assertNotIn("report:CURRENT", refs)

    def test_result_ref_must_be_string_and_cannot_fallback(self) -> None:
        gold = self._gold("S10")
        checkpoint = gold["checkpoints"][0]
        row = dict(checkpoint["results"][0])
        row["ref"] = 123
        capture = prediction(
            "claim-source",
            status=checkpoint["expected_condition"]["status"],
            error_semantic=checkpoint["expected_condition"]["error_semantic"],
            results=[row],
            ranking_authority=checkpoint["ranking_authority"],
            route_sequence=checkpoint["route_sequence"],
        )
        with self.assertRaisesRegex(ScenarioContractError, "ref must be string"):
            validate_prediction(capture, capture_id="claim-source")
        result = evaluate_scenario(gold, ExecutionRecord("S10", predictions={"claim-source": capture}), self.manifest)
        self.assertFalse(result.passed)
        self.assertTrue(any(check["kind"] == "prediction_contract" for check in result.checks))

    def test_result_metadata_and_opaque_rows_cannot_false_pass(self) -> None:
        gold = self._gold("S10")
        expected = gold["checkpoints"][0]["results"]
        capture = prediction(
            "claim-source",
            results=[{**row, "status": "COMPLETELY_WRONG"} for row in expected],
        )
        result = evaluate_scenario(gold, ExecutionRecord("S10", predictions={"claim-source": capture}), self.manifest)
        self.assertFalse(result.passed)

    def test_s07_fabricated_hash_and_commit_fail_with_civ(self) -> None:
        gold = self._gold("S07")
        capture = prediction(
            "run-binding",
            ranking_authority="authoritative",
            route_sequence=["current"],
            results=[{**gold["checkpoints"][0]["results"][0], "content_hash": "sha256:fake", "git_commit": "fake"}],
            asserted_facts=[{"subject": "run:R052", "predicate": "bound_version", "value": "EXP-017@v1"}],
        )
        result = evaluate_scenario(gold, ExecutionRecord("S07", predictions={"run-binding": capture}), self.manifest)
        self.assertFalse(result.passed)
        self.assertEqual(
            {row["code"] for row in result.civ_violations},
            {"FABRICATED_CONTENT_HASH", "FABRICATED_GIT_COMMIT"},
        )

    def test_s14_current_source_substitution_fails_with_civ(self) -> None:
        gold = self._gold("S14")
        capture = prediction(
            "historical-source",
            status="warning",
            ranking_authority="authoritative",
            route_sequence=["sources"],
            results=[{
                "ref": "organized:EXP-017", "entity_id": "ORG-EXP017",
                "version_ref": "ORG-EXP017@v3", "path": "organized/EXP-017/result.md",
                "content_hash": "sha256:cb064f9775ce8463f9bdc7f4d793d686a15ab05f6979f148d18ffd6c29f49ee5",
                "git_commit": "17a61f69c2a31efdafca0953a6e9d8ee0bfee292",
                "status": None, "is_stale": False, "relation_type": "based_on",
                "section": None, "is_available": True,
            }],
        )
        result = evaluate_scenario(gold, ExecutionRecord("S14", predictions={"historical-source": capture}), self.manifest)
        self.assertFalse(result.passed)
        self.assertIn("HISTORICAL_SOURCE_SUBSTITUTION", {row["code"] for row in result.civ_violations})

    def test_s15_rejects_post_cutoff_fact(self) -> None:
        gold = self._gold("S15")
        checkpoint = gold["checkpoints"][0]
        capture = prediction(
            "as-of-history",
            ranking_authority="authoritative",
            route_sequence=["history"],
            as_of="2026-08-15T00:00:00Z",
            results=checkpoint["results"],
            asserted_facts=[
                *checkpoint["asserted_facts"],
                next(row for row in self.manifest.document["facts"] if row["fact_id"] == "fact:R051:invalid-reason"),
            ],
        )
        result = evaluate_scenario(gold, ExecutionRecord("S15", predictions={"as-of-history": capture}), self.manifest)
        self.assertFalse(result.passed)
        self.assertIn(
            "UNVERIFIED_FACT_ASSERTED_AS_AUTHORITATIVE",
            {row["code"] for row in result.civ_violations},
        )

    def test_s18_universal_stale_fails(self) -> None:
        gold = self._gold("S18")
        checkpoint = gold["checkpoints"][0]
        capture = prediction(
            "unrelated-state",
            ranking_authority="authoritative",
            route_sequence=["current"],
            results=[{**checkpoint["results"][0], "is_stale": True}],
            asserted_facts=checkpoint["asserted_facts"],
        )
        result = evaluate_scenario(gold, ExecutionRecord("S18", predictions={"unrelated-state": capture}), self.manifest)
        self.assertFalse(result.passed)

    def test_integrity_issue_requires_exact_ref(self) -> None:
        for scenario_id, capture_id, code, status, ref in (
            ("S20", "tamper-detection", "HASH_MISMATCH", "fail_closed", None),
            ("S21", "orphan-detection", "ORPHAN_ARTIFACT", "warning", "wrong/ref"),
        ):
            gold = self._gold(scenario_id)
            capture = prediction(
                capture_id,
                status=status,
                error_semantic=code if status == "fail_closed" else None,
                route_sequence=["reconcile"],
                errors=[{"code": code, "ref": ref}] if status == "fail_closed" else [],
                warnings=[{"code": code, "ref": ref}] if status == "warning" else [],
            )
            result = evaluate_scenario(gold, ExecutionRecord(scenario_id, predictions={capture_id: capture}), self.manifest)
            self.assertFalse(result.passed, scenario_id)

    def test_s28_requires_new_process_and_both_routes(self) -> None:
        gold = self._gold("S28")
        current_checkpoint = next(row for row in gold["checkpoints"] if row["capture_id"] == "project-current")
        current = prediction(
            "project-current",
            ranking_authority="authoritative",
            route_sequence=["current"],
            results=current_checkpoint["results"],
            asserted_facts=current_checkpoint["asserted_facts"],
        )
        execution = ExecutionRecord(
            "S28",
            predictions={"project-current": current},
            observations={"new-session": {"session_id": "fresh-session-s28", "process_restarted": True}},
        )
        self.assertFalse(evaluate_scenario(gold, execution, self.manifest).passed)

    def test_s31_nonempty_reconcile_result_fails(self) -> None:
        gold = {
            "scenario_id": "state",
            "gold_digest": "sha256:test",
            "checkpoints": [{
                "capture_id": "reconcile",
                "expected_condition": {"status": "success", "error_semantic": None, "behavior": "success_answer"},
                "results": [],
            }],
        }
        capture = prediction("reconcile", results=[{"ref": "run:R052"}])
        result = evaluate_scenario(gold, ExecutionRecord("state", predictions={"reconcile": capture}), self.manifest)
        self.assertFalse(result.passed)


class RuntimeIsolationTests(unittest.TestCase):
    def test_cle_reads_one_transaction_snapshot_during_concurrent_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "cle.sqlite")
            connection = sqlite3.connect(db_path)
            connection.execute("PRAGMA journal_mode=WAL")
            for table, columns, _sort_keys in CLE_PROFILE:
                definitions = ",".join(f'"{column}" TEXT' for column in columns)
                connection.execute(f'CREATE TABLE "{table}" ({definitions})')
            connection.execute("INSERT INTO documents(id) VALUES ('D1')")
            connection.commit()
            connection.close()
            baseline = canonical_index_digest(db_path)
            wrote = False

            def after_table(table: str) -> None:
                nonlocal wrote
                if table != "documents" or wrote:
                    return
                wrote = True
                writer = sqlite3.connect(db_path)
                writer.execute("INSERT INTO events(event_id) VALUES ('EV-LATE')")
                writer.commit()
                writer.close()

            during = canonical_index_digest(db_path, _after_table=after_table)
            after = canonical_index_digest(db_path)
            self.assertEqual(during, baseline)
            self.assertNotEqual(after, baseline)

    @unittest.skipUnless(os.name == "posix", "process-group cleanup requires POSIX")
    def test_timeout_kills_participant_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "child.pid"
            adapter = ProcessSUTAdapter(
                [sys.executable, "-m", "bench.tests.fixtures.hanging_sut"],
                cwd=str(ROOT),
                env={"BENCH_CHILD_PID_FILE": str(pid_file)},
                request_timeout_ms=30_000,
            )
            try:
                adapter.prepare(tmp)
                adapter.health()
                with self.assertRaisesRegex(SUTAdapterError, "timed out"):
                    adapter.invoke(["hang"], timeout_ms=100)
                child_pid = int(pid_file.read_text())
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    status = subprocess.run(
                        ["ps", "-o", "stat=", "-p", str(child_pid)],
                        capture_output=True,
                        text=True,
                    ).stdout.strip()
                    if not status or status.startswith("Z"):
                        break
                    time.sleep(0.05)
                self.assertTrue(not status or status.startswith("Z"), status)
            finally:
                adapter.shutdown()


class OracleOnlyCutoverTests(unittest.TestCase):
    @staticmethod
    def _evaluation(passed: bool):
        from bench.evaluators.scenario import OracleScenarioEvaluation
        return OracleScenarioEvaluation(
            scenario_id="S01", passed=passed, score=1.0 if passed else 0.0,
            checks=[{"kind": "synthetic", "passed": passed}], civ_count=0,
        )

    def test_default_cli_never_calls_legacy_runner(self) -> None:
        import contextlib
        import io
        import bench.cli as cli_module

        legacy_runner = mock.Mock(side_effect=AssertionError("legacy runner called"))
        registration = SimpleNamespace(scenario_id="S01", track=TRACKS[0], runner=legacy_runner)
        with mock.patch.object(cli_module, "ORACLE_SCENARIO_IDS", ("S01",)), mock.patch.object(
            cli_module, "REQUIRED_SCENARIO_IDS", ["S01"]
        ), mock.patch.object(cli_module, "SCENARIO_REGISTRY", [registration]), mock.patch.object(
            cli_module, "run_oracle_scenario", return_value=(self._evaluation(True), {"adapter": "stub"}, {})
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                cli_module.main(["--json"])
        report = json.loads(output.getvalue())
        legacy_runner.assert_not_called()
        self.assertEqual(report["evaluation_engine"], "oracle_only")
        self.assertEqual(report["legacy_diagnostic"], {})

    def test_legacy_flag_is_diagnostic_and_cannot_change_formal_result(self) -> None:
        import contextlib
        import io
        import bench.cli as cli_module

        legacy_runner = mock.Mock(return_value=ScenarioResult("S01", TRACKS[0], "legacy", True, 1.0))
        registration = SimpleNamespace(scenario_id="S01", track=TRACKS[0], runner=legacy_runner)

        class Sandbox:
            sut_metadata = {"adapter": "stub"}
            def __init__(self, *args, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): return None

        with mock.patch.object(cli_module, "ORACLE_SCENARIO_IDS", ("S01",)), mock.patch.object(
            cli_module, "REQUIRED_SCENARIO_IDS", ["S01"]
        ), mock.patch.object(cli_module, "SCENARIO_REGISTRY", [registration]), mock.patch.object(
            cli_module, "BenchmarkSandbox", Sandbox
        ), mock.patch.object(
            cli_module, "run_oracle_scenario", return_value=(self._evaluation(False), {"adapter": "stub"}, {})
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                cli_module.main(["--legacy-diagnostic", "--json"])
        report = json.loads(output.getvalue())
        legacy_runner.assert_called_once()
        self.assertEqual(report["passed_scenarios"], 0)
        self.assertEqual(report["legacy_diagnostic"]["passed_scenarios"], 1)
        self.assertEqual(report["score_provenance"], "independent_oracle")


class StateAnchorTests(unittest.TestCase):
    def test_s29_rejects_participant_schema_incompatible_with_frozen_cle(self) -> None:
        evaluation, _metadata, _gold = run_oracle_scenario("S29")
        self.assertFalse(evaluation.passed)
        self.assertTrue(any("CLE schema mismatch" in error for error in evaluation.execution_errors))

    def test_s30_observes_real_lock_collision(self) -> None:
        evaluation, _metadata, _gold = run_oracle_scenario("S30")
        self.assertTrue(evaluation.passed, evaluation.to_dict())
        self.assertTrue(evaluation.fail_closed_expected)
        self.assertTrue(evaluation.fail_closed_satisfied)

    def test_s31_uses_external_sigkill_and_proves_fixed_point(self) -> None:
        evaluation, _metadata, _gold = run_oracle_scenario("S31")
        kinds = [row["kind"] for row in evaluation.checks if row["passed"]]
        self.assertIn("external_termination", kinds)
        self.assertGreaterEqual(kinds.count("canonical_state_exact"), 3)
        self.assertGreaterEqual(kinds.count("tx_residue_empty"), 2)
        self.assertFalse(evaluation.passed)
        self.assertTrue(any(check["kind"] == "result_set_exact" and not check["passed"] for check in evaluation.checks))


if __name__ == "__main__":
    unittest.main()
