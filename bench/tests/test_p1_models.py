"""Unit tests for task-family/v1 model, families, and release identity chain."""
from __future__ import annotations

import unittest

from bench.dsl.cjson import bench_cjson_digest
from bench.generator import identity as ident
from bench.generator.families import FAMILIES, all_families, get_family
from bench.generator.models import (
    B1_OPERATIONS,
    TaskFamilyError,
    build_family_identity,
    family_body_digest,
    family_identity_digest,
    validate_task_family,
)


class TaskFamilyModelTests(unittest.TestCase):
    def test_all_eight_families_validate(self) -> None:
        fams = all_families()
        self.assertEqual([f["family_id"] for f in fams], [f"F{i:02d}" for i in range(1, 9)])
        for fam in fams:
            self.assertEqual(fam["family_version"], "1.0.0")

    def test_unknown_field_rejected(self) -> None:
        fam = dict(get_family("F01"))
        fam["gold_answer"] = "cheating"
        with self.assertRaises(TaskFamilyError):
            validate_task_family(fam)

    def test_missing_field_rejected(self) -> None:
        fam = dict(get_family("F01"))
        del fam["capability"]
        with self.assertRaises(TaskFamilyError):
            validate_task_family(fam)

    def test_no_gold_or_score_fields(self) -> None:
        forbidden = {"gold", "expected", "score", "tp", "fp", "fn"}
        for fam in all_families():
            for key in fam:
                self.assertNotIn(key.lower(), forbidden)
            # no requirement/predicate may positively reference gold or scores
            for key in ("positive_requirements", "generation_acceptance_predicates"):
                for item in fam[key]:
                    self.assertNotIn("gold", item.lower())
                    self.assertNotIn("score", item.lower())

    def test_subvariant_parameter_closed_set(self) -> None:
        fam = dict(get_family("F01"))
        fam["subvariant_schedule"] = [
            {"subvariant_id": "x", "weight": 1, "parameters": {"gold_bias": 1}},
        ]
        with self.assertRaises(TaskFamilyError):
            validate_task_family(fam)

        fam2 = dict(get_family("F01"))
        fam2["subvariant_schedule"] = [
            {"subvariant_id": "x", "weight": 1, "parameters": {"noise_rate_ppm": -5}},
        ]
        with self.assertRaises(TaskFamilyError):
            validate_task_family(fam2)

    def test_operation_allowlist_closed(self) -> None:
        fam = dict(get_family("F02"))
        fam["operation_allowlist"] = ["make_gold"]
        with self.assertRaises(TaskFamilyError):
            validate_task_family(fam)
        self.assertEqual(len(B1_OPERATIONS), 21)

    def test_identity_chain(self) -> None:
        fam = get_family("F03")
        body = family_body_digest(fam)
        identity = build_family_identity(fam)
        self.assertEqual(identity["family_id"], "F03")
        self.assertEqual(identity["family_version"], fam["family_version"])
        self.assertEqual(identity["family_body_digest"], body)
        digest = family_identity_digest(fam)
        self.assertTrue(digest.startswith("sha256:"))
        # deterministic
        self.assertEqual(family_identity_digest(get_family("F03")), digest)


class ReleaseIdentityTests(unittest.TestCase):
    def test_generator_config_digest_stable(self) -> None:
        d1 = ident.generator_config_digest()
        d2 = ident.generator_config_digest()
        self.assertEqual(d1, d2)
        cfg = ident.build_generator_config()
        self.assertEqual(cfg["attempt_limit"], 64)
        self.assertEqual(bench_cjson_digest(cfg), d1)

    def test_instance_descriptor_and_display_id(self) -> None:
        d = ident.build_instance_descriptor(
            attempt=0,
            family_digest="sha256:" + "a" * 64,
            family_id="F01",
            family_version="1.0.0",
            fixture_tree_digest="sha256:" + "b" * 64,
            oracle_manifest_digest="sha256:" + "c" * 64,
            ordinal=0,
            query_registry_digest="sha256:" + "d" * 64,
            scenario_action_digest="sha256:" + "e" * 64,
            source_tree_digest="sha256:" + "f" * 64,
            split="public",
        )
        dg = ident.instance_digest(d)
        did = ident.display_id(d)
        self.assertTrue(dg.startswith("sha256:"))
        self.assertTrue(did.startswith("RCTL1-F01-public-0-"))
        self.assertEqual(len(did.removeprefix(f"RCTL1-F01-public-0-")), 24)
        # determinism
        d2 = ident.build_instance_descriptor(
            attempt=0,
            family_digest="sha256:" + "a" * 64,
            family_id="F01",
            family_version="1.0.0",
            fixture_tree_digest="sha256:" + "b" * 64,
            oracle_manifest_digest="sha256:" + "c" * 64,
            ordinal=0,
            query_registry_digest="sha256:" + "d" * 64,
            scenario_action_digest="sha256:" + "e" * 64,
            source_tree_digest="sha256:" + "f" * 64,
            split="public",
        )
        self.assertEqual(ident.instance_digest(d2), dg)

    def test_display_id_invalid_split(self) -> None:
        with self.assertRaises(ValueError):
            ident.build_instance_descriptor(
                attempt=0,
                family_digest="sha256:" + "a" * 64,
                family_id="F01",
                family_version="1.0.0",
                fixture_tree_digest="sha256:" + "b" * 64,
                oracle_manifest_digest="sha256:" + "c" * 64,
                ordinal=0,
                query_registry_digest="sha256:" + "d" * 64,
                scenario_action_digest="sha256:" + "e" * 64,
                source_tree_digest="sha256:" + "f" * 64,
                split="hidden-evil",
            )

    def test_lockfile_ordering_and_size(self) -> None:
        entries = []
        for fid in [f"F{i:02d}" for i in range(1, 9)]:
            for split in ("local-hidden", "private", "public"):  # deliberately unsorted
                for ordinal in range(6):
                    entries.append({
                        "family_id": fid,
                        "split": split,
                        "ordinal": ordinal,
                        "instance_digest": f"sha256:{fid}{split}{ordinal}".ljust(71, "0")[:71],
                    })
        # make it exactly 144 by extending F06 to 8 and trimming F07 to 4 adjustments:
        # simpler: build proper quota-based set
        quota = {"F01": 6, "F02": 6, "F03": 6, "F04": 6, "F05": 6, "F06": 8, "F07": 4, "F08": 6}
        entries = []
        for fid, n in quota.items():
            for split in ("public", "private", "local-hidden"):
                for ordinal in range(n):
                    entries.append({
                        "family_id": fid,
                        "split": split,
                        "ordinal": ordinal,
                        "instance_digest": "sha256:" + (f"{fid}{split}{ordinal}".encode().hex() * 8)[:64],
                    })
        self.assertEqual(len(entries), 144)
        lock = ident.build_release_lockfile(entries)
        self.assertEqual(len(lock["entries"]), 144)
        # ordering check
        split_rank = {"public": 0, "private": 1, "local-hidden": 2}
        keys = [(e["family_id"], split_rank[e["split"]], e["ordinal"]) for e in lock["entries"]]
        self.assertEqual(keys, sorted(keys))
        # determinism
        lock2 = ident.build_release_lockfile(entries)
        self.assertEqual(ident.lockfile_digest(lock), ident.lockfile_digest(lock2))

    def test_lockfile_size_enforced(self) -> None:
        with self.assertRaises(ValueError):
            ident.build_release_lockfile([])

    def test_release_identity(self) -> None:
        fams = all_families()
        identities = [build_family_identity(f) for f in fams]
        quota = {"F01": 6, "F02": 6, "F03": 6, "F04": 6, "F05": 6, "F06": 8, "F07": 4, "F08": 6}
        entries = []
        for fam in fams:
            fid = fam["family_id"]
            for split in ("public", "private", "local-hidden"):
                for ordinal in range(quota[fid]):
                    entries.append({
                        "family_id": fid,
                        "split": split,
                        "ordinal": ordinal,
                        "instance_digest": "sha256:" + (f"{fid}{split}{ordinal}".encode().hex() * 8)[:64],
                    })
        lock = ident.build_release_lockfile(entries)
        rel = ident.build_release_identity(
            b1_api_digest="sha256:e8cf1488cc32be80a53d8c8e803d9182c59623abd488c564ce504655741f8e1e",
            family_identities=identities,
            lockfile=lock,
        )
        dg = ident.release_digest(rel)
        self.assertTrue(dg.startswith("sha256:"))
        self.assertEqual(rel["release_id"], "RCTL-P1-B1-2026-01")
        self.assertEqual(len(rel["family_identities"]), 8)

        # wrong count rejected
        with self.assertRaises(ValueError):
            ident.build_release_identity(
                b1_api_digest="sha256:" + "0" * 64,
                family_identities=identities[:7],
                lockfile=lock,
            )
        # wrong order rejected
        with self.assertRaises(ValueError):
            ident.build_release_identity(
                b1_api_digest="sha256:" + "0" * 64,
                family_identities=list(reversed(identities)),
                lockfile=lock,
            )


if __name__ == "__main__":
    unittest.main()
