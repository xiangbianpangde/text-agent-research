"""Strict loaders for execution-only scenarios and participant predictions."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Mapping, Tuple

from bench.oracle.manifest import canonical_json_bytes, digest_json
from bench.oracle.time import TimestampError, parse_rfc3339


class ScenarioContractError(ValueError):
    """A scenario or prediction attempted to cross the evaluation boundary."""


TOP_KEYS = frozenset({"schema_version", "scenario_id", "track", "name", "initial_fixture", "steps"})
COMMON_STEP_KEYS = frozenset({"step", "action"})
STEP_KEYS = {
    "invoke": COMMON_STEP_KEYS | {"capture_id", "operation", "params", "timeout_ms"},
    "mutate": COMMON_STEP_KEYS | {
        "type", "target", "content_hash", "content", "reason", "new_ref",
        "entity_id", "version_ref", "path", "properties",
    },
    "advance_time": COMMON_STEP_KEYS | {"new_timestamp"},
    "context_reset": COMMON_STEP_KEYS,
    "restart_sut": COMMON_STEP_KEYS,
    "new_session": COMMON_STEP_KEYS | {"session_id", "capture_id"},
    "invoke_while_locked": COMMON_STEP_KEYS | {
        "capture_id", "operation", "params", "lock_path", "timeout_ms",
    },
    "external_crash": COMMON_STEP_KEYS | {"capture_id", "operation", "params", "pause_at", "timeout_ms"},
    "snapshot_state": COMMON_STEP_KEYS | {"capture_id", "require_no_tx_residue"},
    "snapshot_index": COMMON_STEP_KEYS | {"capture_id"},
}
REQUIRED_STEP_KEYS = {
    "invoke": COMMON_STEP_KEYS | {"operation", "params"},
    "mutate": COMMON_STEP_KEYS | {"type", "target"},
    "advance_time": COMMON_STEP_KEYS | {"new_timestamp"},
    "context_reset": COMMON_STEP_KEYS,
    "restart_sut": COMMON_STEP_KEYS,
    "new_session": COMMON_STEP_KEYS | {"session_id", "capture_id"},
    "invoke_while_locked": COMMON_STEP_KEYS | {"capture_id", "operation", "params", "lock_path"},
    "external_crash": COMMON_STEP_KEYS | {"capture_id", "operation", "params", "pause_at"},
    "snapshot_state": COMMON_STEP_KEYS | {"capture_id"},
    "snapshot_index": COMMON_STEP_KEYS | {"capture_id"},
}
MUTATION_TYPES = frozenset({
    "external_update", "semantic_change", "raw_invalidation", "create_version",
    "duplicate_version", "delete_file", "tamper_file", "create_file",
    "delete_tree", "touch_file", "corrupt_index", "semantic_tamper", "runtime_deviation",
})
FORBIDDEN_EVALUATION_KEYS = frozenset({
    "passed", "score", "expected_status", "expected_error", "expected_behavior",
    "expected_post_state", "gold_results", "gold_provenance_graph",
    "version_correct", "graph_exact_match", "tp", "fp", "fn", "civ",
    "impact_tp", "impact_fp", "impact_fn", "stale_tp", "stale_fp", "stale_fn",
})
PREDICTION_KEYS = frozenset({
    "schema_version", "capture_id", "status", "error_semantic", "warnings", "errors",
    "results", "provenance_graph", "asserted_facts", "evidence", "retrieval_mode",
    "ranking_authority", "route_sequence", "as_of",
})
PREDICTION_STATUSES = frozenset({"success", "warning", "error", "fail_closed", "review_required"})
RESULT_KEYS = frozenset({
    "ref", "entity_id", "version_ref", "path", "content_hash", "git_commit",
    "status", "is_stale", "relation_type", "section", "is_available",
})
REQUIRED_RESULT_KEYS = RESULT_KEYS - {"ref"}
QUERY_OPERATIONS = frozenset({
    "query_entity", "query_facts", "query_lineage", "query_state",
    "query_external_basis", "trace_evidence", "trace_graph", "query_sources",
    "query_history", "reconcile_integrity", "query_text_semantic",
    "query_text_lexical", "query_exact_routing", "query_project_current",
    "query_project_index", "query_as_of_state", "impact", "stale_status", "tx_reconcile",
})


def _string(value: Any, label: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value):
        raise ScenarioContractError(f"{label} must be a {'string' if empty else 'non-empty string'}")
    return value


def _assert_no_evaluation_fields(value: Any, label: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_EVALUATION_KEYS or normalized.startswith(("expected_", "gold_")):
                raise ScenarioContractError(f"{label} contains forbidden evaluation field: {key}")
            _assert_no_evaluation_fields(child, label)
    elif isinstance(value, list):
        for child in value:
            _assert_no_evaluation_fields(child, label)


def _strict_keys(value: Any, allowed: set[str] | frozenset[str], required: set[str] | frozenset[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioContractError(f"{label} must be an object")
    actual = set(value)
    extra = actual - set(allowed)
    missing = set(required) - actual
    if extra or missing:
        raise ScenarioContractError(f"{label} keys mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    if actual & FORBIDDEN_EVALUATION_KEYS:
        raise ScenarioContractError(f"{label} contains forbidden evaluation fields")
    return value


@dataclasses.dataclass(frozen=True)
class ScenarioActions:
    document: Mapping[str, Any]
    digest: str
    path: str

    @property
    def scenario_id(self) -> str:
        return str(self.document["scenario_id"])

    @property
    def steps(self) -> Tuple[Mapping[str, Any], ...]:
        return tuple(self.document["steps"])


def validate_scenario(document: Any, *, path: str = "<memory>") -> ScenarioActions:
    _assert_no_evaluation_fields(document, "scenario")
    doc = _strict_keys(document, TOP_KEYS, TOP_KEYS, "scenario")
    if doc["schema_version"] != "scenario-actions/v1":
        raise ScenarioContractError("unsupported scenario schema_version")
    for field in ("scenario_id", "track", "name", "initial_fixture"):
        _string(doc[field], field)
    if not isinstance(doc["steps"], list) or not doc["steps"]:
        raise ScenarioContractError("steps must be a non-empty array")

    captures = set()
    expected_step = 1
    normalized = []
    for index, raw in enumerate(doc["steps"]):
        if not isinstance(raw, dict):
            raise ScenarioContractError(f"steps[{index}] must be an object")
        action = raw.get("action")
        if action not in STEP_KEYS:
            raise ScenarioContractError(f"unsupported action: {action}")
        step = _strict_keys(raw, STEP_KEYS[action], REQUIRED_STEP_KEYS[action], f"steps[{index}]")
        if step["step"] != expected_step:
            raise ScenarioContractError("step numbers must be consecutive starting at 1")
        expected_step += 1
        if "capture_id" in step:
            capture_id = _string(step["capture_id"], f"steps[{index}].capture_id")
            if capture_id in captures:
                raise ScenarioContractError(f"duplicate capture_id: {capture_id}")
            captures.add(capture_id)
        if action in ("invoke", "invoke_while_locked", "external_crash"):
            operation = _string(step["operation"], f"steps[{index}].operation")
            if not isinstance(step["params"], dict):
                raise ScenarioContractError(f"steps[{index}].params must be an object")
            if operation in QUERY_OPERATIONS:
                if set(step["params"]) != {"query_id"}:
                    raise ScenarioContractError(
                        f"steps[{index}].params for {operation} must contain only query_id"
                    )
                _string(step["params"].get("query_id"), f"steps[{index}].params.query_id")
            elif action == "invoke" and operation == "index":
                if step["params"]:
                    raise ScenarioContractError("index params must be empty")
            elif action == "invoke_while_locked" and operation == "freeze_report":
                required_write = {"query_id", "idempotency_key", "actor", "authorization_ref"}
                if set(step["params"]) != required_write:
                    raise ScenarioContractError("locked freeze_report params are not exact")
            elif action == "external_crash" and operation == "freeze_report":
                required_write = {"idempotency_key", "actor", "authorization_ref"}
                if set(step["params"]) != required_write:
                    raise ScenarioContractError("crash freeze_report params are not exact")
            else:
                raise ScenarioContractError(f"unsupported action/operation pair: {action}/{operation}")
            timeout = step.get("timeout_ms", 30_000)
            if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 600_000:
                raise ScenarioContractError("timeout_ms must be an integer in [1, 600000]")
        if action == "mutate":
            if step["type"] not in MUTATION_TYPES:
                raise ScenarioContractError(f"unsupported mutation: {step['type']}")
            if step["type"] in ("create_version", "duplicate_version"):
                for field in ("new_ref", "entity_id", "version_ref", "path"):
                    _string(step.get(field), f"steps[{index}].{field}")
                if "content" in step:
                    raise ScenarioContractError("version mutations are materialized only from structured properties")
                if "properties" in step and not isinstance(step["properties"], dict):
                    raise ScenarioContractError(f"steps[{index}].properties must be an object")
        if action == "advance_time":
            try:
                parse_rfc3339(step["new_timestamp"], f"steps[{index}].new_timestamp")
            except TimestampError as exc:
                raise ScenarioContractError(str(exc)) from exc
        if action == "new_session":
            _string(step["session_id"], f"steps[{index}].session_id")
        if action == "invoke_while_locked":
            _string(step["lock_path"], f"steps[{index}].lock_path")
        if action == "snapshot_state" and not isinstance(step.get("require_no_tx_residue", False), bool):
            raise ScenarioContractError("require_no_tx_residue must be boolean")
        normalized.append(dict(step))

    output = dict(doc)
    output["steps"] = normalized
    return ScenarioActions(document=output, digest=digest_json(output), path=path)


def load_scenario(path: str | Path) -> ScenarioActions:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScenarioContractError(f"cannot load scenario {source}: {exc}") from exc
    return validate_scenario(value, path=str(source))


def validate_prediction(value: Any, *, capture_id: str | None = None) -> Mapping[str, Any]:
    _assert_no_evaluation_fields(value, "prediction")
    prediction = _strict_keys(value, PREDICTION_KEYS, PREDICTION_KEYS, "prediction")
    if prediction["schema_version"] != "prediction/v1":
        raise ScenarioContractError("unsupported prediction schema_version")
    _string(prediction["capture_id"], "prediction.capture_id", empty=True)
    if capture_id is not None and prediction["capture_id"] != capture_id:
        raise ScenarioContractError("prediction capture_id mismatch")
    if prediction["status"] not in PREDICTION_STATUSES:
        raise ScenarioContractError("unsupported prediction status")
    if prediction["error_semantic"] is not None and not isinstance(prediction["error_semantic"], str):
        raise ScenarioContractError("prediction.error_semantic must be string or null")
    for field in ("warnings", "errors", "asserted_facts", "evidence", "route_sequence"):
        if not isinstance(prediction[field], list):
            raise ScenarioContractError(f"prediction.{field} must be an array")
    if prediction["results"] is not None and not isinstance(prediction["results"], list):
        raise ScenarioContractError("prediction.results must be an array or null")
    for index, row in enumerate(prediction["results"] or []):
        result = _strict_keys(row, RESULT_KEYS, REQUIRED_RESULT_KEYS, f"prediction.results[{index}]")
        if "ref" in result and not isinstance(result["ref"], str):
            raise ScenarioContractError(f"prediction.results[{index}].ref must be string")
        for field in ("entity_id", "version_ref", "path", "content_hash", "git_commit", "status", "relation_type", "section"):
            if result[field] is not None and not isinstance(result[field], str):
                raise ScenarioContractError(f"prediction.results[{index}].{field} must be string or null")
        for field in ("is_stale", "is_available"):
            if not isinstance(result[field], bool):
                raise ScenarioContractError(f"prediction.results[{index}].{field} must be boolean")
    if prediction["provenance_graph"] is not None and not isinstance(prediction["provenance_graph"], dict):
        raise ScenarioContractError("prediction.provenance_graph must be object or null")
    for field in ("retrieval_mode", "ranking_authority", "as_of"):
        if prediction[field] is not None and not isinstance(prediction[field], str):
            raise ScenarioContractError(f"prediction.{field} must be string or null")
    return dict(prediction)
