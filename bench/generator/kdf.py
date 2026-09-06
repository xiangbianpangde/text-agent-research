"""HMAC-SHA256 Key Derivation Function (KDF) & PRNG streams (§19.9)."""
from __future__ import annotations

import hmac
import hashlib
import struct
from typing import List, Sequence

from .frame import (
    encode_frame,
    encode_string_frame,
    encode_u32_frame,
    encode_u64_frame,
)


PUBLIC_SPLIT_SECRET = bytes(range(32))

ALLOWED_DOMAINS = frozenset({
    "objects",
    "relations",
    "content",
    "timestamps",
    "mutation",
    "actions",
    "query",
    "run-seed",
    "bootstrap",
})


def build_instance_message(
    *,
    release_id: str,
    generator_version: str,
    family_id: str,
    family_version: str,
    split: str,
    ordinal: int,
    attempt: int,
) -> bytes:
    """Construct the 8-frame InstanceMessage according to §19.9.1."""
    return (
        encode_string_frame("context", "ResearchCTL-Bench/P1-B1/v1")
        + encode_string_frame("release_id", release_id)
        + encode_string_frame("generator_version", generator_version)
        + encode_string_frame("family_id", family_id)
        + encode_string_frame("family_version", family_version)
        + encode_string_frame("split", split)
        + encode_u32_frame("ordinal", ordinal)
        + encode_u32_frame("attempt", attempt)
    )


def derive_instance_key(split_secret: bytes, instance_message: bytes) -> bytes:
    """Derive 32-byte K_instance = HMAC-SHA256(S_split, InstanceMessage)."""
    if len(split_secret) != 32:
        raise ValueError(f"split_secret must be 32 bytes, got {len(split_secret)}")
    return hmac.new(split_secret, instance_message, hashlib.sha256).digest()


def derive_domain_key(instance_key: bytes, domain: str) -> bytes:
    """Derive K_domain(D) = HMAC-SHA256(K_instance, Frame('domain', ASCII(D)))."""
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(f"unknown or unallowed domain: {domain!r}")
    frame = encode_frame("domain", domain.encode("ascii"))
    return hmac.new(instance_key, frame, hashlib.sha256).digest()


def derive_run_seed(instance_key: bytes, repetition: int) -> str:
    """Derive 64-hex lowercase run_seed(i, r) = HMAC-SHA256(K_domain('run-seed'), Frame('repetition', u32be(r)))."""
    if not (0 <= repetition <= 4):
        raise ValueError(f"repetition must be in 0..4, got {repetition}")
    domain_key = derive_domain_key(instance_key, "run-seed")
    frame = encode_u32_frame("repetition", repetition)
    return hmac.new(domain_key, frame, hashlib.sha256).hexdigest().lower()


class PRNGStream:
    """Stateful pseudo-random number generator for a specific domain (§19.9.3)."""

    def __init__(self, domain_key: bytes) -> None:
        if len(domain_key) != 32:
            raise ValueError(f"domain_key must be 32 bytes, got {len(domain_key)}")
        self.domain_key = domain_key
        self.counter = 0
        self.word_index = 0
        self._current_words: List[int] = []

    def _generate_next_block(self) -> List[int]:
        """Compute Block(D, c) = HMAC-SHA256(K_domain(D), Frame('counter', u64be(c)))."""
        frame = encode_u64_frame("counter", self.counter)
        block_bytes = hmac.new(self.domain_key, frame, hashlib.sha256).digest()
        # Unpack 8 big-endian 32-bit unsigned integers
        return list(struct.unpack(">8I", block_bytes))

    def _next_word(self) -> int:
        if self.word_index == 0:
            self._current_words = self._generate_next_block()
        val = self._current_words[self.word_index]
        self.word_index += 1
        if self.word_index == 8:
            self.counter += 1
            self.word_index = 0
        return val

    def uniform(self, n: int) -> int:
        """Sample an unbiased integer in [0, n - 1] using rejection sampling (§19.9.3)."""
        if not (1 <= n <= 4294967296):
            raise ValueError(f"n must be between 1 and 2^32, got {n}")
        if n == 1:
            return 0
        limit = (4294967296 // n) * n
        while True:
            x = self._next_word()
            if x < limit:
                return x % n

    def weighted_choice(self, weights: Sequence[int]) -> int:
        """Sample an index according to integer weights (§19.9.3)."""
        if not weights:
            raise ValueError("weights must not be empty")
        for w in weights:
            if w <= 0:
                raise ValueError(f"each weight must be a positive integer, got {w}")
        total_weight = sum(weights)
        if not (1 <= total_weight <= 4294967296):
            raise ValueError(f"total weight out of range: {total_weight}")

        v = self.uniform(total_weight)
        cumulative = 0
        for idx, w in enumerate(weights):
            cumulative += w
            if v < cumulative:
                return idx
        return len(weights) - 1
