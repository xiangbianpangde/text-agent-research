"""P0.4 negative-control attestation and isolation gates."""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from bench.adapters.process import ProcessSUTAdapter
from bench.controls import CONTROL_MODES
from bench.controls.runner import validate_attestation


ROOT = Path(__file__).resolve().parents[2]
ATTESTATION = ROOT / "bench" / "controls" / "attestation.json"


class NegativeControlAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = json.loads(ATTESTATION.read_text(encoding="utf-8"))

    def test_attestation_is_bound_and_all_controls_are_rejected(self) -> None:
        self.assertTrue(validate_attestation(self.value))
        self.assertEqual([row["mode"] for row in self.value["controls"]], list(CONTROL_MODES))
        self.assertTrue(self.value["all_controls_rejected"])
        self.assertTrue(self.value["random_deterministic"])
        self.assertTrue(self.value["official_deterministic"])
        self.assertTrue(self.value["gold_reader_blocked"])
        for control in self.value["controls"]:
            self.assertFalse(control["passed_conclusion"])
            self.assertFalse(control["certification_eligible"])
            self.assertFalse(control["iqg_passed"])
            self.assertEqual(control["tier"], "N/A")

    def test_attestation_tampering_fails_closed(self) -> None:
        mutations = []
        changed = copy.deepcopy(self.value)
        changed["controls"][0]["passed_conclusion"] = True
        mutations.append(changed)
        changed = copy.deepcopy(self.value)
        changed["manifest_digest"] = "sha256:" + "0" * 64
        mutations.append(changed)
        changed = copy.deepcopy(self.value)
        changed["harness_digest"] = "sha256:" + "0" * 64
        mutations.append(changed)
        changed = copy.deepcopy(self.value)
        changed["official_retry_digest"] = "sha256:" + "0" * 64
        mutations.append(changed)
        for value in mutations:
            self.assertFalse(validate_attestation(value))

    @unittest.skipUnless(sys.platform == "darwin", "Gold-reader sandbox requires macOS sandbox-exec")
    def test_unicode_gold_path_is_blocked_by_os_sandbox(self) -> None:
        pack_root = str(ROOT / "bench" / "packs" / "p0_seed_v1")
        probe = str(Path(pack_root) / "oracle-manifest.json")
        with tempfile.TemporaryDirectory() as workspace:
            adapter = ProcessSUTAdapter(
                [sys.executable, "-m", "bench.controls.control_sut"],
                cwd=str(ROOT),
                env={"BENCH_CONTROL_MODE": "gold-reader", "BENCH_GOLD_PROBE": probe},
                denied_read_paths=[pack_root],
            )
            try:
                adapter.prepare(workspace)
                health = adapter.health()
                self.assertTrue(health["gold_read_blocked"])
            finally:
                adapter.shutdown()


if __name__ == "__main__":
    unittest.main()
