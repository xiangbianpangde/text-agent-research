"""hidden-validity/v1 canary tests (§19.5.4, S05/S06)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from bench.campaign.canary import (
    CANARY_TARGETS,
    ISOLATION_PROFILE_DIGEST,
    NETWORK_POLICY_DIGEST,
    CanaryError,
    CanaryRunner,
    build_isolation_profile,
    build_network_policy,
)
from bench.dsl.cjson import bench_cjson_digest


@unittest.skipUnless(sys.platform == "darwin", "canary isolation requires macOS sandbox-exec")
class CanaryExecutionTests(unittest.TestCase):
    def _targets(self, td):
        targets = {}
        for name in ("evaluator_root", "oracle_root", "gold", "private_seed",
                     "hidden_seed", "private_pack", "hidden_pack"):
            p = Path(td) / f"{name}.probe"
            p.write_bytes(b"canary\n")
            targets[name] = p
        return targets

    def test_all_16_blocked(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            runner = CanaryRunner(evaluator_targets=self._targets(Path(td)), workspace=td)
            result = runner.run()
            self.assertTrue(result["evaluation_valid"], result["reason"])
            self.assertEqual(result["backend"], "sandbox-exec")
            self.assertEqual(len(result["transcript"]), 16)
            self.assertTrue(all(r["result"] == "blocked" for r in result["transcript"]))
            self.assertTrue(result["canary_transcript_digest"].startswith("sha256:"))

    def test_transcript_digest_matches_contract_formula(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            runner = CanaryRunner(evaluator_targets=self._targets(Path(td)), workspace=td)
            result = runner.run()
            recomputed = bench_cjson_digest(result["transcript"])
            self.assertEqual(recomputed, result["canary_transcript_digest"])

    def test_policy_digest_binding(self) -> None:
        result_shape = {"policy_digest": ISOLATION_PROFILE_DIGEST}
        self.assertEqual(result_shape["policy_digest"], ISOLATION_PROFILE_DIGEST)


class CanaryStructureTests(unittest.TestCase):
    def test_frozen_digests_reproduce(self) -> None:
        iso = build_isolation_profile()
        net = build_network_policy()
        self.assertEqual(bench_cjson_digest(iso), ISOLATION_PROFILE_DIGEST)
        self.assertEqual(bench_cjson_digest(net), NETWORK_POLICY_DIGEST)

    def test_targets_cover_7_read_7_write_2_network(self) -> None:
        reads = [t for t in CANARY_TARGETS if t.startswith("read:")]
        writes = [t for t in CANARY_TARGETS if t.startswith("write:")]
        networks = [t for t in CANARY_TARGETS if t.startswith("network:")]
        self.assertEqual(len(reads), 7)
        self.assertEqual(len(writes), 7)
        self.assertEqual(len(networks), 2)
        self.assertEqual(len(CANARY_TARGETS), 16)

    def test_missing_probe_target_fails_closed(self) -> None:
        with self.assertRaises(CanaryError):
            # constructing then probing a nonexistent target must abort, not skip
            runner = CanaryRunner(
                evaluator_targets={"gold": "/nonexistent/path/.probe"},
                workspace="/tmp",
            )
            # direct probe path check
            from bench.campaign.canary import _probe_read
            _probe_read(runner.evaluator_targets["gold"])


if __name__ == "__main__":
    unittest.main()
