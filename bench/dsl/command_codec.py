"""Closed Oracle query registry mapped to participant CLI arguments."""
from __future__ import annotations

from typing import Any, List, Mapping

from bench.oracle.manifest import OracleManifest


class CommandCodecError(ValueError):
    pass


def _required(params: Mapping[str, Any], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise CommandCodecError(f"missing non-empty parameter: {key}")
    return value


def resolve_query(
    manifest: OracleManifest,
    operation: str,
    params: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    query_id = params.get("query_id")
    if query_id is None:
        return None
    if not isinstance(query_id, str) or not query_id:
        raise CommandCodecError("query_id must be a non-empty string")
    query = manifest.query(query_id)
    if query["operation"] != operation:
        raise CommandCodecError(
            f"query operation mismatch: {query_id} declares {query['operation']}, action requested {operation}"
        )
    return query


def encode_operation(
    operation: str,
    params: Mapping[str, Any],
    manifest: OracleManifest,
) -> List[str]:
    """Encode only participant-visible fields from the same manifest query used by Gold."""
    query = resolve_query(manifest, operation, params)
    source = query if query is not None else params
    if operation == "index":
        if params:
            raise CommandCodecError("index params must be empty")
        return ["index"]
    if operation in ("query_entity", "query_facts", "query_lineage", "query_state", "query_exact_routing"):
        return ["query", "--entity", _required(source, "participant_locator")]
    if operation == "query_external_basis":
        return ["query", "--entity", _required(source, "participant_locator")]
    if operation in ("trace_evidence", "trace_graph"):
        return ["trace", _required(source, "participant_locator")]
    if operation == "query_sources":
        return ["sources", _required(source, "participant_locator")]
    if operation in ("query_history", "query_as_of_state"):
        arguments = ["history"]
        if source.get("as_of"):
            arguments.extend(["--as-of", str(source["as_of"])])
        return arguments
    if operation == "reconcile_integrity":
        return ["reconcile"]
    if operation == "query_text_semantic":
        return ["query", "--text", _required(source, "text"), "--semantic"]
    if operation == "query_text_lexical":
        return ["query", "--text", _required(source, "text")]
    if operation == "query_project_current":
        return ["query", "--entity", _required(source, "participant_locator")]
    if operation == "query_project_index":
        # Gold semantics project the target entity row (like project_current);
        # the index route is declared via route_sequence, not via --text.
        return ["query", "--entity", _required(source, "participant_locator")]
    if operation in ("impact", "stale_status"):
        arguments = ["impact", _required(source, "participant_locator")]
        if source.get("change_type"):
            arguments.extend(["--change-type", str(source["change_type"])])
        return arguments
    if operation == "tx_reconcile":
        return ["tx-reconcile"]
    if operation == "freeze_report":
        return [
            "freeze-report",
            "--idempotency-key", _required(params, "idempotency_key"),
            "--actor", _required(params, "actor"),
            "--authorization-ref", _required(params, "authorization_ref"),
        ]
    raise CommandCodecError(f"unsupported benchmark operation: {operation}")
