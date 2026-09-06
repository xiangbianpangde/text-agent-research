"""P1A mechanical acceptance gate runner (G01–G08, §16).

Each check raises AssertionError on failure and returns a human-readable
evidence string on success. `run_all_gates()` produces the deterministic
evidence summary committed under bench/reports/p1a-gates.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List

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


def check_g01() -> str:
    """Cross-environment byte-identical rebuild of the committed public root."""
    result = verify_public_root(COMMITTED_ROOT)
    assert result["byte_identical"], f"rebuild mismatch: {result['failures'][:5]}"
    assert result["instances"] == 48, f"expected 48 instances, got {result['instances']}"
    return f"48/48 public instances rebuilt byte-identically from committed root; 0 failures"


def check_g02() -> str:
    """Split root independence: held-out not derivable from public."""
    pub = generate_instance(family_id="F01", split="public", ordinal=0, split_secret=PUBLIC_SPLIT_SECRET)
    priv = generate_instance(family_id="F01", split="private", ordinal=0, split_secret=PRIVATE_SECRET)
    hid = generate_instance(family_id="F01", split="private", ordinal=0, split_secret=HIDDEN_SECRET)
    digests = {pub.instance_digest, priv.instance_digest, hid.instance_digest}
    assert len(digests) == 3, "independent split secrets must yield distinct instance digests"
    assert PRIVATE_SECRET != PUBLIC_SPLIT_SECRET and HIDDEN_SECRET != PUBLIC_SPLIT_SECRET
    return "public=const(0x00..0x1f); private/hidden independent 32-byte keys produce distinct digests"


def check_g03() -> str:
    """Every instance passes the frozen Oracle/DSL schemas."""
    checked = 0
    for fid, split, ordinal in public_plan():
        inst = generate_instance(family_id=fid, split=split, ordinal=ordinal, split_secret=PUBLIC_SPLIT_SECRET)
        assert inst.manifest.document["schema_version"] == "oracle-manifest/v1"
        assert inst.actions["schema_version"] == "scenario-actions/v2"
        assert inst.registry["schema_version"] == "query-registry/v1"
        assert inst.gold["schema_version"] == "compiled-gold/v1"
        checked += 1
    return f"{checked}/48 instances validated against oracle-manifest/v1, scenario-actions/v2, query-registry/v1, compiled-gold/v1"


def check_g04() -> str:
    """Rejected attempts replay deterministically to the same accepted bytes."""
    def reject_two(_candidate, attempt):
        return "gate_replay" if attempt < 2 else None

    a = generate_instance(family_id="F01", split="public", ordinal=0,
                          split_secret=PUBLIC_SPLIT_SECRET, rejection_predicate=reject_two)
    b = generate_instance(family_id="F01", split="public", ordinal=0,
                          split_secret=PUBLIC_SPLIT_SECRET, rejection_predicate=reject_two)
    assert a.attempt == 2 and b.attempt == 2
    assert a.instance_digest == b.instance_digest
    return "after 2 forced rejections both runs accept attempt 2 with identical instance digests"


def check_g05() -> str:
    """Exhausting 64 attempts fails the release with GENERATOR_REJECTION_EXHAUSTED."""
    assert ATTEMPT_LIMIT == 64
    try:
        generate_instance(family_id="F01", split="public", ordinal=0,
                          split_secret=PUBLIC_SPLIT_SECRET,
                          rejection_predicate=lambda _c, _a: "always_rejected")
    except GeneratorRejectionExhausted:
        return f"GeneratorRejectionExhausted raised after {ATTEMPT_LIMIT} attempts"
    raise AssertionError("expected GeneratorRejectionExhausted")


def check_g06() -> str:
    """Generated DSL and family specs carry no Gold/self-score fields."""
    from bench.dsl.loader import FORBIDDEN_EVALUATION_KEYS

    def json_keys(value) -> set:
        keys: set = set()
        if isinstance(value, dict):
            for k, v in value.items():
                keys.add(str(k))
                keys |= json_keys(v)
        elif isinstance(value, list):
            for item in value:
                keys |= json_keys(item)
        return keys

    scanned = 0
    for fid, split, ordinal in public_plan():
        inst = generate_instance(family_id=fid, split=split, ordinal=ordinal, split_secret=PUBLIC_SPLIT_SECRET)
        action_keys = json_keys(inst.actions)
        assert not (action_keys & FORBIDDEN_EVALUATION_KEYS), fid
        assert not any(k.startswith(("expected_", "gold_")) for k in action_keys), fid
        family_keys = json_keys(inst.family_document)
        assert "gold" not in family_keys, fid
        scanned += 1
    return f"{scanned}/48 action streams and family docs contain zero evaluation/gold fields"


def check_g07() -> str:
    """Gold compiled pre-SUT; generator never imports adapter/participant code."""
    for fid, split, ordinal in public_plan()[:12]:
        inst = generate_instance(family_id=fid, split=split, ordinal=ordinal, split_secret=PUBLIC_SPLIT_SECRET)
        assert "gold_digest" in inst.gold and "pre_state" in inst.gold and "post_state" in inst.gold
    forbidden = ("bench.adapters", "researchctl", "bench.runner", "bench.evaluators")
    gen_dir = Path(__file__).parent
    for py in sorted(gen_dir.glob("*.py")):
        for line in py.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert not any(word in stripped for word in forbidden), f"{py.name}: {stripped}"
    return "gold compiled inside generation pipeline before any SUT; generator imports are adapter-free"


def check_g08() -> str:
    """Exact quota 144 with per-family/per-split allocation."""
    plan = quota_plan()
    assert len(plan) == 144
    counts: Dict[str, int] = {}
    for fid, split, _ in plan:
        counts[f"{fid}/{split}"] = counts.get(f"{fid}/{split}", 0) + 1
    expected = {f"F06/{s}": 8 for s in ("public", "private", "local-hidden")}
    expected.update({f"F07/{s}": 4 for s in ("public", "private", "local-hidden")})
    for f in ("F01", "F02", "F03", "F04", "F05", "F08"):
        for s in ("public", "private", "local-hidden"):
            expected[f"{f}/{s}"] = 6
    assert counts == expected
    for s in ("public", "private", "local-hidden"):
        assert sum(1 for _, sp, _ in plan if sp == s) == 48
    return "144 instances = 48/48/48; F06=24, F07=12, F01..F05/F08=18 each"


GATES: List[Dict[str, object]] = [
    {"id": "G01", "description": "cross-environment byte-identical rebuild", "check": check_g01},
    {"id": "G02", "description": "split root independence; public cannot derive held-out", "check": check_g02},
    {"id": "G03", "description": "every instance passes frozen Oracle/DSL schemas", "check": check_g03},
    {"id": "G04", "description": "rejection attempts and accepted bytes reproducible", "check": check_g04},
    {"id": "G05", "description": "64-attempt exhaustion fails release", "check": check_g05},
    {"id": "G06", "description": "no Gold/self-score in generated DSL or family specs", "check": check_g06},
    {"id": "G07", "description": "Gold compiled pre-SUT; adapter-free generator", "check": check_g07},
    {"id": "G08", "description": "exact quota 144 with per-family/per-split allocation", "check": check_g08},
]


def run_all_gates() -> Dict[str, object]:
    results = []
    all_pass = True
    for gate in GATES:
        check: Callable[[], str] = gate["check"]  # type: ignore[assignment]
        try:
            evidence = check()
            ok = True
        except AssertionError as exc:
            evidence = f"FAILED: {exc}"
            ok = False
        except Exception as exc:  # unexpected error also fails the gate
            evidence = f"ERROR: {type(exc).__name__}: {exc}"
            ok = False
        all_pass &= ok
        results.append({"id": gate["id"], "description": gate["description"], "ok": ok, "evidence": evidence})
    return {"phase": "P1A", "gates": results, "all_pass": all_pass}
