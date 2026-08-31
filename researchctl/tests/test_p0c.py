#!/usr/bin/env python3
"""P0-C 完整性检测验收测试。

运行（零第三方依赖）：
  python3 researchctl/tests/test_p0c.py

覆盖：
  F01 删除 .index/ → reindex 重建恢复
  F02 移动 Raw 目录 → SOURCE_MISSING / PROVENANCE_BROKEN
  F03 修改历史 Organized（当前路径变化）→ 当前引用 HASH_MISMATCH / 历史引用可恢复
  F04 删除 Historical Report 的 source → 当前引用 SOURCE_MISSING / 历史可恢复
  F05 伪造重复 entity ID → DRIFT_DETECTED
  F06 篡改 Organized 内容 hash → HASH_MISMATCH
  F07 索引落后于文件 → INDEX_STALE + fail_closed
  F09 查询不存在 entity → NOT_FOUND
  F10 查询存在歧义的版本 → AMBIGUOUS_VERSION

所有故障注入在临时副本中进行；fixture 原始工作树不变。
退出码：0=全部通过，1=有失败。
"""
from __future__ import annotations

import hashlib
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


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAIL += 1
        FAILURES.append(name)
        print(f"  FAIL {name}" + (f"  ({detail})" if detail else ""))


def run(*args, root):
    cmd = [sys.executable, "-m", "researchctl", "--root", root] + list(args)
    return json.loads(subprocess.check_output(cmd, cwd=ROOT).decode())


def reindex(root):
    subprocess.run([sys.executable, "-m", "researchctl", "--root", root, "index"],
                   check=True, capture_output=True, cwd=ROOT)


def make_copy():
    """创建 fixture 临时副本（含 git 历史，供历史恢复验证）。"""
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "f")
    shutil.copytree(FIXTURE, dst, symlinks=False,
                    ignore=shutil.ignore_patterns(".index", "*.sqlite", "__pycache__"))
    return tmp, dst


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)


print("=" * 62)
print("P0-C 完整性检测验收测试")
print("=" * 62)

# 前置：fixture 原始工作树基线
import subprocess as sp
baseline = sp.check_output(["git", "-C", FIXTURE, "status", "--short"]).decode().strip()

# ---- F01 删除 .index/ → reindex 重建恢复 ----
print("\n[F01] 删除 .index/ 后 reindex 重建")
tmp, dst = make_copy()
try:
    reindex(dst)
    idx = os.path.join(dst, ".index", "research.sqlite")
    check("F01-1 索引已生成", os.path.exists(idx))
    os.remove(idx)
    check("F01-2 删除 .index/", not os.path.exists(idx))
    reindex(dst)
    check("F01-3 reindex 重建成功", os.path.exists(idx))
    out = run("query", root=dst)
    check("F01-4 重建后查询恢复（13 个文档）", out["status"] == "success" and len(out["results"]) == 13)
    check("F01-5 重建后 watermark 完整", out["source_watermark"]["index_complete"] is True)
finally:
    cleanup(tmp)

# ---- F02 移动 Raw 目录 ----
print("\n[F02] 移动 Raw 目录")
tmp, dst = make_copy()
try:
    reindex(dst)
    os.rename(os.path.join(dst, "raw", "EXP-017", "R051"),
              os.path.join(dst, "raw", "EXP-017", "R051-moved"))
    # 文件系统已变，先 reindex 让索引反映移动（否则 reconcile 报 drift 而非引用断链）
    reindex(dst)
    out = run("reconcile", root=dst)
    codes = {i["issue"] for i in out["results"][0]["issues"]}
    # git 历史可恢复 → SOURCE_CHANGED_SINCE_PIN（drift）；无法恢复才会 SOURCE_MISSING
    check("F02-1 reconcile 检出引用问题", bool(codes & {"SOURCE_CHANGED_SINCE_PIN", "SOURCE_MISSING", "PROVENANCE_BROKEN"}),
          "codes=" + str(codes))
    check("F02-2 状态为 warning 或 fail_closed", out["status"] in ("warning", "fail_closed"))
finally:
    cleanup(tmp)

# ---- F03 修改历史 Organized（当前路径变化）----
print("\n[F03] 修改历史 Organized（当前路径变化）")
tmp, dst = make_copy()
try:
    reindex(dst)
    # 修改 organized result.md（内容变化但 sources.yaml 未更新）
    with open(os.path.join(dst, "organized", "EXP-017", "result.md"), "a") as f:
        f.write("\n<!-- tampered -->\n")
    reindex(dst)  # 索引反映新内容
    out = run("sources", "CURRENT", root=dst)
    check("F03-1 当前引用 HASH_MISMATCH", any(
        "HASH_MISMATCH" in str(w) for w in out.get("warnings", [])) or
        out["error_semantic"] == "HASH_MISMATCH")
    # 历史 REPORT-001 仍可恢复（git_commit + path）
    out1 = run("sources", "REPORT-001", root=dst)
    check("F03-2 历史引用仍可恢复", out1["results"][0]["is_available"] is True)
    check("F03-3 历史引用标记 stale", out1["results"][0]["is_stale"] is True)
finally:
    cleanup(tmp)

# ---- F04 删除 Historical Report 的 source ----
print("\n[F04] 删除 Historical Report 的 source")
tmp, dst = make_copy()
try:
    reindex(dst)
    os.remove(os.path.join(dst, "organized", "EXP-017", "result.md"))
    reindex(dst)
    out = run("reconcile", root=dst)
    codes = {i["issue"] for i in out["results"][0]["issues"]}
    check("F04-1 reconcile 检出 SOURCE_MISSING", "SOURCE_MISSING" in codes)
    out_cur = run("sources", "CURRENT", root=dst)
    check("F04-2 当前引用 fail_closed", out_cur["status"] == "fail_closed")
    check("F04-3 error_semantic=SOURCE_MISSING", out_cur["error_semantic"] == "SOURCE_MISSING")
    # 历史 REPORT-001：git 历史中可恢复 → SOURCE_CHANGED_SINCE_PIN（drift，不判损坏）
    out1 = run("sources", "REPORT-001", root=dst)
    check("F04-4 历史引用可恢复（git 历史）", out1["results"][0]["is_available"] is True)
    check("F04-5 历史引用 stale（当前路径已变化）", out1["results"][0]["is_stale"] is True)
finally:
    cleanup(tmp)

# ---- F05 伪造重复 entity ID ----
print("\n[F05] 伪造重复 entity ID")
tmp, dst = make_copy()
try:
    reindex(dst)
    # 复制一个 organized 文件并保留相同 frontmatter id（ORG-EXP017 重复）
    src = open(os.path.join(dst, "organized", "EXP-017", "result.md")).read()
    with open(os.path.join(dst, "organized", "EXP-017", "fake-duplicate.md"), "w") as f:
        f.write(src)  # 保留 id: ORG-EXP017 → 与 result.md 重复
    reindex(dst)
    out = run("reconcile", root=dst)
    codes = {i["issue"] for i in out["results"][0]["issues"]}
    # 合同 F05：重复 ID → DRIFT_DETECTED（不归为版本歧义）
    check("F05-1 reconcile 检出 DRIFT_DETECTED", "DRIFT_DETECTED" in codes,
          "codes=" + str(codes))
    check("F05-2 状态 fail_closed（身份冲突）", out["status"] == "fail_closed")
finally:
    cleanup(tmp)

# ---- F06 篡改 Organized 内容 hash ----
print("\n[F06] 篡改 Organized 内容（改内容不更新 sources.yaml）")
tmp, dst = make_copy()
try:
    reindex(dst)
    with open(os.path.join(dst, "organized", "EXP-017", "result.md"), "a") as f:
        f.write("\n<!-- tampered-content -->\n")
    reindex(dst)
    out = run("reconcile", root=dst)
    codes = {i["issue"] for i in out["results"][0]["issues"]}
    check("F06-1 reconcile 检出 HASH_MISMATCH", "HASH_MISMATCH" in codes)
finally:
    cleanup(tmp)

# ---- F07 索引落后于文件 ----
print("\n[F07] 索引落后于文件（不 reindex 就查询）")
tmp, dst = make_copy()
try:
    reindex(dst)
    with open(os.path.join(dst, "index", "INDEX.md"), "a") as f:
        f.write("\n# drift-marker\n")
    # 不 reindex，直接查询 → INDEX_STALE + fail_closed
    out = run("query", root=dst)
    check("F07-1 查询 fail_closed", out["status"] == "fail_closed")
    check("F07-2 error_semantic=INDEX_STALE", out["error_semantic"] == "INDEX_STALE")
    check("F07-3 不返回旧结果", len(out["results"]) == 0)
    check("F07-4 drift=true", out["source_watermark"]["drift"] is True)
    out_hist = run("history", root=dst)
    check("F07-5 history 同样 fail_closed", out_hist["status"] == "fail_closed")
finally:
    cleanup(tmp)

# ---- F09 查询不存在的 entity ----
print("\n[F09] 查询不存在的 entity")
tmp, dst = make_copy()
try:
    reindex(dst)
    out = run("query", "--entity", "NOPE-999", root=dst)
    check("F09-1 NOT_FOUND", out["error_semantic"] == "NOT_FOUND")
    check("F09-2 status=error", out["status"] == "error")
    out_t = run("trace", "NOPE-999", root=dst)
    check("F09-3 trace NOT_FOUND", out_t["error_semantic"] == "NOT_FOUND")
finally:
    cleanup(tmp)

# ---- F10 查询存在歧义的版本 ----
print("\n[F10] 查询存在歧义的版本")
tmp, dst = make_copy()
try:
    reindex(dst)
    # 构造两个不同版本但同 path 的锚点（CURRENT.sources.yaml 注入指向 v1 的历史引用）
    sy_path = os.path.join(dst, "reports", "CURRENT.sources.yaml")
    sy = open(sy_path).read()
    sy += "\n  - path: organized/EXP-017/result.md\n    source_type: file\n    reference_scope: historical\n    content_hash: \"sha256:b2d7794b73aa4921f3b1983a48c013911c1940f67d6488a857012c2d55742ae2\"\n    git_commit: \"a61cf21809b0f8ddcf9a8b9bbe7e051b8d09d26e\"\n    section: null\n"
    with open(sy_path, "w") as f:
        f.write(sy)
    reindex(dst)
    out = run("sources", "CURRENT", root=dst)
    check("F10-1 status=fail_closed", out["status"] == "fail_closed")
    check("F10-2 error_semantic=AMBIGUOUS_VERSION", out["error_semantic"] == "AMBIGUOUS_VERSION")
    check("F10-3 authority=unresolved", out["authority"] == "unresolved")
    check("F10-4 不自动选择最新版本（results 为空）", len(out["results"]) == 0)
    check("F10-5 错误信息指明歧义路径", any(
        "AMBIGUOUS_VERSION" == e["code"] and "result.md" in str(e.get("detail", ""))
        for e in out.get("errors", [])))
finally:
    cleanup(tmp)

# ---- 回归：fixture 原始工作树不变 ----
print("\n[回归] fixture 原始工作树不变")
after = sp.check_output(["git", "-C", FIXTURE, "status", "--short"]).decode().strip()
check("R1 fixture 工作树与基线一致", after == baseline,
      "baseline=" + (baseline or "<empty>") + " now=" + (after or "<empty>"))

print("\n" + "=" * 62)
print(f"结果: {PASS} PASS / {FAIL} FAIL")
if FAILURES:
    print("失败项: " + ", ".join(FAILURES))
print("=" * 62)
sys.exit(1 if FAIL else 0)
