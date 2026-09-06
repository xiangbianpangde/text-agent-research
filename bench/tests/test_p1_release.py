"""P1A release/G-gate tests: public root write, byte-identical rebuild (G01)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bench.generator.release import (
    public_plan,
    verify_public_root,
    write_public_root,
)


class PublicRootTests(unittest.TestCase):
    COMMITTED_ROOT = Path(__file__).resolve().parents[2] / "bench" / "packs" / "p1_public_v1"

    def test_committed_public_root_rebuilds_byte_identically(self) -> None:
        """G01/G02 regression: the committed 48-instance public root rebuilds."""
        self.assertTrue(self.COMMITTED_ROOT.is_dir(), "committed public root missing")
        result = verify_public_root(self.COMMITTED_ROOT)
        self.assertTrue(result["byte_identical"], result["failures"][:5])
        self.assertEqual(result["instances"], 48)

    def test_public_plan_is_48(self) -> None:
        self.assertEqual(len(public_plan()), 48)

    def test_write_and_verify_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "public-root"
            digests = write_public_root(root)
            self.assertEqual(len(digests), 48)
            self.assertTrue((root / "generator" / "identity.json").exists())
            self.assertEqual(len(list((root / "families").glob("F*.json"))), 8)

            result = verify_public_root(root)
            self.assertTrue(result["byte_identical"], result["failures"][:5])
            self.assertEqual(result["instances"], 48)

    def test_write_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "public-root"
            write_public_root(root)
            with self.assertRaises(FileExistsError):
                write_public_root(root)

    def test_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "public-root"
            write_public_root(root)
            # tamper one fixture byte
            target = next(
                (root / "instances" / "public").glob("*/fixture/raw/*/R001/metrics.csv")
            )
            data = target.read_bytes()
            target.write_bytes(data.replace(b"accuracy", b"ACCURACY", 1))
            result = verify_public_root(root)
            self.assertFalse(result["byte_identical"])
            self.assertTrue(any("byte mismatch" in f for f in result["failures"]))


if __name__ == "__main__":
    unittest.main()
