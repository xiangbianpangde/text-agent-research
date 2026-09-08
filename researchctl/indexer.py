"""SQLite 派生索引构建（P0-Contract §9 最小表结构）。

从 fixture canonical 文件扫描，构建 research.sqlite。
始终是 derived index，可删除重建，不成为真源。
"""
from __future__ import annotations

import os
import re
import time
import hashlib
import sqlite3
from typing import Optional

from .hashing import dir_manifest_hash, file_hash, sha256_bytes
from .resolver import _dir_files_from_fs
from .mini_yaml import load as yaml_load, load_file as yaml_load_file


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS index_metadata (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  doc_type TEXT,
  path TEXT,
  version TEXT,
  content_hash TEXT,
  git_commit TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY,
  entity_type TEXT,
  path TEXT,
  current_version TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS versions (
  entity_id TEXT,
  version TEXT,
  path TEXT,
  content_hash TEXT,
  git_commit TEXT,
  PRIMARY KEY (entity_id, version)
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  experiment_ref TEXT,
  status TEXT,
  model TEXT,
  context_length TEXT,
  raw_ref_path TEXT,
  raw_ref_hash TEXT,
  raw_ref_commit TEXT
);

CREATE TABLE IF NOT EXISTS relations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT,
  relation TEXT,
  target TEXT,
  source_path TEXT,
  target_path TEXT,
  source_version TEXT,
  target_version TEXT
);

CREATE TABLE IF NOT EXISTS source_refs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner TEXT,
  owner_path TEXT,
  ref_path TEXT,
  source_type TEXT,
  reference_scope TEXT,
  content_hash TEXT,
  git_commit TEXT,
  section TEXT
);

CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  event_type TEXT,
  occurred_at TEXT,
  subject TEXT
);
"""

RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
RE_YAML_DICT = re.compile(r"^(\w[\w_]*):\s*(.*)$", re.MULTILINE)


def _parse_yaml_frontmatter(text: str) -> dict:
    """解析 YAML 前注（无依赖 mini_yaml，支持嵌套结构）。"""
    m = RE_FRONTMATTER.match(text)
    if not m:
        return {}
    try:
        return yaml_load(m.group(1)) or {}
    except Exception:
        return {}


def _parse_sources_yaml(path: str) -> list:
    """解析 .sources.yaml 文件，返回 source_ref 列表。"""
    data = yaml_load_file(path)
    if not data or not isinstance(data, dict):
        return []
    refs = data.get("sources", [])
    return refs if isinstance(refs, list) else []


def _parse_manifest_yaml(path: str) -> dict:
    """解析 YAML manifest 文件。"""
    return yaml_load_file(path) or {}


def build_index(root: str, db_path: str, git_commit: str = "HEAD") -> dict:
    """从 canonical 文件构建派生索引。

    root: fixture 目录路径
    db_path: 输出 .sqlite 路径
    git_commit: 解析为真实 commit hash 用于 scan_fingerprint 与 documents

    返回 watermark dict。
    """
    import subprocess
    if git_commit == "HEAD":
        try:
            git_commit = subprocess.check_output(
                ["git", "-C", root, "rev-parse", "HEAD"], text=True
            ).strip()
        except subprocess.CalledProcessError:
            git_commit = "HEAD"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)

    # 清空可重建表
    for tbl in ["documents", "entities", "versions", "runs", "relations", "source_refs", "events"]:
        conn.execute(f"DELETE FROM {tbl}")
    conn.execute("DELETE FROM index_metadata")

    _now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    wm = {
        "schema_version": "1",
        "index_built_at": _now,
        "last_event_id": "",
        "index_complete": "0",
        "drift": "0",
        "scan_fingerprint": "",
    }

    # ---- 扫描文件树 ----
    # 收集所有文件，计算 scan_fingerprint
    scan_lines = []
    for dirpath, subdirs, filenames in os.walk(root):
        subdirs.sort()
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if rel.startswith(".index") or rel.startswith(".git") or rel.startswith(".researchctl"):
                continue
            h = file_hash(full)
            if h:
                scan_lines.append(f"{rel}:{h}")
    scan_fp = "sha256:" + hashlib.sha256("\n".join(scan_lines).encode()).hexdigest()
    wm["scan_fingerprint"] = scan_fp

    # ---- Documents ----
    doc_insert = "INSERT OR REPLACE INTO documents(id,doc_type,path,version,content_hash,git_commit,status) VALUES(?,?,?,?,?,?,?)"

    # reports
    curr = os.path.join(root, "reports", "CURRENT.md")
    if os.path.exists(curr):
        h = file_hash(curr)
        conn.execute(doc_insert, ("CURRENT", "report_current", "reports/CURRENT.md", None, h, git_commit, "fresh"))

    hist_dir = os.path.join(root, "reports", "history")
    if os.path.isdir(hist_dir):
        for fn in sorted(os.listdir(hist_dir)):
            if fn.endswith(".md"):
                h = file_hash(os.path.join(hist_dir, fn))
                conn.execute(doc_insert, (fn.replace(".md", ""), "report_historical", f"reports/history/{fn}", None, h, git_commit, "frozen"))

    # organized
    org_id_paths = {}
    for dirpath, subdirs, filenames in os.walk(os.path.join(root, "organized")):
        subdirs.sort()
        for fn in sorted(filenames):
            if fn.endswith(".md"):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root)
                h = file_hash(full)
                fm = _parse_yaml_frontmatter(open(full).read())
                ver = fm.get("version", "1")
                eid = fm.get("id", fn.replace(".md", ""))
                # 检测重复 entity ID（frontmatter id 冲突）
                if eid in org_id_paths:
                    wm["duplicates"] = wm.get("duplicates", {})
                    wm["duplicates"].setdefault(eid, []).append(org_id_paths[eid])
                    wm["duplicates"][eid].append(rel)
                else:
                    org_id_paths[eid] = rel
                conn.execute(doc_insert, (eid, "organized", rel, f"v{ver}", h, git_commit, "valid"))

    # raw 目录
    raw_root = os.path.join(root, "raw")
    if os.path.isdir(raw_root):
        for exp_dir in sorted(os.listdir(raw_root)):
            exp_path = os.path.join(raw_root, exp_dir)
            if not os.path.isdir(exp_path):
                continue
            for run_dir in sorted(os.listdir(exp_path)):
                run_path = os.path.join(exp_path, run_dir)
                if not os.path.isdir(run_path):
                    continue
                rel = os.path.relpath(run_path, root)
                # 计算目录 manifest hash
                files = _dir_files_from_fs(root, rel)
                if files:
                    _m, dh = dir_manifest_hash(files)
                    # 检查是否有 STATUS 标记 invalid
                    status = "invalid" if "STATUS.yaml" in files else "valid"
                    conn.execute(doc_insert, (rel, "raw", rel, None, dh, git_commit, status))

    # ---- Source Refs ----
    sref_insert = "INSERT INTO source_refs(owner,owner_path,ref_path,source_type,reference_scope,content_hash,git_commit,section) VALUES(?,?,?,?,?,?,?,?)"

    # runs
    runs_dir = os.path.join(root, "runs")
    if os.path.isdir(runs_dir):
        for rd in sorted(os.listdir(runs_dir)):
            rp = os.path.join(runs_dir, rd, "manifest.yaml")
            if os.path.exists(rp):
                h = file_hash(rp)
                conn.execute(doc_insert, (rd, "run_manifest", f"runs/{rd}/manifest.yaml", None, h, git_commit, "completed"))
                # runs 表
                mf = _parse_manifest_yaml(rp)
                raw_ref = mf.get("raw_ref", {})
                ref_path = raw_ref.get("path") if isinstance(raw_ref, dict) else mf.get("raw_ref", "")
                ref_hash = raw_ref.get("content_hash") if isinstance(raw_ref, dict) else ""
                ref_commit = raw_ref.get("git_commit") if isinstance(raw_ref, dict) else ""
                conn.execute("INSERT OR REPLACE INTO runs(run_id,experiment_ref,status,model,context_length,raw_ref_path,raw_ref_hash,raw_ref_commit) VALUES(?,?,?,?,?,?,?,?)",
                             (rd, mf.get("experiment_ref"), mf.get("status"), mf.get("model"), mf.get("context_length"), ref_path, ref_hash, ref_commit))
                # run 的 raw_ref 也写入 source_refs（trace 统一处理）
                if isinstance(raw_ref, dict) and raw_ref.get("path"):
                    conn.execute(sref_insert, (rd, f"runs/{rd}/manifest.yaml", raw_ref.get("path"),
                                               raw_ref.get("source_type", "directory"),
                                               raw_ref.get("reference_scope", "historical"),
                                               raw_ref.get("content_hash", ""),
                                               raw_ref.get("git_commit", ""), ""))

    # experiments
    exp_dir = os.path.join(root, "experiments")
    if os.path.isdir(exp_dir):
        for exp_id in sorted(os.listdir(exp_dir)):
            sp = os.path.join(exp_dir, exp_id, "spec.yaml")
            if os.path.exists(sp):
                h = file_hash(sp)
                conn.execute(doc_insert, (exp_id, "experiment_spec", f"experiments/{exp_id}/spec.yaml", None, h, git_commit, "frozen"))

    # ---- Entities ----
    ent_insert = "INSERT OR REPLACE INTO entities(id,entity_type,path,current_version,status) VALUES(?,?,?,?,?)"
    for row in conn.execute("SELECT id,doc_type,path,version,status FROM documents WHERE doc_type NOT IN ('index','placeholder')"):
        conn.execute(ent_insert, (row[0], row[1], row[2], row[3], row[4] or "unknown"))

    # ---- Relations ----
    rel_insert = "INSERT INTO relations(source,relation,target,source_path,target_path,source_version,target_version) VALUES(?,?,?,?,?,?,?)"

    # organized → raw（from frontmatter sources）
    for row in conn.execute("SELECT id,path FROM documents WHERE doc_type='organized'"):
        full = os.path.join(root, row[1])
        if not os.path.exists(full):
            continue
        fm = _parse_yaml_frontmatter(open(full).read())
        for src in fm.get("sources", []):
            if isinstance(src, str):
                tgt = src
            elif isinstance(src, dict):
                tgt = src.get("path", "")
            else:
                continue
            conn.execute(rel_insert, (row[0], "organized_from", tgt, row[1], tgt, fm.get("version"), ""))

    # run → raw
    for row in conn.execute("SELECT run_id,raw_ref_path FROM runs WHERE raw_ref_path!=''"):
        conn.execute(rel_insert, (row[0], "uses", row[1], f"runs/{row[0]}/manifest.yaml", row[1], "", ""))

    # report → organized（from sources.yaml）
    for doc_type, prefix in [("report_current", "reports/CURRENT"), ("report_historical", "reports/history")]:
        for row in conn.execute("SELECT id,path FROM documents WHERE doc_type=?", (doc_type,)):
            base = os.path.splitext(row[1])[0]
            sy_path = os.path.join(root, base + ".sources.yaml")
            if not os.path.exists(sy_path):
                continue
            refs = _parse_sources_yaml(sy_path)
            for ref in refs:
                rp = ref.get("path", "")
                gv = ref.get("git_commit", "")[:8] if ref.get("git_commit") else ""
                conn.execute(rel_insert, (row[0], "based_on", rp, row[1], rp, "", gv))

    # report 顺序链
    reports = [r[0] for r in conn.execute("SELECT id FROM documents WHERE doc_type='report_historical' ORDER BY id").fetchall()]
    for i in range(1, len(reports)):
        conn.execute(rel_insert, (reports[i], "supersedes", reports[i-1], "", "", "", ""))

    # ---- Source Refs（report sources.yaml）----
    for doc_type, prefix in [("report_current", "reports/CURRENT"), ("report_historical", "reports/history")]:
        for row in conn.execute("SELECT id,path FROM documents WHERE doc_type=?", (doc_type,)):
            base = os.path.splitext(row[1])[0]
            sy_path = os.path.join(root, base + ".sources.yaml")
            if not os.path.exists(sy_path):
                continue
            refs = _parse_sources_yaml(sy_path)
            for ref in refs:
                conn.execute(sref_insert, (row[0], row[1], ref.get("path",""), ref.get("source_type","file"),
                                           ref.get("reference_scope","current"), ref.get("content_hash",""),
                                           ref.get("git_commit",""), ref.get("section","")))

    # organized files 的 frontmatter sources
    for row in conn.execute("SELECT id,path FROM documents WHERE doc_type='organized'"):
        full = os.path.join(root, row[1])
        if not os.path.exists(full):
            continue
        fm = _parse_yaml_frontmatter(open(full).read())
        for src in fm.get("sources", []):
            if isinstance(src, dict):
                conn.execute(sref_insert, (row[0], row[1], src.get("path",""), src.get("source_type","directory"),
                                           src.get("reference_scope","historical"), src.get("content_hash",""),
                                           src.get("git_commit",""), src.get("section","")))

    # ---- 完成 ----
    wm["index_complete"] = "1"
    import json as _json
    for k, v in wm.items():
        if isinstance(v, (dict, list)):
            v = _json.dumps(v, ensure_ascii=False)
        conn.execute("INSERT OR REPLACE INTO index_metadata(key,value) VALUES(?,?)", (k, str(v)))
    conn.commit()
    conn.close()
    return wm
