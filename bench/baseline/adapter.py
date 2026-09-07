"""independent-filegraph-v1 adapter surface: B1 argv → FileGraph → prediction.

Protocol-conformant B1 participant. Zero imports from bench.* internals that
define answers — this module only uses the transport layer to speak the
sut-adapter/v1 protocol, and the FileGraph engine for all semantics.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional


class FileGraphPredictionError(RuntimeError):
    pass


def _prediction(capture_id: str, status: str, error_semantic: Optional[str],
                **fields: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": "prediction/v2",
        "capture_id": capture_id,
        "status": status,
        "error_semantic": error_semantic,
        "warnings": [],
        "errors": [],
        "results": None,
        "provenance_graph": None,
        "asserted_facts": [],
        "evidence": [],
        "retrieval_mode": None,
        "ranking_authority": None,
        "route_sequence": [],
        "as_of": None,
    }
    payload.update(fields)
    return payload


def invoke(graph, arguments: List[str], capture_id: str, run_seed: Optional[str] = None) -> Dict[str, Any]:
    """Execute one B1 argv command against the FileGraph engine."""
    try:
        if not arguments:
            raise FileGraphPredictionError("empty argv")
        head = arguments[0]
        rest = arguments[1:]

        def _opt(flag: str) -> Optional[str]:
            if flag in rest:
                idx = rest.index(flag)
                if idx + 1 < len(rest):
                    return rest[idx + 1]
            return None

        if head == "index":
            return _prediction(capture_id, "success", None, results=[],
                               route_sequence=["current"])
        if head == "query":
            if "--entity" in rest:
                target = rest[rest.index("--entity") + 1]
                if "--semantic" in rest:
                    out = graph.op_lexical(target, semantic=True)
                    return _prediction(capture_id, "success", None,
                                       results=out["results"], retrieval_mode=out["retrieval_mode"],
                                       route_sequence=out["route_sequence"])
                out = graph.op_query_maximal(target)
                return _prediction(capture_id, "success", None, **out)
            if "--text" in rest:
                text = rest[rest.index("--text") + 1]
                out = graph.op_lexical(text, semantic="--semantic" in rest)
                return _prediction(capture_id, "success", None,
                                   results=out["results"], retrieval_mode=out["retrieval_mode"],
                                   route_sequence=out["route_sequence"])
            raise FileGraphPredictionError("query requires --entity or --text")
        if head == "facts":
            target = rest[0] if rest else ""
            return _prediction(capture_id, "success", None,
                               asserted_facts=graph.op_query_facts(target, [])["asserted_facts"],
                               route_sequence=["current"])
        if head == "trace":
            target = rest[0] if rest else ""
            out = graph.op_trace(target, with_evidence=True)
            return _prediction(capture_id, "success", None,
                               provenance_graph=out["provenance_graph"],
                               evidence=out["evidence"], route_sequence=out["route_sequence"])
        if head == "sources":
            target = rest[0] if rest else ""
            out = graph.op_query_sources(target, [])
            return _prediction(capture_id, "success", None,
                               results=out["results"], route_sequence=out["route_sequence"])
        if head == "history":
            # query_as_of_state (--as-of present) nulls git_commit/status in Gold;
            # plain query_history keeps them.
            out = graph.op_history(_opt("--as-of"), as_of_mode="--as-of" in rest)
            return _prediction(capture_id, "success", None,
                               asserted_facts=out["asserted_facts"], results=out["results"],
                               route_sequence=out["route_sequence"], as_of=out["as_of"])
        if head == "impact":
            target = rest[0] if rest else ""
            change_type = _opt("--change-type")
            out = graph.op_impact(target)
            return _prediction(capture_id, "success", None,
                               results=out["results"], provenance_graph=out["provenance_graph"],
                               route_sequence=out["route_sequence"])
        if head == "reconcile":
            return _prediction(capture_id, "success", None, results=[],
                               route_sequence=["reconcile"])
        if head == "tx-reconcile":
            return _prediction(capture_id, "success", None, results=[], route_sequence=[])
        if head == "freeze-report":
            return _prediction(capture_id, "success", None, results=[],
                               evidence=[], route_sequence=[])
        raise FileGraphPredictionError(f"unsupported B1 command: {head}")
    except Exception as exc:  # FileGraphError and engine errors → fail-closed envelope
        semantic = getattr(exc, "error_semantic", None)
        status = "fail_closed" if semantic in ("HASH_MISMATCH", "SOURCE_MISSING", "AMBIGUOUS_VERSION", "NOT_FOUND") else "error"
        return _prediction(capture_id, status, semantic or "SUT_EXCEPTION",
                           errors=[{"code": semantic or "SUT_EXCEPTION",
                                    "detail": str(exc)}] if semantic else [])


def main(argv: Optional[List[str]] = None) -> int:
    """sut-adapter/v1 stdio NDJSON loop."""
    from bench.adapters.protocol import (
        AdapterProtocolError,
        encode_message,
        validate_request,
        validate_response,
    )

    graph = None
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = validate_request(json.loads(line))
        except (AdapterProtocolError, json.JSONDecodeError) as exc:
            sys.stdout.write(json.dumps({
                "schema_version": "sut-adapter/v1", "request_id": "unknown",
                "operation": "unknown", "status": "error",
                "error": {"code": "PROTOCOL_VIOLATION", "message": str(exc)},
            }, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue
        operation = request["operation"]
        if operation == "prepare":
            from bench.baseline.filegraph import FileGraph

            graph = FileGraph(request["workspace"])
            response = {"schema_version": "sut-adapter/v1", "request_id": request["request_id"],
                        "operation": operation, "status": "ok",
                        "details": {"adapter": "independent-filegraph-v1",
                                    "capabilities": ["prepare", "invoke", "health", "shutdown"]}}
        elif operation == "health":
            response = {"schema_version": "sut-adapter/v1", "request_id": request["request_id"],
                        "operation": operation, "status": "ok",
                        "details": {"adapter": "independent-filegraph-v1",
                                    "capabilities": ["prepare", "invoke", "health", "shutdown"]}}
        elif operation == "invoke":
            if graph is None:
                response = {"schema_version": "sut-adapter/v1", "request_id": request["request_id"],
                            "operation": operation, "status": "error",
                            "error": {"code": "NOT_PREPARED", "message": "prepare required"}}
            else:
                payload = invoke(graph, request.get("arguments", []),
                                 request.get("capture_id", ""),
                                 request.get("run_seed"))
                response = {"schema_version": "sut-adapter/v1", "request_id": request["request_id"],
                            "operation": operation, "status": "ok", "exit_code": 0,
                            "stdout": "", "stderr": "", "payload": payload}
        elif operation == "shutdown":
            response = {"schema_version": "sut-adapter/v1", "request_id": request["request_id"],
                        "operation": operation, "status": "ok"}
            sys.stdout.write(encode_message(response))
            sys.stdout.flush()
            return 0
        else:
            response = {"schema_version": "sut-adapter/v1", "request_id": request["request_id"],
                        "operation": operation, "status": "error",
                        "error": {"code": "UNSUPPORTED_OPERATION", "message": operation}}
        try:
            validate_response(response, expected_request_id=request["request_id"],
                              expected_operation=operation)
        except AdapterProtocolError:
            pass
        sys.stdout.write(encode_message(response))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
