"""Runtime state（P1-A-Contract §3.8）。

可变状态，不参与任何 canonical hash；不影响 marker / receipt。
needs_reconcile 只记录于此文件。
"""
from __future__ import annotations

import os
from typing import Optional

from .canonical import canonical_json


def build_state(*, transaction_id: str, state: str, updated_at: str, notes: Optional[list] = None) -> dict:
    return {
        "transaction_id": transaction_id,
        "state": state,
        "updated_at": updated_at,
        "notes": notes or [],
    }


def state_path(root: str, tx_id: str) -> str:
    return os.path.join(root, ".index", "tx", f"{tx_id}.state.yaml")


def serialize_state(st: dict) -> bytes:
    from ..mini_yaml import dump
    return dump(st).encode("utf-8")


def load_state(root: str, tx_id: str) -> Optional[dict]:
    from ..mini_yaml import load_file
    p = state_path(root, tx_id)
    if not os.path.exists(p):
        return None
    try:
        return load_file(p, strict=True) or {}
    except Exception:
        return None


def write_state(root: str, tx_id: str, state: str, updated_at: str, notes: Optional[list] = None) -> None:
    """写 state（可变，覆盖式原子写）。"""
    from .fs import write_atomic
    st = build_state(transaction_id=tx_id, state=state, updated_at=updated_at, notes=notes)
    write_atomic(state_path(root, tx_id), serialize_state(st))
