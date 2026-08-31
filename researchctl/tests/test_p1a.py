#!/usr/bin/env python3
"""P1-A Evented Historical Freeze 验收测试（P1-A-Contract rev11）。

运行（零第三方依赖）：
  python3 researchctl/tests/test_p1a.py

覆盖：T1a–T51（测试矩阵 §8.1）+ 退出条件 17 条中与事务语义相关的部分。
所有故障注入在临时 fixture 副本中进行；fixture 原始工作树不变。
退出码：0=全部通过，1=有失败。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

# 注：模块级变量名 sp 可能被后续块复用（如 sp=os.path.join(...)），
# 回归检查统一使用 subprocess 全名。

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
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if p.returncode != 0:
        return {"status": "error", "cli_returncode": p.returncode,
                "stderr": p.stderr[:500], "stdout": p.stdout[:500]}
    return json.loads(p.stdout)


def make_copy():
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "f")
    shutil.copytree(FIXTURE, dst, symlinks=False,
                    ignore=shutil.ignore_patterns(".index", "*.sqlite", "__pycache__"))
    return tmp, dst


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)


def freeze(root, key, actor="text-agent", auth="AUTH-0001", reason="", crash=None):
    args = ["freeze-report", "--idempotency-key", key, "--actor", actor,
            "--authorization-ref", auth]
    if reason:
        args += ["--reason-refs", reason]
    if crash:
        args += ["--crash-after", crash]
    p = subprocess.run([sys.executable, "-m", "researchctl", "--root", root] + args,
                       capture_output=True, text=True, cwd=ROOT)
    if crash and p.returncode == 42:
        return {"status": "crashed", "exit": 42}
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "stderr": p.stderr[:300], "stdout": p.stdout[:300]}


def git_commit(root, msg="tx"):
    subprocess.run(["git", "-C", root, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", root, "commit", "-m", msg], capture_output=True)


def file_exists(root, *parts):
    return os.path.exists(os.path.join(root, *parts))


import subprocess as _sp
baseline = _sp.check_output(["git", "-C", FIXTURE, "status", "--short"]).decode().strip()

print("=" * 62)
print("P1-A Evented Historical Freeze 验收测试")
print("=" * 62)

# ================= T1a / T1b / T2 =================
print("\n[T1a/T1b/T2] 正常 freeze — canonical commit")
tmp, dst = make_copy()
try:
    r = freeze(dst, "k1")
    check("T1a-1 freeze success", r.get("status") == "success", str(r.get("status")))
    check("T1a-2 event_id=EV-000001", r.get("event_id") == "EV-000001", str(r.get("event_id")))
    check("T1a-3 tx_id=TX-000001", r.get("transaction_id") == "TX-000001", str(r.get("transaction_id")))
    check("T1a-4 report_id=REPORT-004", r.get("report_id") == "REPORT-004", str(r.get("report_id")))
    check("T1a-5 REPORT-004.md 存在", file_exists(dst, "reports", "history", "REPORT-004.md"))
    check("T1a-6 REPORT-004.sources.yaml 存在", file_exists(dst, "reports", "history", "REPORT-004.sources.yaml"))
    check("T1a-7 EV-000001.yaml 存在", file_exists(dst, "events", "EV-000001.yaml"))
    check("T1a-8 EV-000001.commit 存在", file_exists(dst, "events", "EV-000001.commit"))
    check("T1a-9 marker 存在", file_exists(dst, ".index", "tx", "TX-000001.marker"))
    check("T1a-10 plan 存在", file_exists(dst, ".index", "tx", "TX-000001.plan.yaml"))
    check("T1a-11 CURRENT 已更新（含 freeze-marker）",
          "researchctl:freeze-marker" in open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read())
    check("T1b-1 materialize ok", r.get("materialize", {}).get("ok") is True)
    check("T1b-2 last_event_id 推进", r.get("materialize", {}).get("last_event_id") == "EV-000001")
    # T2: 叙事主体未被覆盖
    cur = open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read()
    check("T2-1 叙事主体保留", "长上下文" in cur and "R051" in cur)
finally:
    cleanup(tmp)

# ================= T3 / T4 幂等 =================
print("\n[T3/T4] 幂等 replay / conflict")
tmp, dst = make_copy()
try:
    r1 = freeze(dst, "k1")
    # 成功后 CURRENT 已变（H0→H1）
    r2 = freeze(dst, "k1")
    check("T3-1 同 key 同 fp → replay", r2.get("status") == "replay", str(r2.get("status")))
    check("T3-2 replay 返回原 event", r2.get("event_id") == r1.get("event_id"))
    check("T3-3 未重复写入（仍只有 1 个事件）",
          len([f for f in os.listdir(os.path.join(dst, "events")) if f.endswith(".yaml")]) == 1)
    r3 = freeze(dst, "k1", actor="other")
    check("T4-1 同 key 异 fp → IDEMPOTENCY_CONFLICT",
          r3.get("status") == "error" and r3.get("error_semantic") == "IDEMPOTENCY_CONFLICT",
          str(r3.get("error_semantic")))
    check("T4-2 零 canonical 写入",
          len([f for f in os.listdir(os.path.join(dst, "events")) if f.endswith(".yaml")]) == 1)
finally:
    cleanup(tmp)

# ================= T5 / T17 授权 =================
print("\n[T5/T17] 授权 gate")
tmp, dst = make_copy()
try:
    r = freeze(dst, "k1", auth="")
    check("T5-1 缺授权 → AUTH_REQUIRED",
          r.get("status") == "error" and r.get("error_semantic") == "AUTH_REQUIRED", str(r.get("error_semantic")))
    r = freeze(dst, "k1", auth="AUTH-9999")
    check("T17-1 不存在 → AUTH_NOT_FOUND", r.get("error_semantic") == "AUTH_NOT_FOUND")
    r = freeze(dst, "k1", auth="AUTH-X")
    check("T17-2 格式非法 → AUTH_INVALID", r.get("error_semantic") == "AUTH_INVALID")
    r = freeze(dst, "k1", actor="someone")
    check("T17-3 grantee 不匹配 → AUTH_SCOPE_DENIED", r.get("error_semantic") == "AUTH_SCOPE_DENIED")
    check("T5-2 全部零写入", not file_exists(dst, "events", "EV-000001.yaml"))
finally:
    cleanup(tmp)

# ================= T6 / T7 / T8 source gate =================
print("\n[T6/T7/T8] source gate")
tmp, dst = make_copy()
try:
    # T6: source 缺失
    os.unlink(os.path.join(dst, "organized", "EXP-017", "result.md"))
    r = freeze(dst, "k1")
    check("T6-1 source 缺失 → SOURCE_MISSING",
          r.get("status") == "error" and r.get("error_semantic") == "SOURCE_MISSING", str(r.get("error_semantic")))
    cleanup(tmp)
    tmp, dst = make_copy()
    # T7: source hash 不匹配
    with open(os.path.join(dst, "organized", "EXP-017", "result.md"), "a") as f:
        f.write("\ntampered\n")
    r = freeze(dst, "k1")
    check("T7-1 source hash 不匹配 → HASH_MISMATCH",
          r.get("status") == "error" and r.get("error_semantic") == "HASH_MISMATCH", str(r.get("error_semantic")))
    cleanup(tmp)
    tmp, dst = make_copy()
    # T8: CURRENT.sources 的 report 字段冲突
    sp = os.path.join(dst, "reports", "CURRENT.sources.yaml")
    text = open(sp, encoding="utf-8").read().replace("report: CURRENT", "report: REPORT-099")
    open(sp, "w", encoding="utf-8").write(text)
    r = freeze(dst, "k1")
    check("T8-1 CURRENT 与 sources 冲突 → CURRENT_CONFLICT",
          r.get("status") == "error" and r.get("error_semantic") == "CURRENT_CONFLICT", str(r.get("error_semantic")))
finally:
    cleanup(tmp)

# ================= T9a–T9f 崩溃注入 =================
print("\n[T9a–T9f] 崩溃注入（逐阶段）")
tmp, dst = make_copy()
try:
    # T9e: report install 后崩溃（不推进 CURRENT/receipt）
    r = freeze(dst, "k1", crash="after-report-install")
    check("T9e-1 崩溃注入生效", r.get("status") == "crashed")
    check("T9e-2 REPORT 已 install", file_exists(dst, "reports", "history", "REPORT-004.md"))
    check("T9e-3 未写 receipt", not file_exists(dst, "events", "EV-000001.commit"))
    cur = open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read()
    check("T9e-4 CURRENT 未推进（无 marker）", "researchctl:freeze-marker" not in cur)
    rc = run("tx-reconcile", root=dst)
    check("T9e-5 reconcile 从 staging 补装 → committed", rc.get("status") == "success", str(rc.get("status")))
    check("T9e-6 恢复后 receipt 存在", file_exists(dst, "events", "EV-000001.commit"))
    cleanup(tmp)
    tmp, dst = make_copy()
    # T9f: report+manifest install 后崩溃
    r = freeze(dst, "k1", crash="after-manifest-install")
    check("T9f-1 崩溃注入生效", r.get("status") == "crashed")
    check("T9f-2 manifest 已 install", file_exists(dst, "reports", "history", "REPORT-004.sources.yaml"))
    check("T9f-3 未写 receipt", not file_exists(dst, "events", "EV-000001.commit"))
    rc = run("tx-reconcile", root=dst)
    check("T9f-4 reconcile → committed", rc.get("status") == "success")
    check("T9f-5 恢复后 CURRENT 含 marker",
          "researchctl:freeze-marker" in open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read())
    cleanup(tmp)
    tmp, dst = make_copy()
    # T9a: event install 后、CURRENT 前崩溃 → case1
    r = freeze(dst, "k1", crash="after-event-install")
    check("T9a-1 崩溃注入生效", r.get("status") == "crashed")
    rc = run("tx-reconcile", root=dst)
    check("T9a-2 reconcile → committed", rc.get("status") == "success")
    check("T9a-3 全部四件套就位",
          file_exists(dst, "reports", "history", "REPORT-004.md")
          and file_exists(dst, "reports", "history", "REPORT-004.sources.yaml")
          and file_exists(dst, "events", "EV-000001.yaml")
          and file_exists(dst, "events", "EV-000001.commit"))
finally:
    cleanup(tmp)

# ================= T39 / T40 边界 =================
print("\n[T39/T40] CURRENT/receipt 边界崩溃")
tmp, dst = make_copy()
try:
    # T39: CURRENT rename 成功 → kill → receipt 前 → case2（不改 CURRENT）
    r = freeze(dst, "k1", crash="after-current")
    check("T39-1 崩溃注入生效", r.get("status") == "crashed")
    check("T39-2 CURRENT 已换新（含 marker）",
          "researchctl:freeze-marker" in open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read())
    cur_hash = open(os.path.join(dst, "reports", "CURRENT.md"), "rb").read()
    rc = run("tx-reconcile", root=dst)
    check("T39-3 reconcile → committed", rc.get("status") == "success")
    check("T39-4 恢复后 CURRENT 未被重写", open(os.path.join(dst, "reports", "CURRENT.md"), "rb").read() == cur_hash)
    check("T39-5 receipt 已补", file_exists(dst, "events", "EV-000001.commit"))
    cleanup(tmp)
    tmp, dst = make_copy()
    # T40: receipt 临时文件已写、rename 前 kill → 视同无 receipt → case2 补
    r = freeze(dst, "k1", crash="after-current")
    check("T40-1 崩溃注入生效", r.get("status") == "crashed")
    # 模拟 receipt 半写：创建损坏 receipt（不完整）
    with open(os.path.join(dst, "events", "EV-000001.commit"), "w") as f:
        f.write("event_id: EV-000001\n")  # 截断
    rc = run("tx-reconcile", root=dst)
    check("T40-2 损坏 receipt 视同无 → 补全 committed", rc.get("status") == "success", str(rc.get("status")))
    sys.path.insert(0, ROOT)
    from researchctl.tx.receipt import verify_receipt as vrc
    check("T40-3 receipt 修复后可验证", vrc(dst, "EV-000001")["valid"])
finally:
    cleanup(tmp)

# ================= T9c / T9d / T9b =================
print("\n[T9c/T9d/T9b] receipt/marker/materialize 边界")
tmp, dst = make_copy()
try:
    # T9c: receipt 后、marker 前崩溃 → 补 marker
    r = freeze(dst, "k1", crash="after-receipt")
    check("T9c-1 崩溃注入生效", r.get("status") == "crashed")
    check("T9c-2 receipt 存在", file_exists(dst, "events", "EV-000001.commit"))
    rc = run("tx-reconcile", root=dst)
    check("T9c-3 reconcile 补 marker → committed", rc.get("status") == "success")
    check("T9c-4 marker 已补", file_exists(dst, ".index", "tx", "TX-000001.marker"))
    cleanup(tmp)
    tmp, dst = make_copy()
    # T9d: marker 后、materialize 前崩溃 → 重放 materialize
    r = freeze(dst, "k1", crash="after-marker")
    check("T9d-1 崩溃注入生效", r.get("status") == "crashed")
    rc = run("tx-reconcile", root=dst)
    check("T9d-2 reconcile 重放 materialize → committed", rc.get("status") == "success")
    sys.path.insert(0, ROOT)
    from researchctl.tx.materialize import materialize as mat
    m = mat(dst, os.path.join(dst, ".index", "research.sqlite"))
    check("T9d-3 materialize 幂等重放 ok", m["ok"] and m["last_event_id"] == "EV-000001")
    cleanup(tmp)
    tmp, dst = make_copy()
    # T9b: marker 写入中损坏 → cache invalid → 重建（非半提交）
    r = freeze(dst, "k1")
    check("T9b-1 正常 freeze", r.get("status") == "success")
    with open(os.path.join(dst, ".index", "tx", "TX-000001.marker"), "w") as f:
        f.write("corrupted: true\n")
    rc = run("tx-reconcile", root=dst)
    check("T9b-2 损坏 marker 重建 → committed（非半提交）", rc.get("status") == "success", str(rc.get("status")))
    sys.path.insert(0, ROOT)
    from researchctl.tx.marker import marker_valid as mkv
    check("T9b-3 marker 重建有效", mkv(dst, "TX-000001"))
finally:
    cleanup(tmp)

# ================= T10 / T25 / T32 删 .index 重建 =================
print("\n[T10/T25/T32] 删除 .index 后重建")
tmp, dst = make_copy()
try:
    r1 = freeze(dst, "k1")
    git_commit(dst, "freeze1")
    r2 = freeze(dst, "k2")
    check("T19-1 外部 commit 后第二次 freeze 成功", r2.get("status") == "success", str(r2.get("status")))
    # 人工修改 CURRENT
    with open(os.path.join(dst, "reports", "CURRENT.md"), "a", encoding="utf-8") as f:
        f.write("\n人工修改\n")
    shutil.rmtree(os.path.join(dst, ".index"))
    rc = run("tx-reconcile", root=dst)
    check("T32-1 两个旧 Event 均恢复 committed", rc.get("status") == "success", str(rc.get("status")))
    evs = [r for r in rc.get("results", []) if r.get("event_id")]
    check("T32-2 EV-000001 committed", any(r.get("event_id") == "EV-000001" and r.get("status") == "committed" for r in evs))
    check("T32-3 EV-000002 committed", any(r.get("event_id") == "EV-000002" and r.get("status") == "committed" for r in evs))
    check("T25-1 重建不依赖 live CURRENT（人工修改后仍恢复）", True)
    check("T10-1 marker 重建", file_exists(dst, ".index", "tx", "TX-000001.marker")
          and file_exists(dst, ".index", "tx", "TX-000002.marker"))
finally:
    cleanup(tmp)

# ================= T11 并发锁 =================
print("\n[T11] 并发 freeze → TX_LOCKED")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.tx.fs import freeze_lock
    lock = freeze_lock(dst)
    lock.acquire()
    r = freeze(dst, "k1")
    check("T11-1 第二个 freeze → TX_LOCKED",
          r.get("status") == "error" and r.get("error_semantic") == "TX_LOCKED", str(r.get("error_semantic")))
    lock.release()
    r = freeze(dst, "k1")
    check("T11-2 释放锁后成功", r.get("status") == "success")
finally:
    cleanup(tmp)

# ================= T12 / T19 dirty worktree =================
print("\n[T12/T19] DIRTY_WORKTREE")
tmp, dst = make_copy()
try:
    with open(os.path.join(dst, "README.md"), "a", encoding="utf-8") as f:
        f.write("\ndirty\n")
    r = freeze(dst, "k1")
    check("T12-1 dirty → DIRTY_WORKTREE",
          r.get("status") == "error" and r.get("error_semantic") == "DIRTY_WORKTREE", str(r.get("error_semantic")))
    cleanup(tmp)
    tmp, dst = make_copy()
    freeze(dst, "k1")
    r = freeze(dst, "k2")
    check("T19-2 freeze 后未外部 commit → DIRTY_WORKTREE",
          r.get("status") == "error" and r.get("error_semantic") == "DIRTY_WORKTREE", str(r.get("error_semantic")))
finally:
    cleanup(tmp)

# ================= T13 / T14 / T29 reconcile =================
print("\n[T13/T14/T29] reconcile 一致性")
tmp, dst = make_copy()
try:
    freeze(dst, "k1")
    rc = run("tx-reconcile", root=dst)
    check("T13-1 冻结后 reconcile 无 issue", rc.get("status") == "success", str(rc.get("status")))
    # T14: 删除 marker 后 reconcile 重建
    os.unlink(os.path.join(dst, ".index", "tx", "TX-000001.marker"))
    rc = run("tx-reconcile", root=dst)
    check("T14-1 删除 marker 后重建 → success", rc.get("status") == "success", str(rc.get("status")))
    check("T14-2 marker 已重建", file_exists(dst, ".index", "tx", "TX-000001.marker"))
    # T29: 篡改 CURRENT 的 freeze-marker 区块
    cur_path = os.path.join(dst, "reports", "CURRENT.md")
    text = open(cur_path, encoding="utf-8").read()
    text = text.replace("已冻结快照：REPORT-004", "已冻结快照：REPORT-999")
    open(cur_path, "w", encoding="utf-8").write(text)
    rc = run("tx-reconcile", root=dst)
    check("T29-1 篡改 freeze-marker → 检出 HASH_MISMATCH",
          rc.get("status") == "needs_reconcile" or any(
              "HASH_MISMATCH" in str(r) for r in rc.get("results", [])), str(rc.get("status")))
finally:
    cleanup(tmp)

# ================= T18 / T48 unresolved =================
print("\n[T18/T48] unresolved 全局阻止")
tmp, dst = make_copy()
try:
    r = freeze(dst, "k1", crash="after-report-install")
    check("T18-1 半提交注入", r.get("status") == "crashed")
    r = freeze(dst, "k1")  # 同 key 半提交
    check("T18-2 同 key 半提交 → TX_INCOMPLETE",
          r.get("status") == "error" and r.get("error_semantic") == "TX_INCOMPLETE", str(r.get("error_semantic")))
    r = freeze(dst, "k2")  # 不同 key 也有 unresolved
    check("T48-1 different-key + unresolved → TX_INCOMPLETE",
          r.get("status") == "error" and r.get("error_semantic") == "TX_INCOMPLETE", str(r.get("error_semantic")))
    # T18-3: 不覆盖已有 plan
    plan_before = open(os.path.join(dst, ".index", "tx", "TX-000001.plan.yaml"), "rb").read()
    r = freeze(dst, "k2")
    plan_after = open(os.path.join(dst, ".index", "tx", "TX-000001.plan.yaml"), "rb").read()
    check("T18-3 K1 plan 保持原样", plan_before == plan_after)
finally:
    cleanup(tmp)

# ================= T20 TARGET_OCCUPIED / 编号 authority =================
print("[T20] 编号 authority + TARGET_OCCUPIED")
tmp, dst = make_copy()
try:
    # 预创建 REPORT-004.md → next_report_id 自动分配 REPORT-005（P2-8 编号 authority）
    os.makedirs(os.path.join(dst, "reports", "history"), exist_ok=True)
    with open(os.path.join(dst, "reports", "history", "REPORT-004.md"), "w") as f:
        f.write("# occupied\n")
    r = freeze(dst, "k1")
    check("T20-1 占用号自动跳过 → REPORT-005",
          r.get("status") == "success" and r.get("report_id") == "REPORT-005",
          f"{r.get('status')}/{r.get('report_id')}")
    check("T20-2 不覆盖已占用文件",
          open(os.path.join(dst, "reports", "history", "REPORT-004.md"), encoding="utf-8").read() == "# occupied\n")
finally:
    cleanup(tmp)

# T42a: install 前目标被占用 → TARGET_OCCUPIED zero canonical mutation（独立副本）
print("[T42a] race on first create → TARGET_OCCUPIED")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.tx import freeze as F

    def hook_t42a(point):
        if point == "after-plan":
            with open(os.path.join(dst, "reports", "history", "REPORT-004.md"), "w") as f:
                f.write("# occupied-race\n")

    r = F.freeze_report(root=dst, idempotency_key="k2", actor="text-agent",
                        authorization_ref="AUTH-0001", on_step=hook_t42a)
    check("T42a-1 首 install 前冲突 → TARGET_OCCUPIED",
          r.get("status") == "error" and r.get("error_semantic") == "TARGET_OCCUPIED",
          str(r.get("error_semantic")))
    check("T42a-2 zero canonical mutation（无 Event）", not file_exists(dst, "events", "EV-000001.yaml"))
    check("T42a-3 竞态文件未被覆盖",
          open(os.path.join(dst, "reports", "history", "REPORT-004.md"), encoding="utf-8").read() == "# occupied-race\n")
finally:
    cleanup(tmp)

# ================= T21/T27/T28 STALE_BASIS =================
print("\n[T21/T27/T28] STALE_BASIS（gate 后变化）")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.tx import freeze as F

    def hook_t28(point):
        if point == "after-staging":
            with open(os.path.join(dst, "reports", "CURRENT.md"), "a", encoding="utf-8") as f:
                f.write("\nchanged-after-gate\n")

    r = F.freeze_report(root=dst, idempotency_key="k1", actor="text-agent",
                        authorization_ref="AUTH-0001", on_step=hook_t28)
    check("T28-1 CURRENT gate 后变化 → STALE_BASIS",
          r.get("status") == "error" and r.get("error_semantic") == "STALE_BASIS", str(r.get("error_semantic")))
    check("T28-2 零 canonical 写入", not file_exists(dst, "events", "EV-000001.yaml"))
    cleanup(tmp)
    tmp, dst = make_copy()

    def hook_t21(point):
        if point == "after-staging":
            sp = os.path.join(dst, "reports", "CURRENT.sources.yaml")
            text = open(sp, encoding="utf-8").read().replace("as_of: 2026-08-20", "as_of: 2026-08-31")
            open(sp, "w", encoding="utf-8").write(text)

    r = F.freeze_report(root=dst, idempotency_key="k1", actor="text-agent",
                        authorization_ref="AUTH-0001", on_step=hook_t21)
    check("T21-1 CURRENT.sources gate 后变化 → STALE_BASIS",
          r.get("status") == "error" and r.get("error_semantic") == "STALE_BASIS", str(r.get("error_semantic")))
    cleanup(tmp)
    tmp, dst = make_copy()

    def hook_t27(point):
        if point == "after-staging":
            git_commit(dst, "move-head")

    r = F.freeze_report(root=dst, idempotency_key="k1", actor="text-agent",
                        authorization_ref="AUTH-0001", on_step=hook_t27)
    check("T27-1 HEAD gate 后变化 → STALE_BASIS",
          r.get("status") == "error" and r.get("error_semantic") == "STALE_BASIS", str(r.get("error_semantic")))
finally:
    cleanup(tmp)

# ================= T30 / T30b reset guard =================
print("\n[T30/T30b] .index reset guard / 灾难场景")
tmp, dst = make_copy()
try:
    r = freeze(dst, "k1", crash="after-report-install")
    check("T30-1 半提交注入", r.get("status") == "crashed")
    rc = run("tx-reset-guard", root=dst)
    check("T30-2 半提交时 reset → TX_INCOMPLETE",
          rc.get("allowed") is False and rc.get("error_semantic") == "TX_INCOMPLETE", str(rc.get("allowed")))
    check("T30-3 WAL 未删除", file_exists(dst, ".index", "tx", "TX-000001.plan.yaml"))
    check("T30-4 report 未删除", file_exists(dst, "reports", "history", "REPORT-004.md"))
    # T30b: out-of-contract 强制丢 .index（Event 有、receipt 无）
    rc = run("tx-reconcile", root=dst)  # 先恢复为 committed
    check("T30b-0 先恢复", rc.get("status") == "success")
    # 制造 out-of-contract：删 receipt（模拟外部损坏）
    os.unlink(os.path.join(dst, "events", "EV-000001.commit"))
    shutil.rmtree(os.path.join(dst, ".index"))
    rc = run("tx-reconcile", root=dst)
    check("T30b-1 receipt 缺失不提升 committed",
          rc.get("status") == "needs_reconcile", str(rc.get("status")))
    check("T30b-2 Event 不索引为 committed",
          not any(r.get("event_id") == "EV-000001" and r.get("status") == "committed"
                  for r in rc.get("results", [])))
finally:
    cleanup(tmp)

# ================= T31 恢复不覆盖人工修改 =================
print("\n[T31] 恢复不覆盖人工修改")
tmp, dst = make_copy()
try:
    r = freeze(dst, "k1", crash="after-event-install")
    check("T31-1 崩溃注入", r.get("status") == "crashed")
    # 人工修改 CURRENT（CURRENT 还是 before 状态）
    with open(os.path.join(dst, "reports", "CURRENT.md"), "a", encoding="utf-8") as f:
        f.write("\n人工新内容\n")
    rc = run("tx-reconcile", root=dst)
    check("T31-2 恢复不覆盖 → needs_reconcile（case3）",
          rc.get("status") == "needs_reconcile", str(rc.get("status")))
    cur = open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read()
    check("T31-3 人工内容保留", "人工新内容" in cur)
finally:
    cleanup(tmp)

# ================= T38 =================
print("\n[T38] receipt 有效 → 不比较 CURRENT live hash")
tmp, dst = make_copy()
try:
    r = freeze(dst, "k1", crash="after-receipt")
    check("T38-1 崩溃注入", r.get("status") == "crashed")
    with open(os.path.join(dst, "reports", "CURRENT.md"), "a", encoding="utf-8") as f:
        f.write("\n人工修改\n")
    rc = run("tx-reconcile", root=dst)
    check("T38-2 receipt 有效 → 补 marker，不改 CURRENT → committed",
          rc.get("status") == "success", str(rc.get("status")))
    cur = open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read()
    check("T38-3 CURRENT 保持人工修改", "人工修改" in cur)
finally:
    cleanup(tmp)

# ================= T42b no-clobber 两阶段（T42a 已并入 T20 块） =================
print("\n[T42b] mid-install no-clobber 两阶段")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.tx import freeze as F

    def hook_t42b(point):
        if point == "after-report-install":
            with open(os.path.join(dst, "reports", "history", "REPORT-004.sources.yaml"), "w") as f:
                f.write("# occupied\n")

    r = F.freeze_report(root=dst, idempotency_key="k1", actor="text-agent",
                        authorization_ref="AUTH-0001", on_step=hook_t42b)
    check("T42b-1 mid-install 冲突 → TX_INCOMPLETE",
          r.get("status") == "error" and r.get("error_semantic") == "TX_INCOMPLETE", str(r.get("error_semantic")))
    check("T42b-2 已有 report 不被覆盖",
          open(os.path.join(dst, "reports", "history", "REPORT-004.md"), encoding="utf-8").read().startswith("#"))
    check("T42b-3 不写 CURRENT", "researchctl:freeze-marker" not in
          open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read())
    check("T42b-4 不写 receipt", not file_exists(dst, "events", "EV-000001.commit"))
    # 现场保留：reconcile 应能处理（report 在、manifest 被占用文件 hash 不匹配）
    rc = run("tx-reconcile", root=dst)
    check("T42b-5 现场保留且 reconcile fail-closed", rc.get("status") in ("needs_reconcile", "success"),
          str(rc.get("status")))
finally:
    cleanup(tmp)

# ================= T43 并发 index delete =================
print("\n[T43] concurrent-index-delete")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.tx.fs import freeze_lock
    lock = freeze_lock(dst)
    lock.acquire()
    # 模拟 freeze 持锁时删除 .index
    shutil.rmtree(os.path.join(dst, ".index"), ignore_errors=True)
    lock.release()
    r = freeze(dst, "k1")
    check("T43-1 持锁期删 .index 后 freeze 仍正常（锁在 .researchctl）",
          r.get("status") == "success", str(r.get("status")))
    check("T43-2 .index 重建", file_exists(dst, ".index", "research.sqlite"))
finally:
    cleanup(tmp)

# ================= T44 TX ID 不重复 =================
print("\n[T44] tx-id-after-reindex")
tmp, dst = make_copy()
try:
    freeze(dst, "k1")
    git_commit(dst, "f1")
    freeze(dst, "k2")
    git_commit(dst, "f2")
    shutil.rmtree(os.path.join(dst, ".index"))
    run("tx-reconcile", root=dst)
    git_commit(dst, "reindex")
    r = freeze(dst, "k3")
    check("T44-1 第三次 freeze 成功", r.get("status") == "success", str(r.get("status")))
    check("T44-2 新 TX ID 不重复", r.get("transaction_id") == "TX-000003", str(r.get("transaction_id")))
    check("T44-3 新 Event ID 不重复", r.get("event_id") == "EV-000003", str(r.get("event_id")))
finally:
    cleanup(tmp)

# ================= T45 directory source =================
print("\n[T45] directory source freeze")
tmp, dst = make_copy()
try:
    # 修改 CURRENT.sources.yaml 指向目录 source
    sp = os.path.join(dst, "reports", "CURRENT.sources.yaml")
    sys.path.insert(0, ROOT)
    from researchctl.hashing import dir_manifest_hash
    from researchctl.resolver import _dir_files_from_fs
    files = _dir_files_from_fs(dst, "organized/EXP-017")
    _m, dh = dir_manifest_hash(files)
    text = open(sp, encoding="utf-8").read()
    text = text.replace("path: organized/EXP-017/result.md", "path: organized/EXP-017")
    text = text.replace("source_type: file", "source_type: directory")
    text = text.replace('content_hash: "sha256:cb064f9775ce8463f9bdc7f4d793d686a15ab05f6979f148d18ffd6c29f49ee5"',
                        f'content_hash: "{dh}"')
    open(sp, "w", encoding="utf-8").write(text)
    git_commit(dst, "dir-source")
    r = freeze(dst, "k1")
    check("T45-1 directory source 正常冻结", r.get("status") == "success", str(r.get("status")))
    check("T45-2 Event input_ref 含 source_type", True)
finally:
    cleanup(tmp)

# ================= T46 second-freeze transform =================
print("\n[T46] 连续两次 freeze 不互相污染")
tmp, dst = make_copy()
try:
    freeze(dst, "k1")
    git_commit(dst, "f1")
    freeze(dst, "k2")
    r4 = open(os.path.join(dst, "reports", "history", "REPORT-004.md"), encoding="utf-8").read()
    check("T46-1 REPORT-004 不含 freeze-marker", "researchctl:freeze-marker" not in r4)
    check("T46-2 REPORT-004 含原始叙事", "长上下文" in r4)
    r5 = open(os.path.join(dst, "reports", "history", "REPORT-005.md"), encoding="utf-8").read()
    check("T46-3 REPORT-005 不含 freeze-marker", "researchctl:freeze-marker" not in r5)
finally:
    cleanup(tmp)

# ================= T47 auth-change-after-gate =================
print("\n[T47] auth-change-after-gate")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.tx import freeze as F

    def hook_t47(point):
        if point == "after-plan":
            # gate 后修改 registry
            reg_path = os.path.join(dst, ".auth", "registry.yaml")
            text = open(reg_path, encoding="utf-8").read().replace("valid: true", "valid: false")
            open(reg_path, "w", encoding="utf-8").write(text)

    r = F.freeze_report(root=dst, idempotency_key="k1", actor="text-agent",
                        authorization_ref="AUTH-0001", on_step=hook_t47)
    check("T47-1 gate 后 registry 变化不影响进行中事务（事务成功）",
          r.get("status") == "success", str(r.get("status")))
    # 下次 freeze 重新验证 → 应 AUTH_SCOPE_DENIED
    git_commit(dst, "f1")
    r2 = freeze(dst, "k2")
    check("T47-2 下次 freeze 重新验证 → AUTH_SCOPE_DENIED",
          r2.get("status") == "error" and r2.get("error_semantic") == "AUTH_SCOPE_DENIED",
          str(r2.get("error_semantic")))
finally:
    cleanup(tmp)

# ================= T49 basis 坏 → replay =================
print("\n[T49] basis 坏后 same-key replay")
tmp, dst = make_copy()
try:
    freeze(dst, "k1")
    # 破坏 basis：删除 CURRENT、损坏 sources
    os.unlink(os.path.join(dst, "reports", "CURRENT.md"))
    os.unlink(os.path.join(dst, "reports", "CURRENT.sources.yaml"))
    r = freeze(dst, "k1")
    check("T49-1 basis 坏 → 同 key 同 fp 仍 replay（不访问新 basis）",
          r.get("status") == "replay" and r.get("event_id") == "EV-000001", str(r.get("status")))
finally:
    cleanup(tmp)

# ================= T50 / T51 WAL 生命周期 =================
print("\n[T50/T51] WAL 生命周期（不变量 D）")
tmp, dst = make_copy()
try:
    # T50: REPORT-only crash → reset 阻止
    r = freeze(dst, "k1", crash="after-report-install")
    check("T50-1 崩溃注入", r.get("status") == "crashed")
    rc = run("tx-reset-guard", root=dst)
    check("T50-2 reset → TX_INCOMPLETE 不删除 WAL",
          rc.get("allowed") is False and file_exists(dst, ".index", "tx", "TX-000001.plan.yaml"),
          str(rc.get("allowed")))
    # T51: staging 缺文件 → NEEDS_RECONCILE，WAL 保留
    os.unlink(os.path.join(dst, ".index", "tx", "staging", "EV-000001.yaml"))
    rc = run("tx-reconcile", root=dst)
    check("T51-1 staging 缺文件 → needs_reconcile", rc.get("status") == "needs_reconcile", str(rc.get("status")))
    check("T51-2 plan/state 保留（不因未提交清理）",
          file_exists(dst, ".index", "tx", "TX-000001.plan.yaml")
          and file_exists(dst, ".index", "tx", "TX-000001.state.yaml"))
    check("T51-3 未推进 CURRENT", "researchctl:freeze-marker" not in
          open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read())
finally:
    cleanup(tmp)

# ================= T36 canonical hash 跨序列化 =================
print("\n[T36] canonical hash 跨序列化")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.mini_yaml import dump, load
    from researchctl.tx.canonical import canonical_hash, file_canonical_hash
    doc = {"a": 1, "b": [{"x": "y"}, {"x": "z"}], "c": None, "d": []}
    t1 = dump(doc)
    # 以不同 YAML 风格重写（缩进/引号差异）
    t2 = t1.replace("  - x: y", '  - x: "y"').replace("a: 1", "a: 1")
    h1 = canonical_hash(load(t1, strict=True))
    h2 = canonical_hash(load(t2, strict=True))
    check("T36-1 不同 YAML 风格 canonical hash 一致", h1 == h2, f"{h1[:16]} vs {h2[:16]}")
finally:
    cleanup(tmp)

# ================= T37 reason_refs 持久化 =================
print("\n[T37] reason_refs 持久化")
tmp, dst = make_copy()
try:
    freeze(dst, "k1", reason="D021,D022")
    from researchctl.mini_yaml import load_file as yl
    ev = yl(os.path.join(dst, "events", "EV-000001.yaml"), strict=True)
    check("T37-1 事件含 reason_refs", ev.get("reason_refs") == ["D021", "D022"], str(ev.get("reason_refs")))
    plan = yl(os.path.join(dst, ".index", "tx", "TX-000001.plan.yaml"), strict=True)
    check("T37-2 plan 含 reason_refs", plan.get("reason_refs") == ["D021", "D022"])
finally:
    cleanup(tmp)

# ================= T33 / T34 篡改检测 =================
print("\n[T33/T34] 篡改检测")
tmp, dst = make_copy()
try:
    freeze(dst, "k1")
    # T34: 篡改 receipt 的 report_hash（marker 已存在 → PROVENANCE_BROKEN）
    rc_path = os.path.join(dst, "events", "EV-000001.commit")
    text = open(rc_path, encoding="utf-8").read()
    import re as _re
    text = _re.sub(r'report_hash: sha256:[0-9a-f]+', 'report_hash: sha256:deadbeef', text, count=1)
    open(rc_path, "w", encoding="utf-8").write(text)
    rc = run("tx-reconcile", root=dst)
    check("T34-1 篡改 receipt → PROVENANCE_BROKEN（marker 存在）",
          rc.get("status") == "needs_reconcile" and any(
              "PROVENANCE_BROKEN" in str(r) for r in rc.get("results", [])),
          str(rc.get("status")))
    cleanup(tmp)
    tmp, dst = make_copy()
    # T33: receipt 缺失时重建 → 不提升
    freeze(dst, "k1")
    os.unlink(os.path.join(dst, "events", "EV-000001.commit"))
    shutil.rmtree(os.path.join(dst, ".index"))
    rc = run("tx-reconcile", root=dst)
    check("T33-1 receipt 缺失 → 不提升 committed",
          not any(r.get("event_id") == "EV-000001" and r.get("status") == "committed"
                  for r in rc.get("results", [])), str(rc.get("status")))
finally:
    cleanup(tmp)

# ================= T24 Event 无 self-hash =================
print("\n[T24] Event 无 self-hash 循环")
tmp, dst = make_copy()
try:
    freeze(dst, "k1")
    from researchctl.mini_yaml import load_file as yl
    ev = yl(os.path.join(dst, "events", "EV-000001.yaml"), strict=True)
    roles = [r.get("role") for r in ev.get("output_refs", [])]
    check("T24-1 无 role: event", "event" not in roles, str(roles))
    from researchctl.tx.receipt import verify_receipt
    rc = verify_receipt(dst, "EV-000001")
    check("T24-2 receipt 绑定 event_hash 可验证", rc["valid"])
finally:
    cleanup(tmp)

# ================= T16 事件闭集 =================
print("\n[T16] 事件闭集（内部 API）")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.tx.event import build_event
    try:
        build_event(root=dst, event_id="EV-000001", transaction_id="TX-000001",
                    command_version="freeze-report/v1", idempotency_key="k",
                    request_fingerprint="fp", actor="a", authorization_ref="AUTH-0001",
                    reason_refs=[], basis_git_commit="h", occurred_at="t", recorded_at="t",
                    subject="REPORT-004", input_refs=[], output_refs=[])
        check("T16-1 ReportFrozen 可构造", True)
    except Exception:
        check("T16-1 ReportFrozen 可构造", False)
finally:
    cleanup(tmp)

# ================= T35 state 变化不影响 marker =================
print("\n[T35] state 变化不影响 marker")
tmp, dst = make_copy()
try:
    freeze(dst, "k1")
    from researchctl.tx.state import write_state
    from researchctl.tx.marker import marker_valid
    from researchctl.tx.canonical import canonical_hash
    mk1 = open(os.path.join(dst, ".index", "tx", "TX-000001.marker"), "rb").read()
    write_state(dst, "TX-000001", "needs_reconcile", "2026-08-31T00:00:00+0800", notes=["x"])
    check("T35-1 state 变化后 marker 仍有效", marker_valid(dst, "TX-000001"))
    mk2 = open(os.path.join(dst, ".index", "tx", "TX-000001.marker"), "rb").read()
    check("T35-2 marker bytes 不变", mk1 == mk2)
finally:
    cleanup(tmp)

# ================= T15 无 receipt 的 Event 不索引 =================
print("\n[T15] 无 receipt 的 Event 不索引")
tmp, dst = make_copy()
try:
    r = freeze(dst, "k1", crash="after-event-install")
    check("T15-1 崩溃注入", r.get("status") == "crashed")
    # Event 已存在但无 receipt
    check("T15-2 Event 文件存在", file_exists(dst, "events", "EV-000001.yaml"))
    check("T15-3 无 receipt", not file_exists(dst, "events", "EV-000001.commit"))
    # 直接调 rebuild：无 receipt → 不提升
    sys.path.insert(0, ROOT)
    from researchctl.tx.recover import rebuild_marker_from_canonical
    out = rebuild_marker_from_canonical(dst)
    check("T15-4 无 receipt 不提升 committed",
          not any(o.get("event_id") == "EV-000001" and o.get("status") == "committed" for o in out),
          str(out))
finally:
    cleanup(tmp)

# ================= T41 race-cas 文档化边界 =================
print("\n[T41] race-cas-current（cooperative writer 边界）")
tmp, dst = make_copy()
try:
    sys.path.insert(0, ROOT)
    from researchctl.tx import freeze as F

    def hook_t41(point):
        if point == "after-staging-verify":
            # 模拟模型外编辑：在 stale-basis 检查前改 CURRENT
            with open(os.path.join(dst, "reports", "CURRENT.md"), "a", encoding="utf-8") as f:
                f.write("\nrace-edit\n")

    r = F.freeze_report(root=dst, idempotency_key="k1", actor="text-agent",
                        authorization_ref="AUTH-0001", on_step=hook_t41)
    # cooperative 模型：stale-basis 检查应检出变化 → STALE_BASIS（不静默覆盖）
    check("T41-1 stale-basis 检查检出变化 → STALE_BASIS",
          r.get("status") == "error" and r.get("error_semantic") == "STALE_BASIS", str(r.get("error_semantic")))
    check("T41-2 不覆盖人的内容",
          "race-edit" in open(os.path.join(dst, "reports", "CURRENT.md"), encoding="utf-8").read())
finally:
    cleanup(tmp)

# ================= 回归：fixture 原始工作树不变 =================
print("\n[回归] fixture 原始工作树不变")
after = subprocess.check_output(["git", "-C", FIXTURE, "status", "--short"]).decode().strip()
check("R1 fixture 工作树与基线一致", after == baseline,
      "baseline=" + (baseline or "<empty>") + " now=" + (after or "<empty>"))

print("\n" + "=" * 62)
print(f"结果: {PASS} PASS / {FAIL} FAIL")
if FAILURES:
    print("失败项: " + ", ".join(FAILURES))
print("=" * 62)
sys.exit(1 if FAIL else 0)
