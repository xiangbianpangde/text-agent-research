"""Per-instance generation pipeline (P1A, §6.5, §6.6, §19.3.3).

Fixed order: derive candidate seed → construct base universe →
entities/artifacts/facts/relations → physical fixture → preassigned subvariant →
mutations → action/query registry → schema validation → Gold compilation →
static acceptance → accept/reject.

Gold is compiled strictly pre-SUT: this module never imports any adapter,
runner, evaluator, or participant code.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from bench.dsl.cjson import bench_cjson_bytes, bench_cjson_digest
from bench.generator.families import get_family
from bench.generator.identity import (
    ATTEMPT_LIMIT,
    GENERATOR_VERSION,
    RELEASE_ID,
    build_instance_descriptor,
    display_id,
    instance_digest,
)
from bench.generator.kdf import (
    ALLOWED_DOMAINS,
    PRNGStream,
    build_instance_message,
    derive_domain_key,
    derive_instance_key,
)
from bench.generator.scenario import validate_scenario_v2
from bench.generator.tree import compute_bench_tree_digest_from_entries
from bench.generator.universe import (
    build_action_stream,
    build_fixture_files,
    build_query_registry,
    build_universe_document,
    emit_state_ledgers,
    finalize_manifest_filler_hashes,
)
from bench.oracle.compiler import compile_gold
from bench.oracle.manifest import OracleManifest, validate_manifest


class GeneratorRejectionExhausted(RuntimeError):
    """All attempts for one ordinal were rejected (G05)."""

    def __init__(self, family_id: str, split: str, ordinal: int, reasons: List[str]) -> None:
        super().__init__(
            f"GENERATOR_REJECTION_EXHAUSTED: {family_id}/{split}/{ordinal} "
            f"rejected {ATTEMPT_LIMIT} attempts; last reasons: {reasons[-3:]}"
        )
        self.family_id = family_id
        self.split = split
        self.ordinal = ordinal
        self.reasons = list(reasons)


RejectionPredicate = Callable[[Mapping[str, Any], int], Optional[str]]


@dataclass
class GeneratedInstance:
    family_id: str
    family_version: str
    split: str
    ordinal: int
    attempt: int
    subvariant_id: str
    descriptor: Dict[str, Any]
    instance_digest: str
    display: str
    manifest: OracleManifest
    actions: Dict[str, Any]
    registry: Dict[str, Any]
    gold: Dict[str, Any]
    fixture_files: Dict[str, Tuple[int, bytes]]
    family_document: Dict[str, Any]

    def public_payload(self) -> Dict[str, Any]:
        """Serializable artifact bundle (no secrets, no participant data)."""
        return {
            "display_id": self.display,
            "descriptor": self.descriptor,
            "instance_digest": self.instance_digest,
            "manifest": self.manifest.document,
            "actions": self.actions,
            "query_registry": self.registry,
            "gold": self.gold,
        }


def _check_acyclic(relations: List[Mapping[str, Any]]) -> None:
    """Static acceptance predicate: the declared relation graph must be acyclic."""
    adjacency: Dict[str, List[str]] = {}
    for edge in relations:
        adjacency.setdefault(edge["source_ref"], []).append(edge["target_ref"])
    state: Dict[str, int] = {}

    def visit(node: str, stack: List[str]) -> None:
        if state.get(node) == 1:
            raise ValueError(f"relation graph contains a cycle at {node}: {' -> '.join(stack + [node])}")
        if state.get(node) == 2:
            return
        state[node] = 1
        for nxt in adjacency.get(node, []):
            visit(nxt, stack + [node])
        state[node] = 2

    for node in sorted(adjacency):
        visit(node, [])


def _candidate(
    *,
    family: Mapping[str, Any],
    split: str,
    ordinal: int,
    attempt: int,
    split_secret: bytes,
) -> Dict[str, Any]:
    family_id = family["family_id"]
    family_version = family["family_version"]
    message = build_instance_message(
        release_id=RELEASE_ID,
        generator_version=GENERATOR_VERSION,
        family_id=family_id,
        family_version=family_version,
        split=split,
        ordinal=ordinal,
        attempt=attempt,
    )
    instance_key = derive_instance_key(split_secret, message)
    streams: Dict[str, PRNGStream] = {
        domain: PRNGStream(derive_domain_key(instance_key, domain))
        for domain in sorted(ALLOWED_DOMAINS)
    }

    # preassigned subvariant (§6.5): weighted choice over the family schedule
    schedule = family["subvariant_schedule"]
    weights = [entry["weight"] for entry in schedule]
    subvariant = schedule[streams["mutation"].weighted_choice(weights)]

    universe_id = f"RCTL-P1-{family_id}-{split}-{ordinal:03d}-a{attempt}"
    universe = build_universe_document(
        family=family,
        ordinal=ordinal,
        streams=streams,
        universe_id=universe_id,
    )
    fixture_files = build_fixture_files(universe=universe, streams=streams)
    finalize_manifest_filler_hashes(universe, fixture_files)
    emit_state_ledgers(universe, fixture_files)

    manifest = validate_manifest(universe)
    actions = build_action_stream(
        family=family,
        universe=universe,
        streams=streams,
        scenario_id=f"P1-{family_id}-{split.upper()}-{ordinal:03d}",
    )
    actions = validate_scenario_v2(actions)
    registry = build_query_registry(universe)
    gold = compile_gold(manifest, actions)

    _check_acyclic(universe["relations"])

    fixture_tree_digest = compute_bench_tree_digest_from_entries(fixture_files)
    source_tree_digest = _source_tree_digest()

    descriptor = build_instance_descriptor(
        attempt=attempt,
        family_digest=bench_cjson_digest({
            "family_body_digest": bench_cjson_digest(family),
            "family_id": family_id,
            "family_schema_version": "task-family/v1",
            "family_version": family_version,
        }),
        family_id=family_id,
        family_version=family_version,
        fixture_tree_digest=fixture_tree_digest,
        oracle_manifest_digest=bench_cjson_digest(manifest.document),
        ordinal=ordinal,
        query_registry_digest=bench_cjson_digest(registry),
        scenario_action_digest=bench_cjson_digest(_scenario_actions_v2_schema()),
        source_tree_digest=source_tree_digest,
        split=split,
    )

    return {
        "subvariant_id": subvariant["subvariant_id"],
        "descriptor": descriptor,
        "manifest": manifest,
        "actions": actions.document,
        "registry": registry,
        "gold": gold,
        "fixture_files": fixture_files,
        "family": dict(family),
    }


_V2_SCHEMA_CACHE: Optional[Dict[str, Any]] = None


def _scenario_actions_v2_schema() -> Dict[str, Any]:
    global _V2_SCHEMA_CACHE
    if _V2_SCHEMA_CACHE is None:
        import json

        _V2_SCHEMA_CACHE = json.loads(
            (compute_schema_path()).read_text(encoding="utf-8")
        )
    return _V2_SCHEMA_CACHE


def compute_schema_path():
    from pathlib import Path

    return Path(__file__).parent / "schemas" / "scenario-actions-v2.schema.json"


SOURCE_TREE_FILES = (
    # Complete transitive closure of generation-affecting sources, mapped into
    # a single virtual tree. Any edit to any listed file changes every instance
    # digest (§6.2 binding); the G01 rebuild check catches any drift.
    ("bench/dsl/cjson.py", "bench/dsl/cjson.py"),
    ("bench/dsl/loader.py", "bench/dsl/loader.py"),
    ("bench/generator/families.py", "bench/generator/families.py"),
    ("bench/generator/frame.py", "bench/generator/frame.py"),
    ("bench/generator/identity.py", "bench/generator/identity.py"),
    ("bench/generator/instance.py", "bench/generator/instance.py"),
    ("bench/generator/kdf.py", "bench/generator/kdf.py"),
    ("bench/generator/models.py", "bench/generator/models.py"),
    ("bench/generator/scenario.py", "bench/generator/scenario.py"),
    ("bench/generator/tree.py", "bench/generator/tree.py"),
    ("bench/generator/universe.py", "bench/generator/universe.py"),
    ("bench/generator/yamlemit.py", "bench/generator/yamlemit.py"),
    ("bench/generator/schemas/scenario-actions-v2.schema.json", "bench/generator/schemas/scenario-actions-v2.schema.json"),
    ("bench/oracle/compiler.py", "bench/oracle/compiler.py"),
    ("bench/oracle/conditions.py", "bench/oracle/conditions.py"),
    ("bench/oracle/manifest.py", "bench/oracle/manifest.py"),
    ("bench/oracle/model.py", "bench/oracle/model.py"),
    ("bench/oracle/time.py", "bench/oracle/time.py"),
)

_SOURCE_TREE_CACHE: Optional[str] = None


def _source_tree_digest() -> str:
    """bench-tree/v1 digest over the frozen generation-affecting source list.

    Fail-closed: every listed file must exist. The list is explicit code, so
    adding a generation-affecting file requires editing this tuple (a conscious
    act reviewed in diff), and verification-only files never churn digests.
    """
    global _SOURCE_TREE_CACHE
    if _SOURCE_TREE_CACHE is None:
        root = Path(__file__).resolve().parents[2]
        files: Dict[str, Tuple[int, bytes]] = {}
        for repo_rel, tree_path in SOURCE_TREE_FILES:
            data = (root / repo_rel).read_bytes()
            files[tree_path] = (0o644, data)
        _SOURCE_TREE_CACHE = compute_bench_tree_digest_from_entries(files)
    return _SOURCE_TREE_CACHE


def generate_instance(
    *,
    family_id: str,
    split: str,
    ordinal: int,
    split_secret: bytes,
    rejection_predicate: Optional[RejectionPredicate] = None,
    attempt_limit: int = ATTEMPT_LIMIT,
) -> GeneratedInstance:
    """Generate one instance with deterministic rejection sampling (§6.6)."""
    if len(split_secret) != 32:
        raise ValueError("split_secret must be exactly 32 bytes")
    family = get_family(family_id)
    reasons: List[str] = []
    for attempt in range(attempt_limit):
        candidate = _candidate(
            family=family, split=split, ordinal=ordinal,
            attempt=attempt, split_secret=split_secret,
        )
        reject_reason = (
            rejection_predicate(candidate, attempt) if rejection_predicate is not None else None
        )
        if reject_reason is None:
            descriptor = candidate["descriptor"]
            return GeneratedInstance(
                family_id=family_id,
                family_version=family["family_version"],
                split=split,
                ordinal=ordinal,
                attempt=attempt,
                subvariant_id=candidate["subvariant_id"],
                descriptor=descriptor,
                instance_digest=instance_digest(descriptor),
                display=display_id(descriptor),
                manifest=candidate["manifest"],
                actions=candidate["actions"],
                registry=candidate["registry"],
                gold=candidate["gold"],
                fixture_files=candidate["fixture_files"],
                family_document=candidate["family"],
            )
        reasons.append(reject_reason)
    raise GeneratorRejectionExhausted(family_id, split, ordinal, reasons)


def quota_plan() -> List[Tuple[str, str, int]]:
    """Enumerate the frozen 144-instance quota plan (family, split, ordinal).

    Mirrors quota-profile/v1 (§19.2.1); used to verify the allocation contract.
    """
    quotas = {
        "F01": 6, "F02": 6, "F03": 6, "F04": 6,
        "F05": 6, "F06": 8, "F07": 4, "F08": 6,
    }
    plan: List[Tuple[str, str, int]] = []
    for family_id in sorted(quotas):
        for split in ("public", "private", "local-hidden"):
            for ordinal in range(quotas[family_id]):
                plan.append((family_id, split, ordinal))
    if len(plan) != 144:
        raise AssertionError("quota plan must enumerate exactly 144 instances")
    return plan
