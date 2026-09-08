"""Pre-commit impact planning（P1-B-Contract §4.5，确定性）。

从 as-of canonical snapshot 计算 affected_entities：
  root = previous definition version
  沿 reverse dependency edges（based_on/uses/references/caused_by）求 transitive closure
  → 分类矩阵 → reason_code 映射（A. revision-change + B. lifecycle override）
  → 排序/去重 → 写入 Event（impact 在 commit 前固定，materialize 只 replay）。

INV-010 机器强制：impact 只允许 stale | needs_review | superseded，绝不允许 invalidated/fresh。
"""
from __future__ import annotations

import os
import re
from typing import Optional

from .canonical import canonical_hash

# impact 硬限制枚举（INV-010）
ALLOWED_IMPACTS = {"stale", "needs_review", "superseded"}

# reason_code 闭集
REASON_CODES = {
    "upstream_definition_changed", "active_result_bundle",
    "upstream_method_changed", "upstream_scope_changed",
    "upstream_assumption_changed", "other_upstream_change",
}

# change_type 受控 enum（§4.2，顺序即 canonical 排序）
CHANGE_TYPES = [
    "scope_change", "population_change", "measurement_change", "outcome_change",
    "threshold_change", "method_change", "assumption_change", "other_semantic",
]

# A. revision-change reason 映射（Sol rev9 P2-2 写死）
CHANGE_TYPE_TO_REASON = {
    "scope_change": "upstream_scope_changed",
    "method_change": "upstream_method_changed",
    "assumption_change": "upstream_assumption_changed",
    "population_change": "upstream_definition_changed",
    "measurement_change": "upstream_definition_changed",
    "outcome_change": "upstream_definition_changed",
    "threshold_change": "upstream_definition_changed",
    "other_semantic": "other_upstream_change",
}

# 依赖关系（provenance edges）——冻结 whitelist（Sol rev2 P1-7）：只认四个显式 relation
_DEPENDENCY_KEYS = ("based_on", "uses", "references", "caused_by")

# 非 dependency 字段但被 schema 允许提取 version ref 的容器键（仅这些，不放开任意字段）
_CONTAINER_KEYS = ("dependencies", "relations", "provenance")


def canonicalize_for_fingerprint(change_types) -> list:
    """用于 fingerprint 的 canonicalization：排序+去重，保留全部值（含未知值）。

    与 canonicalize_change_types 的区别：不过滤任何值，确保不同请求有不同的 fingerprint。
    """
    if not change_types:
        return []
    seen = set()
    out = []
    for ct in change_types:
        if ct and ct not in seen:
            out.append(ct)
            seen.add(ct)
    out.sort()
    return out


def canonicalize_change_types(change_types, strict=True) -> list:
    """change_type 集合语义：unique + 按 enum 顺序排序（§4.2）。

    strict=True：任一值不在受控 enum 中 → 抛出 ValueError("DEF_CHANGE_TYPE_INVALID")。
    strict=False：静默过滤非法值（用于 fingerprint 预计算；实际拒绝在 PRE-GATE）。
    """
    if not change_types:
        return []
    if strict:
        for ct in change_types:
            if ct not in CHANGE_TYPES:
                raise ValueError(f"DEF_CHANGE_TYPE_INVALID: '{ct}' 不在受控 enum 中")
    seen = set()
    out = []
    for ct in CHANGE_TYPES:
        if ct in change_types and ct not in seen:
            out.append(ct)
            seen.add(ct)
    return out


def _entity_refs_of(doc: dict) -> list:
    """提取文档中版本引用，只认冻结 whitelist 的显式 dependency 字段（Sol rev2 P1-7）。

    使用通用 entity-reference 解析（不限定 @vN 格式，Sol rev5 P1-1）。
    返回 [(ref, relation)]，ref 为完整 version_ref（如 H003@v1、TS-0043@r1），
    relation ∈ {based_on, uses, references, caused_by}。
    """
    def is_entity_ref(s: str) -> bool:
        """通用 entity-reference 检测：至少含一个 @ 符号（如 H003@v1, TS-0043@r1, E017@v3）。"""
        return bool(s) and "@" in s and len(s) >= 3
    refs = []

    def walk(value, parent_key=None):
        if isinstance(value, dict):
            for k, v in value.items():
                if k in _DEPENDENCY_KEYS:
                    if isinstance(v, str) and is_entity_ref(v):
                        refs.append((v, k))
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and is_entity_ref(item):
                                refs.append((item, k))
                            elif isinstance(item, dict):
                                walk(item, k)
                    elif isinstance(v, dict):
                        walk(v, k)
                elif k in _CONTAINER_KEYS and isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            for ik, iv in item.items():
                                if ik in _DEPENDENCY_KEYS and isinstance(iv, str) and is_entity_ref(iv):
                                    refs.append((iv, ik))
        elif isinstance(value, list):
            for v in value:
                walk(v, parent_key)

    walk(doc)
    return refs


def _load_entities(root: str) -> dict:
    """加载 fixture 中所有实体文档，key = (entity_id, version_ref)。"""
    from ..mini_yaml import load_file
    entities = {}
    # definitions 目录
    ddir = os.path.join(root, "definitions")
    if os.path.isdir(ddir):
        for entity in sorted(os.listdir(ddir)):
            edir = os.path.join(ddir, entity)
            if not os.path.isdir(edir):
                continue
            for fn in sorted(os.listdir(edir)):
                if not fn.endswith(".yaml") or fn == "APPROVED.yaml" or fn == "BOOTSTRAP.yaml":
                    continue
                p = os.path.join(edir, fn)
                try:
                    doc = load_file(p, strict=True) or {}
                except Exception as e:
                    # P2-2（Sol rev6）：canonical impact entity parse failure 必须 fail-closed
                    raise ValueError(f"IMPACT_INVALID: definition 解析失败 {p}: {e}")
                eid = doc.get("entity_id") or entity
                ver = doc.get("version_ref") or fn[:-5]
                entities[(eid, ver)] = {"doc": doc, "path": p}
    # runs
    rdir = os.path.join(root, "runs")
    if os.path.isdir(rdir):
        for rn in sorted(os.listdir(rdir)):
            p = os.path.join(rdir, rn, "manifest.yaml")
            if not os.path.exists(p):
                continue
            try:
                doc = load_file(p, strict=True) or {}
            except Exception as e:
                # P1-2（Sol rev7）：Run manifest 是 canonical impact entity，strict-parse 失败
                # 必须 fail-closed（IMPACT_INVALID），禁止静默从 graph 删除
                raise ValueError(f"IMPACT_INVALID: Run manifest 解析失败 {p}: {e}")
            eid = doc.get("run_id") or rn
            # 优先文档内 version_ref；无则用 run_id（canonical identity rule，非物理路径）
            ver = doc.get("version_ref") or eid
            entities[(eid, ver)] = {"doc": doc, "path": p}
    # organized 下的其他实体（实验结果/分析）
    odir = os.path.join(root, "organized")
    if os.path.isdir(odir):
        for fn in sorted(os.listdir(odir)):
            p = os.path.join(odir, fn)
            if not os.path.isfile(p):
                continue
            if not (fn.endswith(".md") or fn.endswith(".yaml")):
                continue
            try:
                doc = load_file(p, strict=True) or {}
            except Exception as e:
                # P2-2（Sol rev6）：canonical impact entity parse failure 必须 fail-closed
                raise ValueError(f"IMPACT_INVALID: organized 实体解析失败 {p}: {e}")
            eid = doc.get("entity_id") or fn.rsplit(".", 1)[0]
            # P1-2（Sol rev5）：优先文档内 version_ref（如 TS-0043@r1），
            # 绝不用带 .yaml/.md 的物理文件名冒充 semantic version_ref
            ver = doc.get("version_ref") or eid
            entities[(eid, ver)] = {"doc": doc, "path": p}
    return entities


def _is_executed_uncommitted(doc: dict) -> bool:
    """ResultBundle executed AND uncommitted 的 canonical predicate（Sol rev7 P1-1）。

    executed 由 lifecycle 表达；uncommitted 必须由独立 commitment 信号（doc.committed is not True）
    判定——lifecycle==executed 本身不等于 uncommitted。_impact_classification 与
    _lifecycle_override_reason 共用同一 predicate，防止 impact/reason 漂移。
    """
    lifecycle = str(doc.get("lifecycle") or doc.get("state") or "").strip()
    executed = lifecycle == "executed"
    uncommitted = doc.get("committed") is not True
    return executed and uncommitted


def _impact_classification(entity_key, doc: dict) -> str:
    """分类矩阵（§4.5，Sol P2-2 + rev6 P1-2 + rev7 P1-1）。

    只按 canonical entity_type × lifecycle 精确分类；绝不按 entity_id substring 猜类型
    （RUNBOOK-001 不能因含 "run" 被当 Run）。
    返回 impact 枚举或 None（不参与）。
    """
    eid, ver = entity_key
    etype = str(doc.get("entity_type") or doc.get("kind") or "").strip()
    lifecycle = str(doc.get("lifecycle") or doc.get("state") or "").strip()
    if etype == "Run":
        if lifecycle == "committed" or doc.get("committed") is True:
            return "superseded"
        return None
    if etype == "TaskSlice":
        if lifecycle != "executed":
            return "stale"
        return None
    if etype == "ResultBundle":
        if _is_executed_uncommitted(doc):
            return "needs_review"
        return None
    if etype == "Conclusion":
        return "stale"
    # ExperimentSpec / Observation / Inference / Claim 引用旧版本
    if etype in ("ExperimentSpec", "Observation", "Inference", "Claim"):
        return "stale"
    return "stale"  # 兜底（明示，不允许隐性默认）


def _lifecycle_override_reason(entity_key, doc: dict) -> Optional[str]:
    """B. lifecycle override（Sol rev9 P2-2 + rev7 P1-1）：ResultBundle executed+uncommitted
    → active_result_bundle。与 _impact_classification 共用同一 predicate。"""
    eid, ver = entity_key
    etype = str(doc.get("entity_type") or doc.get("kind") or "").strip()
    lifecycle = str(doc.get("lifecycle") or doc.get("state") or "").strip()
    if etype == "ResultBundle":
        if _is_executed_uncommitted(doc):
            return "active_result_bundle"
    return None


def compute_affected(root: str, *, definition: str, previous: str,
                     change_types: list, candidate_subject: str) -> list:
    """确定性 impact planning（§4.5 closure 规则）。

    返回 affected_entities 列表（已按 (entity_id, version_ref) 字典序排序）。
    每条：{entity_id, version_ref, impact, stale_reasons[], upstream_revision}。
    """
    entities = _load_entities(root)
    # reverse dependency graph：entity → (引用它的实体, relation)
    reverse: dict = {}  # (eid, ver) -> list of (entity_key, relation)
    for key, info in entities.items():
        doc = info["doc"]
        for ref, rel in _entity_refs_of(doc):
            ref_key = None
            # 通用 entity-reference 解析：取 @ 之前的部分作为 entity_id
            if "@" in ref:
                eid = ref.split("@", 1)[0]
                ref_key = (eid, ref)
            if ref_key in entities:
                reverse.setdefault(ref_key, []).append((key, rel))

    root_key = (definition, previous)
    # node-expansion visited：只控制 BFS 是否展开下游；不阻断 edge/reason 累积（Sol rev3 P1-5）
    expanded = set()
    queue = [root_key]
    # edge 累积：同一实体可经多条路径命中，保留全部 reason（P2-2/P2-5 多路径）
    edge_accum: dict = {}  # dependent_key -> list of relation
    while queue:
        cur = queue.pop(0)
        if cur in expanded:
            continue
        expanded.add(cur)
        for dep_entry in reverse.get(cur, []):
            dependent, relation = dep_entry
            if dependent == root_key:
                continue
            # 总是累积 edge/reason（即使 dependent 已 expanded，多路径 reason 仍保留）
            edge_accum.setdefault(dependent, []).append(relation)
            # node expansion：仅在未展开时入队（BFS 终止）
            if dependent not in expanded:
                queue.append(dependent)

    # 现在对累积到的每个依赖实体做分类与 reason 构建（确定性）
    affected = []
    for dependent, relations in edge_accum.items():
        dep_doc = entities.get(dependent, {}).get("doc", {})
        impact = _impact_classification(dependent, dep_doc)
        if impact is None:
            continue
        # 该实体经多路径命中的全部 relation 合并生成 reason
        merged = []
        for rel in sorted(set(relations)):
            merged.extend(_build_reasons(dependent, dep_doc, change_types, previous,
                                         candidate_subject, rel))
        # 去重 + 排序（(upstream_revision, canonical(change_type), reason_code, via_relation)）
        seen = set()
        uniq = []
        for r in merged:
            k = (r.get("reason_code"), r.get("via_relation"))
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        uniq.sort(key=lambda r: (candidate_subject,
                                 canonical_hash({"change_type": canonicalize_change_types(change_types)}),
                                 r.get("reason_code"), r.get("via_relation")))
        affected.append({
            "entity_id": dependent[0],
            "version_ref": dependent[1],
            "impact": impact,
            "stale_reasons": uniq,
            "upstream_revision": candidate_subject,
        })

    # 最终输出排序：按 (entity_id, version_ref) 固定字典序（canonical bytes 稳定）
    affected.sort(key=lambda a: (a["entity_id"], a["version_ref"]))
    # INV-010 硬检查
    for a in affected:
        if a["impact"] not in ALLOWED_IMPACTS:
            raise ValueError(f"IMPACT_INVALID: impact={a['impact']} 不在闭集")
    return affected


def _build_reasons(entity_key, doc: dict, change_types: list,
                   previous: str, candidate_subject: str,
                   relation: str = "uses") -> list:
    """为受影响实体构造 stale_reasons[]。

    A. revision-change 映射：每个 canonicalized change_type member → reason_code
    B. lifecycle override 命中时取代（而非追加）
    via_relation 使用真实 edge relation（Sol rev 实现复审 P1-3）。
    """
    reasons = []
    override = _lifecycle_override_reason(entity_key, doc)
    if override:
        reasons.append({"reason_code": override, "via_relation": relation})
        return reasons
    for ct in canonicalize_change_types(change_types):
        rc = CHANGE_TYPE_TO_REASON.get(ct, "other_upstream_change")
        reasons.append({"reason_code": rc, "via_relation": relation})
    if not reasons:
        reasons.append({"reason_code": "other_upstream_change", "via_relation": relation})
    return reasons


def impact_basis_digest(*, basis_git_commit: str, max_committed_event_id: str,
                        impact_algorithm_version: str) -> str:
    """impact_basis_digest = hash(basis_git_commit + committed event frontier + algorithm version)。"""
    return canonical_hash({
        "basis_git_commit": basis_git_commit,
        "max_committed_event_id": max_committed_event_id,
        "impact_algorithm_version": impact_algorithm_version,
    })


def max_committed_event_id(root: str) -> str:
    """从 canonical events 中找最大 committed event_id。

    ReportFrozen 用 verify_receipt；DefinitionRevised 用 verify_definition_receipt
    （Sol rev2 P2-2 + rev5 P2-2 closed-set：未知 event_type → needs_reconcile/空）。
    """
    from .receipt import verify_receipt, verify_definition_receipt
    edir = os.path.join(root, "events")
    if not os.path.isdir(edir):
        return ""
    best = ""
    for fn in sorted(os.listdir(edir)):
        if not fn.endswith(".yaml"):
            continue
        eid = fn[:-5]
        try:
            from ..mini_yaml import load_file
            ev = load_file(os.path.join(edir, fn), strict=True) or {}
            etype = ev.get("event_type", "")
        except Exception:
            continue
        try:
            if etype == "DefinitionRevised":
                res = verify_definition_receipt(root, eid)
            elif etype == "ReportFrozen":
                res = verify_receipt(root, eid)
            else:
                # 未知 event_type → closed-set reject（不 fallback 到 P1-A validator，Sol rev5 P2-2）
                continue
        except Exception:
            continue
        if res.get("valid") is True:
            if eid > best:
                best = eid
    return best
