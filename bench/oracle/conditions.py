"""Independent condition derivation and strict precedence for Oracle state."""
from __future__ import annotations

from typing import Any, Dict, Mapping


CONDITION_PRECEDENCE = (
    "AMBIGUOUS_VERSION",
    "HASH_MISMATCH",
    "SOURCE_MISSING",
    "CANONICAL_SEMANTIC_DRIFT",
    "DEF_NOT_FOUND",
    "NOT_FOUND",
)


def _condition(status: str, error: str | None, behavior: str) -> Dict[str, Any]:
    return {"status": status, "error_semantic": error, "behavior": behavior}


def expected_condition(state: Any, operation: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    """Derive expected behavior from Oracle state, never from an authored expected field."""
    target = str(
        params.get("ref")
        or params.get("entity_ref")
        or params.get("definition_ref")
        or params.get("entity")
        or params.get("owner")
        or ""
    )
    obj = state.object_for(target) if target else None

    if params.get("lock_held") is True:
        return _condition("error", "TX_LOCKED", "fail_closed")
    if obj is not None and obj["entity_id"] in state.ambiguous_versions:
        return _condition("fail_closed", "AMBIGUOUS_VERSION", "fail_closed")
    if operation == "query_sources" and obj is not None:
        dependencies = {row["ref"] for row in state.dependency_subgraph(obj["ref"])["nodes"]}
        if dependencies & state.missing_refs:
            return _condition("fail_closed", "SOURCE_MISSING", "fail_closed")
    if target in state.hash_mismatch_refs:
        return _condition("fail_closed", "HASH_MISMATCH", "fail_closed")
    if target in state.missing_refs:
        return _condition("fail_closed", "SOURCE_MISSING", "fail_closed")
    if target in state.semantic_tamper_refs:
        return _condition("review_required", "CANONICAL_SEMANTIC_DRIFT", "review_required")
    if operation == "reconcile_integrity":
        if state.index_state == "stale":
            return _condition("fail_closed", "DRIFT_DETECTED", "fail_closed")
        if state.hash_mismatch_refs:
            return _condition("fail_closed", "HASH_MISMATCH", "fail_closed")
        if state.missing_refs:
            return _condition("fail_closed", "SOURCE_MISSING", "fail_closed")
        if state.semantic_tamper_refs:
            return _condition("review_required", "CANONICAL_SEMANTIC_DRIFT", "review_required")
        if state.orphan_paths:
            return _condition("warning", None, "warning_attached")
        return _condition("success", None, "success_answer")
    if operation in ("query_entity", "query_external_basis") and target and obj is None:
        error = "DEF_NOT_FOUND" if target.startswith("definition:") or "@v" in target else "NOT_FOUND"
        return _condition("fail_closed", error, "fail_closed")
    return _condition("success", None, "success_answer")
