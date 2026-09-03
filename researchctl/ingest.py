"""
researchctl.ingest — Raw Ingest Hook 模块
========================================
依据《超长程实验 Agent 检索系统设计方案.md》§14 设计。
执行四个标准步骤：
  1. 分配 identity（run_id 与规范目录，严格白名单与路径 containment 校验）
  2. 导入数据并计算 directory manifest hash（staging 暂存 + 原子安装）
  3. 写入 metadata（runs/<run_id>/manifest.yaml 与可选 STATUS.yaml，严格绑定真实 spec 版本）
  4. 更新索引（SQLite 派生索引、全量语义重建 fail-closed 检查、INDEX.md 自动刷新）
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
from .tx.fs import freeze_lock


def _auto_allocate_run_id(root: str, experiment: str) -> str:
    """自动扫描 runs 目录与 raw 目录，分配下一个可用的 Rxxx ID。"""
    max_num = 0
    runs_dir = os.path.join(root, "runs")
    if os.path.isdir(runs_dir):
        for name in os.listdir(runs_dir):
            m = re.match(r"^R(\d+)$", name)
            if m:
                max_num = max(max_num, int(m.group(1)))

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
    """Raw Ingest Hook 核心流程（P1-4, P1-5, P1-6, P1-7 严格收口）。"""
    if not experiment or not experiment.strip():
        raise ValueError("experiment 参数不能为空（如 EXP-017）")
    exp_clean = experiment.strip()

    # P1-4: 严格正则白名单校验，防止路径逃逸
    if not re.fullmatch(r"^EXP-[0-9A-Za-z_.-]+$", exp_clean):
        raise ValueError(f"INVALID_EXPERIMENT_ID: experiment ID 格式非法 '{exp_clean}'（只允许 EXP-[0-9A-Za-z_.-]+）")

    if run_id and run_id.strip():
        rid_clean = run_id.strip()
        if not re.fullmatch(r"^R[0-9]{3,}$", rid_clean):
            raise ValueError(f"INVALID_RUN_ID: run_id 格式非法 '{rid_clean}'（只允许 R[0-9]{{3,}}）")
    else:
        rid_clean = None

    if not os.path.exists(source_path):
        raise FileNotFoundError(f"指定的原始数据源不存在: {source_path}")

    # P1-5: 必须继承并获取全局 mutation 锁
    with freeze_lock(root):
        real_root = os.path.realpath(root)

        # 步骤 1: 分配 identity
        assigned_run_id = rid_clean or _auto_allocate_run_id(root, exp_clean)
        raw_target_dir = os.path.join(root, "raw", exp_clean, assigned_run_id)
        runs_dir = os.path.join(root, "runs", assigned_run_id)
        manifest_path = os.path.join(runs_dir, "manifest.yaml")

        # P1-4: 严格 realpath / commonpath containment 校验
        real_raw = os.path.realpath(raw_target_dir)
        real_man = os.path.realpath(manifest_path)
        if os.path.commonpath([real_root, real_raw]) != real_root:
            raise ValueError(f"PATH_TRAVERSAL_DENIED: 目标 Raw 目录越出项目根目录: {raw_target_dir}")
        if os.path.commonpath([real_root, real_man]) != real_root:
            raise ValueError(f"PATH_TRAVERSAL_DENIED: 目标 manifest 路径越出项目根目录: {manifest_path}")

        # P1-5: 双端冲突校验（同时检查 Raw 目录与 runs/<run_id>/manifest.yaml，禁止任何覆盖）
        if os.path.exists(raw_target_dir) or os.path.exists(manifest_path):
            raise ValueError(f"TARGET_OCCUPIED: Run 目录或 manifest 已存在: {assigned_run_id}")

        # P1-6: 严格绑定真实 spec 版本，禁止盲猜 @v1
        if experiment_ref and experiment_ref.strip():
            exp_spec_ref = experiment_ref.strip()
        else:
            spec_path = os.path.join(root, "experiments", exp_clean, "spec.yaml")
            if os.path.isfile(spec_path):
                from .mini_yaml import load_file
                try:
                    spec_doc = load_file(spec_path, strict=True) or {}
                except Exception as e:
                    raise ValueError(f"SPEC_PARSE_FAILED: 实验规格解析失败: {spec_path}: {e}")
                spec_ver = spec_doc.get("version")
                if not spec_ver or not str(spec_ver).strip():
                    raise ValueError(f"SPEC_VERSION_MISSING: 实验规格缺少版本定义: {spec_path}")
                exp_spec_ref = f"{exp_clean}@v{spec_ver}"
            else:
                raise ValueError(f"SPEC_NOT_FOUND: 实验规格文件不存在: {spec_path}，必须显式传入 --experiment-ref")

        # 步骤 2: Staging 暂存导入（中途失败可靠回滚，绝不遗留半状态，P1-5 闭合）
        installed_artifacts: list[str] = []
        staging_dir = os.path.join(root, ".index", "staging", f"ingest_{assigned_run_id}_{uuid.uuid4().hex[:8]}")
        os.makedirs(staging_dir, exist_ok=True)
        try:
            if os.path.isdir(source_path):
                for item in sorted(os.listdir(source_path)):
                    s = os.path.join(source_path, item)
                    d = os.path.join(staging_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
            else:
                fname = os.path.basename(source_path)
                shutil.copy2(source_path, os.path.join(staging_dir, fname))

            # 若标记为 invalid，在 staging 目录下写 STATUS.yaml
            if status.lower() in ("invalid", "corrupted", "failed") or invalid_reason:
                status_yaml_path = os.path.join(staging_dir, "STATUS.yaml")
                today = time.strftime("%Y-%m-%d")
                reason_text = invalid_reason or "标记为 invalid 实验数据"
                with open(status_yaml_path, "w", encoding="utf-8") as f:
                    f.write(f"status: invalid\ninvalidated_at: {today}\nreason: {reason_text}\n")

            # 计算 directory manifest hash
            files_map = {}
            for dirpath, _, filenames in os.walk(staging_dir):
                for fn in filenames:
                    full = os.path.join(dirpath, fn)
                    rel = os.path.relpath(full, staging_dir)
                    with open(full, "rb") as f:
                        files_map[rel] = f.read()

            _manifest_text, dir_hash = dir_manifest_hash(files_map)

            # 原子安装到目标 raw 目录
            os.makedirs(os.path.dirname(raw_target_dir), exist_ok=True)
            shutil.move(staging_dir, raw_target_dir)
            installed_artifacts.append(raw_target_dir)

            # 步骤 3: 写 runs/<run_id>/manifest.yaml
            runs_dir_existed = os.path.isdir(runs_dir)
            os.makedirs(runs_dir, exist_ok=True)
            if not runs_dir_existed:
                installed_artifacts.append(runs_dir)
            else:
                installed_artifacts.append(manifest_path)

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

            manifest_tmp = manifest_path + f".tmp.{uuid.uuid4().hex[:8]}"
            installed_artifacts.append(manifest_tmp)
            with open(manifest_tmp, "w", encoding="utf-8") as f:
                f.write("\n".join(manifest_lines) + "\n")
            os.replace(manifest_tmp, manifest_path)
            if manifest_tmp in installed_artifacts:
                installed_artifacts.remove(manifest_tmp)

            # 步骤 4: 更新索引（原子顺序：吸纳数据 → 渲染 INDEX.md → 封装 scan_fingerprint）
            actual_db = db_path or os.path.join(root, ".index/research.sqlite")
            build_index(root, actual_db, git_commit=git_commit)

            # 刷新 INDEX.md
            nav_res = generate_index_md(root, actual_db, write_file=True)
            if isinstance(nav_res, dict) and nav_res.get("status") == "fail_closed":
                raise RuntimeError(f"INDEX_NAV_FAILED: {nav_res.get('error_semantic')}")

            p0_wm = build_index(root, actual_db, git_commit=git_commit)

            # P1-7: semantic 重建结果必须严格检查，绝不 fail-open 吞异常
            import sqlite3
            conn = sqlite3.connect(actual_db)
            try:
                tbl_rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('terms', 'ngrams', 'semantic_metadata')"
                ).fetchall()
                sem_tables = set(r[0] for r in tbl_rows)
            finally:
                conn.close()

            if len(sem_tables) in (1, 2):
                raise RuntimeError("SEMANTIC_INDEX_CORRUPT: semantic 表仅部分存在，索引损坏")
            elif len(sem_tables) == 3:
                from .semantic import build_semantic_index
                sem_res = build_semantic_index(root, actual_db)
                if isinstance(sem_res, dict) and sem_res.get("status") == "fail_closed":
                    raise RuntimeError(f"SEMANTIC_REBUILD_FAILED: {sem_res.get('error_semantic')}")
        except Exception as e:
            # P1-5 回滚保证：清理已安装的 raw、manifest 以及任何未完成的临时文件，绝不遗留半状态
            if 'manifest_tmp' in locals() and os.path.exists(manifest_tmp):
                try:
                    os.remove(manifest_tmp)
                except OSError:
                    pass
            for p in reversed(installed_artifacts):
                if os.path.isdir(p):
                    shutil.rmtree(p, ignore_errors=True)
                elif os.path.isfile(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            raise e
        finally:
            if 'manifest_tmp' in locals() and os.path.exists(manifest_tmp):
                try:
                    os.remove(manifest_tmp)
                except OSError:
                    pass
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir, ignore_errors=True)

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
