"""Unit tests for bench-cjson/v1 canonical JSON encoding (§19.1.1)."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from bench.dsl.cjson import (
    INT64_MAX,
    INT64_MIN,
    bench_cjson_bytes,
    bench_cjson_digest,
    bench_cjson_str,
)


class BenchCJsonTests(unittest.TestCase):
    def test_primitives(self) -> None:
        self.assertEqual(bench_cjson_bytes(None), b"null")
        self.assertEqual(bench_cjson_bytes(True), b"true")
        self.assertEqual(bench_cjson_bytes(False), b"false")
        self.assertEqual(bench_cjson_bytes(0), b"0")
        self.assertEqual(bench_cjson_bytes(42), b"42")
        self.assertEqual(bench_cjson_bytes(-100), b"-100")
        self.assertEqual(bench_cjson_bytes(INT64_MIN), str(INT64_MIN).encode("ascii"))
        self.assertEqual(bench_cjson_bytes(INT64_MAX), str(INT64_MAX).encode("ascii"))

    def test_integer_overflow_rejection(self) -> None:
        with self.assertRaises(ValueError):
            bench_cjson_bytes(INT64_MIN - 1)
        with self.assertRaises(ValueError):
            bench_cjson_bytes(INT64_MAX + 1)

    def test_float_rejection(self) -> None:
        with self.assertRaises(TypeError):
            bench_cjson_bytes(1.23)
        with self.assertRaises(TypeError):
            bench_cjson_bytes(float("nan"))
        with self.assertRaises(TypeError):
            bench_cjson_bytes(float("inf"))

    def test_string_escaping(self) -> None:
        self.assertEqual(bench_cjson_bytes("hello world"), b'"hello world"')
        self.assertEqual(bench_cjson_bytes('quote: " and backslash: \\'), b'"quote: \\" and backslash: \\\\"')
        self.assertEqual(bench_cjson_bytes("slash: / is not escaped"), b'"slash: / is not escaped"')
        self.assertEqual(bench_cjson_bytes("\x00\x09\x0a\x1f"), b'"\\u0000\\u0009\\u000a\\u001f"')
        self.assertEqual(bench_cjson_bytes("Unicode: 你好世界 🌍"), "Unicode: 你好世界 🌍".encode("utf-8").join([b'"', b'"']))

    def test_key_sorting_and_nfc(self) -> None:
        # Byte lexical sorting: "b", "a", "Z" -> "Z" (0x5A) < "a" (0x61) < "b" (0x62)
        d = {"b": 1, "a": 2, "Z": 3}
        self.assertEqual(bench_cjson_str(d), '{"Z":3,"a":2,"b":1}')

        # NFC normalization and collision detection
        # e + combining acute (U+0065 U+0301) vs precomposed é (U+00E9)
        k_decomp = "\u0065\u0301"
        k_precomp = "\u00e9"
        colliding_dict = {k_decomp: 1, k_precomp: 2}
        with self.assertRaises(ValueError):
            bench_cjson_bytes(colliding_dict)

    def test_all_contract_hashes(self) -> None:
        contract_path = Path("docs/contracts/ResearchCTL-Bench-P1-Contract.md")
        if not contract_path.exists():
            contract_path = Path("ResearchCTL-Bench-P1-Contract.md")
        contract_text = contract_path.read_text(encoding="utf-8")

        # 1. Quota profile
        m_quota = re.search(r'```json\n({"families":.*?"total_instances":144})\n```', contract_text)
        self.assertIsNotNone(m_quota)
        self.assertEqual(
            bench_cjson_digest(json.loads(m_quota.group(1))),
            "sha256:6c26fb4ce20da8030fdef949292925115441c73471562b93275c4a83fe65dbb6",
        )

        # 2. Metric profile
        m_metric = re.search(r'```json\n({"metric_ids_ordered":.*?"schema_version":"metric-profile/v1"})\n```', contract_text)
        self.assertIsNotNone(m_metric)
        self.assertEqual(
            bench_cjson_digest(json.loads(m_metric.group(1))),
            "sha256:2e998c351aa12f82595feb1c935b359bbd1e677a44a2c159c878455ef0fb69be",
        )

        # 3. Known answer
        m_known = re.search(r'```json\n({"families":.*?"schema_version":"statistics-known-answer/v1",.*?"statistics_profile_version":"p1-statistics/v1"})\n```', contract_text)
        self.assertIsNotNone(m_known)
        self.assertEqual(
            bench_cjson_digest(json.loads(m_known.group(1))),
            "sha256:a8bc8261ea3eb542241a145bc2ebf2e363ebd5d526c5977088f24b742298503a",
        )

        # 4. Statistics profile
        m_prof = re.search(r'```json\n({"bootstrap_profile":"p1-bootstrap/v1",.*?"schema_version":"statistics-profile/v1"})\n```', contract_text)
        self.assertIsNotNone(m_prof)
        self.assertEqual(
            bench_cjson_digest(json.loads(m_prof.group(1))),
            "sha256:bd08e958ec639020396e8446c076bccd047989765ea7969bdae97a9ef9761eab",
        )

        # 5. Filegraph profile
        m_fg = re.search(r'```json\n({"casefold":"default-full-casefold",.*?"unicode_data_version":"15.0.0",.*?"zero_score":"omit"})\n```', contract_text)
        self.assertIsNotNone(m_fg)
        self.assertEqual(
            bench_cjson_digest(json.loads(m_fg.group(1))),
            "sha256:9df1b1509829995c465d5f50717cf31ace9448cd4a36f6b30a46abb71e27ffa6",
        )

        # 6. B1 API
        for m in re.finditer(r'```json\n(.*?)\n```', contract_text, re.S):
            if '"kernel_version": "b1-kernel/v1"' in m.group(1):
                self.assertEqual(
                    bench_cjson_digest(json.loads(m.group(1))),
                    "sha256:e8cf1488cc32be80a53d8c8e803d9182c59623abd488c564ce504655741f8e1e",
                )


if __name__ == "__main__":
    unittest.main()
