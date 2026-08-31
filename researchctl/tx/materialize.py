"""Post-commit materialize hook（P1-A-Contract §3.4）。

只有这一个 hook：SQLite events 表更新 + 派生索引 events 重建 + INDEX.md 更新。
位于 COMMITTED 之后，可重放、幂等；失败不撤销已提交内容 → state=needs_reconcile。
进度由 SQLite index_metadata.last_event_id 体现；marker 永不改写。
"""
from __future__ import annotations

import os
import re
import sqlite3


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS index_metadata (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS events (
      event_id TEXT PRIMARY KEY, event_type TEXT, occurred_at TEXT, subject TEXT
    );
    """)
    return conn


def materialize(root: str, db_path: str) -> dict:
    """重放 materialize：从 events/EV-*.yaml 重建 events 表 + 更新 last_event_id + INDEX.md。

    幂等：重复执行得到相同结果。
    返回 {"ok": bool, "last_event_id": str, "detail": str}。
    """
    edir = os.path.join(root, "events")
    events = []
    if os.path.isdir(edir):
        from ..mini_yaml import load_file
        for fn in sorted(os.listdir(edir)):
            m = re.fullmatch(r"EV-(\d{6})\.yaml", fn)
            if not m:
                continue
            try:
                ev = load_file(os.path.join(edir, fn), strict=True) or {}
            except Exception:
                continue
            events.append((ev.get("event_id"), ev.get("event_type"),
                           ev.get("occurred_at"), ev.get("subject")))

    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM events")
        for row in events:
            conn.execute("INSERT OR REPLACE INTO events(event_id,event_type,occurred_at,subject) VALUES(?,?,?,?)", row)
        last = events[-1][0] if events else ""
        conn.execute("INSERT OR REPLACE INTO index_metadata(key,value) VALUES('last_event_id',?)", (last,))
        conn.execute("INSERT OR REPLACE INTO index_metadata(key,value) VALUES('events_materialized','1')", )
        conn.commit()
    finally:
        conn.close()

    # INDEX.md 更新（派生导航，幂等重写）
    _write_index_md(root, events)

    return {"ok": True, "last_event_id": last, "detail": f"materialized {len(events)} events"}


def _write_index_md(root: str, events: list) -> None:
    """重写 index/INDEX.md（在原始导航基础上追加事件节；保持幂等）。"""
    idx_dir = os.path.join(root, "index")
    os.makedirs(idx_dir, exist_ok=True)
    idx_path = os.path.join(idx_dir, "INDEX.md")
    body = "# INDEX — 导航层（可重建，不是证据）\n\n"
    if os.path.exists(idx_path):
        # 去掉旧的 events 节，保留人维护/原始导航部分
        orig = open(idx_path, encoding="utf-8").read()
        body = re.split(r"\n## 事件时间线\n", orig)[0].rstrip() + "\n"
    if events:
        body += "\n## 事件时间线\n\n"
        for eid, etype, occ, subj in events:
            body += f"- {eid} {etype} {occ} → {subj}\n"
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(body)


def replay_materialize(root: str, db_path: str) -> dict:
    """可重放入口（崩溃恢复 / hook 失败重放）。"""
    return materialize(root, db_path)
