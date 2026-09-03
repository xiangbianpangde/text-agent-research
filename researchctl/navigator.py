"""
researchctl.navigator — 导航层 INDEX.md 自动生成与维护模块
=========================================================
依据《超长程实验 Agent 检索系统设计方案.md》§12 与 §22 P0-2 设计。
维护四种核心导航：
  1. 实验与运行索引 (Hypothesis / Experiment → Runs → Organized → Reports)
  2. 主题与整理索引 (Topic / Organized Files)
  3. 状态索引 (fresh / active / completed / stale / invalid / frozen)
  4. 事件时间线 (Events timeline)
"""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

from .queries import _connect


def _default_db(root: str) -> str:
    return os.path.join(root, ".index/research.sqlite")


def generate_index_md(root: str, db_path: Optional[str] = None, write_file: bool = True) -> str:
    """从派生 SQLite 数据库及文件系统提取全量元数据，生成规范的 index/INDEX.md 导航文件。"""
    actual_db = db_path or _default_db(root)
    if not os.path.isfile(actual_db):
        return "# INDEX — 导航层（可重建，不是证据）\n\n> 索引尚未构建，请先运行 index 命令。\n"

    conn = _connect(actual_db)
    try:
        # 1. 查询所有 runs
        run_rows = conn.execute(
            "SELECT run_id, experiment_ref, status, model, context_length, raw_ref_path, raw_ref_hash "
            "FROM runs ORDER BY run_id"
        ).fetchall()
        runs_by_exp: dict[str, list] = {}
        for r in run_rows:
            run_id, exp_ref, r_status, model, ctx_len, raw_path, raw_hash = r
            exp_id = (exp_ref.split("@")[0] if exp_ref else "UNASSIGNED")
            runs_by_exp.setdefault(exp_id, []).append({
                "run_id": run_id,
                "exp_ref": exp_ref,
                "status": r_status,
                "model": model,
                "context_length": ctx_len,
                "raw_path": raw_path,
                "raw_hash": raw_hash,
            })

        # 2. 查询所有 organized 文档
        org_rows = conn.execute(
            "SELECT id, path, version, status FROM documents WHERE doc_type='organized' ORDER BY id"
        ).fetchall()

        # 3. 查询 source_refs 建立从 organized 到 reports 的映射
        ref_rows = conn.execute(
            "SELECT owner, ref_path FROM source_refs ORDER BY owner"
        ).fetchall()
        reports_by_org: dict[str, set[str]] = {}
        for owner, ref_path in ref_rows:
            if ref_path:
                reports_by_org.setdefault(ref_path, set()).add(owner)

        # 4. 查询所有实验规格定义
        spec_rows = conn.execute(
            "SELECT id, path, status FROM entities WHERE entity_type='experiment_spec' ORDER BY id"
        ).fetchall()
        specs_by_id = {r[0]: {"path": r[1], "status": r[2]} for r in spec_rows}

        # 5. 查询所有历史与当前报告
        rep_rows = conn.execute(
            "SELECT id, doc_type, path, status FROM documents "
            "WHERE doc_type IN ('report_current', 'report_historical') ORDER BY id"
        ).fetchall()

        # 6. 查询事件时间线
        event_rows = []
        try:
            event_rows = conn.execute(
                "SELECT event_id, event_type, occurred_at, subject FROM events ORDER BY event_id"
            ).fetchall()
        except Exception:
            pass

        # ---- 开始渲染 INDEX.md 文本 ----
        lines = [
            "# INDEX — 导航层（可重建，不是证据）",
            "",
            "> 依据《超长程实验 Agent 检索系统设计方案.md》§12 自动生成。",
            "> 包含实验与运行索引、主题与整理索引、状态索引与事件时间线。",
            "",
            "## 1. 实验与运行索引 (Experiments & Runs)",
            "",
        ]

        # 收集所有已知的 Experiment ID
        all_exp_ids = sorted(set(list(specs_by_id.keys()) + list(runs_by_exp.keys())))
        if not all_exp_ids:
            lines.append("- (暂无实验记录)")
            lines.append("")
        else:
            for exp_id in all_exp_ids:
                lines.append(f"### {exp_id}")
                lines.append("")
                # 规格
                if exp_id in specs_by_id:
                    sp = specs_by_id[exp_id]
                    lines.append(f"- 规格定义: `{sp['path']}` (状态: {sp['status']})")
                # 运行
                exp_runs = runs_by_exp.get(exp_id, [])
                if exp_runs:
                    lines.append("- 运行记录 (Runs):")
                    for rn in exp_runs:
                        ctx_info = f", 模型: {rn['model']}" if rn['model'] else ""
                        lines.append(f"  - `{rn['run_id']}` ({rn['status']}{ctx_info}) → `{rn['raw_path']}`")
                # 关联整理文件
                matching_orgs = [o for o in org_rows if exp_id in o[1] or exp_id in o[0]]
                if matching_orgs:
                    lines.append("- 整理文件 (Organized):")
                    for o in matching_orgs:
                        reps = sorted(reports_by_org.get(o[1], set()))
                        rep_str = f" (关联汇报: {', '.join(reps)})" if reps else ""
                        ver_str = f"@{o[2]}" if o[2] else ""
                        lines.append(f"  - `{o[1]}` (`{o[0]}{ver_str}`){rep_str}")
                lines.append("")

        # ---- 2. 报告索引 ----
        lines.extend([
            "## 2. 报告导航 (Reports)",
            "",
        ])
        curr_reps = [r for r in rep_rows if r[1] == 'report_current']
        hist_reps = [r for r in rep_rows if r[1] == 'report_historical']
        if curr_reps:
            lines.append(f"- **当前结论 (Current)**: `{curr_reps[0][2]}` (状态: {curr_reps[0][3]})")
        if hist_reps:
            lines.append("- **历史沉淀 (Historical)**:")
            for hr in hist_reps:
                lines.append(f"  - `{hr[0]}`: `{hr[2]}` (状态: {hr[3]})")
        lines.append("")

        # ---- 3. 状态索引 ----
        lines.extend([
            "## 3. 状态索引 (Status Index)",
            "",
        ])
        # 按状态对所有实体与文档分组
        status_groups: dict[str, list[str]] = {
            "fresh / active": [],
            "completed / valid": [],
            "stale / needs_review": [],
            "invalid / corrupted": [],
            "frozen": [],
        }

        doc_all = conn.execute("SELECT id, doc_type, status FROM documents").fetchall()
        for did, dtype, st in doc_all:
            s_low = str(st).lower()
            entry = f"`{did}` ({dtype})"
            if s_low in ("fresh", "active"):
                status_groups["fresh / active"].append(entry)
            elif s_low in ("valid", "completed"):
                status_groups["completed / valid"].append(entry)
            elif s_low in ("stale", "needs_review"):
                status_groups["stale / needs_review"].append(entry)
            elif s_low in ("invalid", "corrupted", "failed"):
                status_groups["invalid / corrupted"].append(entry)
            elif s_low in ("frozen",):
                status_groups["frozen"].append(entry)

        for sname, items in status_groups.items():
            if items:
                lines.append(f"- **{sname}** ({len(items)} 项):")
                for item in sorted(items):
                    lines.append(f"  - {item}")
        lines.append("")

        # ---- 4. 事件时间线 ----
        lines.extend([
            "## 4. 事件时间线 (Events Timeline)",
            "",
        ])
        if event_rows:
            for eid, etype, occ, subj in event_rows:
                lines.append(f"- `{eid}` {etype} ({occ}) → {subj}")
        else:
            lines.append("- (暂无提交事件)")
        lines.append("")

        content = "\n".join(lines)

        if write_file:
            idx_dir = os.path.join(root, "index")
            os.makedirs(idx_dir, exist_ok=True)
            idx_path = os.path.join(idx_dir, "INDEX.md")
            with open(idx_path, "w", encoding="utf-8") as f:
                f.write(content)

        return content
    finally:
        conn.close()
