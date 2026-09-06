"""scenario-actions/v2 validation (deterministic delta over P0 v1 rules).

§19.3.3: v2 differs from v1 only in $id, schema_version.const, and
$defs.invokeParams (expanded oneOf adding writeParamsWithQuery). The loader in
bench/dsl/loader.py enforces the v1 closed set; this module re-uses those rules
and permits ordinary `invoke` steps carrying full freeze_report write params.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from bench.dsl.loader import (
    FORBIDDEN_EVALUATION_KEYS,
    QUERY_OPERATIONS,
    REQUIRED_STEP_KEYS,
    STEP_KEYS,
    MUTATION_TYPES,
    ScenarioContractError,
    ScenarioActions,
    _assert_no_evaluation_fields,
    _string,
    _strict_keys,
)
from bench.oracle.manifest import digest_json
from bench.oracle.time import parse_rfc3339, TimestampError

V2_SCHEMA_PATH = Path(__file__).parent / "schemas" / "scenario-actions-v2.schema.json"

TOP_KEYS = frozenset({"schema_version", "scenario_id", "track", "name", "initial_fixture", "steps"})

FREEZE_REPORT_WRITE_PARAMS = frozenset({"query_id", "idempotency_key", "actor", "authorization_ref"})
FREEZE_REPORT_WRITE_PARAMS_REQUIRED = frozenset({"idempotency_key", "actor", "authorization_ref"})


def load_v2_schema() -> Mapping[str, Any]:
    return json.loads(V2_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_scenario_v2(document: Any, *, path: str = "<memory>") -> ScenarioActions:
    """Validate a scenario-actions/v2 document (same closed set as v1 plus the
    invokeParams write-params union)."""
    _assert_no_evaluation_fields(document, "scenario")
    doc = _strict_keys(document, TOP_KEYS, TOP_KEYS, "scenario")
    if doc["schema_version"] != "scenario-actions/v2":
        raise ScenarioContractError("unsupported scenario schema_version")
    for field in ("scenario_id", "track", "name", "initial_fixture"):
        _string(doc[field], field)
    if not isinstance(doc["steps"], list) or not doc["steps"]:
        raise ScenarioContractError("steps must be a non-empty array")

    captures: set[str] = set()
    expected_step = 1
    normalized: list[dict[str, Any]] = []
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
            params = step["params"]
            if operation in QUERY_OPERATIONS:
                if set(params) != {"query_id"}:
                    raise ScenarioContractError(
                        f"steps[{index}].params for {operation} must contain only query_id"
                    )
                _string(params.get("query_id"), f"steps[{index}].params.query_id")
            elif action == "invoke" and operation == "index":
                if params:
                    raise ScenarioContractError("index params must be empty")
            elif action == "invoke" and operation == "freeze_report":
                # v2 delta: ordinary invoke carrying full write params
                extra = set(params) - FREEZE_REPORT_WRITE_PARAMS
                missing = FREEZE_REPORT_WRITE_PARAMS_REQUIRED - set(params)
                if extra or missing:
                    raise ScenarioContractError(
                        f"steps[{index}].params freeze_report write params mismatch: "
                        f"missing={sorted(missing)}, extra={sorted(extra)}"
                    )
                for field in FREEZE_REPORT_WRITE_PARAMS & set(params):
                    _string(params[field], f"steps[{index}].params.{field}")
            elif action == "invoke_while_locked" and operation == "freeze_report":
                required_write = FREEZE_REPORT_WRITE_PARAMS
                if set(params) != required_write:
                    raise ScenarioContractError("locked freeze_report params are not exact")
            elif action == "external_crash" and operation == "freeze_report":
                required_write = FREEZE_REPORT_WRITE_PARAMS_REQUIRED
                if set(params) != required_write:
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
