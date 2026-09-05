"""Independent, deliberately weak SUT speaking sut-adapter/v1.

It imports no benchmark adapter implementation. This proves the wire contract
can be implemented independently and measured by the same runner.
"""
from __future__ import annotations

import json
import os
import sys


VERSION = "sut-adapter/v1"
workspace = None


def emit(request, status="ok", **fields):
    response = {
        "schema_version": VERSION,
        "request_id": request.get("request_id", "invalid"),
        "operation": request.get("operation", "invalid"),
        "status": status,
    }
    response.update(fields)
    print(json.dumps(response, sort_keys=True, separators=(",", ":")), flush=True)


for line in sys.stdin:
    try:
        request = json.loads(line)
    except json.JSONDecodeError as exc:
        request = {"request_id": "invalid", "operation": "invalid"}
        emit(request, "error", error={"code": "INVALID_JSON", "message": str(exc)})
        continue

    operation = request.get("operation")
    if request.get("schema_version") != VERSION:
        emit(request, "error", error={"code": "BAD_VERSION", "message": "unsupported version"})
    elif operation == "prepare":
        workspace = request.get("workspace")
        emit(request, details={"workspace_ready": bool(workspace)})
    elif operation == "health":
        emit(
            request,
            details={
                "adapter": "independent-stub",
                "pid": os.getpid(),
                "capabilities": ["prepare", "invoke", "reset_context", "restart", "health", "shutdown"],
                "pythonpath_present": "PYTHONPATH" in os.environ,
            },
        )
    elif operation == "invoke":
        payload = {
            "schema_version": "prediction/v1",
            "capture_id": request.get("capture_id", ""),
            "status": "error",
            "error_semantic": "BASELINE_UNSUPPORTED",
            "warnings": [],
            "errors": [{"code": "BASELINE_UNSUPPORTED"}],
            "results": [],
            "provenance_graph": None,
            "asserted_facts": [],
            "evidence": [],
            "retrieval_mode": None,
            "ranking_authority": None,
            "route_sequence": [],
            "as_of": None,
        }
        emit(
            request,
            exit_code=1,
            stdout=json.dumps(payload),
            stderr="independent baseline does not implement ResearchCTL operations",
            payload=payload,
        )
    elif operation == "reset_context":
        emit(request, details={"context_reset": True})
    elif operation == "restart":
        emit(request, details={"restarting": True})
        raise SystemExit(0)
    elif operation == "shutdown":
        emit(request, details={"shutdown": True})
        raise SystemExit(0)
    else:
        emit(request, "error", error={"code": "BAD_OPERATION", "message": "unsupported operation"})
