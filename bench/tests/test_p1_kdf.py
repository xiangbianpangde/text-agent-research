"""Unit tests for deterministic KDF and PRNG stream (§19.9)."""
from __future__ import annotations

import unittest

from bench.generator.frame import (
    encode_frame,
    encode_string_frame,
    encode_u16_frame,
    encode_u32_frame,
    encode_u64_frame,
)
from bench.generator.kdf import (
    PUBLIC_SPLIT_SECRET,
    PRNGStream,
    build_instance_message,
    derive_domain_key,
    derive_instance_key,
    derive_run_seed,
)


class KDFTests(unittest.TestCase):
    def test_frame_encoding(self) -> None:
        frame = encode_frame("test", b"\x01\x02\x03")
        self.assertEqual(frame[:2], b"\x00\x04")  # u16be(4)
        self.assertEqual(frame[2:6], b"test")
        self.assertEqual(frame[6:10], b"\x00\x00\x00\x03")  # u32be(3)
        self.assertEqual(frame[10:], b"\x01\x02\x03")

    def test_instance_key_derivation_determinism(self) -> None:
        msg1 = build_instance_message(
            release_id="RCTL-P1-B1-2026-01",
            generator_version="universe-generator/v1",
            family_id="F01",
            family_version="1.0.0",
            split="public",
            ordinal=0,
            attempt=0,
        )
        msg2 = build_instance_message(
            release_id="RCTL-P1-B1-2026-01",
            generator_version="universe-generator/v1",
            family_id="F01",
            family_version="1.0.0",
            split="public",
            ordinal=0,
            attempt=0,
        )
        self.assertEqual(msg1, msg2)

        key1 = derive_instance_key(PUBLIC_SPLIT_SECRET, msg1)
        key2 = derive_instance_key(PUBLIC_SPLIT_SECRET, msg2)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)

        # Different ordinal produces different key
        msg_diff = build_instance_message(
            release_id="RCTL-P1-B1-2026-01",
            generator_version="universe-generator/v1",
            family_id="F01",
            family_version="1.0.0",
            split="public",
            ordinal=1,
            attempt=0,
        )
        key_diff = derive_instance_key(PUBLIC_SPLIT_SECRET, msg_diff)
        self.assertNotEqual(key1, key_diff)

    def test_run_seed_derivation(self) -> None:
        msg = build_instance_message(
            release_id="RCTL-P1-B1-2026-01",
            generator_version="universe-generator/v1",
            family_id="F01",
            family_version="1.0.0",
            split="public",
            ordinal=0,
            attempt=0,
        )
        k_inst = derive_instance_key(PUBLIC_SPLIT_SECRET, msg)

        seeds = [derive_run_seed(k_inst, r) for r in range(5)]
        # 5 distinct seeds
        self.assertEqual(len(set(seeds)), 5)
        for s in seeds:
            self.assertEqual(len(s), 64)
            self.assertTrue(all(c in "0123456789abcdef" for c in s))

        # Re-deriving repetition 0 yields identical seed
        self.assertEqual(derive_run_seed(k_inst, 0), seeds[0])

    def test_prng_stream_uniform(self) -> None:
        domain_key = b"\xaa" * 32
        stream1 = PRNGStream(domain_key)
        stream2 = PRNGStream(domain_key)

        samples1 = [stream1.uniform(100) for _ in range(50)]
        samples2 = [stream2.uniform(100) for _ in range(50)]
        self.assertEqual(samples1, samples2)
        for val in samples1:
            self.assertTrue(0 <= val < 100)

    def test_prng_stream_weighted_choice(self) -> None:
        domain_key = b"\xbb" * 32
        stream = PRNGStream(domain_key)
        weights = [10, 20, 70]
        counts = [0, 0, 0]
        for _ in range(1000):
            idx = stream.weighted_choice(weights)
            counts[idx] += 1

        # Most samples should land on index 2 (weight 70)
        self.assertTrue(counts[2] > counts[1] > counts[0])


if __name__ == "__main__":
    unittest.main()
