"""researchctl 查询实现（P0-B）。

命令：
  query     结构化查询（SQLite）+ lexical 关键词检索
  sources   报告/实体来源（含校验）
  trace     provenance 追踪链
  history   历史报告 / 结论演化

只读：不写入 T0–T3。输出统一 QueryResult envelope。
"""
from __future__ import annotations

import os
import re
import sqlite3
from typing import Optional

from .schema import QueryResult, result_item, empty_state, ERROR_SEMANTICS
from .resolver import verify_source_ref, _git_show


def _connect(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def get_watermark(conn: sqlite3.Connection) -> dict:
    rows = dict(conn.execute("SELECT key,value FROM index_metadata").fetchall())
    return {
        "index_built_at": rows.get("index_built_at"),
        "last_event_id": rows.get("last_event_id") or None,
        "index_complete": rows.get("index_complete") == "1",
        "drift": rows.get("drift") == "1",
        "scan_fingerprint": rows.get("scan_fingerprint"),
    }


def current_fingerprint(root: str) -> str:
    """对当前文件系统重新计算 scan fingerprint。"""
    import hashlib
    from .hashing import file_hash
    lines = []
    for dirpath, subdirs, filenames in os.walk(root):
        subdirs.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if rel.startswith(".index") or rel.startswith(".git") or rel.startswith(".researchctl"):
                continue
            h = file_hash(full)
            if h:
                lines.append(f"{rel}:{h}")
    return "sha256:" + hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _query_envelope(qt: str, conn: sqlite3.Connection, root: str, results=None,
                    warnings=None, errors=None, error_semantic=None, status="success",
                    authority="derived", index_dependent=True) -> dict:
    """构造 QueryResult envelope。

    - 依赖索引的查询（index_dependent=True）检测到 drift → fail_closed，不返回旧结果。
    - authority: canonical（直接读真源）/ derived（派生索引）/ unresolved（无法确定）。
    """
    wm = get_watermark(conn)
    drift = False
    if wm.get("scan_fingerprint"):
        drift = current_fingerprint(root) != wm["scan_fingerprint"]
    wm["drift"] = drift
    if drift and index_dependent:
        status = "fail_closed"
        authority = "unresolved"
        error_semantic = error_semantic or "INDEX_STALE"
        errors = list(errors or []) + [{"code": "INDEX_STALE", "detail": "索引 watermark 与文件系统不一致（需 reindex），不返回旧结果"}]
        results = []
    qr = QueryResult(
        query_type=qt, status=status, authority=authority, source_watermark=wm,
        results=results, warnings=warnings, errors=errors, error_semantic=error_semantic,
    )
    return qr.to_dict()


def _has_hard_error(status: str) -> bool:
    """硬错误（应 fail_closed）vs 软警告（drift）。"""
    return status in ("SOURCE_MISSING", "HASH_MISMATCH", "SOURCE_UNAVAILABLE", "PROVENANCE_BROKEN", "NOT_FOUND")


# ---------------- query ----------------

def cmd_query(args) -> dict:
    if getattr(args, "semantic", False) and getattr(args, "text", None) and not (
        getattr(args, "entity", None) or getattr(args, "doc_type", None) or getattr(args, "status", None) or getattr(args, "raw", False)
    ):
        from .semantic import query_semantic
        limit = getattr(args, "limit", 50) or 50
        return query_semantic(args.root, args.text, db_path=args.db, limit=limit)

    conn = _connect(args.db)
    try:
        # 构建 path→id 映射（用于 trace 下钻）
        path2id = {}
        for r in conn.execute("SELECT id,path FROM entities WHERE path IS NOT NULL"):
            if r[1]:
                path2id[r[1]] = r[0]

        if args.entity:
            rows = conn.execute(
                "SELECT e.id,e.entity_type,e.path,e.current_version,"
                "       d.content_hash,d.git_commit,e.status "
                "FROM entities e LEFT JOIN documents d ON e.id=d.id "
                "WHERE e.id=? OR e.path=?",
                (args.entity, args.entity),
            ).fetchall()
        elif args.doc_type:
            rows = conn.execute(
                "SELECT id,doc_type,path,version,content_hash,git_commit,status FROM documents WHERE doc_type=?",
                (args.doc_type,),
            ).fetchall()
        elif args.status:
            rows = conn.execute(
                "SELECT id,doc_type,path,version,content_hash,git_commit,status FROM documents WHERE status=?",
                (args.status,),
            ).fetchall()
        elif args.raw:
            rows = conn.execute(
                "SELECT e.id,e.entity_type,e.path,e.current_version,"
                "       d.content_hash,d.git_commit,e.status "
                "FROM entities e LEFT JOIN documents d ON e.id=d.id "
                "WHERE e.entity_type='raw'"
            ).fetchall()
        elif args.text:
            # lexical 检索：关键词匹配文件内容 / 路径 / 实体名
            text = args.text.lower()
            all_rows = conn.execute(
                "SELECT id,doc_type,path,version,content_hash,git_commit,status FROM documents"
            ).fetchall()
            rows = []
            for r in all_rows:
                doc_id, doc_type, doc_path = r[0], r[1], r[2]
                hit = text in str(doc_id).lower() or text in str(doc_path).lower()
                if not hit:
                    full = os.path.join(args.root, doc_path)
                    if os.path.isfile(full):
                        try:
                            content = open(full, encoding="utf-8", errors="ignore").read().lower()
                            if text in content:
                                hit = True
                        except OSError:
                            pass
                if hit:
                    rows.append(r)
        else:
            rows = conn.execute(
                "SELECT id,doc_type,path,version,content_hash,git_commit,status FROM documents ORDER BY doc_type,id"
            ).fetchall()

        results = []
        for row in rows:
            results.append(result_item(
                entity_id=str(row[0]),
                versioned_ref=f"{row[0]}@{row[3]}" if row[3] else None,
                path=str(row[2]),
                content_hash=str(row[4]) if len(row) > 4 and row[4] else None,
                git_commit=str(row[5]) if len(row) > 5 and row[5] else None,
                status=empty_state(),
            ))
        if args.entity and not results:
            return _query_envelope("query", conn, args.root, status="error",
                                   errors=[{"code": "NOT_FOUND", "detail": f"实体 {args.entity} 不存在"}],
                                   error_semantic="NOT_FOUND", authority="unresolved")
        # query_type 用合同枚举中的 "current"
        return _query_envelope("current", conn, args.root, results=results, authority="derived")
    finally:
        conn.close()


# ---------------- sources ----------------

def cmd_sources(args) -> dict:
    conn = _connect(args.db)
    try:
        owner = args.owner
        rows = conn.execute(
            "SELECT owner_path,ref_path,source_type,reference_scope,content_hash,git_commit,section "
            "FROM source_refs WHERE owner=?", (owner,),
        ).fetchall()
        if not rows:
            return _query_envelope("sources", conn, args.root, status="error",
                                   errors=[{"code": "NOT_FOUND", "detail": f"实体 {owner} 没有来源记录或不存在"}],
                                   error_semantic="NOT_FOUND", authority="unresolved")
        # 检测同一 source 的版本歧义：相同 ref_path 存在多个不同 (content_hash, git_commit) 锚点
        by_path = {}
        for (_owner_path, ref_path, _stype, _scope, chash, gcommit, _section) in rows:
            anchor = (chash or "", gcommit or "")
            by_path.setdefault(ref_path, set()).add(anchor)
        ambiguous_paths = [p for p, anchors in by_path.items() if len(anchors) > 1]
        if ambiguous_paths:
            return _query_envelope(
                "sources", conn, args.root,
                status="fail_closed",
                errors=[{"code": "AMBIGUOUS_VERSION",
                         "detail": f"source '{p}' 存在多个候选版本锚点，无法确定精确版本"}
                        for p in ambiguous_paths],
                error_semantic="AMBIGUOUS_VERSION",
                authority="unresolved",
                results=[])
        results = []
        warnings = []
        errors = []
        hard_fail = False
        for (owner_path, ref_path, stype, scope, chash, gcommit, section) in rows:
            ref = {"path": ref_path, "source_type": stype, "reference_scope": scope,
                   "content_hash": chash, "git_commit": gcommit, "section": section}
            v = verify_source_ref(ref, args.root, args.gitdir)
            v_status = v["status"]
            # SOURCE_CHANGED_SINCE_PIN：历史可恢复，只是 drift → 视为可用 + stale
            ok = v_status in ("ok", "SOURCE_CHANGED_SINCE_PIN")
            is_stale = v_status == "SOURCE_CHANGED_SINCE_PIN"
            if v_status == "ok":
                warnings.append({"code": "OK", "detail": v["note"]}) if False else None
            elif is_stale:
                warnings.append({"code": v_status, "detail": v["note"]})
            elif _has_hard_error(v_status):
                errors.append({"code": v_status, "detail": v["note"]})
                hard_fail = True
            data_state = "valid" if ok else ("stale" if is_stale else "corrupted")
            item = result_item(
                entity_id=owner,
                path=ref_path,
                content_hash=chash or None,
                git_commit=gcommit or None,
                section=section or None,
                relation_type="based_on",
                is_available=ok,
                is_stale=is_stale,
                status={"research": None, "data": data_state},
            )
            results.append(item)
        # 硬错误 → fail_closed（阻断），但保留已校验结果标注
        status = "fail_closed" if hard_fail else ("warning" if warnings else "success")
        if hard_fail and errors:
            error_semantic = errors[0]["code"]
        else:
            error_semantic = None
        # sources 直接读真源（.sources.yaml + git/fs 校验）→ canonical
        return _query_envelope("sources", conn, args.root, results=results,
                               warnings=warnings if status != "fail_closed" else [],
                               errors=errors, error_semantic=error_semantic, status=status,
                               authority="canonical")
    finally:
        conn.close()


def cmd_impact(args) -> dict:
    """查询逆向依赖与下游影响链（方案 §19 核心命令）。"""
    conn = _connect(args.db)
    try:
        target = args.entity
        if not target or not target.strip():
            return _query_envelope(
                "impact", conn, args.root, status="fail_closed",
                errors=[{"code": "NOT_FOUND", "detail": "entity 参数不能为空"}],
                error_semantic="NOT_FOUND", authority="unresolved"
            )
        target = target.strip()

        # P1-1: 首先严格精确解析目标，验证其存在性（严禁通配符或模糊命中未建实体）
        ent_row = conn.execute(
            "SELECT id, entity_type, path FROM entities WHERE id=? OR path=?", (target, target)
        ).fetchone()
        doc_row = conn.execute(
            "SELECT id, doc_type, path FROM documents WHERE id=? OR path=?", (target, target)
        ).fetchone() if not ent_row else None

        def_dir = os.path.join(args.root, "definitions")
        def_name = target.split("@")[0]
        has_def = os.path.isdir(os.path.join(def_dir, def_name)) if os.path.isdir(def_dir) else False

        # 如果实体不在 entities、documents、definitions 任何一处，必须立即 fail-closed 报 NOT_FOUND
        if not ent_row and not doc_row and not has_def:
            return _query_envelope(
                "impact", conn, args.root, status="fail_closed",
                errors=[{"code": "NOT_FOUND", "detail": f"目标实体或路径不存在: '{target}'"}],
                error_semantic="NOT_FOUND", authority="unresolved"
            )

        # P1-3: 如果指定了 --change-type，必须首先校验受控枚举（严格 fail-closed）
        if getattr(args, "change_type", None):
            from .tx.impact import CHANGE_TYPES
            raw_ct = args.change_type.strip()
            if raw_ct not in CHANGE_TYPES:
                return _query_envelope(
                    "impact", conn, args.root, status="fail_closed",
                    errors=[{"code": "DEF_CHANGE_TYPE_INVALID", "detail": f"change_type '{raw_ct}' 不在受控 enum 中: {CHANGE_TYPES}"}],
                    error_semantic="DEF_CHANGE_TYPE_INVALID", authority="unresolved"
                )

        def_impact = []
        # P1-3: Definition 影响分析分支
        if has_def:
            from .tx.impact import _load_entities, compute_affected
            all_defs = _load_entities(args.root)
            # 解析版本，不脑补默认 @v1；且版本必须真实存在（P1-1 反例 B）
            if "@" in target:
                def_name, ver = target.split("@", 1)
                ver_yaml = os.path.join(def_dir, def_name, f"{ver}.yaml")
                if (def_name, target) in all_defs:
                    prev_ref = target
                elif (def_name, ver) in all_defs:
                    prev_ref = ver
                elif os.path.isfile(ver_yaml):
                    prev_ref = target
                else:
                    return _query_envelope(
                        "impact", conn, args.root, status="fail_closed",
                        errors=[{"code": "NOT_FOUND", "detail": f"目标定义版本不存在: '{target}'"}],
                        error_semantic="NOT_FOUND", authority="unresolved"
                    )
            else:
                appr_file = os.path.join(def_dir, def_name, "APPROVED.yaml")
                if os.path.isfile(appr_file):
                    from .mini_yaml import load_file
                    try:
                        appr = load_file(appr_file, strict=True) or {}
                        prev_ref = appr.get("version_ref")
                    except Exception:
                        prev_ref = None
                else:
                    r = conn.execute("SELECT current_version FROM entities WHERE id=?", (def_name,)).fetchone()
                    prev_ref = f"{def_name}@{r[0]}" if r and r[0] else None

                if not prev_ref:
                    return _query_envelope(
                        "impact", conn, args.root, status="fail_closed",
                        errors=[{"code": "DEF_VERSION_MISSING", "detail": f"定义 '{def_name}' 缺少已批准版本，需显式指定带有 @version 的引用"}],
                        error_semantic="DEF_VERSION_MISSING", authority="unresolved"
                    )

            # 仅当显式指定了 --change-type 时才进行语义变更推演
            if getattr(args, "change_type", None):
                raw_ct = args.change_type.strip()
                # P1-2: compute_affected 失败原样 fail_closed，绝不裸 except pass 吞异常
                try:
                    def_impact = compute_affected(
                        args.root,
                        definition=def_name,
                        previous=prev_ref,
                        change_types=[raw_ct],
                        candidate_subject=f"{def_name}@preview"
                    )
                except Exception as e:
                    return _query_envelope(
                        "impact", conn, args.root, status="fail_closed",
                        errors=[{"code": "IMPACT_INVALID", "detail": f"impact 分析失败: {e}"}],
                        error_semantic="IMPACT_INVALID", authority="unresolved"
                    )
            else:
                # 未指定 change_type，做纯拓扑依赖分析，不自动猜测 contract_tightened
                from .tx.impact import _entity_refs_of
                try:
                    rev_graph: dict = {}
                    for k, v in all_defs.items():
                        doc = v["doc"]
                        for r, rel in _entity_refs_of(doc):
                            if "@" in r:
                                eid = r.split("@", 1)[0]
                                rev_graph.setdefault((eid, r), []).append((k, rel))

                    root_k = (def_name, prev_ref)
                    visited = set()
                    q = [root_k]
                    while q:
                        curr_k = q.pop(0)
                        if curr_k in visited:
                            continue
                        visited.add(curr_k)
                        for dep_k, rel in rev_graph.get(curr_k, []):
                            dep_info = all_defs.get(dep_k, {})
                            def_impact.append({
                                "entity_id": dep_k[0],
                                "version_ref": dep_k[1] if len(dep_k) > 1 else None,
                                "path": dep_info.get("path") or "",
                                "impact": "downstream_dependent",
                                "stale_reasons": [{"reason_code": "depends_on_definition", "via_relation": rel}],
                            })
                            if dep_k not in visited:
                                q.append(dep_k)
                except Exception as e:
                    return _query_envelope(
                        "impact", conn, args.root, status="fail_closed",
                        errors=[{"code": "IMPACT_INVALID", "detail": f"依赖拓扑分析失败: {e}"}],
                        error_semantic="IMPACT_INVALID", authority="unresolved"
                    )

        # 2. 从 source_refs 遍历下游物理引用（精确匹配，严禁 SQL LIKE 模糊匹配）
        queue = []
        if ent_row:
            queue.append(ent_row[0])
            if ent_row[2]:
                queue.append(ent_row[2])
        if doc_row:
            queue.append(doc_row[0])
            if doc_row[2]:
                queue.append(doc_row[2])
        # 检查 runs 表是否有关联 raw_ref_path
        run_row = conn.execute("SELECT run_id, raw_ref_path FROM runs WHERE run_id=?", (target,)).fetchone()
        if run_row and run_row[1]:
            queue.append(run_row[1])
        if not queue:
            queue.append(target)

        seen = set()
        downstream = []
        while queue:
            curr = queue.pop(0)
            if curr in seen:
                continue
            seen.add(curr)

            # P1-1: 精确匹配 ref_path（仅精确值或带/不带尾随斜杠），严禁 LIKE '%curr%'
            exact_paths = [curr, curr.rstrip("/"), curr.rstrip("/") + "/"]
            placeholders = ",".join("?" for _ in exact_paths)
            rows = conn.execute(
                f"SELECT owner, owner_path, ref_path, source_type FROM source_refs "
                f"WHERE ref_path IN ({placeholders})",
                exact_paths
            ).fetchall()

            for owner, owner_path, ref_path, stype in rows:
                if owner not in seen:
                    downstream.append({
                        "entity_id": owner,
                        "path": owner_path,
                        "referenced_source": ref_path,
                        "source_type": stype,
                    })
                    queue.append(owner)
                    if owner_path:
                        queue.append(owner_path)

        results = []
        for item in def_impact:
            results.append(result_item(
                entity_id=item["entity_id"],
                versioned_ref=item.get("version_ref"),
                path=item.get("path") or "",
                relation_type="impacts",
                status={"lifecycle": item.get("impact"), "stale_reasons": item.get("stale_reasons", [])},
            ))

        seen_results = set(r["entity_id"] for r in results)
        for item in downstream:
            if item["entity_id"] not in seen_results:
                seen_results.add(item["entity_id"])
                results.append(result_item(
                    entity_id=item["entity_id"],
                    path=item["path"],
                    relation_type="impacts",
                ))

        # P2-1: 正确使用 query_type="impact"
        return _query_envelope("impact", conn, args.root, results=results, authority="derived")
    finally:
        conn.close()


# ---------------- trace ----------------

def cmd_trace(args) -> dict:
    conn = _connect(args.db)
    try:
        entity = args.entity
        # 构建 path→id 映射（用于 trace 下钻）
        path2id = {}
        for r in conn.execute("SELECT id,path FROM entities WHERE path IS NOT NULL"):
            if r[1]:
                path2id[r[1]] = r[0]
        # 从 entities 找起点（支持 id 或 path）
        ent = conn.execute(
            "SELECT id,entity_type,path FROM entities WHERE id=?", (entity,)
        ).fetchone()
        if not ent:
            ent = conn.execute(
                "SELECT id,entity_type,path FROM entities WHERE path=?", (entity,)
            ).fetchone()
        if not ent:
            return _query_envelope("trace", conn, args.root, status="error",
                                   errors=[{"code": "NOT_FOUND", "detail": f"实体 {entity} 不存在"}],
                                   error_semantic="NOT_FOUND", authority="unresolved")
        results = []
        warnings = []
        errors = []
        hard_fail = False
        seen = set()
        stack = [(ent[0], ent[1], ent[2], 0)]
        while stack:
            eid, etype, epath, depth = stack.pop(0)
            if eid in seen:
                continue
            seen.add(eid)
            results.append(result_item(
                entity_id=eid, versioned_ref=f"{eid}" if not etype.startswith("raw") else None,
                path=epath or "", relation_type="start" if depth == 0 else "child",
                status=empty_state(), is_available=True,
            ))
            # 下一层：source_refs 中的来源
            nexts = conn.execute(
                "SELECT ref_path,source_type,reference_scope,content_hash,git_commit FROM source_refs WHERE owner=?",
                (eid,),
            ).fetchall()
            for (rp, stype, scope, chash, gc) in nexts:
                ref = {"path": rp, "source_type": stype, "reference_scope": scope,
                       "content_hash": chash, "git_commit": gc}
                v = verify_source_ref(ref, args.root, args.gitdir)
                v_status = v["status"]
                available = v_status in ("ok", "SOURCE_CHANGED_SINCE_PIN")
                is_stale = v_status == "SOURCE_CHANGED_SINCE_PIN"
                if is_stale:
                    # drift：历史可恢复但当前已变化 → warning
                    warnings.append({"code": v_status, "detail": f"{eid} → {rp}: {v['note']}"})
                elif _has_hard_error(v_status):
                    errors.append({"code": v_status, "detail": f"{eid} → {rp}: {v['note']}"})
                    hard_fail = True
                results.append(result_item(
                    entity_id=rp, versioned_ref=f"{rp}@{gc[:8]}" if gc else None,
                    path=rp, content_hash=chash or None, git_commit=gc or None,
                    relation_type="based_on" if etype.startswith("report") else ("organized_from" if etype == "organized" else "uses"),
                    is_available=available,
                    is_stale=is_stale,
                    status=empty_state(),
                ))
                # 推下一层：用 path 映射回 entity id 以便继续下钻
                if available:
                    child_id = path2id.get(rp, rp)
                    stack.append((child_id, "raw" if stype == "directory" else "organized", rp, depth + 1))
        status = "fail_closed" if hard_fail else ("warning" if warnings else "success")
        error_semantic = errors[0]["code"] if (hard_fail and errors) else None
        # trace 基于派生索引 + git 校验 → derived
        return _query_envelope("trace", conn, args.root, results=results,
                               warnings=warnings if status != "fail_closed" else [],
                               errors=errors, error_semantic=error_semantic, status=status,
                               authority="derived")
    finally:
        conn.close()


# ---------------- history ----------------

def cmd_history(args) -> dict:
    conn = _connect(args.db)
    try:
        # 所有报告（当前 + 历史）
        rows = conn.execute(
            "SELECT id,doc_type,path,content_hash FROM documents WHERE doc_type IN ('report_current','report_historical') ORDER BY id"
        ).fetchall()
        results = []
        cutoff = getattr(args, "as_of", None)
        for (rid, rtype, rpath, rhash) in rows:
            if cutoff and rtype == "report_current":
                continue
            if cutoff and rtype == "report_historical":
                from .mini_yaml import load_file
                sidecar = os.path.join(args.root, os.path.splitext(rpath)[0] + ".sources.yaml")
                frozen_at = None
                if os.path.isfile(sidecar):
                    try:
                        frozen_at = (load_file(sidecar, strict=True) or {}).get("frozen_at")
                    except Exception:
                        frozen_at = None
                if not frozen_at or str(frozen_at) > str(cutoff)[:10]:
                    continue
            full = os.path.join(args.root, rpath)
            summary = ""
            if os.path.exists(full):
                text = open(full).read()
                text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for i, l in enumerate(lines):
                    if l.startswith("#") or l.startswith(">"):
                        continue
                    if len(l) > 10:
                        summary = l[:80]
                        break
            refs = conn.execute(
                "SELECT ref_path,content_hash,git_commit,reference_scope FROM source_refs WHERE owner=?",
                (rid,),
            ).fetchall()
            src_list = []
            stale = False
            for (rp, chash, gc, scope) in refs:
                v = verify_source_ref({"path": rp, "source_type": "file", "reference_scope": scope,
                                       "content_hash": chash, "git_commit": gc}, args.root, args.gitdir)
                if v["status"] == "SOURCE_CHANGED_SINCE_PIN":
                    stale = True
                src_list.append({"path": rp, "content_hash": (chash or "")[:16], "git_commit": (gc or "")[:8],
                                "status": v["status"]})
            # 六轴 research 合法值: fresh | stale | needs_review；历史报告未变则 not_applicable(None)
            if rtype == "report_current":
                research_state = "fresh"
            else:
                research_state = "stale" if stale else None
            results.append(result_item(
                entity_id=rid, path=rpath, content_hash=rhash or None,
                versioned_ref=rid,
                status={"research": research_state,
                        "review": None},
                is_stale=stale,
            ))
            results[-1]["summary"] = summary
            results[-1]["sources"] = src_list
        # history 直接读报告文件 + 来源校验 → canonical
        envelope = _query_envelope("history", conn, args.root, results=results, authority="canonical")
        if cutoff:
            envelope["as_of"] = cutoff
        return envelope
    finally:
        conn.close()
