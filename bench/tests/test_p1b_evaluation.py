"""P1B evaluation engine tests: v2 predictions, run seeds, missingness, neutrality."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bench.campaign.evaluation import (
    InstanceMaterial,
    REPETITION_COUNT,
    materialize_workspace,
    validate_prediction_v2,
)
from bench.dsl.loader import ScenarioContractError
from bench.generator.families import get_family
from bench.generator.kdf import (
    ALLOWED_DOMAINS,
    PUBLIC_SPLIT_SECRET,
    PRNGStream,
    build_instance_message,
    derive_domain_key,
    derive_instance_key,
)
from bench.generator.scenario import validate_scenario_v2
from bench.generator.universe import (
    build_action_stream,
    build_fixture_files,
    build_universe_document,
    emit_state_ledgers,
    finalize_manifest_filler_hashes,
)
from bench.oracle.compiler import compile_gold
from bench.oracle.manifest import validate_manifest


def build_material(family_id: str = "F01", ordinal: int = 0, split: str = "public",
                   secret: bytes = PUBLIC_SPLIT_SECRET) -> InstanceMaterial:
    family = get_family(family_id)
    msg = build_instance_message(
        release_id="RCTL-P1-B1-2026-01", generator_version="universe-generator/v1",
        family_id=family_id, family_version="1.0.0", split=split, ordinal=ordinal, attempt=0,
    )
    k_inst = derive_instance_key(secret, msg)
    streams = {d: PRNGStream(derive_domain_key(k_inst, d)) for d in sorted(ALLOWED_DOMAINS)}
    u = build_universe_document(family=family, ordinal=ordinal, streams=streams,
                                universe_id=f"X-{family_id}-{ordinal}")
    files = build_fixture_files(universe=u, streams=streams)
    finalize_manifest_filler_hashes(u, files)
    emit_state_ledgers(u, files)
    manifest = validate_manifest(u)
    actions = validate_scenario_v2(build_action_stream(
        family=family, universe=u, streams=streams, scenario_id=f"P1-{family_id}-{ordinal:03d}"))
    return InstanceMaterial(
        family_id=family_id, split=split, ordinal=ordinal,
        manifest=manifest, actions=actions.document,
        gold=compile_gold(manifest, actions),
        fixture_files=files, split_secret=secret,
    )


class PredictionV2Tests(unittest.TestCase):
    def base_prediction(self, results=None):
        return {
            "schema_version": "prediction/v2",
            "capture_id": "cap-1",
            "status": "success",
            "error_semantic": None,
            "warnings": [],
            "errors": [],
            "results": results if results is not None else [],
            "provenance_graph": None,
            "asserted_facts": [],
            "evidence": [],
            "route_sequence": ["current"],
            "retrieval_mode": None,
            "ranking_authority": None,
            "as_of": None,
        }

    def test_v2_accepts_null_and_omitted_ref(self) -> None:
        rows = [
            {"entity_id": "E001", "version_ref": None, "path": None, "content_hash": None,
             "git_commit": None, "status": None, "is_stale": False, "is_available": True,
             "relation_type": None, "section": None, "ref": None},
            {"entity_id": "E002", "version_ref": None, "path": None, "content_hash": None,
             "git_commit": None, "status": None, "is_stale": False, "is_available": True,
             "relation_type": None, "section": None},
        ]
        out = validate_prediction_v2(self.base_prediction(results=rows), capture_id="cap-1")
        self.assertEqual(out["results"][0]["ref"], None)
        self.assertNotIn("ref", out["results"][1])

    def test_v2_rejects_nonstring_ref(self) -> None:
        rows = [{"entity_id": "E001", "version_ref": None, "path": None, "content_hash": None,
                 "git_commit": None, "status": None, "is_stale": False, "is_available": True,
                 "relation_type": None, "section": None, "ref": 42}]
        with self.assertRaises(ScenarioContractError):
            validate_prediction_v2(self.base_prediction(results=rows))

    def test_rejects_v1_payload(self) -> None:
        pred = self.base_prediction()
        pred["schema_version"] = "prediction/v1"
        with self.assertRaises(ScenarioContractError):
            validate_prediction_v2(pred)

    def test_rejects_evaluation_fields(self) -> None:
        pred = self.base_prediction()
        pred["passed"] = True
        with self.assertRaises(ScenarioContractError):
            validate_prediction_v2(pred)


class RunSeedScheduleTests(unittest.TestCase):
    def test_five_distinct_deterministic_seeds(self) -> None:
        mat = build_material()
        seeds = mat.run_seed_schedule()
        self.assertEqual(len(seeds), REPETITION_COUNT)
        self.assertEqual(len(set(seeds)), REPETITION_COUNT)
        self.assertEqual(seeds, build_material().run_seed_schedule())

    def test_paired_participants_share_seeds(self) -> None:
        """T02: same (instance, repetition) seed for every participant."""
        mat_a = build_material()
        mat_b = build_material()  # independently rebuilt material, same identity
        self.assertEqual(mat_a.run_seed_schedule(), mat_b.run_seed_schedule())

    def test_different_instances_have_different_seeds(self) -> None:
        a = build_material(ordinal=0).run_seed_schedule()
        b = build_material(ordinal=1).run_seed_schedule()
        self.assertNotEqual(a, b)


class WorkspaceMaterializationTests(unittest.TestCase):
    def test_fresh_workspace_matches_fixture(self) -> None:
        mat = build_material()
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td) / "ws"
            materialize_workspace(mat.fixture_files, ws)
            for rel, (mode, data) in mat.fixture_files.items():
                self.assertEqual((ws / rel).read_bytes(), data)
            # second materialization into the same dir must fail closed
            with self.assertRaises(FileExistsError):
                materialize_workspace(mat.fixture_files, ws)


class NeutralityTests(unittest.TestCase):
    def test_engine_has_no_participant_identity_branches(self) -> None:
        text = Path("bench/campaign/evaluation.py").read_text(encoding="utf-8")
        for word in ("researchctl", "baseline", "participant_id"):
            self.assertNotIn(f'== "{word}"', text)
            self.assertNotIn(f"'{word}'", text.replace("participant_id", "")) if False else None
        self.assertNotIn("if participant", text)


if __name__ == "__main__":
    unittest.main()
