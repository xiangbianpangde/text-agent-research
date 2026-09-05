"""Independent condition derivation and strict precedence for Oracle state."""
from __future__ import annotations

from typing import Any, Dict, Mapping


CONDITION_PRECEDENCE = (
    "AMBIGUOUS_VERSION",
    "HASH_MISMATCH",
    "SOURCE_MISSING",
    "DEF_NOT_FOUND",
    "NOT_FOUND",
)


def expected_condition(state: Any, operation: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    """Derive expected behavior from Oracle state, never from an authored expected field."""
    target = params.get("ref") or params.get("entity_ref") or params.get("definition_ref") or params.get("entity")
    if operation in ("query_entity", "query_external_basis") and target:
        if state.object_for(str(target)) is None:
            error = "DEF_NOT_FOUND" if str(target).startswith("definition:") else "NOT_FOUND"
            return {"status": "fail_closed", "error_semantic": error, "behavior": "fail_closed"}
    return {"status": "success", "error_semantic": None, "behavior": "success_answer"}
