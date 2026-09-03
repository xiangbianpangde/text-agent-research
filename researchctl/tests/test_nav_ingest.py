#!/usr/bin/env python3
"""验收测试：导航层 INDEX.md 自动生成（方案 §12）与 Raw Ingest Hook（方案 §14）。

运行：
  python3 researchctl/tests/test_nav_ingest.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE = os.path.join(ROOT, "fixture")

PASS = 0
FAIL = 0
FAILURES = []


def check(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAIL += 1
        FAILURES.append(name)
        print(f"  FAIL {name}" + (f"  ({detail})" if detail else ""))


def make_copy():
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "f")
    shutil.copytree(FIXTURE, dst, symlinks=False,
                    ignore=shutil.ignore_patterns(".index", "*.sqlite", "__pycache__"))
    return tmp, dst


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)


def run_cmd(*args, root):
    cmd = [sys.executable, "-m", "researchctl", "--root", root] + list(args)
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"status": "error", "cli_returncode": p.returncode,
                "stderr": p.stderr[:500], "stdout": p.stdout[:500]}


def main():
    print("=" * 62)
    print("INDEX.md 导航生成（方案 §12）与 Raw Ingest Hook（方案 §14）验收测试")
    print("=" * 62)

    # -------------------------------------------------------------------------
    # [N1] generate-index 自动生成四维导航
    # -------------------------------------------------------------------------
    print("\n[N1] generate-index 自动生成四维导航 (方案 §12)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        res = run_cmd("generate-index", root=dst)
        check("N1-1 generate-index 命令执行成功", res.get("status") == "success")
        idx_path = os.path.join(dst, "index/INDEX.md")
        check("N1-2 INDEX.md 文件存在", os.path.isfile(idx_path))

        content = open(idx_path, encoding="utf-8").read()
        check("N1-3 包含实验与运行索引节", "## 1. 实验与运行索引" in content)
        check("N1-4 包含报告导航节", "## 2. 报告导航" in content)
        check("N1-5 包含状态索引节", "## 3. 状态索引" in content)
        check("N1-6 包含事件时间线节", "## 4. 事件时间线" in content)
        check("N1-7 包含 EXP-017", "EXP-017" in content)
        check("N1-8 包含历史运行 R051-R053", all(r in content for r in ("R051", "R052", "R053")))
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [N2] Raw Ingest Hook 正常流 (方案 §14)
    # -------------------------------------------------------------------------
    print("\n[N2] Raw Ingest Hook 正常流 (方案 §14)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)

        # 模拟生成一份真实的新 Raw 实验输出
        sample_dir = os.path.join(tmp, "sample_raw")
        os.makedirs(sample_dir)
        with open(os.path.join(sample_dir, "execution.log"), "w", encoding="utf-8") as f:
            f.write("cmd: train --model model-z\noutput: step 100 loss 0.05\n")
        with open(os.path.join(sample_dir, "metrics.csv"), "w", encoding="utf-8") as f:
            f.write("step,loss,eval_acc\n50,0.12,0.88\n100,0.05,0.96\n")

        res = run_cmd(
            "ingest-raw",
            "--experiment", "EXP-017",
            "--source", sample_dir,
            "--model", "model-z",
            "--context-length", "128K",
            "--seed", "2026",
            root=dst,
        )
        check("N2-1 ingest-raw 成功", res.get("status") == "success")
        run_item = res.get("results", [{}])[0]
        allocated_run_id = run_item.get("run_id")
        check("N2-2 自动分配递增 Run ID R054", allocated_run_id == "R054", f"id={allocated_run_id}")

        # 验证物理文件结构
        raw_exec = os.path.join(dst, "raw/EXP-017/R054/execution.log")
        raw_metrics = os.path.join(dst, "raw/EXP-017/R054/metrics.csv")
        check("N2-3 raw 目录下生成 execution.log", os.path.isfile(raw_exec))
        check("N2-4 raw 目录下生成 metrics.csv", os.path.isfile(raw_metrics))

        # 验证 runs/<run_id>/manifest.yaml
        manifest_path = os.path.join(dst, "runs/R054/manifest.yaml")
        check("N2-5 生成 runs/R054/manifest.yaml", os.path.isfile(manifest_path))
        m_content = open(manifest_path, encoding="utf-8").read()
        check("N2-6 manifest 包含 model 与 content_hash", "model: model-z" in m_content and "content_hash:" in m_content)

        # 验证 INDEX.md 自动刷新包含新 Run
        idx_content = open(os.path.join(dst, "index/INDEX.md"), encoding="utf-8").read()
        check("N2-7 INDEX.md 自动刷新并包含 R054", "R054" in idx_content and "model-z" in idx_content)

        # 验证检索系统即时感知该实体且无 drift
        q = run_cmd("query", "--text", "model-z", root=dst)
        check("N2-8 检索可直接命中新入库的 Run", any("R054" in r.get("entity_id", "") for r in q.get("results", [])))
        check("N2-9 查询未触发 drift 报警", q.get("status") == "success")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [N3] Raw Ingest Hook: invalid 状态与 STATUS.yaml 标记
    # -------------------------------------------------------------------------
    print("\n[N3] Raw Ingest Hook 异常标记流 (status=invalid)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)

        sample_dir = os.path.join(tmp, "sample_invalid")
        os.makedirs(sample_dir)
        with open(os.path.join(sample_dir, "execution.log"), "w", encoding="utf-8") as f:
            f.write("crash at step 2\n")

        res = run_cmd(
            "ingest-raw",
            "--experiment", "EXP-017",
            "--source", sample_dir,
            "--status", "invalid",
            "--reason", "显存溢出训练中断",
            root=dst,
        )
        check("N3-1 invalid ingest 成功", res.get("status") == "success")
        status_file = os.path.join(dst, "raw/EXP-017/R054/STATUS.yaml")
        check("N3-2 生成 STATUS.yaml", os.path.isfile(status_file))
        s_content = open(status_file, encoding="utf-8").read()
        check("N3-3 STATUS.yaml 记录 invalid 与原因", "status: invalid" in s_content and "显存溢出" in s_content)

        # 检查 INDEX.md 状态分类
        idx_content = open(os.path.join(dst, "index/INDEX.md"), encoding="utf-8").read()
        check("N3-4 INDEX.md 将 R054/raw 归入 invalid 分组", "raw/EXP-017/R054" in idx_content)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [N4] Raw Ingest Hook: 目录冲突安全拒绝 (TARGET_OCCUPIED)
    # -------------------------------------------------------------------------
    print("\n[N4] Raw Ingest Hook 目录冲突安全拒绝")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)

        sample_dir = os.path.join(tmp, "sample_dup")
        os.makedirs(sample_dir)
        with open(os.path.join(sample_dir, "log.txt"), "w") as f:
            f.write("test")

        # 显式指定已存在的 R051
        res = run_cmd(
            "ingest-raw",
            "--experiment", "EXP-017",
            "--source", sample_dir,
            "--run-id", "R051",
            root=dst,
        )
        check("N4-1 重复已存在目录被安全拒绝", res.get("cli_returncode") != 0 or res.get("status") == "error")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # 汇总
    # -------------------------------------------------------------------------
    print("\n" + "=" * 62)
    print(f"结果: {PASS} PASS / {FAIL} FAIL")
    if FAIL:
        print(f"失败项: {FAILURES}")
        sys.exit(1)
    else:
        print("全部测试通过！✅")
        sys.exit(0)


if __name__ == "__main__":
    main()
