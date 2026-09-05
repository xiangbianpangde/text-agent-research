"""Closed typed benchmark operations mapped to participant CLI arguments."""
from __future__ import annotations

from typing import Any, List, Mapping


class CommandCodecError(ValueError):
    pass


def _required(params: Mapping[str, Any], key: str) -> str:
    value = params.get(key)
    if not isinstance(value, str) or not value:
        raise CommandCodecError(f"missing non-empty parameter: {key}")
    return value


def encode_operation(operation: str, params: Mapping[str, Any]) -> List[str]:
    """No arbitrary shell is accepted; operations form a closed semantic table."""
    if operation == "index":
        return ["index"]
    if operation == "query_entity":
        value = params.get("entity_id") or params.get("entity_ref") or params.get("ref")
        return ["query", "--entity", _required({"value": value}, "value")]
    if operation == "query_external_basis":
        value = params.get("entity_id") or params.get("definition_ref") or params.get("ref")
        return ["query", "--entity", _required({"value": value}, "value")]
    if operation == "trace_evidence":
        value = params.get("entity") or params.get("ref")
        return ["trace", _required({"value": value}, "value")]
    if operation in ("impact", "stale_status"):
        value = params.get("entity") or params.get("ref")
        return ["impact", _required({"value": value}, "value")]
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
