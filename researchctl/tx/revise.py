"""revise-definition 事务编排（P1-B-Contract §3.2 / §4）。

18 步固定步骤（rev11）：
  锁 → request_fingerprint → canonical idempotency lookup → unresolved 全局检查
  → 读 basis → PRE-GATE（~15 项）+ identity + chain CAS + approval + authorization
  → structural diff → impact planning → 分配 ID → plan(no-clobber)+state
  → staging → 校验 staging hash + identity → stale-basis
  → 原子 no-clobber install（definition → Event → APPROVED update）
  → receipt → marker → materialize → 释放锁
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from typing import Optional

from .canonical import canonical_hash, canonical_hash_bytes, canonical_json
from .fs import TxError, freeze_lock, install_no_clobber, is_unresolved, write_atomic, cleanup_staging
from .ids import next_event_id, next_transaction_id
from .auth import validate_authorization_scope, validate_approval_binding
from .receipt import build_definition_receipt, verify_definition_receipt
from .event import build_definition_revised_event, event_path, serialize_event
from .plan import build_definition_plan, plan_path, serialize_plan
from .state import write_state, load_state
from .marker import build_marker, marker_path, serialize_marker
from .materialize import replay_materialize
from .definition import (successor, entity_of, read_definition, read_approved,
                         read_approved_hash, definition_path, approved_path,
                         wrap_definition_input, validate_definition_identity,
                         structural_diff, get_previous_hash)
from .impact import (compute_affected, impact_basis_digest, max_committed_event_id,
                     canonicalize_change_types, canonicalize_for_fingerprint, CHANGE_TYPES)

COMMAND_VERSION = "revise-definition/v1"
SCHEMA_VERSION = 1


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _git_head(root: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError:
        raise TxError("DIRTY_WORKTREE", "无法读取 git HEAD（root 不是 git 仓库）")


def _git_clean(root: str) -> bool:
    """工作树完整 clean（§4.2，Sol rev7 P1-1）：git status --porcelain 完全为空，含 untracked canonical files。"""
    try:
        out = subprocess.check_output(
            ["git", "-C", root, "status", "--porcelain"],
            text=True).strip()
        return out == ""
    except subprocess.CalledProcessError:
        return False


def _git_show_commit(root: str, commit: str, path: str) -> Optional[bytes]:
    """git show <commit>:<path>，返回 bytes 或 None。"""
    try:
        return subprocess.check_output(
            ["git", "-C", root, "show", f"{commit}:{path}"],
            stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None


def _canonical_idempotency_lookup(root: str, key: str, fp: str) -> dict:
    """按 idempotency_key 查 canonical Event/receipt（§6.1 判定 1-4）。"""
    from .receipt import verify_definition_receipt as _verify_def_receipt
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
        rc = _verify_def_receipt(root, eid)
        if rc["valid"]:
            if ev.get("request_fingerprint") == fp:
                return {"status": "replay", "event_id": eid}
            return {"status": "conflict", "event_id": eid}
        return {"status": "incomplete", "event_id": eid}
    return {"status": "miss"}


def latest_approved_evidence(root: str, definition: str):
    """返回该定义实体最新 committed DefinitionRevised 的 receipt 证据。

    按 event_id 单调序取最大（§5.4 / Sol rev3 P2-7）。
    返回 {approved_ref_after, approved_after_hash, event_id} 或 None（无 P1-B history）。
    """
    from .receipt import verify_definition_receipt as _vdrc
    from ..mini_yaml import load_file as _yaml_load
    edir = os.path.join(root, "events")
    if not os.path.isdir(edir):
        return None
    latest = None
    for fn in sorted(os.listdir(edir)):
        m = re.fullmatch(r"EV-(\d{6})\.yaml", fn)
        if not m:
            continue
        eid = fn[:-5]
        try:
            ev = _yaml_load(os.path.join(edir, fn), strict=True) or {}
        except Exception:
            continue
        if ev.get("event_type") != "DefinitionRevised":
            continue
        if (ev.get("subject") or "").split("@")[0] != definition:
            continue
        rc = _vdrc(root, eid)
        if rc.get("valid") is not True:
            continue
        from ..mini_yaml import load_file as _yaml_load2
        rc_doc = _yaml_load2(os.path.join(edir, f"{eid}.commit"), strict=True) or {}
        latest = {
            "approved_ref_after": rc_doc.get("approved_ref_after"),
            "approved_after_hash": rc_doc.get("approved_after_hash"),
            "event_id": eid,
        }
    return latest


def _maybe_crash(crash_after: Optional[str], point: str,
                 on_step: Optional[callable] = None) -> None:
    """故障注入：on_step(point) 先执行（测试用），crash_after 命中时模拟进程崩溃。"""
    if on_step is not None:
        on_step(point)
    if crash_after and crash_after == point:
        raise SystemExit(42)


# ---- 主入口 ----

def revise_definition(*, root: str, db_path: Optional[str] = None,
                      idempotency_key: str, definition: str,
                      expected_previous: str,
                      definition_input: dict,
                      change_type: list,
                      actor: str, authorization_ref: str,
                      approval_ref: str,
                      reason_refs: Optional[list] = None,
                      crash_after: Optional[str] = None,
                      on_step: Optional[callable] = None) -> dict:
    """执行一次 revise-definition 事务（§3.2 步骤 1-18）。

    definition_input: body-only semantic payload（无 entity_id/version_ref/previous）。
    crash_after: 故障注入点（测试用）。
    on_step: 测试钩子。
    """
    reason_refs = reason_refs or []
    if db_path is None:
        db_path = os.path.join(root, ".index", "research.sqlite")

    try:
        with freeze_lock(root):
            try:
                return _revise_locked(root, db_path, idempotency_key, definition,
                                      expected_previous, definition_input, change_type,
                                      actor, authorization_ref, approval_ref,
                                      reason_refs, crash_after, on_step)
            except TxError as e:
                return {"status": "error", "error_semantic": e.semantic, "detail": str(e)}
    except TxError as e:
        return {"status": "error", "error_semantic": e.semantic, "detail": str(e)}


def _revise_locked(root, db_path, idempotency_key, definition,
                   expected_previous, definition_input, change_type,
                   actor, authorization_ref, approval_ref,
                   reason_refs, crash_after, on_step=None):
    ts0 = _now()
    # P2-1: 先做宽松 canonicalize（仅排序去重，不拒绝非法值）；
    # 非法值检测延迟到 PRE-GATE 中 DEF_NO_CHANGE 之后（合同错误优先级，Sol rev3 P2-1）
    ct_canonical = canonicalize_change_types(change_type, strict=False)
    ct_invalid = [c for c in (change_type or []) if c not in CHANGE_TYPES]

    # ---- 步骤 1: 锁已获取（with freeze_lock） ----
    _maybe_crash(crash_after, "after-lock", on_step)

    # ---- 步骤 2: candidate_subject + request_fingerprint（仅调用参数，不读 repository state） ----
    candidate_subject = successor(expected_previous)
    # 检查 body 中是否有 reserved key
    # 包装 body-only input 为 canonical 版本文件
    try:
        wrapped = wrap_definition_input(entity=definition, previous=expected_previous,
                                        subject=candidate_subject, body=definition_input)
    except ValueError as e:
        raise TxError("DEF_PAYLOAD_MISMATCH", str(e))
    proposed_definition_hash = canonical_hash(wrapped)
    fp = canonical_hash({
        "command_version": COMMAND_VERSION,
        "actor": actor,
        "authorization_ref": authorization_ref,
        "approval_ref": approval_ref,
        "reason_refs": reason_refs or [],
        "definition": definition,
        "expected_previous": expected_previous,
        "candidate_subject": candidate_subject,
        "change_type": canonical_hash({"change_type": canonicalize_for_fingerprint(change_type)}),
        "proposed_definition_hash": proposed_definition_hash,
    })
    _maybe_crash(crash_after, "after-fingerprint", on_step)

    # ---- 步骤 3: canonical idempotency lookup ----
    look = _canonical_idempotency_lookup(root, idempotency_key, fp)
    if look["status"] == "replay":
        return {"status": "replay", "event_id": look["event_id"],
                "detail": "同 key 同 fingerprint 已 committed，返回原结果"}
    if look["status"] == "conflict":
        raise TxError("IDEMPOTENCY_CONFLICT", f"同 key 不同 fingerprint（key={idempotency_key}）")
    if look["status"] == "incomplete":
        raise TxError("TX_INCOMPLETE", f"同 key 存在半提交（{look['event_id']}）")
    _maybe_crash(crash_after, "after-idempotency", on_step)

    # ---- 步骤 4: unresolved 全局检查（不变量 C） ----
    if is_unresolved(root):
        raise TxError("TX_INCOMPLETE", "存在 unresolved 事务；先清完旧事务再开新 revise-definition")
    _maybe_crash(crash_after, "after-unresolved-check", on_step)

    # ---- 步骤 5: 读 basis ----
    head = _git_head(root)
    # 5a: 读 APPROVED
    approved = read_approved(root, definition)
    if approved is None:
        raise TxError("DEF_NOT_FOUND", f"{definition} 尚无 APPROVED（P1-B 不负责 bootstrap）")
    approved_before_hash = read_approved_hash(root, definition)
    # 5b: chain CAS + identity invariant（Sol rev 实现复审 P1-1）
    if approved.get("ref") != expected_previous:
        raise TxError("DEF_CHAIN_MISMATCH",
                      f"expected_previous={expected_previous} != APPROVED.ref={approved.get('ref')}")
    if approved.get("definition") != definition:
        raise TxError("DEF_IDENTITY_MISMATCH",
                      f"APPROVED.definition={approved.get('definition')} != CLI definition={definition}")
    if entity_of(approved.get("ref", "")) != definition:
        raise TxError("DEF_IDENTITY_MISMATCH",
                      f"APPROVED.ref entity={entity_of(approved.get('ref', ''))} != CLI definition={definition}")
    # 5b2: current-pointer invariant（§5.4 / §4.2，Sol rev2 P1-1）
    #   live APPROVED.ref == latest valid committed DefinitionRevised receipt.approved_ref_after
    #   AND hash(live APPROVED) == latest receipt.approved_after_hash
    latest_pointer = latest_approved_evidence(root, definition)
    if latest_pointer is not None:
        # 存在已 committed 的 DefinitionRevised history → 校验 current-pointer invariant
        if approved.get("ref") != latest_pointer["approved_ref_after"]:
            raise TxError("DEF_POINTER_DIVERGED",
                          f"live APPROVED.ref={approved.get('ref')} != latest receipt.approved_ref_after="
                          f"{latest_pointer['approved_ref_after']}")
        if approved_before_hash != latest_pointer["approved_after_hash"]:
            raise TxError("DEF_POINTER_DIVERGED",
                          f"live APPROVED hash != latest receipt.approved_after_hash（exact pointer hash）")
    else:
        # 无 P1-B history → bootstrap baseline：验证 bootstrap APPROVED 与 external pin 一致（Sol rev3 P1-1 C）
        from .definition import verify_bootstrap_approved
        verify_bootstrap_approved(root, definition)
    # 5c: 读 predecessor
    prev_def = read_definition(root, definition, expected_previous)
    if prev_def is None:
        raise TxError("DEF_VERSION_MISSING", f"predecessor 版本文件不存在: {expected_previous}")
    prev_hash = get_previous_hash(root, definition, expected_previous)
    if prev_hash is None:
        raise TxError("DEF_VERSION_MISSING", f"无法获取 predecessor hash: {expected_previous}")
    # 5d: 检查 predecessor 在 basis commit 中（Sol rev7 P1-1）
    prev_path = f"definitions/{definition}/{expected_previous}.yaml"
    if _git_show_commit(root, head, prev_path) is None:
        raise TxError("DIRTY_WORKTREE",
                      f"predecessor {expected_previous} 不在 basis commit {head[:8]} 中")
    # 5e: 获取 committed event frontier
    frontier = max_committed_event_id(root)
    _maybe_crash(crash_after, "after-basis-read", on_step)

    # ---- 步骤 6: PRE-GATE（§4.2 顺序） ----
    # 6a: candidate_subject 路径未被占用
    cand_path = definition_path(root, definition, candidate_subject)
    if os.path.exists(cand_path):
        raise TxError("DEF_VERSION_OCCUPIED",
                      f"candidate_subject {candidate_subject} 已被占用（不跳号）")
    # 6b: 语义变化确认（DEF_NO_CHANGE）——合同优先级最高（Sol rev 实现复审 P2-1）
    changed_fields = structural_diff(prev_def, wrapped)
    if not changed_fields:
        raise TxError("DEF_NO_CHANGE",
                      "changed_fields 为空（structural_diff(previous.body, proposed.body) 无变化）")
    # 6c: change_type 非空且合法（非法值延迟到 DEF_NO_CHANGE 之后才拒绝，Sol rev3 P2-1）
    if not ct_canonical:
        raise TxError("DEF_SEMANTIC_CHANGE_REQUIRED", "change_type 为空")
    if ct_invalid:
        raise TxError("DEF_CHANGE_TYPE_INVALID",
                      f"change_type {ct_invalid} 不在受控 enum 中")
    # 6d: approval binding（approval 必须在 basis commit，§6.3）
    approval_res = validate_approval_binding(root, head, approval_ref,
                                             definition=definition,
                                             previous=expected_previous,
                                             proposed_definition_hash=proposed_definition_hash,
                                             change_type=ct_canonical)
    if not approval_res.get("ok"):
        raise TxError(approval_res.get("error_semantic", "APPROVAL_BINDING_MISMATCH"),
                      approval_res.get("detail", "approval 绑定失败"))
    approval_digest = approval_res.get("digest", "")
    # 6e: authorization
    auth_res = validate_authorization_scope(root, actor, authorization_ref, "revise-definition")
    if not auth_res.get("ok"):
        raise TxError(auth_res.get("error_semantic", "AUTH_REQUIRED"),
                      auth_res.get("detail", "授权校验失败"))
    # 6f: 工作树完整 clean（§4.2 最后）
    if not _git_clean(root):
        raise TxError("DIRTY_WORKTREE", "工作树有未提交变更（含 untracked canonical 文件）")
    _maybe_crash(crash_after, "after-pregate", on_step)

    # ---- 步骤 7: impact planning ----------------
    ibd = impact_basis_digest(basis_git_commit=head,
                              max_committed_event_id=frontier,
                              impact_algorithm_version="definition-impact/v1")
    try:
        affected = compute_affected(root, definition=definition, previous=expected_previous,
                                    change_types=ct_canonical, candidate_subject=candidate_subject)
    except ValueError as e:
        # IMPACT_INVALID（分类越界 / canonical 实体解析失败）→ fail-closed REJECT
        raise TxError("IMPACT_INVALID", str(e))
    _maybe_crash(crash_after, "after-impact", on_step)

    # ---- 步骤 8: 分配 ID ----
    event_id = next_event_id(root)
    tx_id = next_transaction_id(root)
    _maybe_crash(crash_after, "after-id-assign", on_step)

    # ---- 步骤 9: plan(no-clobber) + state ----
    from ..mini_yaml import dump as yaml_dump
    # 序列化定义版本文件
    definition_bytes = yaml_dump(wrapped).encode("utf-8")
    # Event 的 output_refs：只保留冻结 schema 的 definition（§2.2；P1-4：无 self/output refs）
    ev_out_refs = [
        {"role": "definition",
         "path": f"definitions/{definition}/{candidate_subject}.yaml",
         "content_hash": proposed_definition_hash},
    ]
    # plan files：保留全部 recovery 数据（definition/event/approved_pointer/receipt，仅 recovery 用）
    plan_out_refs = [
        {"role": "definition",
         "path": f"definitions/{definition}/{candidate_subject}.yaml",
         "content_hash": proposed_definition_hash},
        {"role": "event",
         "path": f"events/{event_id}.yaml",
         "content_hash": ""},  # 填充后更新
        {"role": "approved_pointer",
         "path": f"definitions/{definition}/APPROVED.yaml",
         "before_hash": approved_before_hash,
         "after_hash": ""},  # 填充后更新
        {"role": "receipt",
         "path": f"events/{event_id}.commit",
         "content_hash": ""},  # 提交后填充
    ]
    # 构造 input_refs
    in_refs = [
        {"role": "definition.previous",
         "path": prev_path,
         "content_hash": prev_hash,
         "reference_scope": "historical"},
    ]
    # 构造 Event（output_refs 只含 definition）
    ev = build_definition_revised_event(
        root=root, event_id=event_id, transaction_id=tx_id,
        command_version=COMMAND_VERSION, idempotency_key=idempotency_key,
        request_fingerprint=fp, actor=actor,
        authorization_ref=authorization_ref, approval_ref=approval_ref,
        approval_digest=approval_digest, reason_refs=reason_refs,
        basis_git_commit=head,
        occurred_at=ts0, recorded_at=_now(),
        subject=candidate_subject, previous=expected_previous,
        change_type=ct_canonical, changed_fields=changed_fields,
        proposed_definition_hash=proposed_definition_hash,
        impact_algorithm_version="definition-impact/v1",
        impact_basis_digest=ibd,
        approved_before_hash=approved_before_hash,
        input_refs=in_refs,
        output_refs=ev_out_refs,
        affected_entities=affected,
    )
    # 构造 APPROVED@new
    approved_new = {
        "definition": definition,
        "ref": candidate_subject,
        "approved_at": ts0,
        "basis_git_commit": head,
    }
    approved_new_bytes = yaml_dump(approved_new).encode("utf-8")
    approved_new_hash = canonical_hash(approved_new)
    plan_out_refs[2]["after_hash"] = approved_new_hash
    event_bytes = serialize_event(ev)
    event_hash = canonical_hash(ev)
    ev_final_hash = event_hash

    # plan files
    files = [
        {"role": "definition", "path": f"definitions/{definition}/{candidate_subject}.yaml",
         "action": "create", "content_hash": proposed_definition_hash},
        {"role": "event", "path": f"events/{event_id}.yaml", "action": "create",
         "content_hash": ev_final_hash},
        {"role": "approved_pointer", "path": f"definitions/{definition}/APPROVED.yaml",
         "action": "update", "before_hash": approved_before_hash, "after_hash": approved_new_hash},
        {"role": "receipt", "path": f"events/{event_id}.commit", "action": "create"},
    ]
    plan = build_definition_plan(
        transaction_id=tx_id, event_id=event_id, command_version=COMMAND_VERSION,
        idempotency_key=idempotency_key, request_fingerprint=fp,
        basis_digest=ibd, actor=actor,
        authorization_ref=authorization_ref, approval_ref=approval_ref,
        approval_digest=approval_digest, reason_refs=reason_refs,
        basis_git_commit=head, created_at=ts0,
        definition=definition, previous=expected_previous,
        proposed_definition_hash=proposed_definition_hash,
        definition_before_hash=prev_hash,
        change_type=ct_canonical, changed_fields=changed_fields,
        impact_algorithm_version="definition-impact/v1",
        impact_basis_digest=ibd,
        approved_before_hash=approved_before_hash,
        approved_ref_after=candidate_subject,
        approved_at=ts0,
        approved_after_hash=approved_new_hash,
        files=files,
    )
    if not install_no_clobber(plan_path(root, tx_id), serialize_plan(plan)):
        raise TxError("TX_INCOMPLETE", f"plan 已存在（可能覆盖旧事务 WAL）: {tx_id}")
    write_state(root, tx_id, "validated", _now())
    _maybe_crash(crash_after, "after-plan", on_step)

    # ---- 步骤 10: staging 写入 ----
    staging_dir = os.path.join(root, ".index", "tx", "staging")
    os.makedirs(staging_dir, exist_ok=True)
    staging_files = {
        "definition": (definition_bytes, f"{candidate_subject}.yaml"),
        "event": (event_bytes, f"{event_id}.yaml"),
        "approved_new": (approved_new_bytes, "APPROVED.yaml.after"),
    }
    for k, (data, name) in staging_files.items():
        write_atomic(os.path.join(staging_dir, name), data, fsync_dir=False)
    _maybe_crash(crash_after, "after-staging", on_step)

    # ---- 步骤 11: 校验 staging hash + identity 与 plan 一致 ----
    from ..mini_yaml import load as _yaml_load
    from .canonical import canonical_hash as _chash
    plan_files = {f["role"]: f for f in plan["files"]}
    expected = {
        "definition": proposed_definition_hash,
        "event": ev_final_hash,
        "approved_new": approved_new_hash,
    }
    staged_def = _yaml_load(definition_bytes.decode("utf-8"), strict=True)
    if _chash(staged_def) != expected["definition"]:
        raise TxError("HASH_MISMATCH", "staging definition hash 校验失败")
    staged_ev = _yaml_load(event_bytes.decode("utf-8"), strict=True)
    if _chash(staged_ev) != expected["event"]:
        raise TxError("HASH_MISMATCH", "staging event hash 校验失败")
    staged_app = _yaml_load(approved_new_bytes.decode("utf-8"), strict=True)
    if _chash(staged_app) != expected["approved_new"]:
        raise TxError("HASH_MISMATCH", "staging APPROVED hash 校验失败")
    # identity 校验（§2.3 j）
    try:
        validate_definition_identity(staged_def, entity=definition,
                                     expected_previous=expected_previous,
                                     candidate_subject=candidate_subject)
    except ValueError as e:
        raise TxError("DEF_IDENTITY_MISMATCH", str(e))
    _maybe_crash(crash_after, "after-staging-verify", on_step)

    # ---- 步骤 12: 最终 stale-basis 检查（HEAD / APPROVED-before / previous hash 全部未变，P2-2） ----
    head2 = _git_head(root)
    approved2_hash = read_approved_hash(root, definition)
    prev2_hash = get_previous_hash(root, definition, expected_previous)
    if head2 != head:
        raise TxError("STALE_BASIS", "HEAD 在 gate 后变化")
    if approved2_hash != approved_before_hash:
        raise TxError("STALE_BASIS", "APPROVED 在 gate 后变化")
    if prev2_hash != prev_hash:
        raise TxError("STALE_BASIS", "predecessor hash 在 gate 后变化")
    _maybe_crash(crash_after, "after-stale-basis", on_step)

    # ---- 步骤 13: 原子 no-clobber install：definition → Event ----
    if not install_no_clobber(cand_path, definition_bytes):
        raise TxError("TARGET_OCCUPIED", f"definition 目标已存在: {candidate_subject}")
    _maybe_crash(crash_after, "after-definition-install", on_step)
    ep = event_path(root, event_id)
    if not install_no_clobber(ep, event_bytes):
        raise TxError("TX_INCOMPLETE", "Event 目标被占用（已产生 canonical output）")
    _maybe_crash(crash_after, "after-event-install", on_step)

    # ---- 步骤 14: 原子替换 APPROVED.yaml（update 语义，Sol rev2 P1-9 TOCTOU 闭合） ----
    # 替换前重新 CAS：HEAD / APPROVED before hash / previous hash 全部未变（optimistic check）
    head3 = _git_head(root)
    approved3_hash = read_approved_hash(root, definition)
    prev3_hash = get_previous_hash(root, definition, expected_previous)
    if head3 != head:
        raise TxError("STALE_BASIS", "HEAD 在 install 后变化（拒绝替换 APPROVED）")
    if approved3_hash != approved_before_hash:
        raise TxError("STALE_BASIS", "APPROVED 在 install 后变化（拒绝覆盖）")
    if prev3_hash != prev_hash:
        raise TxError("STALE_BASIS", "predecessor 在 install 后变化（拒绝替换 APPROVED）")
    # 写 APPROVED@new（临时文件锁内安全）
    write_atomic(approved_path(root, definition), approved_new_bytes)
    _maybe_crash(crash_after, "after-approved-update", on_step)

    # ---- 步骤 15: receipt（= COMMITTED） ----
    from ..mini_yaml import dump as _yaml_dump
    rc = build_definition_receipt(event_id=event_id, transaction_id=tx_id,
                                  event_hash=ev_final_hash,
                                  definition_hash=proposed_definition_hash,
                                  approved_before_hash=approved_before_hash,
                                  approved_after_hash=approved_new_hash,
                                  approved_ref_after=candidate_subject,
                                  committed_at=_now())
    rc_bytes = _yaml_dump(rc).encode("utf-8")
    rc_path = os.path.join(root, "events", f"{event_id}.commit")
    if not install_no_clobber(rc_path, rc_bytes):
        raise TxError("TX_INCOMPLETE", "receipt 目标已存在")
    _maybe_crash(crash_after, "after-receipt", on_step)

    # ---- 步骤 16: marker（derived cache；只在 committed 后写） ----
    # 使用 plan files（recovery 数据全集：definition/event/approved_pointer/receipt）作为 manifest
    output_refs_manifest = [{"role": f["role"], "path": f["path"],
                             "content_hash": f.get("after_hash") or f.get("content_hash") or ""}
                            for f in files]
    mk = build_marker(transaction_id=tx_id, event_id=event_id,
                      event_hash=ev_final_hash,
                      receipt_hash=canonical_hash(rc),
                      output_refs_manifest=output_refs_manifest,
                      committed_at=rc["committed_at"])
    write_atomic(marker_path(root, tx_id), serialize_marker(mk))
    _maybe_crash(crash_after, "after-marker", on_step)

    # ---- 步骤 17: materialize ----
    try:
        mat = replay_materialize(root, db_path)
        # 也写 definition state 到 SQLite
        _materialize_definition_state(root, db_path, definition, candidate_subject, affected)
        write_state(root, tx_id, "committed", _now())
    except Exception as e:
        write_state(root, tx_id, "needs_reconcile", _now(),
                    notes=[f"materialize failed: {e}"])
        mat = {"ok": False, "last_event_id": "", "detail": str(e)}

    # 步骤 18: 释放锁（with 自动）；清理 staging
    cleanup_staging(root)

    return {
        "status": "success",
        "event_id": event_id,
        "transaction_id": tx_id,
        "definition": definition,
        "subject": candidate_subject,
        "previous": expected_previous,
        "request_fingerprint": fp,
        "changed_fields": changed_fields,
        "affected_count": len(affected),
        "materialize": mat,
    }


def _materialize_definition_state(root: str, db_path: str, entity: str,
                                   version: str, affected: list) -> None:
    """将 definition state 写入 SQLite（派生投影，可重建）。"""
    import sqlite3
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS definition_state (
          entity_id TEXT PRIMARY KEY,
          latest_approved_ref TEXT,
          updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS affected_state (
          entity_id TEXT, version_ref TEXT,
          upstream_revision TEXT,
          impact TEXT, stale_reasons TEXT,
          updated_at TEXT,
          PRIMARY KEY (entity_id, version_ref, upstream_revision)
        );
        """)
        # upsert definition_state
        conn.execute("INSERT OR REPLACE INTO definition_state(entity_id, latest_approved_ref, updated_at)"
                     " VALUES(?,?,?)", (entity, version, _now()))
        for a in affected:
            import json
            conn.execute("INSERT OR REPLACE INTO affected_state"
                         "(entity_id, version_ref, upstream_revision, impact, stale_reasons, updated_at)"
                         " VALUES(?,?,?,?,?,?)",
                         (a["entity_id"], a["version_ref"], a["upstream_revision"],
                          a["impact"], json.dumps(a.get("stale_reasons", [])), _now()))
        conn.commit()
    finally:
        conn.close()
