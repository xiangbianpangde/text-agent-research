#!/usr/bin/env python3
"""P0-B 只读检索内核验收测试。

运行（零第三方依赖，可用系统 python3）：
  python3 researchctl/tests/test_p0b.py

覆盖：验收 A–H + 阻断项回归（依赖/字段错位/INDEX_STALE fail_closed/
availability/drift warning/history 状态/lexical/authority/硬错误 fail_closed）。
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


def run(*args, root=FIXTURE):
    cmd = [sys.executable, "-m", "researchctl", "--root", root] + list(args)
    return json.loads(subprocess.check_output(cmd, cwd=ROOT).decode())


def run_raw(*args, root=FIXTURE):
    cmd = [sys.executable, "-m", "researchctl", "--root", root] + list(args)
    return subprocess.check_output(cmd, cwd=ROOT).decode()


def shasum(path):
    with open(path, "rb") as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()


def reindex(root=FIXTURE):
    subprocess.run([sys.executable, "-m", "researchctl", "--root", root, "index"],
                   check=True, capture_output=True, cwd=ROOT)


# ---------------------------------------------------------------------------
print("=" * 62)
print("P0-B 验收测试（researchctl 只读检索内核）")
print("=" * 62)

# --- 0. 无依赖：首次索引可复现 ---
print("\n[0] 依赖 / 首次索引可复现")
tmp_fixture = tempfile.mkdtemp()
try:
    dst = os.path.join(tmp_fixture, "f")
    shutil.copytree(FIXTURE, dst, ignore=shutil.ignore_patterns(".git", ".index", "*.sqlite", "__pycache__"))
    try:
        subprocess.run([sys.executable, "-m", "researchctl", "--root", dst, "index"],
                       check=True, capture_output=True, cwd=ROOT)
        check("0.1 新环境首次 index 成功", True)
    except subprocess.CalledProcessError as e:
        check("0.1 新环境首次 index 成功", False, e.stderr.decode()[:200])
finally:
    shutil.rmtree(tmp_fixture, ignore_errors=True)

with open(os.path.join(ROOT, "researchctl", "indexer.py")) as f:
    check("0.2 indexer 无 import yaml", "import yaml" not in f.read())
with open(os.path.join(ROOT, "researchctl", "requirements.txt")) as f:
    content = f.read()
check("0.3 requirements.txt 存在（声明零依赖）", "零" in content or "标准库" in content)

# 确保 fixture 索引就绪
reindex()

# --- A: 当前结论 ---
print("\n[A] 当前结论")
curr = open(os.path.join(FIXTURE, "reports", "CURRENT.md")).read()
check("A1 CURRENT.md 可读", "128K" in curr and "模型 A" in curr)
src = run("sources", "CURRENT")
check("A2 CURRENT sources 正常", src["status"] in ("success", "warning") and src["error_semantic"] is None)

# --- B: 当前结论来源 ---
print("\n[B] 当前结论来源")
check("B1 sources 指向 result.md", any("organized/EXP-017/result.md" in r["path"] for r in src["results"]))
r0 = src["results"][0]
check("B2 返回精确 pinned hash", str(r0.get("content_hash", "")).startswith("sha256:"))
check("B3 返回精确 git_commit", len(str(r0.get("git_commit", ""))) >= 8)

# --- C: Organized → Raw ---
print("\n[C] Organized → Raw")
tr = run("trace", "ORG-EXP017")
raws = [r["entity_id"] for r in tr["results"] if "raw" in r["entity_id"]]
check("C1 trace 到达 raw 目录", len(raws) >= 3)
check("C2 含 R051", any("R051" in r for r in raws))
check("C3 含 R052", any("R052" in r for r in raws))
check("C4 含 R053", any("R053" in r for r in raws))

# --- D: REPORT-001 历史来源 ---
print("\n[D] REPORT-001 历史来源")
s1 = run("sources", "REPORT-001")
check("D1 指向 result.md", any("result.md" in r["path"] for r in s1["results"]))
check("D2 有 pinned hash", any(r.get("content_hash") for r in s1["results"]))
check("D3 有 pinned git_commit", any(r.get("git_commit") for r in s1["results"]))
check("D4 历史可恢复（is_available=True）", s1["results"][0]["is_available"] is True)
check("D5 且标记 stale（来源已变）", s1["results"][0]["is_stale"] is True)

# --- E: 历史来源变化检测 ---
print("\n[E] 历史来源变化检测")
check("E1 报 SOURCE_CHANGED_SINCE_PIN warning", any(
    "SOURCE_CHANGED_SINCE_PIN" in str(w) for w in s1.get("warnings", [])))
pinned = next((r["content_hash"] for r in s1["results"] if "result.md" in r["path"]), None)
cur = shasum(os.path.join(FIXTURE, "organized", "EXP-017", "result.md"))
check("E2 pinned hash != 当前 hash", pinned != cur)

# --- F: 历史演化 ---
print("\n[F] 历史演化")
hist = run("history")
reports = {r["entity_id"]: r for r in hist["results"]}
check("F1 history 返回 4 条报告", len(hist["results"]) == 4)
check("F2 REPORT-001 research=stale", reports.get("REPORT-001", {}).get("status", {}).get("research") == "stale")
check("F3 REPORT-002 research=stale", reports.get("REPORT-002", {}).get("status", {}).get("research") == "stale")
check("F4 CURRENT research=fresh", reports.get("CURRENT", {}).get("status", {}).get("research") == "fresh")
# 六轴 research 合法值校验
VALID_RESEARCH = {"fresh", "stale", "needs_review", None}
check("F5 research 值全部合法", all(r["status"]["research"] in VALID_RESEARCH for r in hist["results"]))

# --- G: 历史报告不变性 ---
print("\n[G] 历史报告不变性")
cmap = {"REPORT-001": "f0d7ffc", "REPORT-002": "a8cb33c", "REPORT-003": "1bf12e0"}
all_immutable = True
for rep, c in cmap.items():
    for sf in [".md", ".sources.yaml"]:
        frozen_bytes = subprocess.check_output(["git", "-C", FIXTURE, "show", f"{c}:reports/history/{rep}{sf}"])
        now = shasum(os.path.join(FIXTURE, "reports", "history", f"{rep}{sf}"))
        if now != "sha256:" + hashlib.sha256(frozen_bytes).hexdigest():
            all_immutable = False
check("G1 历史报告自冻结后未变", all_immutable)

# --- H: 删除 source 报警（tmp copy，不污染 fixture）---
print("\n[H] 删除 source 报警")
tmp_fixture2 = tempfile.mkdtemp()
try:
    dst2 = os.path.join(tmp_fixture2, "f")
    shutil.copytree(FIXTURE, dst2, symlinks=False,
                    ignore=shutil.ignore_patterns(".git", ".index", "*.sqlite", "__pycache__"))
    os.remove(os.path.join(dst2, "organized", "EXP-017", "result.md"))
    reindex(dst2)
    out = run("sources", "CURRENT", root=dst2)
    check("H1 sources 硬错误 fail_closed", out["status"] == "fail_closed")
    check("H2 error_semantic=SOURCE_MISSING", out["error_semantic"] == "SOURCE_MISSING")
    check("H3 source 标记不可用", len(out["results"]) > 0 and out["results"][0]["is_available"] is False)
    tr2 = run("trace", "CURRENT", root=dst2)
    check("H4 trace 硬错误 fail_closed", tr2["status"] == "fail_closed")
finally:
    shutil.rmtree(tmp_fixture2, ignore_errors=True)

# --- I: INDEX_STALE fail_closed ---
print("\n[I] INDEX_STALE fail_closed")
tmp_fixture3 = tempfile.mkdtemp()
try:
    dst3 = os.path.join(tmp_fixture3, "f")
    shutil.copytree(FIXTURE, dst3, symlinks=False,
                    ignore=shutil.ignore_patterns(".git", ".index", "*.sqlite", "__pycache__"))
    reindex(dst3)
    # 篡改文件使 fingerprint 不匹配
    with open(os.path.join(dst3, "index", "INDEX.md"), "a") as f:
        f.write("\n# tampered\n")
    out = run("query", root=dst3)
    check("I1 索引过期 fail_closed", out["status"] == "fail_closed")
    check("I2 error_semantic=INDEX_STALE", out["error_semantic"] == "INDEX_STALE")
    check("I3 不返回旧结果", len(out["results"]) == 0)
    check("I4 drift 标记为 true", out["source_watermark"]["drift"] is True)
    # reindex 后恢复
    reindex(dst3)
    out = run("query", root=dst3)
    check("I5 reindex 后恢复 success", out["status"] == "success" and len(out["results"]) > 0)
finally:
    shutil.rmtree(tmp_fixture3, ignore_errors=True)

# --- J: query 字段错位回归 ---
print("\n[J] query 字段错位回归")
q = run("query", "--entity", "R051")
r = q["results"][0]
check("J1 R051 hash 正确（sha256:...）", str(r.get("content_hash", "")).startswith("sha256:"))
check("J2 R051 有 git_commit", bool(r.get("git_commit")))
q2 = run("query", "--entity", "EXP-017")
r2 = q2["results"][0]
check("J3 EXP-017 返回 spec.yaml", r2["path"] == "experiments/EXP-017/spec.yaml")
check("J4 EXP-017 hash 正确", str(r2.get("content_hash", "")).startswith("sha256:"))
check("J5 不存在实体 NOT_FOUND", run("query", "--entity", "NOPE")["error_semantic"] == "NOT_FOUND")

# --- K: trace drift warning ---
print("\n[K] trace drift warning")
trk = run("trace", "R051")
check("K1 trace R051 检出历史 Raw 已变化", any(
    "SOURCE_CHANGED_SINCE_PIN" in str(w) for w in trk.get("warnings", [])))
check("K2 trace 状态为 warning（非 success）", trk["status"] == "warning")

# --- L: lexical 检索 ---
print("\n[L] lexical 检索")
lex = run("query", "--text", "数据泄漏")
check("L1 关键词检索有结果", len(lex["results"]) >= 1)
check("L2 命中包含相关文档", any("CURRENT" == r["entity_id"] or "REPORT-003" == r["entity_id"]
                              or "result.md" in r["path"] for r in lex["results"]))
lex2 = run("query", "--text", "accuracy")
check("L3 英文关键词检索", len(lex2["results"]) >= 1)

# --- M: envelope 一致性 ---
print("\n[M] envelope 一致性")
check("M1 query_type 枚举合法", all(
    r["query_type"] in ("current", "sources", "trace", "history", "reindex", "reconcile", "status")
    for r in [run("query"), run("sources", "CURRENT"), run("trace", "CURRENT"), run("history")]))
check("M2 sources authority=canonical", run("sources", "CURRENT")["authority"] == "canonical")
check("M3 query authority=derived", run("query")["authority"] == "derived")
check("M4 trace authority=derived", run("trace", "CURRENT")["authority"] == "derived")
check("M5 history authority=canonical", run("history")["authority"] == "canonical")
check("M6 query_type=current（非 query）", run("query")["query_type"] == "current")

# --- 摘要 ---
print("\n" + "=" * 62)
print(f"结果: {PASS} PASS / {FAIL} FAIL")
if FAILURES:
    print("失败项: " + ", ".join(FAILURES))
print("=" * 62)
sys.exit(1 if FAIL else 0)
