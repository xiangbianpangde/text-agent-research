"""P1A G-gate mechanical acceptance suite (G01–G08, §16).

Each test captures one gate with executable evidence; run as a whole to
declare `candidate_p1a` (allowed claim: "Dynamic B1 benchmark candidate").
"""
from __future__ import annotations

import unittest
from pathlib import Path

from bench.generator.identity import instance_digest
from bench.generator.instance import (
    ATTEMPT_LIMIT,
    GeneratorRejectionExhausted,
    generate_instance,
    quota_plan,
)
from bench.generator.kdf import PUBLIC_SPLIT_SECRET
from bench.generator.release import public_plan, verify_public_root

COMMITTED_ROOT = Path(__file__).resolve().parents[2] / "bench" / "packs" / "p1_public_v1"

PRIVATE_SECRET = bytes(range(32, 64))
HIDDEN_SECRET = bytes(range(64, 96))


class TestG01CrossEnvironmentRebuild(unittest.TestCase):
    def test_committed_public_root_byte_identical(self) -> None:
        result = verify_public_root(COMMITTED_ROOT)
        self.assertTrue(result["byte_identical"], result["failures"][:5])
        self.assertEqual(result["instances"], 48)


class TestG02SplitRootIndependence(unittest.TestCase):
    def test_held_out_not_derivable_from_public(self) -> None:
        pub = generate_instance(
            family_id="F01", split="public", ordinal=0, split_secret=PUBLIC_SPLIT_SECRET,
        )
        priv = generate_instance(
            family_id="F01", split="private", ordinal=0, split_secret=PRIVATE_SECRET,
        )
        hid = generate_instance(
            family_id="F01", split="private", ordinal=0, split_secret=HIDDEN_SECRET,
        )
        digests = {pub.instance_digest, priv.instance_digest, hid.instance_digest}
        self.assertEqual(len(digests), 3)
        # public uses the fixed constant; held-out secrets are independent
        self.assertNotEqual(PRIVATE_SECRET, PUBLIC_SPLIT_SECRET)
        self.assertNotEqual(HIDDEN_SECRET, PUBLIC_SPLIT_SECRET)


class TestG03SchemaConformance(unittest.TestCase):
    def test_all_public_instances_pass_frozen_schemas(self) -> None:
        for fid, split, ordinal in public_plan():
            inst = generate_instance(
                family_id=fid, split=split, ordinal=ordinal,
                split_secret=PUBLIC_SPLIT_SECRET,
            )
            self.assertEqual(inst.manifest.document["schema_version"], "oracle-manifest/v1")
            self.assertEqual(inst.actions["schema_version"], "scenario-actions/v2")
            self.assertEqual(inst.registry["schema_version"], "query-registry/v1")
            self.assertEqual(inst.gold["schema_version"], "compiled-gold/v1")


class TestG04RejectionReproducibility(unittest.TestCase):
    def test_rejected_attempts_replay_identically(self) -> None:
        def reject_two(_candidate, attempt):
            return "gate_test" if attempt < 2 else None

        a = generate_instance(
            family_id="F01", split="public", ordinal=0,
            split_secret=PUBLIC_SPLIT_SECRET, rejection_predicate=reject_two,
        )
        b = generate_instance(
            family_id="F01", split="public", ordinal=0,
            split_secret=PUBLIC_SPLIT_SECRET, rejection_predicate=reject_two,
        )
        self.assertEqual(a.attempt, 2)
        self.assertEqual(a.instance_digest, b.instance_digest)


class TestG05ExhaustionFailsRelease(unittest.TestCase):
    def test_64_attempts_exhausted(self) -> None:
        self.assertEqual(ATTEMPT_LIMIT, 64)
        with self.assertRaises(GeneratorRejectionExhausted):
            generate_instance(
                family_id="F01", split="public", ordinal=0,
                split_secret=PUBLIC_SPLIT_SECRET,
                rejection_predicate=lambda _c, _a: "always_rejected",
            )


class TestG06NoGoldOrSelfScore(unittest.TestCase):
    def test_generated_dsl_carries_no_evaluation_fields(self) -> None:
        from bench.dsl.loader import FORBIDDEN_EVALUATION_KEYS

        for fid, split, ordinal in public_plan()[:12]:
            inst = generate_instance(
                family_id=fid, split=split, ordinal=ordinal,
                split_secret=PUBLIC_SPLIT_SECRET,
            )
            blob = json_keys(inst.actions)
            self.assertFalse(blob & FORBIDDEN_EVALUATION_KEYS, fid)
            self.assertFalse(any(k.startswith(("expected_", "gold_")) for k in blob), fid)

    def test_family_specs_contain_no_gold(self) -> None:
        for fid, split, ordinal in public_plan()[:6]:
            inst = generate_instance(
                family_id=fid, split=split, ordinal=ordinal,
                split_secret=PUBLIC_SPLIT_SECRET,
            )
            self.assertNotIn("gold", json_keys(inst.family_document))


def json_keys(value) -> set:
    keys = set()
    if isinstance(value, dict):
        for k, v in value.items():
            keys.add(str(k))
            keys |= json_keys(v)
    elif isinstance(value, list):
        for item in value:
            keys |= json_keys(item)
    return keys


class TestG07GoldPreSUT(unittest.TestCase):
    def test_gold_compiled_without_sut_or_adapter(self) -> None:
        for fid, split, ordinal in public_plan()[:12]:
            inst = generate_instance(
                family_id=fid, split=split, ordinal=ordinal,
                split_secret=PUBLIC_SPLIT_SECRET,
            )
            self.assertIn("gold_digest", inst.gold)
            self.assertIn("pre_state", inst.gold)
            self.assertIn("post_state", inst.gold)

    def test_generator_source_never_imports_adapters_or_researchctl(self) -> None:
        """Structural gate: generator modules must not import SUT/adapter/participant code."""
        gen_dir = Path(__file__).resolve().parents[1] / "generator"
        forbidden = ("bench.adapters", "researchctl", "bench.runner", "bench.evaluators")
        for py in gen_dir.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")):
                    for word in forbidden:
                        self.assertFalse(
                            word in stripped,
                            f"{py.name}: forbidden import: {stripped}",
                        )


class TestG08ExactQuota(unittest.TestCase):
    def test_quota_144_and_allocation(self) -> None:
        plan = quota_plan()
        self.assertEqual(len(plan), 144)
        counts: dict = {}
        for fid, split, _ in plan:
            counts[(fid, split)] = counts.get((fid, split), 0) + 1
        expected = {("F06", s): 8 for s in ("public", "private", "local-hidden")}
        expected.update({("F07", s): 4 for s in ("public", "private", "local-hidden")})
        for f in ("F01", "F02", "F03", "F04", "F05", "F08"):
            for s in ("public", "private", "local-hidden"):
                expected[(f, s)] = 6
        self.assertEqual(counts, expected)


if __name__ == "__main__":
    unittest.main()
