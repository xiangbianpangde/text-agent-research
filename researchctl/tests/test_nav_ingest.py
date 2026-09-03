#!/usr/bin/env python3
"""验收测试：导航层 INDEX.md 四维生成（方案 §12）与 Raw Ingest Hook（方案 §14）及严格边界复核。

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
    # [N1] generate-index 自动生成方案 §12 原文四维导航
    # -------------------------------------------------------------------------
    print("\n[N1] generate-index 自动生成方案 §12 原文四维导航")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        res = run_cmd("generate-index", root=dst)
        check("N1-1 generate-index 命令执行成功", res.get("status") == "success")
        idx_path = os.path.join(dst, "index/INDEX.md")
        check("N1-2 INDEX.md 文件存在", os.path.isfile(idx_path))

        content = open(idx_path, encoding="utf-8").read()
        check("N1-3 包含 §12 实验索引 (Hypothesis → Experiment)", "## 1. 实验索引 (Hypothesis → Experiment)" in content)
        check("N1-4 包含 §12 时间索引 (Date → Experiment / Run / Report / Event)", "## 2. 时间索引" in content)
        check("N1-5 包含 §12 主题索引 (Topic → Organized Files)", "## 3. 主题索引 (Topic → Organized Files)" in content)
        check("N1-6 包含 §12 状态索引 (Status Index)", "## 4. 状态索引" in content)
        check("N1-7 包含 Hypothesis H003 聚合", "H003" in content)
        check("N1-8 包含历史运行 R051-R053", all(r in content for r in ("R051", "R052", "R053")))
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [N1-Stale] generate-index 缺少 base-freshness 门禁测试 (P1-9)
    # -------------------------------------------------------------------------
    print("\n[N1-Stale] generate-index base freshness 门禁 (P1-9)")
    tmp, dst = make_copy()
    try:
        # 未 index 时运行 generate-index
        res = run_cmd("generate-index", root=dst)
        check("N1-Stale-1 未构建 base 时 fail_closed", res.get("status") == "fail_closed")
        check("N1-Stale-2 error_semantic=INDEX_STALE", res.get("error_semantic") == "INDEX_STALE")

        # 构建后人为引入 drift
        run_cmd("index", root=dst)
        with open(os.path.join(dst, "reports/CURRENT.md"), "a") as f:
            f.write("\ndrift line\n")
        res2 = run_cmd("generate-index", root=dst)
        check("N1-Stale-3 基础索引 stale 时 fail_closed", res2.get("status") == "fail_closed")
        check("N1-Stale-4 error_semantic=INDEX_STALE", res2.get("error_semantic") == "INDEX_STALE")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [N2] Raw Ingest Hook 正常流 (方案 §14)
    # -------------------------------------------------------------------------
    print("\n[N2] Raw Ingest Hook 正常流 (方案 §14)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)

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

        # 验证 runs/<run_id>/manifest.yaml 与真实版本绑定 (P1-6)
        manifest_path = os.path.join(dst, "runs/R054/manifest.yaml")
        check("N2-5 生成 runs/R054/manifest.yaml", os.path.isfile(manifest_path))
        m_content = open(manifest_path, encoding="utf-8").read()
        check("N2-6 manifest 包含 model 与 content_hash", "model: model-z" in m_content and "content_hash:" in m_content)
        check("N2-7 自动解析并绑定真实 spec 版本 EXP-017@v1 (P1-6)", "experiment_ref: EXP-017@v1" in m_content)

        # 验证 INDEX.md 自动刷新包含新 Run
        idx_content = open(os.path.join(dst, "index/INDEX.md"), encoding="utf-8").read()
        check("N2-8 INDEX.md 自动刷新并包含 R054", "R054" in idx_content and "model-z" in idx_content)

        # 验证检索系统即时感知该实体且无 drift
        q = run_cmd("query", "--text", "model-z", root=dst)
        check("N2-9 检索可直接命中新入库的 Run", any("R054" in r.get("entity_id", "") for r in q.get("results", [])))
        check("N2-10 查询未触发 drift 报警", q.get("status") == "success")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [N3] Raw Ingest Hook 异常标记流 (status=invalid)
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
    # [N4] Raw Ingest Hook: 目录冲突安全拒绝与 manifest 覆盖阻断 (P1-5)
    # -------------------------------------------------------------------------
    print("\n[N4] Raw Ingest Hook 冲突与防覆盖阻断 (P1-5)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)

        sample_dir = os.path.join(tmp, "sample_dup")
        os.makedirs(sample_dir)
        with open(os.path.join(sample_dir, "log.txt"), "w") as f:
            f.write("test")

        # 1. 显式指定已存在 Raw 目录的 R051
        res1 = run_cmd(
            "ingest-raw",
            "--experiment", "EXP-017",
            "--source", sample_dir,
            "--run-id", "R051",
            root=dst,
        )
        check("N4-1 重复已存在 Raw 目录被安全拒绝", res1.get("cli_returncode") != 0 or res1.get("status") == "error")

        # 2. 模拟仅存在 runs/<run_id>/manifest.yaml 但 Raw 目录不存在 (P1-5 独立复现)
        ghost_manifest_dir = os.path.join(dst, "runs/R999")
        os.makedirs(ghost_manifest_dir, exist_ok=True)
        ghost_manifest = os.path.join(ghost_manifest_dir, "manifest.yaml")
        with open(ghost_manifest, "w") as f:
            f.write("run_id: R999\nexperiment_ref: EXP-017@v1\nstatus: completed\n")

        res2 = run_cmd(
            "ingest-raw",
            "--experiment", "EXP-017",
            "--source", sample_dir,
            "--run-id", "R999",
            root=dst,
        )
        check("N4-2 仅存在 manifest.yaml 时也被安全拒绝 TARGET_OCCUPIED (P1-5)",
              res2.get("cli_returncode") != 0 or res2.get("status") == "error")
        # 确认原 ghost manifest 未被篡改覆盖
        m_check = open(ghost_manifest).read()
        check("N4-3 已有 manifest.yaml 未被覆盖", "R999" in m_check and "raw_ref" not in m_check)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [N5] Raw Ingest Hook: 路径越界阻断测试 (P1-4)
    # -------------------------------------------------------------------------
    print("\n[N5] Raw Ingest Hook 路径越界阻断测试 (P1-4)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)

        sample_dir = os.path.join(tmp, "sample_esc")
        os.makedirs(sample_dir)
        with open(os.path.join(sample_dir, "log.txt"), "w") as f:
            f.write("escape test")

        # 尝试使用 ../ 越界
        res1 = run_cmd(
            "ingest-raw",
            "--experiment", "../../escape",
            "--source", sample_dir,
            root=dst,
        )
        check("N5-1 experiment 越界被严格正则拒绝", res1.get("cli_returncode") != 0 or res1.get("status") == "error")

        res2 = run_cmd(
            "ingest-raw",
            "--experiment", "EXP-017",
            "--run-id", "R001/../../escape",
            "--source", sample_dir,
            root=dst,
        )
        check("N5-2 run_id 越界被严格正则拒绝", res2.get("cli_returncode") != 0 or res2.get("status") == "error")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [N6] impact 影响链逆向检索严格性测试 (P1-1, P1-2, P1-3, P2-1)
    # -------------------------------------------------------------------------
    print("\n[N6] impact 影响链严格性测试 (P1-1, P1-2, P1-3, P2-1)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)

        # 1. 正常已存在实体查询，验证 query_type="impact" (P2-1)
        res_real = run_cmd("impact", "R051", root=dst)
        check("N6-1 真实实体 impact 查询成功", res_real.get("status") == "success")
        check("N6-2 query_type 正确为 impact (P2-1)", res_real.get("query_type") == "impact")
        check("N6-3 返回下游影响项非空", len(res_real.get("results", [])) > 0)

        # 2. 前缀不存在目标 R05 绝不可误命中 (P1-1 复现拦截)
        res_prefix = run_cmd("impact", "R05", root=dst)
        check("N6-4 前缀目标 R05 必须 fail-closed 报 NOT_FOUND (P1-1)",
              res_prefix.get("status") == "error" and res_prefix.get("error_semantic") == "NOT_FOUND")

        # 3. 通配符 % 绝不可误命中 (P1-1 SQL 注入/通配符防御)
        res_wildcard = run_cmd("impact", "%", root=dst)
        check("N6-5 通配符 % 必须报 NOT_FOUND (P1-1)",
              res_wildcard.get("status") == "error" and res_wildcard.get("error_semantic") == "NOT_FOUND")

        # 4. 非法 change_type 拒绝 (P1-3)
        res_bad_ct = run_cmd("impact", "EXP-017", "--change-type", "totally_invalid_type", root=dst)
        check("N6-6 非法 change_type 报 DEF_CHANGE_TYPE_INVALID (P1-3)",
              res_bad_ct.get("status") == "error" and res_bad_ct.get("error_semantic") == "DEF_CHANGE_TYPE_INVALID")
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
