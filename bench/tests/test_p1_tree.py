"""Unit tests for physical tree specification and bench-tree/v1 (§19.4)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bench.generator.tree import (
    compute_bench_tree_digest_from_dir,
    compute_bench_tree_digest_from_entries,
    normalize_tree_path,
    validate_tree_paths,
)


class BenchTreeTests(unittest.TestCase):
    def test_normalize_path(self) -> None:
        self.assertEqual(normalize_tree_path("a/b/c.txt"), "a/b/c.txt")
        self.assertEqual(normalize_tree_path("foo.md"), "foo.md")

        with self.assertRaises(ValueError):
            normalize_tree_path("/absolute/path.txt")
        with self.assertRaises(ValueError):
            normalize_tree_path("a/../b.txt")
        with self.assertRaises(ValueError):
            normalize_tree_path("a/./b.txt")
        with self.assertRaises(ValueError):
            normalize_tree_path("a//b.txt")

    def test_reserved_namespace_rejection(self) -> None:
        with self.assertRaises(ValueError):
            normalize_tree_path("a/file.tmp.1")
        with self.assertRaises(ValueError):
            normalize_tree_path("temp.tmp")
        with self.assertRaises(ValueError):
            normalize_tree_path("dir/.tmp.foo/bar")

    def test_appledouble_rejection(self) -> None:
        with self.assertRaises(ValueError):
            normalize_tree_path("dir/._hidden")

    def test_prefix_conflict(self) -> None:
        paths = ["a", "a/b"]
        with self.assertRaises(ValueError):
            validate_tree_paths(paths)

        valid_paths = ["a/b", "a/c", "b"]
        self.assertEqual(validate_tree_paths(valid_paths), ["a/b", "a/c", "b"])

    def test_tree_digest_determinism(self) -> None:
        entries = {
            "README.md": (0o644, b"# Hello\n"),
            "scripts/run.sh": (0o755, b"#!/bin/bash\necho ok\n"),
        }
        digest1 = compute_bench_tree_digest_from_entries(entries)
        digest2 = compute_bench_tree_digest_from_entries(entries)
        self.assertEqual(digest1, digest2)
        self.assertTrue(digest1.startswith("sha256:"))

    def test_dir_walk_matches_in_memory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "dir").mkdir()
            (root / "dir" / "file.txt").write_bytes(b"content")
            (root / "README.md").write_bytes(b"readme")

            entries = {
                "README.md": (0o644, b"readme"),
                "dir/file.txt": (0o644, b"content"),
            }
            mem_digest = compute_bench_tree_digest_from_entries(entries)
            dir_digest = compute_bench_tree_digest_from_dir(root)
            self.assertEqual(mem_digest, dir_digest)


if __name__ == "__main__":
    unittest.main()
