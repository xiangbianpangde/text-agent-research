"""ReportFrozen Event schema（P1-A-Contract §2）。

闭集 = { ReportFrozen }。Event 文件无 self-hash；event_hash 绑定：
in-flight=plan.event_hash，committed=receipt.event_hash，derived cache=marker.event_hash。
"""
from __future__ import annotations

import os
from typing import Optional

from .canonical import canonical_hash, canonical_json
from .ids import next_event_id


def build_event(*, root: str, event_id: str, transaction_id: str, command_version: str,
                idempotency_key: str, request_fingerprint: str, actor: str,
                authorization_ref: str, reason_refs: list, basis_git_commit: str,
                occurred_at: str, recorded_at: str, subject: str,
                input_refs: list, output_refs: list, caused_by: Optional[list] = None) -> dict:
    """构造 ReportFrozen 事件文档（canonical）。"""
    return {
        "event_id": event_id,
        "event_type": "ReportFrozen",
        "schema_version": 1,
        "command_version": command_version,
        "transaction_id": transaction_id,
        "tx_state": "committed",
        "idempotency_key": idempotency_key,
        "request_fingerprint": request_fingerprint,
        "actor": actor,
        "authorization_ref": authorization_ref,
        "reason_refs": reason_refs or [],
        "basis_git_commit": basis_git_commit,
        "occurred_at": occurred_at,
        "recorded_at": recorded_at,
        "subject": subject,
        "input_refs": input_refs,
        "output_refs": output_refs,
        "caused_by": caused_by or [],
    }


def event_path(root: str, event_id: str) -> str:
    return os.path.join(root, "events", f"{event_id}.yaml")


def serialize_event(ev: dict) -> bytes:
    from ..mini_yaml import dump
    return dump(ev).encode("utf-8")


def load_event(root: str, event_id: str) -> Optional[dict]:
    from ..mini_yaml import load_file
    p = event_path(root, event_id)
    if not os.path.exists(p):
        return None
    try:
        return load_file(p, strict=True) or {}
    except Exception:
        return None


def next_event_id_for(root: str) -> str:
    return next_event_id(root)
