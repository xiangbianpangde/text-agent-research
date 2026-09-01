"""ID 分配（P1-A-Contract §1.3 / §4.1）。

- event_id:     events/EV-*.yaml 现有最大编号 +1（canonical authority）
- transaction_id: max(canonical events + receipts 中 transaction_id) + 1（.index 永不参与，P2-8）
- report_id:    max(reports/history/REPORT-NNN.md, committed Event.subject REPORT-NNN) + 1（Sol 定义）

编号分配在事务 prepare 阶段、global lock 内完成。
"""
from __future__ import annotations

import os
import re


def next_event_id(root: str) -> str:
    maxn = 0
    edir = os.path.join(root, "events")
    if os.path.isdir(edir):
        for fn in os.listdir(edir):
            m = re.fullmatch(r"EV-(\d{6})\.yaml", fn)
            if m:
                maxn = max(maxn, int(m.group(1)))
    return f"EV-{maxn + 1:06d}"


def _max_tx_from_canonical(root: str) -> int:
    maxn = 0
    edir = os.path.join(root, "events")
    if os.path.isdir(edir):
        for fn in os.listdir(edir):
            # receipts: EV-000001.commit
            m = re.fullmatch(r"EV-(\d{6})\.commit", fn)
            if m:
                maxn = max(maxn, int(m.group(1)))
            # events 内的 transaction_id
            m = re.fullmatch(r"EV-(\d{6})\.yaml", fn)
            if m:
                maxn = max(maxn, int(m.group(1)))
    return maxn


def next_transaction_id(root: str) -> str:
    return f"TX-{_max_tx_from_canonical(root) + 1:06d}"


def next_report_id(root: str) -> str:
    maxn = 0
    hdir = os.path.join(root, "reports", "history")
    if os.path.isdir(hdir):
        for fn in os.listdir(hdir):
            m = re.fullmatch(r"REPORT-(\d{3})\.md", fn)
            if m:
                maxn = max(maxn, int(m.group(1)))
    # committed Event.subject
    edir = os.path.join(root, "events")
    if os.path.isdir(edir):
        for fn in os.listdir(edir):
            if not fn.endswith(".yaml"):
                continue
            try:
                from ..mini_yaml import load_file
                doc = load_file(os.path.join(edir, fn), strict=True) or {}
                subj = doc.get("subject") or ""
            except Exception:
                continue
            m = re.fullmatch(r"REPORT-(\d{3})", subj)
            if m:
                maxn = max(maxn, int(m.group(1)))
    return f"REPORT-{maxn + 1:03d}"


# ---- P1-B：定义版本 ID（successor 在 definition.py 中） ----

def next_definition_version(root: str, entity: str) -> str:
    """从 canonical definitions 找当前最大版本号，返回 next_version。

    用于 bootstrap 场景（非 P1-B 职责，但辅助工具需要）。
    P1-B 事务内使用 successor(APPROVED.ref) 代替。
    """
    import re
    ddir = os.path.join(root, "definitions", entity)
    if not os.path.isdir(ddir):
        return f"{entity}@v1"
    maxn = 0
    for fn in os.listdir(ddir):
        m = re.fullmatch(rf"{re.escape(entity)}@v(\d+)\.yaml", fn)
        if m:
            maxn = max(maxn, int(m.group(1)))
    return f"{entity}@v{maxn + 1}"
