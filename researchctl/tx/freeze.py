"""freeze-report 事务编排（P1-A-Contract §3.2 / §4）。

固定步骤 1-17（rev11）：
  锁 → request_fingerprint → canonical idempotency lookup → unresolved 全局检查
  → 读 basis → basis_digest → PRE-GATE → 分配 ID → plan(no-clobber)+state
  → staging → 校验 → stale-basis → 原子 no-clobber install（report→manifest→event→CURRENT）
  → receipt → marker → materialize → 释放锁

不变量 A/B/C/D 全部由本模块步骤保证。
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from typing import Optional

from .canonical import canonical_hash, canonical_hash_bytes, canonical_json, raw_bytes_hash
from .fs import TxError, freeze_lock, install_no_clobber, is_unresolved, write_atomic, cleanup_staging
from .ids import next_event_id, next_report_id, next_transaction_id
from .auth import validate_authorization
from .receipt import build_receipt, verify_receipt
from .event import build_event, event_path, serialize_event
from .plan import build_plan, plan_path, serialize_plan
from .state import write_state
from .marker import build_marker, marker_path, serialize_marker
from .materialize import replay_materialize

COMMAND_VERSION = "freeze-report/v1"
SCHEMA_VERSION = 1


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _git_head(root: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError:
        raise TxError("DIRTY_WORKTREE", "无法读取 git HEAD（root 不是 git 仓库）")


def _git_clean(root: str) -> bool:
    """工作树是否无已跟踪文件的未提交变更（忽略 P1-A 基础设施未跟踪文件：
    events/、.auth/、.researchctl/、.index/）。"""
    try:
        out = subprocess.check_output(
            ["git", "-C", root, "status", "--porcelain", "--untracked-files=no"],
            text=True).strip()
        return out == ""
    except subprocess.CalledProcessError:
        return False


def request_fingerprint(*, command_version: str, actor: str, authorization_ref: str,
                        reason_refs: list) -> str:
    """请求身份（P1-1）：仅调用参数，不含任何执行后改变的 server 状态。"""
    return canonical_hash({
        "command_version": command_version,
        "actor": actor,
        "authorization_ref": authorization_ref,
        "reason_refs": reason_refs or [],
    })


def basis_digest(*, basis_git_commit: str, current_before_hash: dict, input_refs: list) -> str:
    """执行内容摘要：basis_commit + CURRENT before + sources pin。"""
    return canonical_hash({
        "basis_git_commit": basis_git_commit,
        "current_before_hash": current_before_hash,
        "input_refs": input_refs,
    })


def _read_current(root: str) -> dict:
    """读取 CURRENT.md + CURRENT.sources.yaml（存在性与 before hash）。"""
    cur_md = os.path.join(root, "reports", "CURRENT.md")
    cur_src = os.path.join(root, "reports", "CURRENT.sources.yaml")
    if not os.path.exists(cur_md):
        raise TxError("SOURCE_MISSING", "reports/CURRENT.md 不存在")
    if not os.path.exists(cur_src):
        raise TxError("SOURCE_MISSING", "reports/CURRENT.sources.yaml 不存在")
    return {
        "current_md_path": cur_md,
        "current_sources_path": cur_src,
        "current_md_before": raw_bytes_hash(cur_md),
        "current_sources_before": raw_bytes_hash(cur_src),
    }


def _read_sources(root: str) -> list:
    """解析 CURRENT.sources.yaml 的 sources 列表。"""
    from ..mini_yaml import load_file
    p = os.path.join(root, "reports", "CURRENT.sources.yaml")
    try:
        doc = load_file(p, strict=True) or {}
    except Exception as e:
        raise TxError("HASH_MISMATCH", f"CURRENT.sources.yaml 解析失败: {e}")
    if doc.get("report") not in (None, "CURRENT"):
        raise TxError("CURRENT_CONFLICT", f"CURRENT.sources.yaml report 字段冲突: {doc.get('report')}")
    if doc.get("reference_scope") not in (None, "current"):
        raise TxError("CURRENT_CONFLICT", f"CURRENT.sources.yaml reference_scope 应为 current: {doc.get('reference_scope')}")
    srcs = doc.get("sources") or []
    if not isinstance(srcs, list):
        raise TxError("HASH_MISMATCH", "CURRENT.sources.yaml sources 非列表")
    return srcs


def _verify_sources_current(root: str, srcs: list) -> None:
    """校验每个 source（current scope；继承 P0 Source Reference verifier）。"""
    from ..resolver import verify_source_ref
    for ref in srcs:
        if not isinstance(ref, dict) or not ref.get("path"):
            raise TxError("SOURCE_MISSING", f"source 缺 path: {ref}")
        v = verify_source_ref(ref, root, root)
        if v["status"] == "SOURCE_MISSING":
            raise TxError("SOURCE_MISSING", f"source 缺失: {ref.get('path')}")
        if v["status"] == "HASH_MISMATCH":
            raise TxError("HASH_MISMATCH", f"source hash 不匹配: {ref.get('path')}")


# ---- §4.3 确定性冻结变换 ----

MANAGED_START = "<!-- researchctl:freeze-marker -->"
MANAGED_END = "<!-- /researchctl:freeze-marker -->"
SEP = "---"


def strip_managed_region(text: str) -> str:
    """去除末尾唯一合法的 freeze-marker 区块（含最后一个分隔行至关闭标记）。

    允许 marker 区块后存在非空内容（T22：人工编辑 CURRENT 后追加叙事）。
    若多个 marker 区块 → 只去除最后一个。
    """
    idx = text.rfind(MANAGED_START)
    if idx == -1:
        return text
    end = text.rfind(MANAGED_END)
    if end == -1 or end < idx:
        raise TxError("HASH_MISMATCH", "CURRENT 含非法/未闭合 freeze-marker 区块")
    end += len(MANAGED_END)
    # 去除从该行之前的最后一个分隔行到关闭标记的全部字节
    head = text[:idx]
    cut = head.rfind("\n" + SEP + "\n")
    if cut != -1:
        head = head[:cut]
    head = head.rstrip()
    # 保留 marker 后内容（T22 人工编辑追加）
    tail = text[end:]
    if tail.strip():
        # 人工编辑在 marker 后追加了内容 → 拼回 narrative
        head = head + "\n" + tail.strip()
    return head


def build_current_after(current_before: str, report_id: str, ts: str, before_hash: str,
                        basis_commit: str) -> str:
    """CURRENT@new：在原叙事主体末尾追加/更新 freeze-marker 区块。"""
    stripped = strip_managed_region(current_before)
    block = (
        f"\n{SEP}\n{MANAGED_START}\n"
        f"> 已冻结快照：{report_id}（{ts}）\n"
        f"> 冻结前 hash: {before_hash}\n"
        f"> basis commit: {basis_commit[:8]}\n"
        f"本区块由 researchctl 维护；人工编辑会被 reconcile 检测\n"
        f"{MANAGED_END}\n"
    )
    return stripped + "\n" + block


def transform_historical_sources(srcs: list, basis_commit: str) -> list:
    """current source_ref → historical：reference_scope:=historical, git_commit:=basis_commit。"""
    out = []
    for ref in srcs:
        new = dict(ref)
        new["reference_scope"] = "historical"
        new["git_commit"] = basis_commit
        out.append(new)
    return out


# ---- 幂等 lookup ----

def _canonical_idempotency_lookup(root: str, key: str, fp: str) -> dict:
    """按 idempotency_key 查 canonical Event/receipt（§6.1 判定 1-4）。"""
    edir = os.path.join(root, "events")
    if not os.path.isdir(edir):
        return {"status": "miss"}
    from ..mini_yaml import load_file
    for fn in sorted(os.listdir(edir)):
        if not fn.endswith(".yaml"):
            continue
        try:
            ev = load_file(os.path.join(edir, fn), strict=True) or {}
        except Exception:
            continue
        if ev.get("idempotency_key") != key:
            continue
        eid = fn[:-5]
        rc = verify_receipt(root, eid)
        if rc["valid"]:
            if ev.get("request_fingerprint") == fp:
                return {"status": "replay", "event_id": eid}
            return {"status": "conflict", "event_id": eid}
        return {"status": "incomplete", "event_id": eid}
    return {"status": "miss"}


# ---- 主入口 ----

def freeze_report(*, root: str, db_path: Optional[str] = None,
                  idempotency_key: str, actor: str, authorization_ref: str,
                  reason_refs: Optional[list] = None,
                  crash_after: Optional[str] = None,
                  on_step: Optional[callable] = None) -> dict:
    """执行一次 freeze-report 事务（§3.2 步骤 1-17）。

    crash_after: 故障注入点（测试用）：在指定阶段后模拟进程崩溃。
    on_step: 测试钩子，在每一步执行前调用 on_step(point)。
    """
    reason_refs = reason_refs or []
    if db_path is None:
        db_path = os.path.join(root, ".index", "research.sqlite")

    try:
        with freeze_lock(root):
            try:
                return _freeze_locked(root, db_path, idempotency_key, actor,
                                      authorization_ref, reason_refs, crash_after, on_step)
            except TxError as e:
                return {"status": "error", "error_semantic": e.semantic, "detail": str(e)}
    except TxError as e:
        # 锁获取本身失败（TX_LOCKED）也在 envelope 内
        return {"status": "error", "error_semantic": e.semantic, "detail": str(e)}


def _freeze_locked(root, db_path, idempotency_key, actor, authorization_ref,
                   reason_refs, crash_after, on_step=None):
    ts0 = _now()
    # 步骤 2: request_fingerprint（仅调用参数）
    fp = request_fingerprint(command_version=COMMAND_VERSION, actor=actor,
                             authorization_ref=authorization_ref, reason_refs=reason_refs)
    # 步骤 3: canonical idempotency lookup
    look = _canonical_idempotency_lookup(root, idempotency_key, fp)
    if look["status"] == "replay":
        return {"status": "replay", "event_id": look["event_id"],
                "detail": "同 key 同 fingerprint 已 committed，返回原结果"}
    if look["status"] == "conflict":
        raise TxError("IDEMPOTENCY_CONFLICT", f"同 key 不同 fingerprint（key={idempotency_key}）")
    if look["status"] == "incomplete":
        raise TxError("TX_INCOMPLETE", f"同 key 存在半提交（{look['event_id']}）")
    # 步骤 4: unresolved 全局检查（不变量 C）
    if is_unresolved(root):
        raise TxError("TX_INCOMPLETE", "存在 unresolved 事务；先清完旧事务再开新 freeze")
    # 步骤 5: 读 basis
    head = _git_head(root)
    cur = _read_current(root)
    srcs = _read_sources(root)
    # 步骤 6: basis_digest
    input_refs = [{"role": "source", "path": r.get("path"),
                   "source_type": r.get("source_type", "file"),
                   "content_hash": r.get("content_hash"),
                   "reference_scope": "current"} for r in srcs]
    bd = basis_digest(basis_git_commit=head,
                      current_before_hash={"current_md": cur["current_md_before"],
                                           "current_sources": cur["current_sources_before"]},
                      input_refs=input_refs)

    # 步骤 7: PRE-GATE
    auth = validate_authorization(root, actor, authorization_ref)
    if not auth["ok"]:
        raise TxError(auth["error_semantic"], auth["detail"])
    _verify_sources_current(root, srcs)
    if not _git_clean(root):
        raise TxError("DIRTY_WORKTREE", "工作树有未提交变更")
    report_id = next_report_id(root)
    if os.path.exists(os.path.join(root, "reports", "history", f"{report_id}.md")):
        raise TxError("TARGET_OCCUPIED", f"目标 REPORT 号已占用: {report_id}")

    # 步骤 8: 分配 ID
    event_id = next_event_id(root)
    tx_id = next_transaction_id(root)

    # ---- 冻结内容准备 ----
    from ..mini_yaml import dump as yaml_dump
    current_before_text = open(cur["current_md_path"], encoding="utf-8").read()
    report_bytes = strip_managed_region(current_before_text).encode("utf-8")
    hist_srcs = transform_historical_sources(srcs, head)
    manifest_doc = {
        "report": report_id,
        "reference_scope": "historical",
        "frozen_at": ts0,
        "sources": hist_srcs,
    }
    manifest_bytes = yaml_dump(manifest_doc).encode("utf-8")

    current_after_text = build_current_after(current_before_text, report_id, ts0,
                                             cur["current_md_before"], head)
    current_after_bytes = current_after_text.encode("utf-8")

    out_refs = [
        {"role": "report", "path": f"reports/history/{report_id}.md",
         "content_hash": canonical_hash_bytes(report_bytes)},  # 人维护文件：原始 bytes
        {"role": "sources_manifest", "path": f"reports/history/{report_id}.sources.yaml",
         "content_hash": canonical_hash(manifest_doc)},  # 机器文件：canonical JSON
        {"role": "current.md", "path": "reports/CURRENT.md",
         "content_hash": canonical_hash_bytes(current_after_bytes)},  # 人维护文件：原始 bytes
    ]
    ev = build_event(
        root=root, event_id=event_id, transaction_id=tx_id,
        command_version=COMMAND_VERSION, idempotency_key=idempotency_key,
        request_fingerprint=fp, actor=actor, authorization_ref=authorization_ref,
        reason_refs=reason_refs, basis_git_commit=head,
        occurred_at=ts0, recorded_at=_now(), subject=report_id,
        input_refs=[{"role": "current.md", "path": "reports/CURRENT.md",
                     "content_hash": cur["current_md_before"], "reference_scope": "current"},
                    {"role": "current.sources.yaml", "path": "reports/CURRENT.sources.yaml",
                     "content_hash": cur["current_sources_before"], "reference_scope": "current"}]
                    + input_refs,
        output_refs=out_refs,
    )
    event_bytes = serialize_event(ev)

    # 步骤 9: plan(no-clobber) + state
    files = [
        {"role": "report", "path": f"reports/history/{report_id}.md", "action": "create",
         "content_hash": out_refs[0]["content_hash"]},
        {"role": "sources_manifest", "path": f"reports/history/{report_id}.sources.yaml", "action": "create",
         "content_hash": out_refs[1]["content_hash"]},
        {"role": "event", "path": f"events/{event_id}.yaml", "action": "create",
         "content_hash": canonical_hash(ev)},
        {"role": "receipt", "path": f"events/{event_id}.commit", "action": "create"},
        {"role": "current.md", "path": "reports/CURRENT.md", "action": "update",
         "before_hash": cur["current_md_before"], "after_hash": out_refs[2]["content_hash"]},
    ]
    plan = build_plan(transaction_id=tx_id, event_id=event_id, command_version=COMMAND_VERSION,
                      idempotency_key=idempotency_key, request_fingerprint=fp, basis_digest=bd,
                      actor=actor, authorization_ref=authorization_ref, reason_refs=reason_refs,
                      basis_git_commit=head, created_at=ts0,
                      current_before_hash={"current_md": cur["current_md_before"],
                                           "current_sources": cur["current_sources_before"]},
                      current_after_hash={"current_md": out_refs[2]["content_hash"]},
                      files=files)
    if not install_no_clobber(plan_path(root, tx_id), serialize_plan(plan)):
        raise TxError("TX_INCOMPLETE", f"plan 已存在（可能覆盖旧事务 WAL）: {tx_id}")
    write_state(root, tx_id, "validated", _now())
    _maybe_crash(crash_after, "after-plan", on_step)

    # 步骤 10: staging 写入
    staging_dir = os.path.join(root, ".index", "tx", "staging")
    os.makedirs(staging_dir, exist_ok=True)
    staging_files = {
        "report": (report_bytes, f"{report_id}.md"),
        "manifest": (manifest_bytes, f"{report_id}.sources.yaml"),
        "event": (event_bytes, f"{event_id}.yaml"),
        "current_after": (current_after_bytes, "CURRENT.md.after"),
    }
    for k, (data, name) in staging_files.items():
        write_atomic(os.path.join(staging_dir, name), data, fsync_dir=False)
    _maybe_crash(crash_after, "after-staging", on_step)

    # 步骤 11: 校验 staging hash 与 plan 一致（回读解析后 canonical hash）
    from ..mini_yaml import load as _yaml_load
    from .canonical import canonical_hash as _chash
    plan_files = {f["role"]: f for f in plan["files"]}
    expected = {
        "report": out_refs[0]["content_hash"],  # 人维护文件：原始 bytes
        "manifest": out_refs[1]["content_hash"],
        "event": plan_files["event"]["content_hash"],
        "current_after": out_refs[2]["content_hash"],
    }
    if canonical_hash_bytes(report_bytes) != expected["report"] or \
       _chash(_yaml_load(manifest_bytes.decode("utf-8"), strict=True)) != expected["manifest"] or \
       _chash(_yaml_load(event_bytes.decode("utf-8"), strict=True)) != expected["event"] or \
       canonical_hash_bytes(current_after_bytes) != expected["current_after"]:
        raise TxError("HASH_MISMATCH", "staging hash 校验失败")
    _maybe_crash(crash_after, "after-staging-verify", on_step)

    # 步骤 12: 最终 stale-basis 检查
    cur2 = _read_current(root)
    head2 = _git_head(root)
    if cur2["current_md_before"] != cur["current_md_before"] or \
       cur2["current_sources_before"] != cur["current_sources_before"] or head2 != head:
        raise TxError("STALE_BASIS", "CURRENT/HEAD 在 gate 后变化")

    # 步骤 13: 原子 no-clobber install：report → manifest → event → CURRENT（最后）
    rp = os.path.join(root, "reports", "history", f"{report_id}.md")
    if not install_no_clobber(rp, report_bytes):
        raise TxError("TARGET_OCCUPIED", f"REPORT 目标已存在: {report_id}")
    _maybe_crash(crash_after, "after-report-install", on_step)
    mp = os.path.join(root, "reports", "history", f"{report_id}.sources.yaml")
    if not install_no_clobber(mp, manifest_bytes):
        raise TxError("TX_INCOMPLETE", "manifest 目标被占用（已产生 canonical output）")
    _maybe_crash(crash_after, "after-manifest-install", on_step)
    ep = event_path(root, event_id)
    if not install_no_clobber(ep, event_bytes):
        raise TxError("TX_INCOMPLETE", "Event 目标被占用（已产生 canonical output）")
    _maybe_crash(crash_after, "after-event-install", on_step)
    # CURRENT 最后 rename（update 语义；cooperative writer 模型下锁内安全）
    write_atomic(cur["current_md_path"], current_after_bytes)
    _maybe_crash(crash_after, "after-current", on_step)

    # 步骤 14: receipt
    from ..mini_yaml import dump as _yaml_dump
    rc = build_receipt(root, event_id, tx_id, f"events/{event_id}.yaml",
                       f"reports/history/{report_id}.md",
                       f"reports/history/{report_id}.sources.yaml",
                       "reports/CURRENT.md", _now())
    rc_bytes = _yaml_dump(rc).encode("utf-8")
    rc_path = os.path.join(root, "events", f"{event_id}.commit")
    if not install_no_clobber(rc_path, rc_bytes):
        raise TxError("TX_INCOMPLETE", "receipt 目标已存在")
    _maybe_crash(crash_after, "after-receipt", on_step)

    # 步骤 15: marker（derived cache；只在 committed 后写）
    output_refs_manifest = [{"role": r["role"], "path": r["path"],
                             "content_hash": r["content_hash"]} for r in out_refs]
    mk = build_marker(transaction_id=tx_id, event_id=event_id,
                      event_hash=canonical_hash(ev),
                      receipt_hash=canonical_hash(rc),
                      output_refs_manifest=output_refs_manifest, committed_at=rc["committed_at"])
    write_atomic(marker_path(root, tx_id), serialize_marker(mk))
    _maybe_crash(crash_after, "after-marker", on_step)

    # 步骤 16: materialize（可重放；失败 → state=needs_reconcile，不影响 committed）
    try:
        mat = replay_materialize(root, db_path)
        write_state(root, tx_id, "committed", _now())
    except Exception as e:
        write_state(root, tx_id, "needs_reconcile", _now(),
                    notes=[f"materialize failed: {e}"])
        mat = {"ok": False, "last_event_id": "", "detail": str(e)}

    # 步骤 17: 释放锁（with 语句自动）；committed 后允许清理 staging（§1.1）
    cleanup_staging(root)

    return {
        "status": "success",
        "event_id": event_id,
        "transaction_id": tx_id,
        "report_id": report_id,
        "request_fingerprint": fp,
        "materialize": mat,
    }


def _maybe_crash(crash_after: Optional[str], point: str,
                 on_step: Optional[callable] = None) -> None:
    """故障注入：on_step(point) 先执行（测试用），crash_after 命中时模拟进程崩溃。"""
    if on_step is not None:
        on_step(point)
    if crash_after and crash_after == point:
        raise SystemExit(42)
