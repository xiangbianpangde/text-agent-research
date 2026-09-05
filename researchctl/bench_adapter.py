"""Official ResearchCTL participant adapter for ResearchCTL-Bench P0.2.

This is SUT-owned code. It exposes the same stdio NDJSON contract expected from
any third-party participant and keeps all ResearchCTL imports outside the generic
benchmark runner/client.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import time
from typing import Any, Dict, Optional


PROTOCOL_VERSION = "sut-adapter/v1"
OPERATIONS = {"prepare", "invoke", "reset_context", "restart", "health", "shutdown"}


def _response(request: Dict[str, Any], status: str, **fields: Any) -> Dict[str, Any]:
    payload = {
        "schema_version": PROTOCOL_VERSION,
        "request_id": request.get("request_id", "invalid-request"),
        "operation": request.get("operation", "invalid"),
        "status": status,
    }
    payload.update(fields)
    return payload


def _error(request: Dict[str, Any], code: str, message: str) -> Dict[str, Any]:
    return _response(request, "error", error={"code": code, "message": message})


def _write(message: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _validate_request(value: Any) -> Optional[str]:
    if not isinstance(value, dict):
        return "request must be a JSON object"
    if value.get("schema_version") != PROTOCOL_VERSION:
        return "unsupported schema_version"
    if not isinstance(value.get("request_id"), str) or not value["request_id"]:
        return "request_id must be a non-empty string"
    if value.get("operation") not in OPERATIONS:
        return "unsupported operation"
    if value["operation"] == "prepare":
        workspace = value.get("workspace")
        if not isinstance(workspace, str) or not workspace:
            return "prepare.workspace must be a non-empty string"
    if value["operation"] == "invoke":
        arguments = value.get("arguments")
        if not isinstance(arguments, list) or any(not isinstance(item, str) for item in arguments):
            return "invoke.arguments must be a string array"
        timeout_ms = value.get("timeout_ms", 30_000)
        if not isinstance(timeout_ms, int) or isinstance(timeout_ms, bool) or not 1 <= timeout_ms <= 600_000:
            return "invoke.timeout_ms must be an integer in [1, 600000]"
        if not isinstance(value.get("capture_id", ""), str):
            return "invoke.capture_id must be a string"
        control = value.get("test_control")
        if control is not None:
            if not isinstance(control, dict) or set(control) != {"pause_at", "barrier_path"}:
                return "invoke.test_control requires only pause_at and barrier_path"
            if any(not isinstance(control.get(key), str) or not control[key] for key in control):
                return "invoke.test_control values must be non-empty strings"
    return None


def _normalize_prediction(native: Any, capture_id: str) -> Dict[str, Any]:
    payload = native if isinstance(native, dict) else {}
    status = payload.get("status", "error")
    if status == "replay":
        status = "success"
    if status not in {"success", "warning", "error", "fail_closed", "review_required"}:
        status = "error"
    results = payload.get("results", [])
    if results is not None and not isinstance(results, list):
        results = []
    return {
        "schema_version": "prediction/v1",
        "capture_id": capture_id,
        "status": status,
        "error_semantic": payload.get("error_semantic") if isinstance(payload.get("error_semantic"), str) else None,
        "warnings": payload.get("warnings") if isinstance(payload.get("warnings"), list) else [],
        "errors": payload.get("errors") if isinstance(payload.get("errors"), list) else [],
        "results": results,
        "provenance_graph": payload.get("provenance_graph") if isinstance(payload.get("provenance_graph"), dict) else None,
        "asserted_facts": payload.get("asserted_facts") if isinstance(payload.get("asserted_facts"), list) else [],
        "evidence": payload.get("evidence") if isinstance(payload.get("evidence"), list) else [],
        "retrieval_mode": payload.get("query_type") if isinstance(payload.get("query_type"), str) else None,
        "ranking_authority": payload.get("ranking_authority") if isinstance(payload.get("ranking_authority"), str) else None,
    }


def _option(arguments: list[str], name: str) -> str:
    try:
        return arguments[arguments.index(name) + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError(f"missing adapter option: {name}") from exc


def _invoke_with_barrier(request: Dict[str, Any], workspace: str) -> Dict[str, Any]:
    from .tx.freeze import freeze_report

    arguments = request["arguments"]
    control = request["test_control"]
    if not arguments or arguments[0] != "freeze-report":
        return _error(request, "UNSUPPORTED_TEST_CONTROL", "stage barriers currently require freeze-report")
    barrier = os.path.realpath(os.path.join(workspace, control["barrier_path"]))
    if os.path.commonpath([os.path.realpath(workspace), barrier]) != os.path.realpath(workspace):
        return _error(request, "INVALID_BARRIER_PATH", "barrier path escapes workspace")

    def on_step(point: str) -> None:
        if point != control["pause_at"]:
            return
        os.makedirs(os.path.dirname(barrier), exist_ok=True)
        with open(barrier, "w", encoding="utf-8") as handle:
            json.dump({"stage": point, "pid": os.getpid()}, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        while True:
            time.sleep(1)

    native = freeze_report(
        root=workspace,
        db_path=os.path.join(workspace, ".index", "research.sqlite"),
        idempotency_key=_option(arguments, "--idempotency-key"),
        actor=_option(arguments, "--actor"),
        authorization_ref=_option(arguments, "--authorization-ref"),
        on_step=on_step,
    )
    prediction = _normalize_prediction(native, request.get("capture_id", ""))
    return _response(request, "ok", exit_code=0, stdout=json.dumps(native), stderr="", payload=prediction)


def _invoke(request: Dict[str, Any], workspace: str) -> Dict[str, Any]:
    if request.get("test_control") is not None:
        return _invoke_with_barrier(request, workspace)

    from .cli import main as researchctl_main

    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = researchctl_main(["--root", workspace, *request["arguments"]])
    except SystemExit as exc:
        exit_code = int(exc.code) if isinstance(exc.code, int) else 1
    except BaseException as exc:  # Participant exceptions become observable SUT failures.
        return _error(request, "SUT_EXCEPTION", f"{type(exc).__name__}: {exc}")

    out = stdout.getvalue()
    native = None
    try:
        native = json.loads(out)
    except (json.JSONDecodeError, TypeError):
        pass
    payload = _normalize_prediction(native, request.get("capture_id", ""))
    return _response(
        request,
        "ok",
        exit_code=int(exit_code),
        stdout=out,
        stderr=stderr.getvalue(),
        payload=payload,
    )


def main() -> int:
    workspace: Optional[str] = None
    for raw_line in sys.stdin:
        try:
            request = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            request = {"request_id": "invalid-request", "operation": "invalid"}
            _write(_error(request, "INVALID_JSON", str(exc)))
            continue

        validation_error = _validate_request(request)
        if validation_error:
            _write(_error(request, "INVALID_REQUEST", validation_error))
            continue

        operation = request["operation"]
        if operation == "prepare":
            candidate = os.path.realpath(request["workspace"])
            if not os.path.isdir(candidate):
                _write(_error(request, "WORKSPACE_NOT_FOUND", candidate))
                continue
            workspace = candidate
            _write(_response(request, "ok", details={"workspace_ready": True}))
        elif operation == "health":
            _write(
                _response(
                    request,
                    "ok",
                    details={
                        "adapter": "researchctl",
                        "pid": os.getpid(),
                        "capabilities": sorted(OPERATIONS),
                        "workspace_prepared": workspace is not None,
                        "pythonpath_present": "PYTHONPATH" in os.environ,
                    },
                )
            )
        elif operation == "invoke":
            if workspace is None:
                _write(_error(request, "NOT_PREPARED", "prepare must succeed before invoke"))
            else:
                _write(_invoke(request, workspace))
        elif operation == "reset_context":
            _write(_response(request, "ok", details={"context_reset": True}))
        elif operation == "restart":
            _write(_response(request, "ok", details={"restarting": True}))
            return 0
        elif operation == "shutdown":
            _write(_response(request, "ok", details={"shutdown": True}))
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
