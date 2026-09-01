"""崩溃恢复与 Reconcile（P1-A-Contract §5）。

- §5.2 半提交判定（immutable set step 0 + CURRENT 三态）
- §5.5 无 plan/marker 时从 canonical 重建 derived marker（四件套 a–h）
- §5.6 reconcile 扩展（半提交/绑定/孤儿）
- WAL 生命周期（不变量 D）：partial canonical + uncommitted 禁止清理 WAL
- .index reset guard（§6.2）：unresolved 存在时 TX_INCOMPLETE
"""
from __future__ import annotations

import os
import re
import time
from typing import Optional

from .canonical import canonical_hash_bytes, raw_bytes_hash
from .fs import TxError, write_atomic, install_no_clobber, cleanup_staging
from .receipt import verify_receipt, receipt_path
from .marker import build_marker, marker_path, serialize_marker, marker_valid
from .plan import load_plan, plan_path
from .state import load_state, write_state, state_path
from .materialize import replay_materialize


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


# ---- §5.5 重建 ----

def rebuild_marker_from_canonical(root: str) -> list:
    """扫描 events/EV-*.yaml，对每个事件做四件套验证（§5.5 a–h），通过则补写 derived marker。

    返回处理结果列表 [{event_id, status}]，status in committed|needs_reconcile。
    """
    from ..mini_yaml import load_file
    from .canonical import file_canonical_hash
    edir = os.path.join(root, "events")
    out = []
    if not os.path.isdir(edir):
        return out
    for fn in sorted(os.listdir(edir)):
        m = re.fullmatch(r"EV-\d{6}\.yaml", fn)
        if not m:
            continue
        eid = fn[:-5]  # EV-000001（保留前缀）
        rc = verify_receipt(root, eid)
        if not rc["valid"]:
            out.append({"event_id": eid, "status": "needs_reconcile",
                        "reason": rc["reason"]})
            continue
        # 四件套通过 → 补写 derived marker（不依赖 plan）
        ev = load_file(os.path.join(edir, fn), strict=True) or {}
        rc_doc = load_file(receipt_path(root, eid), strict=True) or {}
        output_refs_manifest = [{"role": r.get("role"), "path": r.get("path"),
                                 "content_hash": r.get("content_hash")}
                                for r in (ev.get("output_refs") or [])]
        mk = build_marker(
            transaction_id=ev.get("transaction_id", ""), event_id=eid,
            event_hash=rc["event_hash"],
            receipt_hash=file_canonical_hash(receipt_path(root, eid)),
            output_refs_manifest=output_refs_manifest,
            committed_at=rc_doc.get("committed_at", _now()),
        )
        mk_path = marker_path(root, ev.get("transaction_id", ""))
        if not os.path.exists(mk_path):
            write_atomic(mk_path, serialize_marker(mk))
            out.append({"event_id": eid, "status": "committed",
                        "detail": "marker rebuilt from canonical"})
        else:
            out.append({"event_id": eid, "status": "committed",
                        "detail": "marker already present"})
    return out


# ---- §5.2 半提交判定 ----

def _immutable_set_status(root: str, plan: dict) -> dict:
    """step 0: 校验 report/manifest/event 三个 create output（不变量 B）。

    四种情况：
      installed: target 存在且 hash 匹配
      staged:    target 缺失但 staging 副本存在（可补装）
      missing:   target 缺失且无 staging（NEEDS_RECONCILE）
      mismatch:  target 存在但 hash != plan（NEEDS_RECONCILE）
    """
    from .canonical import file_canonical_hash
    staging_dir = os.path.join(root, ".index", "tx", "staging")
    result = {}
    files = {f["role"]: f for f in plan.get("files", [])}
    # staging 文件名映射：report→REPORT-NNN.md, sources_manifest→REPORT-NNN.sources.yaml, event→EV-NNNNNN.yaml
    for role in ("report", "sources_manifest", "event"):
        f = files.get(role)
        if not f:
            result[role] = {"ok": False, "reason": "no-plan-entry"}
            continue
        target = os.path.join(root, f["path"])
        if os.path.exists(target):
            if role == "report":
                actual = raw_bytes_hash(target)
            else:
                actual = file_canonical_hash(target)
            if actual != f["content_hash"]:
                result[role] = {"ok": False, "reason": "hash-mismatch", "path": f["path"]}
            else:
                result[role] = {"ok": True, "installed": True}
        else:
            # 查找 staging 副本
            sname = None
            if role == "report":
                sname = os.path.basename(f["path"])
            elif role == "sources_manifest":
                sname = os.path.basename(f["path"])
            else:
                sname = os.path.basename(f["path"])
            sp = os.path.join(staging_dir, sname)
            if os.path.exists(sp):
                result[role] = {"ok": False, "reason": "staged", "path": f["path"],
                                "staging": sp}
            else:
                result[role] = {"ok": False, "reason": "missing", "path": f["path"]}
    return result


def _install_from_staging(root: str, plan: dict, step0: dict, actions: list) -> bool:
    """对缺失但 staging 存在的 create output 做 atomic no-clobber 补装。

    返回是否全部补装成功。任一失败 → False（保留现场）。
    """
    files = {f["role"]: f for f in plan.get("files", [])}
    ok = True
    for role, st in step0.items():
        if st.get("reason") != "staged":
            continue
        f = files.get(role)
        try:
            with open(st["staging"], "rb") as fh:
                data = fh.read()
            if not install_no_clobber(os.path.join(root, f["path"]), data):
                ok = False
                actions.append(f"staging install blocked: {role}")
                continue
            actions.append(f"{role} installed from staging")
            st["ok"] = True
            st["installed"] = True
        except OSError as e:
            ok = False
            actions.append(f"staging install error {role}: {e}")
    return ok


def _abort_precanonical(root: str, tx_id: str, actions: list) -> dict:
    """pre-canonical ABORT：尚无任何 canonical mutation，可安全清理 WAL（§1.1/§5.2 不变量 D 例外 ①）。"""
    for p in (plan_path(root, tx_id), state_path(root, tx_id)):
        if os.path.exists(p):
            os.unlink(p)
            actions.append(f"{os.path.basename(p)} removed (pre-canonical abort)")
    cleanup_staging(root)
    actions.append("staging cleaned (pre-canonical abort)")
    return {"tx_id": tx_id, "status": "aborted", "actions": actions}


def recover_tx(root: str, db_path: str, tx_id: str) -> dict:
    """对单个事务做半提交判定/恢复（§5.2）。

    返回 {"tx_id", "status": committed|needs_reconcile|aborted, "actions": [...]}
    """
    actions = []
    plan = load_plan(root, tx_id)
    if plan is None:
        # 无 plan：走 §5.5 重建
        return {"tx_id": tx_id, "status": "needs_reconcile",
                "actions": ["no-plan; use canonical rebuild"]}

    # A. receipt 存在且四件套验证通过 → committed
    from .canonical import file_canonical_hash as _fch
    ev_id = plan.get("event_id")
    rc = verify_receipt(root, ev_id) if ev_id else {"valid": False}
    if not rc["valid"] and ev_id and marker_valid(root, tx_id):
        # 事务已 committed（marker 存在）但 receipt 失效 → 篡改，fail-closed（T34），不重建
        return {"tx_id": tx_id, "status": "needs_reconcile",
                "actions": [f"PROVENANCE_BROKEN: receipt invalid after commit ({rc.get('reason')})"]}
    if rc["valid"]:
        # 验证 report/manifest 存在且 hash 匹配
        files = {f["role"]: f for f in plan.get("files", [])}
        missing = []
        for role in ("report", "sources_manifest"):
            f = files.get(role)
            if not f or not os.path.exists(os.path.join(root, f["path"])):
                missing.append(role)
                continue
            actual = (raw_bytes_hash(os.path.join(root, f["path"])) if role == "report"
                      else _fch(os.path.join(root, f["path"])))
            if actual != f["content_hash"]:
                missing.append(role)
        if missing:
            return {"tx_id": tx_id, "status": "needs_reconcile",
                    "actions": [f"missing/mismatch: {missing}"]}
        # 补 marker（幂等），不改 CURRENT → COMMITTED → replay materialize
        if not marker_valid(root, tx_id):
            rc_doc = load_state_rc(root, ev_id)
            mk = build_marker(transaction_id=tx_id, event_id=ev_id,
                              event_hash=rc["event_hash"],
                              receipt_hash=_fch(receipt_path(root, ev_id)),
                              output_refs_manifest=_out_manifest(plan),
                              committed_at=rc_doc.get("committed_at", _now()))
            write_atomic(marker_path(root, tx_id), serialize_marker(mk))
            actions.append("marker written")
        replay_materialize(root, db_path)
        write_state(root, tx_id, "committed", _now())
        cleanup_staging(root)
        actions.append("materialize replayed")
        return {"tx_id": tx_id, "status": "committed", "actions": actions}

    # B. receipt 缺失 → step 0 immutable set 完整性校验（不变量 B）
    step0 = _immutable_set_status(root, plan)
    has_canonical = any(s.get("installed") for s in step0.values())
    if not has_canonical:
        # pre-canonical：尚无任何 canonical mutation → 可安全 ABORT 清理 WAL（不变量 D 例外 ①）
        return _abort_precanonical(root, tx_id, actions)
    # 有 partial canonical output：先尝试从 staging 补装缺失的 create output
    _install_from_staging(root, plan, step0, actions)
    incomplete = [r for r, s in step0.items() if not s["ok"]]
    if incomplete:
        return {"tx_id": tx_id, "status": "needs_reconcile",
                "actions": actions + [f"immutable set incomplete: {incomplete} (WAL retained)"]}

    # 三态：before / planned-after / other
    cur_md = os.path.join(root, "reports", "CURRENT.md")
    live_md = raw_bytes_hash(cur_md)
    before = plan.get("current_before_hash", {}).get("current_md")
    planned_after = plan.get("current_after_hash", {}).get("current_md")
    cur_src = os.path.join(root, "reports", "CURRENT.sources.yaml")
    live_src = raw_bytes_hash(cur_src)
    before_src = plan.get("current_before_hash", {}).get("current_sources")

    if live_md == before and live_src == before_src:
        # case 1: CURRENT 尚未提交 → 补 CURRENT + receipt + marker
        staging_after = os.path.join(root, ".index", "tx", "staging", "CURRENT.md.after")
        if not os.path.exists(staging_after):
            return {"tx_id": tx_id, "status": "needs_reconcile",
                    "actions": ["case1 but no staging CURRENT"]}
        with open(staging_after, "rb") as f:
            write_atomic(cur_md, f.read())
        actions.append("CURRENT installed (case1)")
        _complete_receipt_marker(root, db_path, tx_id, plan, actions)
        write_state(root, tx_id, "committed", _now())
        cleanup_staging(root)
        return {"tx_id": tx_id, "status": "committed", "actions": actions}
    elif live_md == planned_after and live_src == before_src:
        # case 2: CURRENT rename 已完成 → 只补 receipt + marker，不改 CURRENT
        actions.append("CURRENT already committed (case2)")
        _complete_receipt_marker(root, db_path, tx_id, plan, actions)
        write_state(root, tx_id, "committed", _now())
        cleanup_staging(root)
        return {"tx_id": tx_id, "status": "committed", "actions": actions}
    else:
        # case 3: 人或进程已修改 → 绝不覆盖
        return {"tx_id": tx_id, "status": "needs_reconcile",
                "actions": ["case3: CURRENT modified by other; not overwritten"]}


def _complete_receipt_marker(root, db_path, tx_id, plan, actions):
    """case1/case2 共同收尾：补 receipt（幂等；损坏/无效 receipt 视同无并重建）→ 补 marker → materialize。"""
    from .receipt import build_receipt, verify_receipt as _vrc
    from .canonical import file_canonical_hash
    from ..mini_yaml import dump as _yaml_dump
    ev_id = plan.get("event_id")
    rc_path = receipt_path(root, ev_id)
    need_receipt = (not os.path.exists(rc_path)) or (not _vrc(root, ev_id)["valid"])
    if need_receipt:
        files = {f["role"]: f for f in plan.get("files", [])}
        rc = build_receipt(root, ev_id, tx_id,
                           files.get("event", {}).get("path", f"events/{ev_id}.yaml"),
                           files.get("report", {}).get("path", ""),
                           files.get("sources_manifest", {}).get("path", ""),
                           "reports/CURRENT.md", _now())
        write_atomic(rc_path, _yaml_dump(rc).encode("utf-8"))
        actions.append("receipt (re)written")
    if not marker_valid(root, tx_id):
        rc_doc = load_state_rc(root, ev_id)
        mk = build_marker(transaction_id=tx_id, event_id=ev_id,
                          event_hash=file_canonical_hash(os.path.join(root, "events", f"{ev_id}.yaml")),
                          receipt_hash=file_canonical_hash(rc_path),
                          output_refs_manifest=_out_manifest(plan),
                          committed_at=rc_doc.get("committed_at", _now()))
        write_atomic(marker_path(root, tx_id), serialize_marker(mk))
        actions.append("marker written")
    replay_materialize(root, db_path)
    actions.append("materialize replayed")


def load_state_rc(root: str, ev_id: str) -> dict:
    """读取 receipt 文档（用于 committed_at 等）。"""
    from ..mini_yaml import load_file
    p = receipt_path(root, ev_id)
    if not os.path.exists(p):
        return {}
    try:
        return load_file(p, strict=True) or {}
    except Exception:
        return {}


def _out_manifest(plan: dict) -> list:
    files = {f["role"]: f for f in plan.get("files", [])}
    out = []
    for role in ("report", "sources_manifest", "current.md"):
        f = files.get(role)
        if f:
            out.append({"role": role, "path": f["path"],
                        "content_hash": f.get("after_hash") or f.get("content_hash")})
    return out


# ---- 顶层入口 ----

def _check_current_freeze_marker(root: str) -> Optional[dict]:
    """reconcile 检查：CURRENT 的 freeze-marker 区块与最新 committed event 一致（T29）。

    只验证最新事务；旧 Event 不受 CURRENT 影响（T32）。
    返回 issue 或 None。
    """
    from .freeze import strip_managed_region, MANAGED_START, MANAGED_END
    from ..mini_yaml import load_file as _yaml_load
    from .receipt import verify_receipt
    cur_md = os.path.join(root, "reports", "CURRENT.md")
    if not os.path.exists(cur_md):
        return None
    text = open(cur_md, encoding="utf-8").read()
    if MANAGED_START not in text:
        return None  # 无 marker 区块（未冻结过）
    # 找最新 committed event（按 subject=REPORT-NNN 最大）
    edir = os.path.join(root, "events")
    latest_ev = None
    if os.path.isdir(edir):
        for fn in sorted(os.listdir(edir)):
            if not fn.endswith(".yaml"):
                continue
            eid = fn[:-5]
            rc = verify_receipt(root, eid)
            if not rc["valid"]:
                continue
            try:
                ev = _yaml_load(os.path.join(edir, fn), strict=True) or {}
            except Exception:
                continue
            if latest_ev is None or (ev.get("subject") or "") > (latest_ev.get("subject") or ""):
                latest_ev = ev
    if latest_ev is None:
        return None
    subject = latest_ev.get("subject") or ""
    # 校验 CURRENT 区块含最新 subject 且结构合法
    try:
        stripped = strip_managed_region(text)
        _ = stripped
    except Exception as e:
        return {"issue": "HASH_MISMATCH", "owner": "CURRENT", "ref": "reports/CURRENT.md",
                "scope": "freeze-marker", "detail": f"freeze-marker 区块非法: {e}"}
    if f"已冻结快照：{subject}" not in text:
        return {"issue": "HASH_MISMATCH", "owner": "CURRENT", "ref": "reports/CURRENT.md",
                "scope": "freeze-marker",
                "detail": f"freeze-marker 区块与最新 committed event 不一致（期望 {subject}）"}
    return None


def reconcile_tx(root: str, db_path: str) -> dict:
    """P1-A reconcile：扫描所有事务 + canonical rebuild。

    返回 {"status", "results": [...]}
    """
    txdir = os.path.join(root, ".index", "tx")
    results = []
    status = "success"
    # 1) 有 plan 的事务
    if os.path.isdir(txdir):
        for name in sorted(os.listdir(txdir)):
            if name.endswith(".plan.yaml"):
                tx_id = name[:-len(".plan.yaml")]
                r = recover_tx(root, db_path, tx_id)
                results.append(r)
                # aborted = 干净终态（pre-canonical），不算需人工
                if r["status"] not in ("committed", "aborted"):
                    status = "needs_reconcile"
    # 2) 无 plan 但有 marker/receipt 的事务（§5.5）
    rebuilt = rebuild_marker_from_canonical(root)
    for r in rebuilt:
        results.append({"tx_id": None, **r})
        if r["status"] != "committed":
            status = "needs_reconcile"
    # 3) 检查 marker 存在但 receipt 缺失（PROVENANCE_BROKEN）
    if os.path.isdir(txdir):
        for name in sorted(os.listdir(txdir)):
            if name.endswith(".marker"):
                tx_id = name[:-len(".marker")]
                plan = load_plan(root, tx_id)
                ev_id = plan.get("event_id") if plan else None
                if ev_id and not os.path.exists(receipt_path(root, ev_id)):
                    results.append({"tx_id": tx_id, "status": "needs_reconcile",
                                    "actions": ["PROVENANCE_BROKEN: marker without receipt"]})
                    status = "needs_reconcile"

    # 5) 检查 CURRENT 的 freeze-marker 区块与最新 committed event 一致（T29）
    fm_issue = _check_current_freeze_marker(root)
    if fm_issue:
        results.append({"tx_id": None, "event_id": "CURRENT", "status": "needs_reconcile",
                        "actions": [f"{fm_issue['issue']}: {fm_issue['detail']}"]})
        status = "needs_reconcile"

    return {"status": status, "results": results}


def reset_index_guard(root: str, db_path: str) -> dict:
    """§6.2 .index reset guard：存在 unresolved → TX_INCOMPLETE，不删除 WAL。

    返回 {"allowed": bool, "error_semantic": ...}
    """
    from .fs import is_unresolved
    if is_unresolved(root):
        return {"allowed": False, "error_semantic": "TX_INCOMPLETE",
                "detail": "存在 unresolved WAL；禁止 .index reset（保留 recovery authority）"}
    return {"allowed": True}


# ---- P1-B DefinitionRevised 半提交恢复（§5.1/§5.2） ----

def _p1b_immutable_set_status(root: str, plan: dict) -> dict:
    """step 0（P1-B）: definition + event 两个 create output。

    返回 {role: {ok, installed?, reason, path, staging?}}。
    """
    from .canonical import file_canonical_hash
    staging_dir = os.path.join(root, ".index", "tx", "staging")
    result = {}
    files = {f["role"]: f for f in plan.get("files", [])}
    for role in ("definition", "event"):
        f = files.get(role)
        if not f:
            result[role] = {"ok": False, "reason": "no-plan-entry"}
            continue
        target = os.path.join(root, f["path"])
        if os.path.exists(target):
            actual = file_canonical_hash(target)
            if actual != f["content_hash"]:
                result[role] = {"ok": False, "reason": "hash-mismatch", "path": f["path"]}
            else:
                result[role] = {"ok": True, "installed": True}
        else:
            sname = os.path.basename(f["path"])
            sp = os.path.join(staging_dir, sname)
            if os.path.exists(sp):
                result[role] = {"ok": False, "reason": "staged", "path": f["path"],
                                "staging": sp}
            else:
                result[role] = {"ok": False, "reason": "missing", "path": f["path"]}
    return result


def _p1b_install_from_staging(root: str, plan: dict, step0: dict, actions: list) -> bool:
    """补装缺失的 definition/event（no-clobber）。"""
    files = {f["role"]: f for f in plan.get("files", [])}
    ok = True
    for role, st in step0.items():
        if st.get("reason") != "staged":
            continue
        f = files.get(role)
        try:
            with open(st["staging"], "rb") as fh:
                data = fh.read()
            if not install_no_clobber(os.path.join(root, f["path"]), data):
                ok = False
                actions.append(f"staging install blocked: {role}")
                continue
            actions.append(f"{role} installed from staging")
            st["ok"] = True
            st["installed"] = True
        except OSError as e:
            ok = False
            actions.append(f"staging install error {role}: {e}")
    return ok


def _p1b_recovery_basis_check(root: str, plan: dict) -> bool:
    """recovery basis check（§5.2 P1-2）：HEAD == plan.basis_git_commit AND
    actual previous_definition_hash == plan.definition_before_hash。"""
    import subprocess as _sp
    try:
        head = _sp.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return False
    if head != plan.get("basis_git_commit"):
        return False
    from .canonical import file_canonical_hash
    prev_path = os.path.join(root, "definitions", plan.get("definition", ""),
                             f"{plan.get('previous', '')}.yaml")
    actual = file_canonical_hash(prev_path)
    return actual == plan.get("definition_before_hash")


def recover_definition_tx(root: str, db_path: str, tx_id: str) -> dict:
    """P1-B 半提交判定（§5.2）：step 0（definition+event）→ step 1（APPROVED 三态）。"""
    from .canonical import file_canonical_hash
    from ..mini_yaml import load_file as _yaml_load
    from .receipt import verify_definition_receipt, build_definition_receipt, receipt_path as _rcpath
    from .marker import marker_valid as _mk_valid
    from .event import serialize_event
    from .plan import serialize_plan

    actions = []
    plan = load_plan(root, tx_id)
    if plan is None:
        return {"tx_id": tx_id, "status": "needs_reconcile",
                "actions": ["no-plan; use canonical rebuild"]}

    ev_id = plan.get("event_id")
    rc = verify_definition_receipt(root, ev_id) if ev_id else {"valid": False}

    # A. receipt valid → committed（补 marker + materialize）
    if rc["valid"]:
        if not _mk_valid(root, tx_id):
            from .receipt import receipt_path as _rp
            rc_doc = _yaml_load(_rp(root, ev_id), strict=True) or {}
            mk = build_marker(transaction_id=tx_id, event_id=ev_id,
                              event_hash=rc["event_hash"],
                              receipt_hash=file_canonical_hash(_rp(root, ev_id)),
                              output_refs_manifest=_out_manifest(plan),
                              committed_at=rc_doc.get("committed_at", _now()))
            write_atomic(marker_path(root, tx_id), serialize_marker(mk))
            actions.append("marker written")
        replay_materialize(root, db_path)
        write_state(root, tx_id, "committed", _now())
        cleanup_staging(root)
        actions.append("materialize replayed")
        return {"tx_id": tx_id, "status": "committed", "actions": actions}

    # B. receipt 缺失 → step 0 immutable set（definition + event）
    step0 = _p1b_immutable_set_status(root, plan)
    has_canonical = any(s.get("installed") for s in step0.values())
    if not has_canonical:
        return _abort_precanonical(root, tx_id, actions)
    _p1b_install_from_staging(root, plan, step0, actions)
    incomplete = [r for r, s in step0.items() if not s["ok"]]
    if incomplete:
        return {"tx_id": tx_id, "status": "needs_reconcile",
                "actions": actions + [f"immutable set incomplete: {incomplete} (WAL retained)"]}

    # recovery basis check（Sol rev5 P1-2）
    if not _p1b_recovery_basis_check(root, plan):
        return {"tx_id": tx_id, "status": "needs_reconcile",
                "actions": ["STALE_BASIS: HEAD != plan.basis or previous hash changed; not recovered"]}

    # step 1: APPROVED 三态
    from .definition import read_approved_hash, approved_path
    live_approved = read_approved_hash(root, plan.get("definition", ""))
    before = plan.get("approved_before_hash")
    after = plan.get("approved_after_hash")
    if live_approved == before:
        # case 1: APPROVED 未更新 → 从 staging 补 APPROVED@new → receipt → marker
        staging_after = os.path.join(root, ".index", "tx", "staging", "APPROVED.yaml.after")
        if not os.path.exists(staging_after):
            return {"tx_id": tx_id, "status": "needs_reconcile",
                    "actions": ["case1 but no staging APPROVED"]}
        with open(staging_after, "rb") as f:
            write_atomic(approved_path(root, plan.get("definition", "")), f.read())
        actions.append("APPROVED installed (case1)")
        _p1b_complete_receipt_marker(root, db_path, tx_id, plan, actions)
        write_state(root, tx_id, "committed", _now())
        cleanup_staging(root)
        return {"tx_id": tx_id, "status": "committed", "actions": actions}
    elif live_approved == after:
        # case 2: APPROVED 已更新 → 只补 receipt + marker
        actions.append("APPROVED already committed (case2)")
        _p1b_complete_receipt_marker(root, db_path, tx_id, plan, actions)
        write_state(root, tx_id, "committed", _now())
        cleanup_staging(root)
        return {"tx_id": tx_id, "status": "committed", "actions": actions}
    else:
        return {"tx_id": tx_id, "status": "needs_reconcile",
                "actions": ["case3: APPROVED modified by other; not overwritten"]}


def _p1b_complete_receipt_marker(root, db_path, tx_id, plan, actions):
    """P1-B case1/case2 收尾：补 receipt → marker → materialize。"""
    from .canonical import file_canonical_hash
    from ..mini_yaml import dump as _yaml_dump
    from ..mini_yaml import load as _yaml_load
    from .receipt import verify_definition_receipt as _vdrc, receipt_path as _rp, build_definition_receipt
    from .definition import read_approved_hash
    ev_id = plan.get("event_id")
    rc_path = _rp(root, ev_id)
    need_receipt = (not os.path.exists(rc_path)) or (not _vdrc(root, ev_id)["valid"])
    if need_receipt:
        rc = build_definition_receipt(
            event_id=ev_id, transaction_id=tx_id,
            event_hash=plan.get("event_hash") or file_canonical_hash(
                os.path.join(root, "events", f"{ev_id}.yaml")),
            definition_hash=plan.get("proposed_definition_hash", ""),
            approved_before_hash=plan.get("approved_before_hash", ""),
            approved_after_hash=plan.get("approved_after_hash", ""),
            approved_ref_after=plan.get("approved_ref_after", ""),
            committed_at=_now())
        write_atomic(rc_path, _yaml_dump(rc).encode("utf-8"))
        actions.append("receipt (re)written")
    if not marker_valid(root, tx_id):
        rc_doc = _yaml_load(rc_path, strict=True) if os.path.exists(rc_path) else {}
        mk = build_marker(transaction_id=tx_id, event_id=ev_id,
                          event_hash=file_canonical_hash(os.path.join(root, "events", f"{ev_id}.yaml")),
                          receipt_hash=file_canonical_hash(rc_path),
                          output_refs_manifest=_out_manifest(plan),
                          committed_at=rc_doc.get("committed_at", _now()))
        write_atomic(marker_path(root, tx_id), serialize_marker(mk))
        actions.append("marker written")
    replay_materialize(root, db_path)
    actions.append("materialize replayed")


def recover_tx_any(root: str, db_path: str, tx_id: str) -> dict:
    """根据 plan.command_version 分发 P1-A / P1-B 恢复。"""
    plan = load_plan(root, tx_id)
    if plan is None:
        return recover_tx(root, db_path, tx_id)
    cmd_ver = plan.get("command_version", "")
    if "revise-definition" in cmd_ver:
        return recover_definition_tx(root, db_path, tx_id)
    return recover_tx(root, db_path, tx_id)
