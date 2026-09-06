"""bench-cjson/v1 canonical JSON serialization.

Conforms strictly to ResearchCTL-Bench-P1-Contract §19.1.1:
- Allowed types: null, boolean, Int64, Unicode NFC string, Array, Object.
- Forbidden types: float, NaN, Infinity, binary, surrogates.
- Normalization: Unicode NFC normalization on all strings and object keys.
- Key ordering: UTF-8 byte lexical ascending order.
- Escaping: only '"', '\\', and C0 control characters (\\u0000..\\u001f). '/' is not escaped.
- Integer format: shortest ASCII decimal, no leading '+', no leading zeros, no '-0'.
- Formatting: compact (':' and ',' separators, no extraneous whitespace, no final newline).
"""
from __future__ import annotations

import hashlib
import unicodedata
from typing import Any, Dict, List, Tuple


INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807


def bench_cjson_bytes(obj: Any) -> bytes:
    """Serialize an object into canonical bench-cjson/v1 UTF-8 bytes."""
    if obj is None:
        return b"null"

    if isinstance(obj, bool):
        return b"true" if obj else b"false"

    if isinstance(obj, int):
        if not (INT64_MIN <= obj <= INT64_MAX):
            raise ValueError(f"integer out of Int64 range: {obj}")
        return str(obj).encode("ascii")

    if isinstance(obj, float):
        raise TypeError("float values are strictly forbidden in bench-cjson/v1")

    if isinstance(obj, str):
        # Validate surrogate-free and apply NFC normalization
        normalized = unicodedata.normalize("NFC", obj)
        buf: List[bytes] = [b'"']
        for ch in normalized:
            cp = ord(ch)
            if 0xD800 <= cp <= 0xDFFF:
                raise ValueError(f"lone surrogate code point U+{cp:04X} forbidden")
            if cp == 0x22:  # '"'
                buf.append(b'\\"')
            elif cp == 0x5C:  # '\\'
                buf.append(b"\\\\")
            elif cp <= 0x1F:  # C0 control chars
                buf.append(f"\\u{cp:04x}".encode("ascii"))
            else:
                buf.append(ch.encode("utf-8"))
        buf.append(b'"')
        return b"".join(buf)

    if isinstance(obj, (list, tuple)):
        return b"[" + b",".join(bench_cjson_bytes(item) for item in obj) + b"]"

    if isinstance(obj, dict):
        normalized_pairs: Dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError(f"dictionary keys must be string, got {type(k).__name__}")
            k_nfc = unicodedata.normalize("NFC", k)
            if k_nfc in normalized_pairs:
                raise ValueError(f"key collision under NFC normalization: {k!r}")
            normalized_pairs[k_nfc] = v

        # Sort keys strictly by UTF-8 bytes in ascending order
        sorted_keys = sorted(normalized_pairs.keys(), key=lambda key_str: key_str.encode("utf-8"))
        items: List[bytes] = []
        for k in sorted_keys:
            items.append(bench_cjson_bytes(k) + b":" + bench_cjson_bytes(normalized_pairs[k]))
        return b"{" + b",".join(items) + b"}"

    raise TypeError(f"unsupported type for bench-cjson/v1: {type(obj).__name__}")


def bench_cjson_str(obj: Any) -> str:
    """Serialize an object into a bench-cjson/v1 UTF-8 string."""
    return bench_cjson_bytes(obj).decode("utf-8")


def bench_cjson_digest(obj: Any) -> str:
    """Compute sha256 digest of bench-cjson/v1 representation."""
    raw_sha = hashlib.sha256(bench_cjson_bytes(obj)).hexdigest()
    return f"sha256:{raw_sha}"
