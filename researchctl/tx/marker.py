"""Transaction marker（P1-A-Contract §3.5）。

derived committed cache：committed 真值来自 canonical receipt。
marker 只在 canonical transaction 已 committed 后写入；创建不产生 commit truth；
损坏 marker = cache invalid → 删除/重建（非半提交）。
不绑定 plan（plan_snapshot_hash 已淘汰）。
"""
from __future__ import annotations

import os
from typing import Optional

from .canonical import canonical_json


def build_marker(*, transaction_id: str, event_id: str, event_hash: str,
                 receipt_hash: str, output_refs_manifest: list,
                 committed_at: str) -> dict:
    return {
        "transaction_id": transaction_id,
        "event_id": event_id,
        "event_hash": event_hash,
        "receipt_hash": receipt_hash,
        "commit_state": "committed",
        "output_refs_manifest": output_refs_manifest,
        "committed_at": committed_at,
    }


def marker_path(root: str, tx_id: str) -> str:
    return os.path.join(root, ".index", "tx", f"{tx_id}.marker")


def serialize_marker(mk: dict) -> bytes:
    from ..mini_yaml import dump
    return dump(mk).encode("utf-8")


def load_marker(root: str, tx_id: str) -> Optional[dict]:
    from ..mini_yaml import load_file
    p = marker_path(root, tx_id)
    if not os.path.exists(p):
        return None
    try:
        return load_file(p, strict=True) or {}
    except Exception:
        return None


def marker_valid(root: str, tx_id: str) -> bool:
    """marker 是否有效（可解析 + commit_state=committed）。"""
    mk = load_marker(root, tx_id)
    return mk is not None and mk.get("commit_state") == "committed"
