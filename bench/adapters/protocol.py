"""Frozen P0.2 wire contract for process-level SUT adapters.

The transport is one UTF-8 JSON object per line on stdin/stdout. Diagnostic
logging belongs on stderr. Request IDs bind every response to exactly one
request; unsolicited stdout is a protocol violation.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable


PROTOCOL_VERSION = "sut-adapter/v1"
OPERATIONS = frozenset({"prepare", "invoke", "reset_context", "restart", "health", "shutdown"})
STATUSES = frozenset({"ok", "error"})


class AdapterProtocolError(RuntimeError):
    """Raised when a participant violates the adapter wire contract."""


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise AdapterProtocolError(f"{field} must be a non-empty string")
    return value


def make_request(request_id: str, operation: str, **fields: Any) -> Dict[str, Any]:
    if operation not in OPERATIONS:
        raise AdapterProtocolError(f"unsupported operation: {operation}")
    request = {
        "schema_version": PROTOCOL_VERSION,
        "request_id": _require_string(request_id, "request_id"),
        "operation": operation,
    }
    request.update(fields)
    validate_request(request)
    return request


def validate_request(request: Any) -> Dict[str, Any]:
    if not isinstance(request, dict):
        raise AdapterProtocolError("request must be a JSON object")
    if request.get("schema_version") != PROTOCOL_VERSION:
        raise AdapterProtocolError("unsupported schema_version")
    _require_string(request.get("request_id"), "request_id")
    operation = _require_string(request.get("operation"), "operation")
    if operation not in OPERATIONS:
        raise AdapterProtocolError(f"unsupported operation: {operation}")
    if operation == "prepare":
        _require_string(request.get("workspace"), "workspace")
    if operation == "invoke":
        arguments = request.get("arguments")
        if not isinstance(arguments, list) or any(not isinstance(item, str) for item in arguments):
            raise AdapterProtocolError("invoke.arguments must be a string array")
        timeout_ms = request.get("timeout_ms", 30_000)
        if not isinstance(timeout_ms, int) or isinstance(timeout_ms, bool) or not 1 <= timeout_ms <= 600_000:
            raise AdapterProtocolError("invoke.timeout_ms must be an integer in [1, 600000]")
        capture_id = request.get("capture_id", "")
        if not isinstance(capture_id, str):
            raise AdapterProtocolError("invoke.capture_id must be a string")
        test_control = request.get("test_control")
        if test_control is not None:
            if not isinstance(test_control, dict):
                raise AdapterProtocolError("invoke.test_control must be an object")
            if set(test_control) != {"pause_at", "barrier_path"}:
                raise AdapterProtocolError("invoke.test_control requires only pause_at and barrier_path")
            _require_string(test_control.get("pause_at"), "invoke.test_control.pause_at")
            _require_string(test_control.get("barrier_path"), "invoke.test_control.barrier_path")
    return request


def validate_response(
    response: Any,
    *,
    expected_request_id: str,
    expected_operation: str,
) -> Dict[str, Any]:
    if not isinstance(response, dict):
        raise AdapterProtocolError("response must be a JSON object")
    if response.get("schema_version") != PROTOCOL_VERSION:
        raise AdapterProtocolError("response has unsupported schema_version")
    if response.get("request_id") != expected_request_id:
        raise AdapterProtocolError("response request_id mismatch")
    if response.get("operation") != expected_operation:
        raise AdapterProtocolError("response operation mismatch")
    if response.get("status") not in STATUSES:
        raise AdapterProtocolError("response status must be ok or error")

    if response["status"] == "error":
        error = response.get("error")
        if not isinstance(error, dict):
            raise AdapterProtocolError("error response requires an error object")
        _require_string(error.get("code"), "error.code")
        _require_string(error.get("message"), "error.message")

    if expected_operation == "invoke" and response["status"] == "ok":
        exit_code = response.get("exit_code")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise AdapterProtocolError("invoke response requires integer exit_code")
        for field in ("stdout", "stderr"):
            if not isinstance(response.get(field), str):
                raise AdapterProtocolError(f"invoke response requires string {field}")
    return response


def encode_message(message: Dict[str, Any]) -> str:
    """Canonical compact NDJSON encoding; embedded newlines are escaped by JSON."""
    return json.dumps(message, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def command_digest(command: Iterable[str]) -> str:
    """Stable digest for report binding without exposing host-specific command paths."""
    import hashlib

    payload = json.dumps(list(command), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
