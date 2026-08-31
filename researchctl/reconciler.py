"""Reconciler（P0-C）：完整性检测。

检测（只读，不写入 T0–T3）：
  1. 索引 drift：index watermark fingerprint vs 当前文件系统
  2. source_ref 断链：Report/Organized/Run 的每条 Source Reference 校验
  3. 缺失文件：documents 表登记的路径在文件系统中不存在
  4. source manifest 缺失：Report .md 存在但 .sources.yaml 缺失
  5. orphan：文件系统存在但索引未登记的文件（raw/organized 层）
  6. hash 不匹配：引用记录的 hash 与当前字节不一致

输出：
  reconcile 报告（QueryResult envelope），含 issues 列表与 fail-closed 状态。
  不修改任何 canonical 文件；唯一允许的写入是派生索引与检测报告。
"""
from __future__ import annotations

import os
import sqlite3
from typing import List

from .queries import _connect, get_watermark, current_fingerprint
from .resolver import verify_source_ref
from .schema import QueryResult, empty_state


def _check_index_drift(conn, root) -> dict:
    """检测索引 watermark 与文件系统是否漂移。"""
    wm = get_watermark(conn)
    if not wm.get("scan_fingerprint"):
        return {"ok": False, "code": "INDEX_STALE", "detail": "索引缺少 scan_fingerprint"}
    fp = current_fingerprint(root)
    if fp != wm["scan_fingerprint"]:
        return {"ok": False, "code": "DRIFT_DETECTED",
                "detail": f"索引 fingerprint 与文件系统不一致（索引落后或文件被改动）"}
    return {"ok": True}


def _check_duplicate_ids(conn) -> List[dict]:
    """检测 frontmatter entity ID 重复（DRIFT_DETECTED）。"""
    import json as _json
    rows = dict(conn.execute("SELECT key,value FROM index_metadata WHERE key='duplicates'").fetchall())
    if not rows:
        return []
    try:
        dups = _json.loads(rows["duplicates"])
    except Exception:
        return []
    issues = []
    for eid, paths in dups.items():
        issues.append({
            "issue": "DRIFT_DETECTED",
            "owner": eid,
            "ref": None,
            "scope": "identity",
            "detail": f"重复 entity ID {eid} 指向多个路径: {paths}",
        })
    return issues


def _check_source_refs(conn, root, gitdir) -> List[dict]:
    """校验所有 source_refs 记录。"""
    issues = []
    for (owner, ref_path, stype, scope, chash, gc, section) in conn.execute(
        "SELECT owner,ref_path,source_type,reference_scope,content_hash,git_commit,section FROM source_refs"
    ).fetchall():
        ref = {"path": ref_path, "source_type": stype, "reference_scope": scope,
               "content_hash": chash, "git_commit": gc, "section": section}
        v = verify_source_ref(ref, root, gitdir)
        if v["status"] != "ok":
            issues.append({
                "issue": v["status"],
                "owner": owner,
                "ref": ref_path,
                "scope": scope,
                "detail": v["note"],
            })
    return issues


def _check_documents_exist(conn, root) -> List[dict]:
    """documents 表登记的路径是否存在于文件系统。"""
    issues = []
    for (doc_id, doc_type, path) in conn.execute(
        "SELECT id,doc_type,path FROM documents"
    ).fetchall():
        if doc_type in ("report_current", "report_historical", "organized", "run_manifest", "experiment_spec"):
            full = os.path.join(root, path)
            if not os.path.exists(full):
                issues.append({
                    "issue": "SOURCE_MISSING",
                    "owner": doc_id,
                    "ref": path,
                    "scope": "index",
                    "detail": f"索引登记的 {doc_type} 文件不存在: {path}",
                })
    return issues


def _check_missing_source_manifests(conn, root) -> List[dict]:
    """Report .md 存在但 .sources.yaml 缺失。"""
    issues = []
    for (doc_id, doc_type, path) in conn.execute(
        "SELECT id,doc_type,path FROM documents WHERE doc_type IN ('report_current','report_historical')"
    ).fetchall():
        base = os.path.splitext(path)[0]
        if not os.path.exists(os.path.join(root, base + ".sources.yaml")):
            issues.append({
                "issue": "SOURCE_MISSING",
                "owner": doc_id,
                "ref": base + ".sources.yaml",
                "scope": "manifest",
                "detail": f"{doc_id} 缺少来源 manifest: {base}.sources.yaml",
            })
    return issues


def _check_orphans(conn, root) -> List[dict]:
    """文件系统存在但索引未登记的 organized/raw 文件（索引未重建）。

    raw 层只检查 run 级目录（如 raw/EXP-017/R051），不检查内部文件。
    """
    registered = set(r[0] for r in conn.execute("SELECT path FROM documents").fetchall())
    registered |= set(r[0] for r in conn.execute("SELECT path FROM entities WHERE path IS NOT NULL").fetchall())
    # 也注册 raw 目录的父路径（filesystem walk 时用于判断）
    registered_dirs = {p for p in registered if p.endswith("/") or os.path.isdir(os.path.join(root, p))}
    issues = []
    for layer in ("organized", "raw", "reports", "runs", "experiments"):
        base = os.path.join(root, layer)
        if not os.path.isdir(base):
            continue
        for dirpath, _subdirs, filenames in os.walk(base):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root)
                if rel in registered:
                    continue
                # 跳过 .sources.yaml（与 report 成对）与 README 等占位
                if fn.endswith(".sources.yaml") or fn in ("README.md",):
                    continue
                # 对 raw 层：如果文件在已注册的 raw 目录下，跳过（raw 单位是目录）
                if layer == "raw":
                    parent_dir = os.path.dirname(rel)
                    if parent_dir in registered:
                        continue
                issues.append({
                    "issue": "ORPHAN",
                    "owner": None,
                    "ref": rel,
                    "scope": layer,
                    "detail": f"文件系统存在但索引未登记: {rel}",
                })
    return issues


def run_reconcile(root: str, db_path: str, gitdir: str) -> dict:
    """执行完整性检测，返回 reconcile 报告。"""
    conn = _connect(db_path)
    try:
        issues = []
        hard_fail = False

        # 1. 索引 drift
        drift = _check_index_drift(conn, root)
        if not drift["ok"]:
            issues.append({"issue": drift["code"], "owner": None, "ref": None,
                           "scope": "index", "detail": drift["detail"]})
            hard_fail = True

        # 2. source_ref 断链 / hash 不匹配
        for iss in _check_source_refs(conn, root, gitdir):
            issues.append(iss)
            if iss["issue"] in ("SOURCE_MISSING", "HASH_MISMATCH", "SOURCE_UNAVAILABLE", "PROVENANCE_BROKEN"):
                hard_fail = True

        # 2.5 重复 entity ID
        for iss in _check_duplicate_ids(conn):
            issues.append(iss)
            hard_fail = True

        # 3. 索引登记文件缺失
        for iss in _check_documents_exist(conn, root):
            issues.append(iss)
            hard_fail = True

        # 4. source manifest 缺失
        for iss in _check_missing_source_manifests(conn, root):
            issues.append(iss)
            hard_fail = True

        # 5. orphan（软警告，提示需要 reindex）
        for iss in _check_orphans(conn, root):
            issues.append(iss)

        status = "fail_closed" if hard_fail else ("warning" if issues else "success")
        results = [{
            "issues": issues,
            "issue_count": len(issues),
            "hard_fail": hard_fail,
        }]
        qr = QueryResult(
            query_type="reconcile",
            status=status,
            authority="derived",
            source_watermark=get_watermark(conn),
            results=results,
            warnings=[] if not issues else [{"code": i["issue"], "detail": i["detail"]} for i in issues if i["issue"] != "DRIFT_DETECTED"],
            errors=[] if not hard_fail else [{"code": i["issue"], "detail": i["detail"]} for i in issues if i["issue"] in ("SOURCE_MISSING", "HASH_MISMATCH", "SOURCE_UNAVAILABLE", "PROVENANCE_BROKEN", "DRIFT_DETECTED")],
            error_semantic=None if not hard_fail else ("DRIFT_DETECTED" if issues and issues[0]["issue"] == "DRIFT_DETECTED" else next((i["issue"] for i in issues if i["issue"] in ("SOURCE_MISSING", "HASH_MISMATCH", "SOURCE_UNAVAILABLE", "PROVENANCE_BROKEN")), "DRIFT_DETECTED")),
        )
        return qr.to_dict()
    finally:
        conn.close()
