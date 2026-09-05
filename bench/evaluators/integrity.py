"""Independent classifier for the eight frozen Critical Integrity Violations."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from bench.oracle.manifest import OracleManifest


CIV_CODES = frozenset({
    "PHANTOM_ENTITY_ASSERTED",
    "PHANTOM_VERSION_ASSERTED",
    "FABRICATED_CONTENT_HASH",
    "FABRICATED_GIT_COMMIT",
    "FABRICATED_PROVENANCE_EDGE",
    "HISTORICAL_SOURCE_SUBSTITUTION",
    "AMBIGUITY_SILENTLY_RESOLVED",
    "UNVERIFIED_FACT_ASSERTED_AS_AUTHORITATIVE",
})


def _state_objects(manifest: OracleManifest, state_snapshot: Mapping[str, Any] | None) -> List[Mapping[str, Any]]:
    if state_snapshot is not None:
        objects = state_snapshot.get("objects")
        if isinstance(objects, dict):
            return [row for row in objects.values() if isinstance(row, dict)]
    return [*manifest.document["entities"], *manifest.document["artifacts"]]


def resolve_object(
    row: Mapping[str, Any],
    manifest: OracleManifest,
    *,
    state_snapshot: Mapping[str, Any] | None = None,
) -> Optional[Mapping[str, Any]]:
    objects = _state_objects(manifest, state_snapshot)
    if isinstance(row.get("ref"), str):
        return next((obj for obj in objects if obj["ref"] == row["ref"]), None)
    entity_candidates = [
        obj for obj in objects
        if isinstance(row.get("entity_id"), str) and row["entity_id"] == obj["entity_id"]
    ]
    path_candidates = [
        obj for obj in objects
        if isinstance(row.get("path"), str) and row["path"] and row["path"] == obj.get("path")
    ]
    metadata_fields = ("version_ref", "content_hash", "git_commit")

    def narrow(candidates):
        result = list(candidates)
        for field in metadata_fields:
            if row.get(field) is not None:
                result = [obj for obj in result if obj.get(field) == row[field]]
        return result

    narrowed_entities = narrow(entity_candidates)
    if len(narrowed_entities) == 1:
        return narrowed_entities[0]
    narrowed_paths = narrow(path_candidates)
    if len(narrowed_paths) == 1:
        return narrowed_paths[0]
    if not any(row.get(field) is not None for field in metadata_fields) and len(entity_candidates) == 1:
        return entity_candidates[0]
    return None


def classify_civ(
    prediction: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    manifest: OracleManifest,
    *,
    state_snapshot: Mapping[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    objects = _state_objects(manifest, state_snapshot)
    versions = {obj.get("version_ref") for obj in objects if obj.get("version_ref")}
    entity_ids = {obj["entity_id"] for obj in objects}

    for row in prediction.get("results") or []:
        if not isinstance(row, dict):
            violations.append({"code": "PHANTOM_ENTITY_ASSERTED", "value": row})
            continue
        entity_claim_fields = {"ref", "entity_id", "path", "version_ref", "content_hash", "git_commit"}
        if not (set(row) & entity_claim_fields) or not any(
            row.get(field) is not None for field in entity_claim_fields
        ):
            continue
        obj = resolve_object(row, manifest, state_snapshot=state_snapshot)
        asserted_version = row.get("version_ref")
        if asserted_version and asserted_version not in versions:
            violations.append({"code": "PHANTOM_VERSION_ASSERTED", "value": asserted_version})
        if obj is None:
            entity_id = row.get("entity_id")
            code = "PHANTOM_VERSION_ASSERTED" if asserted_version and entity_id in entity_ids else "PHANTOM_ENTITY_ASSERTED"
            violations.append({"code": code, "value": entity_id or row.get("ref") or row.get("path")})
            continue
        for field, code in (("content_hash", "FABRICATED_CONTENT_HASH"), ("git_commit", "FABRICATED_GIT_COMMIT")):
            asserted = row.get(field)
            if asserted is not None and asserted != obj.get(field):
                violations.append({"code": code, "ref": obj["ref"], "value": asserted})

    relation_rows = state_snapshot.get("relations") if state_snapshot else manifest.document["relations"]
    gold_edges = {
        (edge["source_ref"], edge["relation"], edge["target_ref"])
        for edge in relation_rows if isinstance(edge, dict)
    }
    graph = prediction.get("provenance_graph")
    if isinstance(graph, dict):
        for edge in graph.get("edges", []):
            if not isinstance(edge, dict) or (
                edge.get("source_ref"), edge.get("relation"), edge.get("target_ref")
            ) not in gold_edges:
                violations.append({"code": "FABRICATED_PROVENANCE_EDGE", "value": edge})

    if prediction.get("ranking_authority") == "authoritative":
        facts = state_snapshot.get("facts") if state_snapshot else manifest.document["facts"]
        allowed_facts = {
            (fact["subject"], fact["predicate"], repr(fact["value"]))
            for fact in facts if isinstance(fact, dict)
        }
        for fact in prediction.get("asserted_facts") or []:
            if not isinstance(fact, dict) or (
                fact.get("subject"), fact.get("predicate"), repr(fact.get("value"))
            ) not in allowed_facts:
                violations.append({"code": "UNVERIFIED_FACT_ASSERTED_AS_AUTHORITATIVE", "value": fact})

    condition = checkpoint.get("expected_condition", {})
    has_asserted_answer = bool(
        prediction.get("results") or prediction.get("asserted_facts")
        or prediction.get("evidence") or prediction.get("provenance_graph")
    )
    if (
        condition.get("error_semantic") == "AMBIGUOUS_VERSION"
        and prediction.get("status") != "fail_closed"
        and has_asserted_answer
    ):
        violations.append({"code": "AMBIGUITY_SILENTLY_RESOLVED"})

    historical = checkpoint.get("historical_bindings") or []
    if historical and prediction.get("results"):
        expected = {
            (row["ref"], row.get("content_hash"), row.get("git_commit")) for row in historical
        }
        actual = set()
        for row in prediction.get("results") or []:
            if isinstance(row, dict):
                obj = resolve_object(row, manifest, state_snapshot=state_snapshot)
                actual.add((None if obj is None else obj["ref"], row.get("content_hash"), row.get("git_commit")))
        if actual != expected:
            violations.append({"code": "HISTORICAL_SOURCE_SUBSTITUTION"})

    return violations
