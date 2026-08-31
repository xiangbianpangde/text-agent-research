"""Commit receipt（P1-A-Contract §2.3 / §5.5）。

receipt = canonical commit truth（含 Event/report/manifest/CURRENT 全部提交证据）。
四件套验证：Event + report + manifest + receipt 完整且内部绑定一致。
"""
from __future__ import annotations

import os

from .canonical import canonical_hash, canonical_json, raw_bytes_hash


def build_receipt(root: str, event_id: str, tx_id: str, event_path: str,
                  report_path: str, manifest_path: str, current_after_path: str,
                  committed_at: str) -> dict:
    """构造 receipt 文档（committed 后生成，含真实 committed_at）。"""
    from .canonical import file_canonical_hash
    event_hash = file_canonical_hash(os.path.join(root, event_path))
    report_hash = raw_bytes_hash(os.path.join(root, report_path))
    manifest_hash = file_canonical_hash(os.path.join(root, manifest_path))
    current_after_hash = raw_bytes_hash(os.path.join(root, current_after_path))
    output_digest = canonical_hash({
        "report_hash": report_hash,
        "manifest_hash": manifest_hash,
        "current_after_hash": current_after_hash,
    })
    return {
        "event_id": event_id,
        "transaction_id": tx_id,
        "event_hash": event_hash,
        "report_hash": report_hash,
        "manifest_hash": manifest_hash,
        "current_after_hash": current_after_hash,
        "output_digest": output_digest,
        "committed_at": committed_at,
    }


def receipt_path(root: str, event_id: str) -> str:
    return os.path.join(root, "events", f"{event_id}.commit")


def receipt_valid_fourpiece(root: str, tx_id: str) -> bool:
    """该事务是否存在 valid receipt + 四件套验证通过（§5.5 a–h）。"""
    try:
        res = verify_receipt_by_tx(root, tx_id)
        return res.get("valid") is True
    except Exception:
        return False


def verify_receipt_by_tx(root: str, tx_id: str) -> dict:
    """按 transaction_id 验证四件套。返回 {valid, reason, detail}。"""
    edir = os.path.join(root, "events")
    if not os.path.isdir(edir):
        return {"valid": False, "reason": "no-events-dir"}
    # 找到该 tx 的 Event 文件
    from ..mini_yaml import load_file
    for fn in sorted(os.listdir(edir)):
        if not fn.endswith(".yaml"):
            continue
        try:
            ev = load_file(os.path.join(edir, fn), strict=True) or {}
        except Exception:
            continue
        if ev.get("transaction_id") != tx_id:
            continue
        return verify_receipt(root, fn.replace(".yaml", ""))
    return {"valid": False, "reason": "tx-not-found"}


def verify_receipt(root: str, event_id: str) -> dict:
    """验证 receipts/Event/report/manifest 四件套绑定（§5.5 a–h）。

    返回 {valid: bool, event_id, report_hash, manifest_hash, event_hash, reason}
    """
    edir = os.path.join(root, "events")
    ev_path = os.path.join(edir, f"{event_id}.yaml")
    rc_path = os.path.join(edir, f"{event_id}.commit")
    from ..mini_yaml import load_file
    if not os.path.exists(ev_path):
        return {"valid": False, "reason": "event-missing"}
    if not os.path.exists(rc_path):
        return {"valid": False, "reason": "receipt-missing"}
    try:
        ev = load_file(ev_path, strict=True) or {}
        rc = load_file(rc_path, strict=True) or {}
    except Exception as e:
        return {"valid": False, "reason": f"parse-error:{e}"}

    # a. 可解析（上面已保证）
    # b. receipt.event_id == event_id == 文件名
    if rc.get("event_id") != event_id:
        return {"valid": False, "reason": "event-id-mismatch"}
    # c. transaction 一致
    if rc.get("transaction_id") != ev.get("transaction_id"):
        return {"valid": False, "reason": "tx-id-mismatch"}
    # d. event_hash
    from .canonical import file_canonical_hash
    actual_event_hash = file_canonical_hash(ev_path)
    if rc.get("event_hash") != actual_event_hash:
        return {"valid": False, "reason": "event-hash-mismatch"}
    # e/f. report/manifest hash + output_refs
    output_refs = {r.get("role"): r for r in (ev.get("output_refs") or [])}
    if rc.get("report_hash") != output_refs.get("report", {}).get("content_hash"):
        return {"valid": False, "reason": "report-hash-mismatch"}
    if rc.get("manifest_hash") != output_refs.get("sources_manifest", {}).get("content_hash"):
        return {"valid": False, "reason": "manifest-hash-mismatch"}
    report_hash = raw_bytes_hash(os.path.join(root, output_refs.get("report", {}).get("path", "")))
    manifest_hash = file_canonical_hash(os.path.join(root, output_refs.get("sources_manifest", {}).get("path", "")))
    if rc.get("report_hash") != report_hash:
        return {"valid": False, "reason": "report-file-mismatch"}
    if rc.get("manifest_hash") != manifest_hash:
        return {"valid": False, "reason": "manifest-file-mismatch"}
    # g. output_digest
    exp_digest = canonical_hash({
        "report_hash": rc.get("report_hash"),
        "manifest_hash": rc.get("manifest_hash"),
        "current_after_hash": rc.get("current_after_hash"),
    })
    if rc.get("output_digest") != exp_digest:
        return {"valid": False, "reason": "output-digest-mismatch"}
    # h. current_after_hash 绑定（内部历史绑定，不比较 live CURRENT）
    cur_ref = output_refs.get("current.md", {})
    if rc.get("current_after_hash") != cur_ref.get("content_hash"):
        return {"valid": False, "reason": "current-after-mismatch"}

    return {"valid": True, "event_id": event_id,
            "report_hash": rc.get("report_hash"),
            "manifest_hash": rc.get("manifest_hash"),
            "event_hash": rc.get("event_hash")}
