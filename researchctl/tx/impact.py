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

# 依赖关系（provenance edges）
_DEPENDENCY_KEYS = ("based_on", "uses", "references", "caused_by")


def canonicalize_change_types(change_types) -> list:
    """change_type 集合语义：unique + 按 enum 顺序排序（§4.2）。"""
    if not change_types:
        return []
    seen = set()
    out = []
    for ct in CHANGE_TYPES:
        if ct in change_types and ct not in seen:
            out.append(ct)
            seen.add(ct)
    return out


def _entity_refs_of(doc: dict) -> list:
    """提取文档中所有版本引用（entity@version 或 entity）。"""
    refs = []

    def walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k in _DEPENDENCY_KEYS or k in ("upstream", "references"):
                    if isinstance(v, str) and re.fullmatch(r"[A-Z][A-Za-z0-9_-]+@v\d+", v):
                        refs.append(v)
                    elif isinstance(v, (dict, list)):
                        walk(v)
                elif isinstance(v, str) and v:
                    if re.fullmatch(r"[A-Z][A-Za-z0-9_-]+@v\d+", v):
                        refs.append(v)
                elif isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

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
                if not fn.endswith(".yaml") or fn == "APPROVED.yaml":
                    continue
                p = os.path.join(edir, fn)
                try:
                    doc = load_file(p, strict=True) or {}
                except Exception:
                    continue
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
            except Exception:
                continue
            eid = doc.get("run_id") or rn
            entities[(eid, rn)] = {"doc": doc, "path": p}
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
            except Exception:
                continue
            eid = doc.get("entity_id") or fn.rsplit(".", 1)[0]
            entities[(eid, fn)] = {"doc": doc, "path": p}
    return entities


def _impact_classification(entity_key, doc: dict) -> str:
    """分类矩阵（§4.5，Sol P2-2）。返回 impact 枚举或 None（不参与）。"""
    eid, ver = entity_key
    etype = str(doc.get("entity_type") or doc.get("kind") or "")
    lifecycle = str(doc.get("lifecycle") or doc.get("state") or "")
    if etype == "Run" or "run" in eid.lower():
        if lifecycle == "committed" or doc.get("committed") is True:
            return "superseded"
        return None
    if etype == "TaskSlice" or "task" in eid.lower():
        if lifecycle != "executed":
            return "stale"
        return None
    if etype == "ResultBundle" or "result" in eid.lower():
        if lifecycle == "executed" and lifecycle != "committed":
            return "needs_review"
        return None
    if etype == "Conclusion" or "conclusion" in eid.lower():
        return "stale"
    # ExperimentSpec / Observation / Inference / Claim 引用旧版本
    if etype in ("ExperimentSpec", "Observation", "Inference", "Claim"):
        return "stale"
    return "stale"  # 兜底（明示，不允许隐性默认）


def _lifecycle_override_reason(entity_key, doc: dict) -> Optional[str]:
    """B. lifecycle override（Sol rev9 P2-2）：ResultBundle executed+uncommitted → active_result_bundle。"""
    eid, ver = entity_key
    etype = str(doc.get("entity_type") or doc.get("kind") or "")
    lifecycle = str(doc.get("lifecycle") or doc.get("state") or "")
    if etype == "ResultBundle" or "result" in eid.lower():
        if lifecycle == "executed" and lifecycle != "committed":
            return "active_result_bundle"
    return None


def compute_affected(root: str, *, definition: str, previous: str,
                     change_types: list, candidate_subject: str) -> list:
    """确定性 impact planning（§4.5 closure 规则）。

    返回 affected_entities 列表（已按 (entity_id, version_ref) 字典序排序）。
    每条：{entity_id, version_ref, impact, stale_reasons[], upstream_revision}。
    """
    entities = _load_entities(root)
    # reverse dependency graph：entity → 引用它的实体
    reverse: dict = {}  # (eid, ver) -> list of (eid2, ver2)
    for key, info in entities.items():
        doc = info["doc"]
        for ref in _entity_refs_of(doc):
            ref_key = None
            m = re.fullmatch(r"([A-Z][A-Za-z0-9_-]+)@v(\d+)", ref)
            if m:
                ref_key = (m.group(1), ref)
            if ref_key in entities:
                reverse.setdefault(ref_key, []).append(key)

    root_key = (definition, previous)
    visited = set()
    queue = [root_key]
    affected = []
    while queue:
        cur = queue.pop(0)
        if cur in visited:
            continue
        visited.add(cur)
        for dependent in reverse.get(cur, []):
            if dependent == root_key or dependent in visited:
                continue
            dep_doc = entities.get(dependent, {}).get("doc", {})
            impact = _impact_classification(dependent, dep_doc)
            if impact is None:
                continue
            # 优先级：needs_review > stale
            existing = next((a for a in affected if a["entity_id"] == dependent[0]
                             and a["version_ref"] == dependent[1]), None)
            if existing is not None:
                if impact == "needs_review":
                    existing["impact"] = "needs_review"
                # reasons 保留全部（多路径聚合）
                existing["stale_reasons"].extend(
                    _build_reasons(dependent, dep_doc, change_types, previous, candidate_subject))
                continue
            affected.append({
                "entity_id": dependent[0],
                "version_ref": dependent[1],
                "impact": impact,
                "stale_reasons": _build_reasons(dependent, dep_doc, change_types, previous, candidate_subject),
                "upstream_revision": candidate_subject,
            })
            # 继续沿 reverse edges（transitive closure）
            queue.append(dependent)

    # 去重 + reason 排序（(upstream_revision, canonical(change_type), reason_code, via_relation)）
    for a in affected:
        seen = set()
        uniq = []
        for r in a["stale_reasons"]:
            k = (r.get("reason_code"), r.get("via_relation"))
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        uniq.sort(key=lambda r: (a["upstream_revision"],
                                 canonical_hash({"change_type": canonicalize_change_types(change_types)}),
                                 r.get("reason_code"), r.get("via_relation")))
        a["stale_reasons"] = uniq

    affected.sort(key=lambda a: (a["entity_id"], a["version_ref"]))
    # INV-010 硬检查
    for a in affected:
        if a["impact"] not in ALLOWED_IMPACTS:
            raise ValueError(f"IMPACT_INVALID: impact={a['impact']} 不在闭集")
    return affected


def _build_reasons(entity_key, doc: dict, change_types: list,
                   previous: str, candidate_subject: str) -> list:
    """为受影响实体构造 stale_reasons[]。

    A. revision-change 映射：每个 canonicalized change_type member → reason_code
    B. lifecycle override 命中时取代（而非追加）
    """
    reasons = []
    override = _lifecycle_override_reason(entity_key, doc)
    if override:
        reasons.append({"reason_code": override, "via_relation": "uses"})
        return reasons
    for ct in canonicalize_change_types(change_types):
        rc = CHANGE_TYPE_TO_REASON.get(ct, "other_upstream_change")
        reasons.append({"reason_code": rc, "via_relation": "uses"})
    if not reasons:
        reasons.append({"reason_code": "other_upstream_change", "via_relation": "uses"})
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
    """从 canonical events 中找最大 committed event_id（含 receipt 验证）。"""
    from .receipt import verify_receipt
    edir = os.path.join(root, "events")
    if not os.path.isdir(edir):
        return ""
    best = ""
    for fn in sorted(os.listdir(edir)):
        if not fn.endswith(".yaml"):
            continue
        eid = fn[:-5]
        try:
            res = verify_receipt(root, eid)
        except Exception:
            continue
        if res.get("valid") is True:
            if eid > best:
                best = eid
    return best