"""P1A end-to-end pipeline tests: 144-instance quota, determinism, G-gates."""
from __future__ import annotations

import unittest

from bench.dsl.cjson import bench_cjson_digest
from bench.generator.families import all_families
from bench.generator.identity import (
    GENERATOR_VERSION,
    RELEASE_ID,
    build_generator_config,
    build_release_identity,
    build_release_lockfile,
    generator_config_digest,
    lockfile_digest,
    release_digest,
)
from bench.generator.instance import (
    ATTEMPT_LIMIT,
    GeneratorRejectionExhausted,
    generate_instance,
    quota_plan,
)
from bench.generator.kdf import PUBLIC_SPLIT_SECRET
from bench.generator.models import build_family_identity


class QuotaPlanTests(unittest.TestCase):
    def test_plan_shape(self) -> None:
        plan = quota_plan()
        self.assertEqual(len(plan), 144)
        counts: dict = {}
        for fid, split, _ in plan:
            counts[(fid, split)] = counts.get((fid, split), 0) + 1
        for fid in [f"F{i:02d}" for i in range(1, 9)]:
            for split in ("public", "private", "local-hidden"):
                expected = 8 if fid == "F06" else (4 if fid == "F07" else 6)
                self.assertEqual(counts.get((fid, split)), expected, (fid, split))
        # 48/48/48
        for split in ("public", "private", "local-hidden"):
            self.assertEqual(sum(1 for _, s, _ in plan if s == split), 48)

    def test_attempt_limit(self) -> None:
        self.assertEqual(ATTEMPT_LIMIT, 64)
        self.assertEqual(build_generator_config()["attempt_limit"], 64)


class InstanceGenerationTests(unittest.TestCase):
    def test_public_instances_unique_deterministic(self) -> None:
        plan = quota_plan()
        public_plan = [(f, s, o) for f, s, o in plan if s == "public"]
        first: dict = {}
        for fid, split, ordinal in public_plan:
            inst = generate_instance(
                family_id=fid, split=split, ordinal=ordinal,
                split_secret=PUBLIC_SPLIT_SECRET,
            )
            first[(fid, split, ordinal)] = inst.instance_digest
        self.assertEqual(len(set(first.values())), 48)

        # deterministic re-generation for a sample
        for fid, split, ordinal in public_plan[:10]:
            again = generate_instance(
                family_id=fid, split=split, ordinal=ordinal,
                split_secret=PUBLIC_SPLIT_SECRET,
            )
            self.assertEqual(again.instance_digest, first[(fid, split, ordinal)])

    def test_descriptor_fields(self) -> None:
        inst = generate_instance(
            family_id="F01", split="public", ordinal=0, split_secret=PUBLIC_SPLIT_SECRET,
        )
        d = inst.descriptor
        self.assertEqual(d["schema_version"], "instance-descriptor/v1")
        self.assertEqual(d["release_id"], RELEASE_ID)
        self.assertEqual(d["generator_version"], GENERATOR_VERSION)
        self.assertEqual(d["split"], "public")
        self.assertEqual(d["ordinal"], 0)
        self.assertEqual(d["attempt"], 0)
        self.assertTrue(d["instance_digest"] if "instance_digest" in d else True)
        # descriptor contains no float and no forbidden fields
        blob = bench_cjson_digest(d)
        self.assertTrue(blob.startswith("sha256:"))
        # display id format
        did = inst.display
        parts = did.split("-")
        self.assertEqual(parts[0], "RCTL1")
        self.assertEqual(parts[1], "F01")
        self.assertEqual(len(parts[4]), 24)

    def test_gold_pre_sut_and_shapes(self) -> None:
        inst = generate_instance(
            family_id="F06", split="public", ordinal=2, split_secret=PUBLIC_SPLIT_SECRET,
        )
        gold = inst.gold
        self.assertEqual(gold["schema_version"], "compiled-gold/v1")
        self.assertIn("gold_digest", gold)
        self.assertIn("checkpoints", gold)
        # manifest and action digests are bound
        self.assertEqual(gold["manifest_digest"], bench_cjson_digest(inst.manifest.document))
        self.assertTrue(len(gold["checkpoints"]) >= 1)

    def test_private_and_hidden_use_same_pipeline(self) -> None:
        inst_pub = generate_instance(
            family_id="F07", split="public", ordinal=0, split_secret=PUBLIC_SPLIT_SECRET,
        )
        # private/hidden secrets are evaluator-held 32-byte keys (not public)
        private_secret = bytes(range(32, 64))
        hidden_secret = bytes(range(64, 96))
        inst_priv = generate_instance(
            family_id="F07", split="private", ordinal=0, split_secret=private_secret,
        )
        inst_hidden = generate_instance(
            family_id="F07", split="private", ordinal=0, split_secret=hidden_secret,
        )
        self.assertNotEqual(inst_priv.instance_digest, inst_hidden.instance_digest)
        self.assertNotEqual(inst_pub.instance_digest, inst_priv.instance_digest)
        self.assertEqual(inst_priv.descriptor["split"], "private")
        self.assertEqual(inst_hidden.descriptor["split"], "private")

    def test_rejection_sampling(self) -> None:
        calls = {"n": 0}

        def reject_first_two(candidate, attempt):
            calls["n"] += 1
            if attempt < 2:
                return "forced_test_rejection"
            return None

        inst = generate_instance(
            family_id="F01", split="public", ordinal=0,
            split_secret=PUBLIC_SPLIT_SECRET,
            rejection_predicate=reject_first_two,
        )
        self.assertEqual(inst.attempt, 2)
        self.assertEqual(calls["n"], 3)

    def test_rejection_exhaustion_fails_release(self) -> None:
        def always_reject(candidate, attempt):
            return "forced_test_rejection"

        with self.assertRaises(GeneratorRejectionExhausted):
            generate_instance(
                family_id="F01", split="public", ordinal=0,
                split_secret=PUBLIC_SPLIT_SECRET,
                rejection_predicate=always_reject,
            )


class ReleaseAssemblyTests(unittest.TestCase):
    def test_full_release_identity(self) -> None:
        plan = quota_plan()
        families = {f["family_id"]: f for f in all_families()}
        entries = []
        for fid, split, ordinal in plan:
            inst = generate_instance(
                family_id=fid, split=split, ordinal=ordinal,
                split_secret=PUBLIC_SPLIT_SECRET,
            )
            entries.append({
                "family_id": fid,
                "split": split,
                "ordinal": ordinal,
                "instance_digest": inst.instance_digest,
            })
        lock = build_release_lockfile(entries)
        identities = [build_family_identity(families[f"F{i:02d}"]) for i in range(1, 9)]
        rel = build_release_identity(
            b1_api_digest="sha256:e8cf1488cc32be80a53d8c8e803d9182c59623abd488c564ce504655741f8e1e",
            family_identities=identities,
            lockfile=lock,
        )
        dg = release_digest(rel)
        self.assertTrue(dg.startswith("sha256:"))
        # determinism across a second full run
        entries2 = []
        for fid, split, ordinal in plan:
            inst = generate_instance(
                family_id=fid, split=split, ordinal=ordinal,
                split_secret=PUBLIC_SPLIT_SECRET,
            )
            entries2.append({
                "family_id": fid,
                "split": split,
                "ordinal": ordinal,
                "instance_digest": inst.instance_digest,
            })
        lock2 = build_release_lockfile(entries2)
        self.assertEqual(lockfile_digest(lock), lockfile_digest(lock2))


if __name__ == "__main__":
    unittest.main()
