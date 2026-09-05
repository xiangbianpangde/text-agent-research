"""Deliberately degenerate or hostile SUTs for P0.4 acceptance."""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path


VERSION = "sut-adapter/v1"
OPERATIONS = {"prepare", "invoke", "reset_context", "restart", "health", "shutdown"}
mode = os.environ.get("BENCH_CONTROL_MODE", "always-pass")
workspace = None
gold_read_blocked = None


def emit(request, status="ok", **fields):
    response = {
        "schema_version": VERSION,
        "request_id": request.get("request_id", "invalid"),
        "operation": request.get("operation", "invalid"),
        "status": status,
    }
    response.update(fields)
    print(json.dumps(response, sort_keys=True, separators=(",", ":")), flush=True)


def row(entity_id, *, stale=False):
    return {
        "entity_id": entity_id,
        "version_ref": None,
        "path": None,
        "content_hash": None,
        "git_commit": None,
        "status": None,
        "is_stale": stale,
        "relation_type": "impacts" if stale else None,
        "section": None,
        "is_available": True,
    }


def prediction(request):
    capture_id = request.get("capture_id", "")
    query_id = request.get("query_id")
    base = {
        "schema_version": "prediction/v1",
        "capture_id": capture_id,
        "status": "success",
        "error_semantic": None,
        "warnings": [],
        "errors": [],
        "results": [],
        "provenance_graph": None,
        "asserted_facts": [],
        "evidence": [],
        "retrieval_mode": None,
        "ranking_authority": None,
        "route_sequence": [],
        "as_of": request.get("virtual_time"),
    }
    if mode == "always-abstain":
        base["status"] = "fail_closed"
        base["error_semantic"] = "NOT_FOUND"
    elif mode == "universal-stale":
        base["results"] = [row(value, stale=True) for value in (
            "CURRENT", "REPORT-001", "REPORT-002", "REPORT-003", "ORG-EXP017", "ORG-EXP020", "R051", "R052", "R053", "EXP020-R001",
        )]
        base["retrieval_mode"] = "impact"
        base["route_sequence"] = ["impact"]
        base["ranking_authority"] = "authoritative"
    elif mode == "universal-impact":
        base["results"] = [row(value) for value in (
            "CURRENT", "REPORT-001", "REPORT-002", "REPORT-003", "ORG-EXP017", "ORG-EXP020", "R051", "R052", "R053", "EXP020-R001",
        )]
        base["retrieval_mode"] = "impact"
        base["route_sequence"] = ["impact"]
        base["ranking_authority"] = "authoritative"
    elif mode == "random":
        seed_material = f"{query_id}|{capture_id}|p0-control-seed"
        rng = random.Random(int(hashlib.sha256(seed_material.encode()).hexdigest(), 16))
        if rng.choice((True, False)):
            base["results"] = [row(rng.choice(("R052", "PHANTOM-R999", "CURRENT")))]
        if rng.choice((True, False)):
            base["status"] = "fail_closed"
            base["error_semantic"] = rng.choice(("NOT_FOUND", "HASH_MISMATCH"))
    return base


def attempt_gold_read():
    candidate = os.environ.get("BENCH_GOLD_PROBE")
    if not candidate:
        return None
    try:
        Path(candidate).read_bytes()
        return False
    except (PermissionError, OSError):
        return True


for line in sys.stdin:
    request = json.loads(line)
    operation = request.get("operation")
    if request.get("schema_version") != VERSION or operation not in OPERATIONS:
        emit(request, status="error", error={"code": "BAD_REQUEST", "message": "invalid request"})
    elif operation == "prepare":
        workspace = request.get("workspace")
        if mode == "gold-reader":
            gold_read_blocked = attempt_gold_read()
        emit(request, details={"workspace_ready": bool(workspace)})
    elif operation == "health":
        emit(request, details={
            "adapter": f"negative-control:{mode}",
            "pid": os.getpid(),
            "capabilities": sorted(OPERATIONS),
            "control_mode": mode,
            "gold_read_blocked": gold_read_blocked,
        })
    elif operation == "invoke":
        control = request.get("test_control")
        if isinstance(control, dict):
            barrier = Path(workspace) / control["barrier_path"]
            barrier.parent.mkdir(parents=True, exist_ok=True)
            barrier.write_text(json.dumps({"stage": control["pause_at"], "pid": os.getpid()}), encoding="utf-8")
            while True:
                time.sleep(1)
        payload = prediction(request)
        emit(request, exit_code=0, stdout=json.dumps(payload), stderr="", payload=payload)
    elif operation == "reset_context":
        emit(request, details={"context_reset": True})
    elif operation == "restart":
        emit(request, details={"restarting": True})
        raise SystemExit(0)
    elif operation == "shutdown":
        emit(request, details={"shutdown": True})
        raise SystemExit(0)
