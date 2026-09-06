"""task-family/v1 closed-set model & identity (§19.3.1).

Every task family object must have exactly the 18 declared top-level fields
(``additionalProperties: false``). This module provides pure validation and
digest computation; it contains no Gold, no scores, and no participant logic.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Sequence

from bench.dsl.cjson import bench_cjson_digest

SCHEMA_VERSION = "task-family/v1"

FAMILY_IDS = tuple(f"F{i:02d}" for i in range(1, 9))

OBJECT_KINDS = frozenset({"entity", "artifact"})

# 21 B1 operations, lexical order (§19.6.2)
B1_OPERATIONS = (
    "freeze_report",
    "impact",
    "index",
    "query_as_of_state",
    "query_entity",
    "query_exact_routing",
    "query_external_basis",
    "query_facts",
    "query_history",
    "query_lineage",
    "query_project_current",
    "query_project_index",
    "query_sources",
    "query_state",
    "query_text_lexical",
    "query_text_semantic",
    "reconcile_integrity",
    "stale_status",
    "trace_evidence",
    "trace_graph",
    "tx_reconcile",
)
B1_OPERATION_SET = frozenset(B1_OPERATIONS)

# P0-owned physical mutation vocabulary (bench/dsl/mutations.py)
MUTATION_KINDS = frozenset({
    "external_update",
    "create_version",
    "duplicate_version",
    "raw_invalidation",
    "delete_file",
    "tamper_file",
    "runtime_deviation",
    "semantic_tamper",
    "touch_file",
    "corrupt_index",
    "create_file",
    "delete_tree",
})

SUBVARIANT_PARAM_KEYS = frozenset({
    "branching_factor",
    "max_depth",
    "min_depth",
    "noise_rate_ppm",
    "redundancy_factor",
})

CHECKPOINT_TYPES = frozenset({"results", "provenance_graph", "asserted_facts", "evidence"})

METRIC_IDS = frozenset({"CIV", "FCAA", "IF1", "PGEM", "SF1", "VLP", "ZHR"})

TOP_LEVEL_FIELDS = (
    "schema_version",
    "family_id",
    "family_version",
    "capability",
    "p0_anchors",
    "object_kinds",
    "operation_allowlist",
    "mutation_allowlist",
    "subvariant_schedule",
    "cardinality_constraints",
    "temporal_constraints",
    "topology_constraints",
    "positive_requirements",
    "negative_requirements",
    "checkpoint_types",
    "applicable_metrics",
    "forbidden_conditions",
    "generation_acceptance_predicates",
)

_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_RFC3339_UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?Z$")


class TaskFamilyError(ValueError):
    """Raised when a task-family/v1 object violates the closed-set schema."""


def _require_string_array(name: str, value: Any, *, non_empty: bool = False) -> List[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
        raise TaskFamilyError(f"{name} must be an array of strings")
    if non_empty and not value:
        raise TaskFamilyError(f"{name} must be non-empty")
    return value


def validate_task_family(document: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate a task-family/v1 object against the §19.3.1 closed set."""
    unknown = set(document.keys()) - set(TOP_LEVEL_FIELDS)
    if unknown:
        raise TaskFamilyError(f"unknown top-level fields: {sorted(unknown)}")
    missing = set(TOP_LEVEL_FIELDS) - set(document.keys())
    if missing:
        raise TaskFamilyError(f"missing required fields: {sorted(missing)}")

    if document["schema_version"] != SCHEMA_VERSION:
        raise TaskFamilyError(f"schema_version must be {SCHEMA_VERSION!r}")

    family_id = document["family_id"]
    if family_id not in FAMILY_IDS:
        raise TaskFamilyError(f"family_id must be one of {FAMILY_IDS}, got {family_id!r}")

    family_version = document["family_version"]
    if not isinstance(family_version, str) or not _SEMVER_RE.fullmatch(family_version):
        raise TaskFamilyError(f"family_version must match semver, got {family_version!r}")

    if not isinstance(document["capability"], str) or not document["capability"]:
        raise TaskFamilyError("capability must be a non-empty string")

    _require_string_array("p0_anchors", document["p0_anchors"], non_empty=True)
    object_kinds = _require_string_array("object_kinds", document["object_kinds"], non_empty=True)
    for kind in object_kinds:
        if kind not in OBJECT_KINDS:
            raise TaskFamilyError(f"object_kinds element invalid: {kind!r}")

    ops = _require_string_array("operation_allowlist", document["operation_allowlist"], non_empty=True)
    for op in ops:
        if op not in B1_OPERATION_SET:
            raise TaskFamilyError(f"operation_allowlist element not a B1 operation: {op!r}")
    if sorted(ops) != ops:
        raise TaskFamilyError("operation_allowlist must be in lexical ascending order")
    if len(set(ops)) != len(ops):
        raise TaskFamilyError("operation_allowlist must not contain duplicates")

    muts = _require_string_array("mutation_allowlist", document["mutation_allowlist"])
    for m in muts:
        if m not in MUTATION_KINDS:
            raise TaskFamilyError(f"mutation_allowlist element invalid: {m!r}")

    schedule = document["subvariant_schedule"]
    if not isinstance(schedule, list) or not schedule:
        raise TaskFamilyError("subvariant_schedule must be a non-empty array")
    seen_ids = set()
    for entry in schedule:
        if not isinstance(entry, dict):
            raise TaskFamilyError("subvariant_schedule entries must be objects")
        unknown_entry = set(entry.keys()) - {"subvariant_id", "weight", "parameters"}
        if unknown_entry:
            raise TaskFamilyError(f"subvariant entry has unknown fields: {sorted(unknown_entry)}")
        missing_entry = {"subvariant_id", "weight", "parameters"} - set(entry.keys())
        if missing_entry:
            raise TaskFamilyError(f"subvariant entry missing fields: {sorted(missing_entry)}")
        sub_id = entry["subvariant_id"]
        if not isinstance(sub_id, str) or not sub_id:
            raise TaskFamilyError("subvariant_id must be a non-empty string")
        if sub_id in seen_ids:
            raise TaskFamilyError(f"duplicate subvariant_id: {sub_id!r}")
        seen_ids.add(sub_id)
        weight = entry["weight"]
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 1:
            raise TaskFamilyError(f"subvariant weight must be Int64 >= 1, got {weight!r}")
        params = entry["parameters"]
        if not isinstance(params, dict):
            raise TaskFamilyError("subvariant parameters must be an object")
        for pk, pv in params.items():
            if pk not in SUBVARIANT_PARAM_KEYS:
                raise TaskFamilyError(f"subvariant parameter key not in closed set: {pk!r}")
            if not isinstance(pv, int) or isinstance(pv, bool) or pv < 0:
                raise TaskFamilyError(f"subvariant parameter {pk!r} must be a non-negative Int64, got {pv!r}")

    card = document["cardinality_constraints"]
    if not isinstance(card, dict) or set(card.keys()) != {"min_entities", "max_entities", "min_artifacts", "max_artifacts"}:
        raise TaskFamilyError("cardinality_constraints must contain exactly min/max_entities and min/max_artifacts")
    for k, v in card.items():
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            raise TaskFamilyError(f"cardinality_constraints.{k} must be a non-negative Int64")
    if card["min_entities"] > card["max_entities"] or card["min_artifacts"] > card["max_artifacts"]:
        raise TaskFamilyError("cardinality min must not exceed max")

    temporal = document["temporal_constraints"]
    if not isinstance(temporal, dict) or set(temporal.keys()) != {"start_time", "tick_interval_seconds"}:
        raise TaskFamilyError("temporal_constraints must contain exactly start_time and tick_interval_seconds")
    if not isinstance(temporal["start_time"], str) or not _RFC3339_UTC_RE.fullmatch(temporal["start_time"]):
        raise TaskFamilyError(f"temporal_constraints.start_time must be RFC3339 UTC, got {temporal['start_time']!r}")
    tick = temporal["tick_interval_seconds"]
    if not isinstance(tick, int) or isinstance(tick, bool) or tick <= 0:
        raise TaskFamilyError("temporal_constraints.tick_interval_seconds must be a positive Int64")

    topo = document["topology_constraints"]
    if not isinstance(topo, dict) or set(topo.keys()) != {"allow_cycles", "max_depth"}:
        raise TaskFamilyError("topology_constraints must contain exactly allow_cycles and max_depth")
    if not isinstance(topo["allow_cycles"], bool):
        raise TaskFamilyError("topology_constraints.allow_cycles must be boolean")
    depth = topo["max_depth"]
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
        raise TaskFamilyError("topology_constraints.max_depth must be a positive Int64")

    _require_string_array("positive_requirements", document["positive_requirements"])
    _require_string_array("negative_requirements", document["negative_requirements"])

    checkpoints = _require_string_array("checkpoint_types", document["checkpoint_types"], non_empty=True)
    for c in checkpoints:
        if c not in CHECKPOINT_TYPES:
            raise TaskFamilyError(f"checkpoint_types element invalid: {c!r}")

    metrics = _require_string_array("applicable_metrics", document["applicable_metrics"], non_empty=True)
    for m in metrics:
        if m not in METRIC_IDS:
            raise TaskFamilyError(f"applicable_metrics element not in metric profile: {m!r}")

    _require_string_array("forbidden_conditions", document["forbidden_conditions"])
    _require_string_array("generation_acceptance_predicates", document["generation_acceptance_predicates"])

    return dict(document)


def family_body_digest(document: Mapping[str, Any]) -> str:
    """family_body_digest = sha256:SHA256(bench-cjson(task-family/v1))."""
    return bench_cjson_digest(document)


def build_family_identity(document: Mapping[str, Any]) -> Dict[str, str]:
    """Build the FamilyIdentity object for a validated task family (§19.3.1)."""
    return {
        "family_body_digest": family_body_digest(document),
        "family_id": document["family_id"],
        "family_schema_version": SCHEMA_VERSION,
        "family_version": document["family_version"],
    }


def family_identity_digest(document: Mapping[str, Any]) -> str:
    """family_digest = sha256:SHA256(bench-cjson(FamilyIdentity))."""
    return bench_cjson_digest(build_family_identity(document))
