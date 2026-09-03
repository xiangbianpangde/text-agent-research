"""
researchctl.ingest — Raw Ingest Hook 模块
========================================
依据《超长程实验 Agent 检索系统设计方案.md》§14 设计。
执行四个标准步骤：
  1. 分配 identity（run_id 与规范目录）
  2. 导入数据并计算 directory manifest hash
  3. 写入 metadata（runs/<run_id>/manifest.yaml 与可选 STATUS.yaml）
  4. 更新索引（SQLite 派生索引与 INDEX.md 自动刷新）
"""

from __future__ import annotations

import os
import re
import shutil
import time
import uuid
from typing import Any, Dict, Optional

from .hashing import dir_manifest_hash
from .indexer import build_index
from .navigator import generate_index_md


def _auto_allocate_run_id(root: str, experiment: str) -> str:
    """自动扫描 runs 目录与 raw 目录，分配下一个可用的 Rxxx ID。"""
    max_num = 0
    # 扫描 runs/
    runs_dir = os.path.join(root, "runs")
    if os.path.isdir(runs_dir):
        for name in os.listdir(runs_dir):
            m = re.match(r"^R(\d+)$", name)
            if m:
                max_num = max(max_num, int(m.group(1)))

    # 扫描 raw/<experiment>/
    raw_exp_dir = os.path.join(root, "raw", experiment)
    if os.path.isdir(raw_exp_dir):
        for name in os.listdir(raw_exp_dir):
            m = re.match(r"^R(\d+)$", name)
            if m:
                max_num = max(max_num, int(m.group(1)))

    next_num = max_num + 1 if max_num > 0 else 1
    return f"R{next_num:03d}"


def ingest_raw(
    root: str,
    *,
    experiment: str,
    source_path: str,
    run_id: Optional[str] = None,
    experiment_ref: Optional[str] = None,
    status: str = "completed",
    model: Optional[str] = None,
    context_length: Optional[str] = None,
    seed: Optional[int] = None,
    invalid_reason: Optional[str] = None,
    db_path: Optional[str] = None,
    git_commit: str = "HEAD",
) -> Dict[str, Any]:
    """Raw Ingest Hook 核心流程。"""
    if not experiment or not experiment.strip():
        raise ValueError("experiment 参数不能为空（如 EXP-017）")
    exp_clean = experiment.strip()

    if not os.path.exists(source_path):
        raise FileNotFoundError(f"指定的原始数据源不存在: {source_path}")

    # 步骤 1: 分配 identity
    assigned_run_id = run_id.strip() if run_id and run_id.strip() else _auto_allocate_run_id(root, exp_clean)
    raw_target_dir = os.path.join(root, "raw", exp_clean, assigned_run_id)
    if os.path.exists(raw_target_dir):
        raise ValueError(f"TARGET_OCCUPIED: 原始数据目录已存在: {raw_target_dir}")

    # 步骤 2: 导入数据并写入原始目录
    os.makedirs(raw_target_dir, exist_ok=True)
    if os.path.isdir(source_path):
        for item in sorted(os.listdir(source_path)):
            s = os.path.join(source_path, item)
            d = os.path.join(raw_target_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
    else:
        # 单文件拷贝
        fname = os.path.basename(source_path)
        shutil.copy2(source_path, os.path.join(raw_target_dir, fname))

    # 若标记为 invalid，在 raw 目录下写 STATUS.yaml
    if status.lower() in ("invalid", "corrupted", "failed") or invalid_reason:
        status_yaml_path = os.path.join(raw_target_dir, "STATUS.yaml")
        today = time.strftime("%Y-%m-%d")
        reason_text = invalid_reason or "标记为 invalid 实验数据"
        with open(status_yaml_path, "w", encoding="utf-8") as f:
            f.write(f"status: invalid\ninvalidated_at: {today}\nreason: {reason_text}\n")

    # 步骤 2（续）: 计算 directory manifest hash
    files_map = {}
    for dirpath, _, filenames in os.walk(raw_target_dir):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, raw_target_dir)
            with open(full, "rb") as f:
                files_map[rel] = f.read()

    _manifest_text, dir_hash = dir_manifest_hash(files_map)

    # 步骤 3: 写 runs/<run_id>/manifest.yaml
    runs_dir = os.path.join(root, "runs", assigned_run_id)
    os.makedirs(runs_dir, exist_ok=True)
    manifest_path = os.path.join(runs_dir, "manifest.yaml")

    exp_spec_ref = experiment_ref or f"{exp_clean}@v1"
    manifest_lines = [
        f"run_id: {assigned_run_id}",
        f"experiment_ref: {exp_spec_ref}",
        f"status: {status}",
    ]
    if model:
        manifest_lines.append(f"model: {model}")
    if context_length:
        manifest_lines.append(f"context_length: {context_length}")
    if seed is not None:
        manifest_lines.append(f"seed: {seed}")

    manifest_lines.extend([
        "raw_ref:",
        f"  path: raw/{exp_clean}/{assigned_run_id}/",
        "  source_type: directory",
        f"  content_hash: \"{dir_hash}\"",
        "  reference_scope: current",
    ])

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(manifest_lines) + "\n")

    # 步骤 4: 更新索引（先 build_index 吸纳新数据，再生成 INDEX.md，最后二次 build_index 保证 scan_fingerprint 包含更新后的导航文件）
    actual_db = db_path or os.path.join(root, ".index/research.sqlite")
    
    # 1. 先执行 build_index 吸纳新 raw 与 manifest 数据入库
    build_index(root, actual_db, git_commit=git_commit)

    # 2. 自动生成与刷新 INDEX.md（从库中提取最新数据渲染）
    generate_index_md(root, actual_db, write_file=True)

    # 3. 二次 build_index（计算包含新 raw、manifest 与最新 INDEX.md 在内的完整 scan_fingerprint）
    p0_wm = build_index(root, actual_db, git_commit=git_commit)

    # 4. 如果之前建过 semantic 表，刷新 semantic 索引
    try:
        from .semantic import build_semantic_index, validate_schema_only
        import sqlite3
        conn = sqlite3.connect(actual_db)
        is_semantic_present, _ = validate_schema_only(conn)
        conn.close()
        if is_semantic_present:
            build_semantic_index(root, actual_db)
    except Exception:
        pass

    return {
        "query_id": uuid.uuid4().hex[:12],
        "query_type": "status",
        "status": "success",
        "authority": "derived",
        "source_watermark": p0_wm,
        "results": [
            {
                "run_id": assigned_run_id,
                "experiment": exp_clean,
                "experiment_ref": exp_spec_ref,
                "raw_path": f"raw/{exp_clean}/{assigned_run_id}/",
                "manifest_path": f"runs/{assigned_run_id}/manifest.yaml",
                "content_hash": dir_hash,
                "status": status,
            }
        ],
        "warnings": [],
        "errors": [],
        "error_semantic": None,
    }
