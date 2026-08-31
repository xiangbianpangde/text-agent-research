"""Plan snapshot（P1-A-Contract §3.7）。

in-flight WAL / recovery journal：写后不可变；committed 后完成使命。
不参与 marker hash（marker 不绑定 plan，P2-2）。
创建必须 no-clobber（防止覆盖旧事务 WAL，Sol P1-4）。
"""
from __future__ import annotations

import os

from .canonical import canonical_json


def build_plan(*, transaction_id: str, event_id: str, command_version: str,
               idempotency_key: str, request_fingerprint: str, basis_digest: str,
               actor: str, authorization_ref: str, reason_refs: list,
               basis_git_commit: str, created_at: str,
               current_before_hash: dict, current_after_hash: dict,
               files: list) -> dict:
    return {
        "transaction_id": transaction_id,
        "event_id": event_id,
        "command_version": command_version,
        "idempotency_key": idempotency_key,
        "request_fingerprint": request_fingerprint,
        "basis_digest": basis_digest,
        "actor": actor,
        "authorization_ref": authorization_ref,
        "reason_refs": reason_refs or [],
        "basis_git_commit": basis_git_commit,
        "created_at": created_at,
        "current_before_hash": current_before_hash,
        "current_after_hash": current_after_hash,
        "files": files,
    }


def plan_path(root: str, tx_id: str) -> str:
    return os.path.join(root, ".index", "tx", f"{tx_id}.plan.yaml")


def serialize_plan(plan: dict) -> bytes:
    from ..mini_yaml import dump
    return dump(plan).encode("utf-8")


def load_plan(root: str, tx_id: str):
    from ..mini_yaml import load_file
    p = plan_path(root, tx_id)
    if not os.path.exists(p):
        return None
    try:
        return load_file(p, strict=True) or {}
    except Exception:
        return None
