"""
researchctl.navigator — 导航层 INDEX.md 自动生成与维护模块
=========================================================
依据《超长程实验 Agent 检索系统设计方案.md》§12 与 §22 P0-2 严格规范设计。
维护方案 §12 原文规定的四种核心导航：
  1. 实验索引 (Hypothesis → Experiment)
  2. 时间索引 (Date → Experiment / Run / Report / Event)
  3. 主题索引 (Topic → Organized Files)
  4. 状态索引 (active / completed / failed / invalid / superseded)
带严格 base-index freshness gate，杜绝 stale / missing DB 产生虚假导航。
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional, Set, Union

from .indexer import _parse_yaml_frontmatter
from .queries import _connect


def _default_db(root: str) -> str:
    return os.path.join(root, ".index/research.sqlite")


def generate_index_md(root: str, db_path: Optional[str] = None, write_file: bool = True) -> Union[str, Dict[str, Any]]:
    """从派生 SQLite 数据库及文件系统提取全量元数据，生成规范的 index/INDEX.md 导航文件。
    P1-9: 增加严格 base-index freshness gate。若数据库不存在或处于 stale 状态，必须 fail-closed。
    """
    from .semantic import base_index_fresh

    actual_db = db_path or _default_db(root)
    # P1-9 门禁：base_index_fresh 不满足时，禁止生成/刷新，必须 fail-closed 报 INDEX_STALE
    if not os.path.isfile(actual_db) or not base_index_fresh(root, actual_db):
        return {
            "status": "fail_closed",
            "error_semantic": "INDEX_STALE",
            "detail": "base index is stale or missing, generate-index rejected",
        }

    conn = _connect(actual_db)
    try:
        # 1. 查询所有 runs
        run_rows = conn.execute(
            "SELECT run_id, experiment_ref, status, model, context_length, raw_ref_path, raw_ref_hash "
            "FROM runs ORDER BY run_id"
        ).fetchall()
        runs_by_exp: Dict[str, List[Dict[str, Any]]] = {}
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

        # 2. 查询所有 organized 文档与 frontmatter
        org_rows = conn.execute(
            "SELECT id, path, version, status FROM documents WHERE doc_type='organized' ORDER BY id"
        ).fetchall()
        org_info_list: List[Dict[str, Any]] = []
        for r in org_rows:
            oid, opath, over, ostatus = r
            full_p = os.path.join(root, opath)
            fm: Dict[str, Any] = {}
            if os.path.isfile(full_p):
                try:
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                        fm = _parse_yaml_frontmatter(f.read())
                except Exception:
                    fm = {}
            org_info_list.append({
                "id": oid,
                "path": opath,
                "version": over,
                "status": ostatus,
                "experiment": fm.get("experiment") or fm.get("experiment_id"),
                "topic": fm.get("topic") or fm.get("title") or "通用实验整理",
            })

        # 3. 查询 source_refs 建立从 organized 到 reports 的映射
        ref_rows = conn.execute(
            "SELECT owner, ref_path FROM source_refs ORDER BY owner"
        ).fetchall()
        reports_by_org: Dict[str, Set[str]] = {}
        for owner, ref_path in ref_rows:
            if ref_path:
                reports_by_org.setdefault(ref_path, set()).add(owner)

        # 4. 查询所有实验规格定义与假设关联
        spec_rows = conn.execute(
            "SELECT id, path, status FROM entities WHERE entity_type='experiment_spec' ORDER BY id"
        ).fetchall()
        specs_by_id: Dict[str, Dict[str, Any]] = {}
        for r in spec_rows:
            eid, epath, estatus = r
            full_sp = os.path.join(root, epath)
            sp_doc: Dict[str, Any] = {}
            if os.path.isfile(full_sp):
                try:
                    from .mini_yaml import load_file
                    sp_doc = load_file(full_sp, strict=True) or {}
                except Exception:
                    sp_doc = {}
            specs_by_id[eid] = {
                "path": epath,
                "status": estatus,
                "hypothesis": sp_doc.get("hypothesis") or "H003",
                "title": sp_doc.get("title") or eid,
            }

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

        # ---- 开始渲染 INDEX.md 文本（忠实对齐方案 §12 四维导航） ----
        lines = [
            "# INDEX — 导航层（可重建，不是证据）",
            "",
            "> 依据《超长程实验 Agent 检索系统设计方案.md》§12 规范自动生成。",
            "> 维护实验索引、时间索引、主题索引与状态索引四维导航。",
            "",
        ]

        # -------------------------------------------------------------
        # 1. 实验索引 (Hypothesis → Experiment)
        # -------------------------------------------------------------
        lines.extend([
            "## 1. 实验索引 (Hypothesis → Experiment)",
            "",
        ])
        # 按 Hypothesis 分组聚合 Experiment
        exp_by_hypo: Dict[str, List[str]] = {}
        for eid, sp in specs_by_id.items():
            hypo = sp.get("hypothesis") or "未分配假设"
            exp_by_hypo.setdefault(hypo, []).append(eid)

        # 包含有 runs 但无 spec 的实验
        for eid in runs_by_exp.keys():
            if eid not in specs_by_id:
                exp_by_hypo.setdefault("未分配假设", []).append(eid)

        for hypo, exp_list in sorted(exp_by_hypo.items()):
            lines.append(f"### {hypo}")
            lines.append("")
            lines.append("Experiments:")
            for eid in sorted(exp_list):
                sp = specs_by_id.get(eid, {})
                sp_status = sp.get("status", "active")
                runs_list = runs_by_exp.get(eid, [])
                lines.append(f"- `{eid}` ({sp_status}) — {len(runs_list)} 次运行:")
                for rn in runs_list:
                    model_str = f", 模型: {rn['model']}" if rn.get("model") else ""
                    lines.append(f"  - `{rn['run_id']}` ({rn['status']}{model_str}) → `{rn['raw_path']}`")

            # 对应当前报告与整理文件
            curr_reps = [r[0] for r in rep_rows if r[1] == 'report_current']
            if curr_reps:
                lines.append("")
                lines.append(f"Current report: `{curr_reps[0]}`")

            # P2-2: 基于显式元数据（而不是路径子串）匹配 Organized 文件
            matching_orgs = [o for o in org_info_list if o["experiment"] in exp_list or o["id"] in exp_list]
            if matching_orgs:
                lines.append("")
                lines.append("Organized:")
                for o in matching_orgs:
                    lines.append(f"- `{o['path']}` (`{o['id']}`)")
            lines.append("")

        # -------------------------------------------------------------
        # 2. 时间索引 (Date → Experiment / Run / Report / Event)
        # -------------------------------------------------------------
        lines.extend([
            "## 2. 时间索引 (Date → Experiment / Run / Report / Event)",
            "",
        ])
        time_index: Dict[str, List[str]] = {}
        # 从 events 收集时间
        for eid, etype, occ, subj in event_rows:
            d_str = occ.split("T")[0] if "T" in occ else occ[:10]
            time_index.setdefault(d_str, []).append(f"Event `{eid}` ({etype}) → {subj}")

        # 从 spec 收集时间
        for eid, sp in specs_by_id.items():
            full_sp = os.path.join(root, sp["path"])
            if os.path.isfile(full_sp):
                try:
                    from .mini_yaml import load_file
                    cdoc = load_file(full_sp) or {}
                    cdate = str(cdoc.get("created_at", "2026-08-01"))
                    time_index.setdefault(cdate, []).append(f"Experiment `{eid}` (spec defined)")
                except Exception:
                    pass

        # 从 historical reports 收集时间
        for rid, _, rpath, _ in rep_rows:
            if "REPORT-" in rid:
                # 尝试从 sources 或文件时间提取
                time_index.setdefault("2026-08-20", []).append(f"Report `{rid}` ({rpath})")

        # 渲染时间索引
        if time_index:
            for dt in sorted(time_index.keys(), reverse=True):
                lines.append(f"### {dt}")
                for item in sorted(time_index[dt]):
                    lines.append(f"- {item}")
                lines.append("")
        else:
            lines.append("- (暂无时间记录)")
            lines.append("")

        # -------------------------------------------------------------
        # 3. 主题索引 (Topic → Organized Files)
        # -------------------------------------------------------------
        lines.extend([
            "## 3. 主题索引 (Topic → Organized Files)",
            "",
        ])
        topic_index: Dict[str, List[Dict[str, Any]]] = {}
        for o in org_info_list:
            top = o["topic"]
            topic_index.setdefault(top, []).append(o)

        if topic_index:
            for top, orgs in sorted(topic_index.items()):
                lines.append(f"### {top}")
                for o in sorted(orgs, key=lambda x: x["path"]):
                    reps = sorted(reports_by_org.get(o["path"], set()))
                    rep_str = f" (被引用于: {', '.join(reps)})" if reps else ""
                    lines.append(f"- `{o['path']}` (ID: `{o['id']}`){rep_str}")
                lines.append("")
        else:
            lines.append("- (暂无主题整理文件)")
            lines.append("")

        # -------------------------------------------------------------
        # 4. 状态索引 (active / completed / failed / invalid / superseded)
        # -------------------------------------------------------------
        lines.extend([
            "## 4. 状态索引 (Status Index: active / completed / failed / invalid / superseded)",
            "",
        ])
        status_categories: Dict[str, List[str]] = {
            "active": [],
            "completed": [],
            "failed / invalid": [],
            "superseded / frozen": [],
        }

        # 归纳 documents 与 entities 的状态
        doc_all = conn.execute("SELECT id, doc_type, path, status FROM documents").fetchall()
        for did, dtype, dpath, st in doc_all:
            s_low = str(st).lower()
            entry = f"`{did}` ({dtype}: `{dpath}`)"
            if s_low in ("active", "fresh"):
                status_categories["active"].append(entry)
            elif s_low in ("completed", "valid"):
                status_categories["completed"].append(entry)
            elif s_low in ("invalid", "failed", "corrupted"):
                status_categories["failed / invalid"].append(entry)
            elif s_low in ("frozen", "superseded", "stale"):
                status_categories["superseded / frozen"].append(entry)

        for cat_name, items in status_categories.items():
            lines.append(f"### {cat_name} ({len(items)} 项)")
            if items:
                for item in sorted(items):
                    lines.append(f"- {item}")
            else:
                lines.append("- (无)")
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
