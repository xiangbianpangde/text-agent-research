"""Frame encoding for deterministic binary structures (§19.9.1).

Frame(name, bytes) = u16be(len(ASCII(name))) || ASCII(name) || u32be(len(bytes)) || bytes.
"""
from __future__ import annotations

import struct
import unicodedata


def encode_frame(name: str, payload: bytes) -> bytes:
    """Encode a named binary frame according to §19.9.1."""
    name_ascii = name.encode("ascii")
    if len(name_ascii) > 65535:
        raise ValueError(f"frame name too long: {len(name_ascii)} bytes")
    name_len = struct.pack(">H", len(name_ascii))
    payload_len = struct.pack(">I", len(payload))
    return name_len + name_ascii + payload_len + payload


def encode_string_frame(name: str, text: str) -> bytes:
    """Encode a named string frame with Unicode NFC normalization."""
    normalized = unicodedata.normalize("NFC", text)
    return encode_frame(name, normalized.encode("utf-8"))


def encode_u32_frame(name: str, value: int) -> bytes:
    """Encode a named 32-bit unsigned integer frame."""
    if not (0 <= value <= 4294967295):
        raise ValueError(f"UInt32 out of range: {value}")
    return encode_frame(name, struct.pack(">I", value))


def encode_u64_frame(name: str, value: int) -> bytes:
    """Encode a named 64-bit unsigned integer frame."""
    if not (0 <= value <= 18446744073709551615):
        raise ValueError(f"UInt64 out of range: {value}")
    return encode_frame(name, struct.pack(">Q", value))


def encode_u16_frame(name: str, value: int) -> bytes:
    """Encode a named 16-bit unsigned integer frame."""
    if not (0 <= value <= 65535):
        raise ValueError(f"UInt16 out of range: {value}")
    return encode_frame(name, struct.pack(">H", value))
