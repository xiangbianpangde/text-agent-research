#!/usr/bin/env python3
"""P1-B Definition Evolution 验收测试（P1-B-Contract rev11）。

运行（零第三方依赖）：
  PYTHONPATH=. python3 researchctl/tests/test_p1b.py

覆盖：U1a–U55（测试矩阵 §8.1 核心子集）+ 退出条件。
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


def make_copy():
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "f")
    shutil.copytree(FIXTURE, dst, symlinks=False,
                    ignore=shutil.ignore_patterns(".index", "*.sqlite", "__pycache__"))
    return tmp, dst


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)


def bootstrap(root, include_approval=True, approval_ref="APR-000001", **kwargs):
    """在 fixture 副本中写入 P1-B bootstrap 数据并 commit。"""
    from researchctl.tests.p1b_bootstrap import write_bootstrap
    write_bootstrap(root, include_approval=include_approval, **kwargs)
    # 添加一个引用 H003@v1 的依赖实体（供 impact closure 使用）
    _add_dependent(root)
    git_commit(root, "dependent")


def _add_dependent(root):
    """创建引用 H003@v1 的 Conclusion 实体（U37/U45/U46 用）。"""
    ddir = os.path.join(root, "organized")
    os.makedirs(ddir, exist_ok=True)
    p = os.path.join(ddir, "TS-0043.yaml")
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write("""entity_type: TaskSlice
lifecycle: not_executed
uses: H003@v1
""")


def approve_and_commit(root, ref, *, definition, previous, proposed_hash, change_type,
                       valid=True):
    """写入 approval + git commit（basis-pinned，每 revision 独立）。"""
    from researchctl.tests.p1b_bootstrap import write_approval
    write_approval(root, ref, definition=definition, previous=previous,
                   proposed_hash=proposed_hash, change_type=change_type, valid=valid)
    subprocess.run(["git", "-C", root, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", root, "commit", "-m", f"approval {ref}"], capture_output=True)


def revise(root, *, key, definition="H003", expected_previous="H003@v1",
           input_body=None, change_type="scope_change",
           actor="text-agent", auth="AUTH-0002", approval="APR-000001",
           reason="", crash=None):
    """运行 revise-definition CLI，返回 dict。"""
    from researchctl.tests.p1b_bootstrap import DEFAULT_BODY
    from researchctl.mini_yaml import dump
    if input_body is None:
        input_body = DEFAULT_BODY
    ddir = os.path.join(root, ".index", "tx", "staging_input")
    os.makedirs(ddir, exist_ok=True)
    inp_path = os.path.join(ddir, f"{key}.yaml")
    with open(inp_path, "w", encoding="utf-8") as f:
        f.write(dump(input_body) if isinstance(input_body, dict) else str(input_body))
    args = ["revise-definition", "--idempotency-key", key,
            "--definition", definition, "--expected-previous", expected_previous,
            "--definition-input", inp_path,
            "--change-type", change_type,
            "--actor", actor, "--authorization-ref", auth,
            "--approval-ref", approval]
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


def recover_tx(root, tx_id=None):
    """运行 tx-reconcile（recover_definition_tx 分发）。"""
    from researchctl.tx.recover import recover_tx_any
    return recover_tx_any(root, os.path.join(root, ".index", "research.sqlite"), tx_id)


def git_commit(root, msg="tx"):
    subprocess.run(["git", "-C", root, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", root, "commit", "-m", msg], capture_output=True)


def file_exists(root, *parts):
    return os.path.exists(os.path.join(root, *parts))


def file_content(root, *parts):
    with open(os.path.join(root, *parts), encoding="utf-8") as f:
        return f.read()


def wrap_hash_for(body=None, definition="H003", previous="H003@v1"):
    from researchctl.tests.p1b_bootstrap import wrap_hash, DEFAULT_BODY
    if body is None:
        body = DEFAULT_BODY
    return wrap_hash(definition, previous, body)


# ================= 测试入口 =================

print("=" * 62)
print("P1-B Definition Evolution 验收测试")
print("=" * 62)

# ================= U1a / U1b =================
print("\n[U1a/U1b] 正常 revision — canonical commit")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    r = revise(dst, key="u1a")
    check("U1a-1 success", r.get("status") == "success", str(r.get("status")))
    check("U1a-2 event_id=EV-000001", r.get("event_id") == "EV-000001", str(r.get("event_id")))
    check("U1a-3 subject=H003@v2", r.get("subject") == "H003@v2", str(r.get("subject")))
    check("U1a-4 previous=H003@v1", r.get("previous") == "H003@v1", str(r.get("previous")))
    check("U1a-5 changed_fields 非空", len(r.get("changed_fields", [])) > 0)
    check("U1a-6 definition 文件存在", file_exists(dst, "definitions", "H003", "H003@v2.yaml"))
    check("U1a-7 Event 存在", file_exists(dst, "events", "EV-000001.yaml"))
    check("U1a-8 receipt 存在", file_exists(dst, "events", "EV-000001.commit"))
    check("U1a-9 APPROVED 已更新", "H003@v2" in file_content(dst, "definitions", "H003", "APPROVED.yaml"))
    check("U1a-10 marker 存在", file_exists(dst, ".index", "tx", "TX-000001.marker"))
    check("U1b-1 materialize ok", r.get("materialize", {}).get("ok") is True)
    check("U1b-2 affected_count>=0", r.get("affected_count", 0) >= 0)
    # receipt a-k
    from researchctl.tx.receipt import verify_definition_receipt
    v = verify_definition_receipt(dst, "EV-000001")
    check("U1b-3 receipt a-k 有效", v.get("valid") is True, str(v.get("reason")))
finally:
    cleanup(tmp)

# ================= U2 =================
print("\n[U2] 历史 committed 验证不比较 live APPROVED")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    revise(dst, key="u2a")
    from researchctl.tx.receipt import verify_definition_receipt
    v = verify_definition_receipt(dst, "EV-000001")
    check("U2-1 receipt 有效", v.get("valid") is True, str(v.get("reason")))
    v2 = verify_definition_receipt(dst, "EV-000001")
    check("U2-2 再次验证仍有效", v2.get("valid") is True)
finally:
    cleanup(tmp)

# ================= U3 / U4 =================
print("\n[U3/U4] 幂等性")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    r1 = revise(dst, key="u3a")
    check("U3-1 首次成功", r1.get("status") == "success")
    git_commit(dst)
    r2 = revise(dst, key="u3a")
    check("U3-2 同 key 同 fp 重放", r2.get("status") == "replay")
    r3 = revise(dst, key="u3a", input_body={"kind": "Hypothesis", "population": "other"})
    check("U4-1 异 fp 冲突", r3.get("status") == "error")
    check("U4-2 error=IDEMPOTENCY_CONFLICT", r3.get("error_semantic") == "IDEMPOTENCY_CONFLICT")
finally:
    cleanup(tmp)

# ================= U5 =================
print("\n[U5] 缺授权/批准")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    r1 = revise(dst, key="u5a", auth="")
    check("U5-1 缺 auth → AUTH_REQUIRED", r1.get("error_semantic") == "AUTH_REQUIRED")
    r2 = revise(dst, key="u5b", approval="")
    check("U5-2 缺 approval → APPROVAL_REQUIRED", r2.get("error_semantic") == "APPROVAL_REQUIRED")
finally:
    cleanup(tmp)

# ================= U6 / U7 / U8 =================
print("\n[U6/U7/U8] 定义不存在/chain CAS/版本缺失")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    r1 = revise(dst, key="u6a", definition="NONEXIST")
    check("U6-1 DEF_NOT_FOUND", r1.get("error_semantic") == "DEF_NOT_FOUND")
    r2 = revise(dst, key="u7a", expected_previous="H003@v0")
    check("U7-1 DEF_CHAIN_MISMATCH", r2.get("error_semantic") == "DEF_CHAIN_MISMATCH")
    r3 = revise(dst, key="u8a", expected_previous="H003@v0")
    check("U8-1 DEF_VERSION_MISSING", r3.get("error_semantic") in ("DEF_VERSION_MISSING", "DEF_CHAIN_MISMATCH"))
finally:
    cleanup(tmp)

# ================= U9 =================
print("\n[U9] DEF_NO_CHANGE — body 不变")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    v1 = file_content(dst, "definitions", "H003", "H003@v1.yaml")
    from researchctl.mini_yaml import load
    v1_doc = load(v1)
    v1_body = v1_doc.get("body", {})
    # approval 绑定 v1 body 的 hash（使 approval 通过，随后触发 DEF_NO_CHANGE）
    approve_and_commit(dst, "APR-000001", definition="H003", previous="H003@v1",
                       proposed_hash=wrap_hash_for(v1_body), change_type=["scope_change"])
    r = revise(dst, key="u9a", input_body=v1_body)
    check("U9-1 DEF_NO_CHANGE", r.get("error_semantic") == "DEF_NO_CHANGE")
finally:
    cleanup(tmp)

# ================= U10 =================
print("\n[U10] change_type 为空/非法")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    r1 = revise(dst, key="u10a", change_type="")
    check("U10-1 空 → DEF_SEMANTIC_CHANGE_REQUIRED",
          r1.get("error_semantic") == "DEF_SEMANTIC_CHANGE_REQUIRED")
finally:
    cleanup(tmp)

# ================= U11 =================
print("\n[U11] approval 绑定 proposed hash 不匹配")
tmp, dst = make_copy()
try:
    bootstrap(dst, proposed_hash="sha256:WRONG")
    r = revise(dst, key="u11a")
    check("U11-1 APPROVAL_BINDING_MISMATCH",
          r.get("error_semantic") == "APPROVAL_BINDING_MISMATCH", str(r.get("detail")))
finally:
    cleanup(tmp)

# ================= U12-U15 崩溃恢复 =================
print("\n[U12-U15] 崩溃恢复")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    from researchctl.tests.p1b_bootstrap import DEFAULT_BODY

    def next_body(revision):
        b = dict(DEFAULT_BODY)
        b["threshold"] = 0.95 + 0.01 * revision
        return b

    # U12: definition install 后、Event 前
    r = revise(dst, key="u12a", crash="after-definition-install")
    check("U12-1 crashed", r.get("status") == "crashed")
    rec = recover_tx(dst, "TX-000001")
    check("U12-2 recover committed", rec.get("status") == "committed", str(rec.get("status")))
    check("U12-3 Event/receipt 补齐", file_exists(dst, "events", "EV-000001.commit"))
    git_commit(dst)

    # U13: Event install 后、APPROVED 前
    body13 = next_body(2)
    approve_and_commit(dst, "APR-000002", definition="H003", previous="H003@v2",
                       proposed_hash=wrap_hash_for(body13, previous="H003@v2"),
                       change_type=["scope_change"])
    r = revise(dst, key="u13a", expected_previous="H003@v2", approval="APR-000002",
               input_body=body13, crash="after-event-install")
    check("U13-1 crashed", r.get("status") == "crashed", str(r))
    rec = recover_tx(dst, "TX-000002")
    check("U13-2 recover committed", rec.get("status") == "committed", str(rec.get("status")))
    git_commit(dst)

    # U14: APPROVED 后、receipt 前
    body14 = next_body(3)
    approve_and_commit(dst, "APR-000003", definition="H003", previous="H003@v3",
                       proposed_hash=wrap_hash_for(body14, previous="H003@v3"),
                       change_type=["scope_change"])
    r = revise(dst, key="u14a", expected_previous="H003@v3", approval="APR-000003",
               input_body=body14, crash="after-approved-update")
    check("U14-1 crashed", r.get("status") == "crashed", str(r))
    rec = recover_tx(dst, "TX-000003")
    check("U14-2 recover committed", rec.get("status") == "committed", str(rec.get("status")))
    git_commit(dst)

    # U15: receipt 后、marker 前
    body15 = next_body(4)
    approve_and_commit(dst, "APR-000004", definition="H003", previous="H003@v4",
                       proposed_hash=wrap_hash_for(body15, previous="H003@v4"),
                       change_type=["scope_change"])
    r = revise(dst, key="u15a", expected_previous="H003@v4", approval="APR-000004",
               input_body=body15, crash="after-receipt")
    check("U15-1 crashed", r.get("status") == "crashed", str(r))
    rec = recover_tx(dst, "TX-000004")
    check("U15-2 recover committed", rec.get("status") == "committed", str(rec.get("status")))
finally:
    cleanup(tmp)

# ================= U16 =================
print("\n[U16] 删除 .index/ 后重建")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    revise(dst, key="u16a")
    git_commit(dst)
    shutil.rmtree(os.path.join(dst, ".index"), ignore_errors=True)
    from researchctl.tx.receipt import verify_definition_receipt
    v = verify_definition_receipt(dst, "EV-000001")
    check("U16-1 删 .index 后 receipt 仍有效", v.get("valid") is True)
    check("U16-2 定义文件存在", file_exists(dst, "definitions", "H003", "H003@v2.yaml"))
    check("U16-3 Event 存在", file_exists(dst, "events", "EV-000001.yaml"))
finally:
    cleanup(tmp)

# ================= U25 =================
print("\n[U25] 并发 revision（第二个持锁）")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    from researchctl.tx.fs import freeze_lock
    lock = freeze_lock(dst)
    lock.acquire()
    r = revise(dst, key="u25a")
    lock.release()
    check("U25-1 TX_LOCKED", r.get("status") == "error", r.get("error_semantic", ""))
    check("U25-2 error=TX_LOCKED", r.get("error_semantic") == "TX_LOCKED")
finally:
    cleanup(tmp)

# ================= U26 =================
print("\n[U26] 工作树 dirty 时 revision")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    open(os.path.join(dst, "UNTACKED"), "w").close()
    r = revise(dst, key="u26a")
    check("U26-1 DIRTY_WORKTREE", r.get("error_semantic") == "DIRTY_WORKTREE")
finally:
    cleanup(tmp)

# ================= U42 =================
print("\n[U42] body-only payload 含 reserved key")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    r = revise(dst, key="u42a", input_body={"entity_id": "H003", "body": {"x": 1}})
    check("U42-1 DEF_PAYLOAD_MISMATCH", r.get("error_semantic") == "DEF_PAYLOAD_MISMATCH")
finally:
    cleanup(tmp)

# ================= U48 =================
print("\n[U48] identity mismatch（CLI）")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    r = revise(dst, key="u48a", definition="H004", expected_previous="H003@v1")
    check("U48-1 DEF_NOT_FOUND or DEF_IDENTITY_MISMATCH",
          r.get("error_semantic") in ("DEF_IDENTITY_MISMATCH", "DEF_NOT_FOUND"))
finally:
    cleanup(tmp)

# ================= U49 =================
print("\n[U49] change_type 数组 canonicalization")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    approve_and_commit(dst, "APR-000001", definition="H003", previous="H003@v1",
                       proposed_hash=wrap_hash_for(None), change_type=["population_change", "scope_change"])
    r1 = revise(dst, key="u49a", change_type="population_change,scope_change")
    check("U49-1 success", r1.get("status") == "success")
    from researchctl.mini_yaml import load_file
    ev = load_file(os.path.join(dst, "events", "EV-000001.yaml"), strict=True) or {}
    check("U49-2 事件含 canonicalized change_type", sorted(ev.get("change_type", [])) == ["population_change", "scope_change"])
finally:
    cleanup(tmp)

# ================= U53 =================
print("\n[U53] approval 未提交进 basis commit")
tmp, dst = make_copy()
try:
    bootstrap(dst, include_approval=False)
    # 写 approval 但不 commit（仅工作树）
    from researchctl.tests.p1b_bootstrap import write_approval
    from researchctl.mini_yaml import dump
    apdir = os.path.join(dst, ".auth", "approvals")
    os.makedirs(apdir, exist_ok=True)
    with open(os.path.join(apdir, "APR-000001.yaml"), "w", encoding="utf-8") as f:
        f.write(dump({"approval_id": "APR-000001", "definition": "H003",
                      "previous": "H003@v1", "proposed_definition_hash": "sha256:x",
                      "change_type": ["scope_change"], "approved_by": "sci", "valid": True}))
    r = revise(dst, key="u53a")
    check("U53-1 APPROVAL_BINDING_MISMATCH", r.get("error_semantic") == "APPROVAL_BINDING_MISMATCH")
finally:
    cleanup(tmp)

# ================= U55 =================
print("\n[U55] Git clean 收窄漏洞 — untracked canonical 文件禁止")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    revise(dst, key="u55a")
    # 不 commit，尝试 v2→v3 应 DIRTY_WORKTREE
    r = revise(dst, key="u55b", expected_previous="H003@v2")
    check("U55-1 DIRTY_WORKTREE", r.get("error_semantic") == "DIRTY_WORKTREE")
finally:
    cleanup(tmp)

# ================= U50 =================
print("\n[U50] staged definition identity + receipt a-k")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    from researchctl.tests.p1b_bootstrap import DEFAULT_BODY
    from researchctl.tx.revise import revise_definition
    r = revise_definition(root=dst, idempotency_key="u50a", definition="H003",
                          expected_previous="H003@v1", definition_input=DEFAULT_BODY,
                          change_type=["scope_change"], actor="text-agent",
                          authorization_ref="AUTH-0002", approval_ref="APR-000001")
    check("U50-1 正常 revision 成功", r.get("status") == "success")
    git_commit(dst)
    from researchctl.tx.receipt import verify_definition_receipt
    v = verify_definition_receipt(dst, "EV-000001")
    check("U50-2 receipt a-k 验证通过", v.get("valid") is True, str(v.get("reason")))
finally:
    cleanup(tmp)

# ================= U37 / U45 / U46 =================
print("\n[U37/U45/U46] impact reverse-edge + stale_reasons 闭集")
tmp, dst = make_copy()
try:
    bootstrap(dst)
    from researchctl.tests.p1b_bootstrap import DEFAULT_BODY
    from researchctl.tx.revise import revise_definition
    r = revise_definition(root=dst, idempotency_key="u45a", definition="H003",
                          expected_previous="H003@v1", definition_input=DEFAULT_BODY,
                          change_type=["scope_change"], actor="text-agent",
                          authorization_ref="AUTH-0002", approval_ref="APR-000001")
    from researchctl.mini_yaml import load_file
    ev = load_file(os.path.join(dst, "events", "EV-000001.yaml"), strict=True) or {}
    affected = ev.get("affected_entities", [])
    check("U37-1 依赖实体被找到（TS-0043）",
          any(a.get("entity_id") == "TS-0043" for a in affected),
          str([a.get("entity_id") for a in affected]))
    for a in affected:
        check(f"U45-2 impact 在闭集中: {a.get('impact')}",
              a.get("impact") in ("stale", "needs_review", "superseded"))
        from researchctl.tx.impact import REASON_CODES
        for rsn in a.get("stale_reasons", []):
            check(f"U45-3 reason_code 在闭集: {rsn.get('reason_code')}",
                  rsn.get("reason_code") in REASON_CODES)
    check("U46-1 有 affected 实体", len(affected) > 0)
finally:
    cleanup(tmp)

# ================= 汇总 =================
print("\n" + "=" * 62)
print(f"结果: {PASS} PASS, {FAIL} FAIL")
if FAIL:
    print("失败项:", FAILURES)
    sys.exit(1)
else:
    print("全部通过 ✅")
    sys.exit(0)