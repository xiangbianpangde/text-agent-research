"""Read-only query handler for strict research-tool manifest v1.

All commands re-validate canonical files before touching the read-only DB. The
DB is only a projection and is never queried as an authority by itself.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from ..schema import QueryResult
from .research_tool import (
    LayoutError,
    Snapshot,
    STAGES,
    _span,
    error_result,
    scan,
    verified_index,
)


def _args(args, name, default=None):
    return getattr(args, name, default)


def _envelope(command, snapshot, wm, results=None, *, status="success", authority="derived",
              warnings=None, errors=None, error_semantic=None, as_of=None):
    return QueryResult(
        query_type=command, status=status, authority=authority,
        source_watermark=wm, results=results or [], warnings=warnings or [],
        errors=errors or [], error_semantic=error_semantic, as_of=as_of,
    ).to_dict()


def _run_item(run, *, kind=None, path=None, suffix=None):
    if kind is None:
        kind = "run"
    entity = f"{kind}:{run['run_key']}" + (f":{suffix}" if suffix is not None else "")
    value = {
        "entity_id": entity,
        "versioned_ref": f"{run['run_key']}@{run['run_id']}",
        "path": path,
        "content_hash": None,
        "git_commit": None,
        "section": None,
        "status": {
            "execution": run["record"]["verdict"],
            "research": ("source_review_passed" if run["review"]["status"] == "passed"
                         else "source_review_rejected" if run["review"]["status"] == "rejected"
                         else "execution_success" if run["success"] else "incomplete"),
        },
        "relation_type": None,
        "is_stale": False,
        "is_available": True,
        "topic": run["topic"],
        "topic_slug": run["topic_slug"],
        "run_id": run["run_id"],
        "verdict": run["record"]["verdict"],
        "pipeline_complete": run["record"]["pipeline_complete"],
        "started_at": run["record"]["started_at"],
        "finished_at": run["record"]["finished_at"],
        "current": run["is_current"],
        "latest_success": run["is_latest_success"],
        "report_type": run["report_type"],
        "current_run": run["current_run"],
        "review": run["review"],
    }
    return value


def _doc_item(run, kind, path, *, suffix=None, content_hash=None, relation=None, extra=None):
    item = _run_item(run, kind=kind, path=path, suffix=suffix)
    item.update({"content_hash": content_hash, "relation_type": relation})
    if extra:
        item.update(extra)
    return item


def _filter_runs(runs, topic=None):
    if topic:
        return [run for run in runs if run["topic_slug"] == topic or run["topic"] == topic]
    return list(runs)


def _resolve_current(runs, topic=None):
    selected = _filter_runs(runs, topic)
    topics = sorted({run["topic_slug"] for run in selected})
    if not topic and len(topics) != 1:
        raise LayoutError("CURRENT 需要单 topic 唯一选择，请提供 --topic", "AMBIGUOUS_VERSION")
    if not selected:
        raise LayoutError(f"topic 不存在: {topic}", "NOT_FOUND")
    current = [run for run in selected if run["is_current"]]
    if len(current) != 1:
        raise LayoutError("当前运行不存在唯一候选", "AMBIGUOUS_VERSION")
    return current[0]


def _as_of(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise LayoutError("--as-of 必须是 UTC ISO 时间", "INVALID_ARGUMENT")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LayoutError("--as-of 不是有效 UTC ISO 时间", "INVALID_ARGUMENT") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise LayoutError("--as-of 必须明确带 Z 或 +00:00", "INVALID_ARGUMENT")
    return parsed


def _topic_filter(args):
    topic = _args(args, "topic")
    if topic is not None and (not isinstance(topic, str) or not topic.strip()):
        raise LayoutError("--topic 不能为空", "INVALID_ARGUMENT")
    return topic.strip() if isinstance(topic, str) else None


def _raw_sources(run):
    result = []
    for path, source in sorted(run["raw"].items()):
        result.append(_doc_item(
            run, "raw", run["prefix"] + path, suffix=source["source_id"],
            content_hash="sha256:" + source["artifact_sha256"], relation="raw",
            extra={"source_id": source["source_id"], "locator": source["locator"],
                   "title": source.get("title", ""), "evidence_kind": source["evidence_kind"],
                   "source_tier": source["source_tier"], "body_sha256": source["body_sha256"]}))
    return result


def _all_sources(run):
    result = []
    for sid, source in sorted(run["clean"].items()):
        result.append(_doc_item(
            run, "source", run["prefix"] + source["clean_path"], suffix=sid,
            content_hash="sha256:" + source["clean_artifact_sha256"],
            relation="supports", extra={
                "source_id": sid, "locator": source["locator"], "title": source.get("title", ""),
                "evidence_kind": "body", "source_tier": source.get("source_tier", "unknown"),
                "raw_path": run["prefix"] + source["raw_path"], "body_sha256": "sha256:" + source["body_sha256"],
                "clean_artifact_sha256": "sha256:" + source["clean_artifact_sha256"],
            }))
    return result


def _selected_sources(run):
    used = {span["source_id"] for paragraph in run["report_claims"] for cid in paragraph["claim_ids"]
            for span in run["facts"][cid]["citations"]}
    return [item for item in _all_sources(run) if item.get("source_id") in used]


def _claim_items(run):
    result = []
    used = {cid for paragraph in run["report_claims"] for cid in paragraph["claim_ids"]}
    for cid in sorted(used):
        fact = run["facts"][cid]
        result.append(_doc_item(
            run, "claim", run["prefix"] + run["manifest"]["artifacts"]["knowledge"], suffix=cid,
            content_hash=None, relation="claims", extra={
                "claim_id": cid, "text": fact["text"], "citations": fact["citations"],
            }))
    return result


def _report_item(run):
    path = run["prefix"] + run["manifest"]["artifacts"]["report"]
    pin = run["manifest"]["artifact_hashes"]["report"]
    # Entity identity is stable across current/latest-success/historical views;
    # the selection is carried by report_type, not by the entity-id namespace.
    return _doc_item(run, "report", path, content_hash=pin, relation="report")


def _run_manifest_item(run):
    return _doc_item(run, "run", run["record_path"], content_hash=run["record_sha256"], relation="run_record",
                     extra={"record_path": run["record_path"], "record_sha256": run["record_sha256"],
                            "manifest_path": run["manifest_path"]})


def _validate_filter(args):
    unknown = getattr(args, "doc_type", None)
    allowed = {"run", "run_manifest", "retrieval_manifest", "report_current", "report_latest_success",
               "report_historical", "report", "source", "citation_source", "claim", "evidence_graph",
               "sources_manifest", "raw", "topic"}
    if unknown and unknown not in allowed:
        raise LayoutError(f"不支持的 research-tool doc-type: {unknown}", "INVALID_ARGUMENT")


def query(args):
    topic = _topic_filter(args)
    _validate_filter(args)
    limit = _args(args, "limit", 50)
    if type(limit) is not int or limit < 0:
        raise LayoutError("--limit 必须是非负整数", "INVALID_ARGUMENT")
    text = _args(args, "text")
    if text is not None and not isinstance(text, str):
        raise LayoutError("--text 必须是字符串", "INVALID_ARGUMENT")
    raw = bool(_args(args, "raw", False))
    entity = _args(args, "entity")
    with verified_index(args.root, args.db) as (snapshot, runs, conn, wm):
        selected = _filter_runs(runs, topic)
        rows = []
        for run in selected:
            doc_type = _args(args, "doc_type")
            if raw:
                candidates = _raw_sources(run)
            else:
                candidates = [_run_manifest_item(run)]
                if run["success"]:
                    candidates += [_report_item(run)] + _claim_items(run)
                    candidates += _selected_sources(run)
                    candidates += [_doc_item(run, "evidence_graph", run["prefix"] + run["manifest"]["artifacts"]["knowledge"],
                                             content_hash=run["manifest"]["artifact_hashes"]["knowledge"], relation="graph"),
                                   _doc_item(run, "sources_manifest", run["prefix"] + run["manifest"]["artifacts"]["sources"],
                                             content_hash=run["manifest"]["artifact_hashes"]["sources"], relation="sources")]
            if doc_type:
                if doc_type == "report":
                    candidates = [item for item in candidates if item["entity_id"].startswith(("report:",))]
                elif doc_type == "raw":
                    candidates = [item for item in (_raw_sources(run) if raw else []) if item["entity_id"].startswith("raw:")]
                elif doc_type == "topic":
                    candidates = [_doc_item(run, "topic", run["topic_path"] if "topic_path" in run else run["topic_slug"], relation="topic")]
                else:
                    aliases = {
                        "run_manifest": "run", "retrieval_manifest": "manifest",
                        "source_artifact": "raw", "sources_manifest": "sources_manifest",
                        "report_current": "report_current", "report_latest_success": "report_latest_success",
                        "report_historical": "report_historical", "evidence_graph": "evidence_graph",
                    }
                    wanted = aliases.get(doc_type, doc_type)
                    if doc_type in {"report_current", "report_latest_success", "report_historical"}:
                        candidates = [item for item in candidates
                                      if item["entity_id"].startswith("report:")
                                      and item.get("report_type") == wanted]
                    else:
                        candidates = [item for item in candidates
                                      if item["entity_id"].startswith(f"{wanted}:")
                                      or item.get("relation_type") == wanted]
            status_filter = _args(args, "status")
            if status_filter:
                candidates = [item for item in candidates if status_filter in {
                    item.get("verdict"), item.get("status", {}).get("execution"),
                    item.get("report_type"), item.get("status", {}).get("research")
                }]
            if entity:
                candidates = [item for item in candidates if entity in {item["entity_id"], item.get("path"), item.get("run_id")}
                              or item["entity_id"] == entity]
            if text:
                needle = text.casefold()
                candidates = [item for item in candidates if needle in json.dumps(item, ensure_ascii=False).casefold()]
            rows.extend(candidates)
        if entity == "CURRENT":
            current = _resolve_current(selected, topic)
            required_review = _args(args, "require_review")
            if required_review:
                approved = (current["success"] and current["review"].get("status") == "passed"
                            and current["review"].get("level") == required_review)
                if not approved:
                    return _envelope("current", snapshot, wm, status="fail_closed", authority="unresolved",
                                     errors=[{"code": "REVIEW_REQUIRED", "detail": "当前精确报告未通过指定审校；禁止回退旧success"}],
                                     error_semantic="REVIEW_REQUIRED")
            if current["success"]:
                rows = [_report_item(current)]
            else:
                latest = next((run for run in selected if run["is_latest_success"]), None)
                rows = [_report_item(latest)] if latest is not None else []
            if not rows:
                return _envelope("current", snapshot, wm, status="fail_closed", authority="unresolved",
                                 errors=[{"code": "SOURCE_UNAVAILABLE", "detail": "当前运行失败且没有可返回的 latest_success"}],
                                 error_semantic="SOURCE_UNAVAILABLE")
        if entity and not rows:
            return _envelope("current", snapshot, wm, status="error", authority="unresolved",
                             errors=[{"code": "NOT_FOUND", "detail": f"实体不存在: {entity}"}], error_semantic="NOT_FOUND")
        required_review = _args(args, "require_review")
        if required_review and entity != "CURRENT":
            rows = [item for item in rows if item["entity_id"].startswith("report:")
                    and item.get("current") is True
                    and item.get("verdict") == "STOP_SUCCESS"
                    and item.get("review", {}).get("status") == "passed"
                    and item.get("review", {}).get("level") == required_review]
            if not rows:
                return _envelope("current", snapshot, wm, status="fail_closed", authority="unresolved",
                                 errors=[{"code": "REVIEW_REQUIRED", "detail": "无满足审校级别的精确报告"}],
                                 error_semantic="REVIEW_REQUIRED")
        rows.sort(key=lambda item: (item.get("topic_slug", ""), item.get("finished_at", ""), item["entity_id"]))
        return _envelope("current", snapshot, wm, rows[:limit])


def sources(args):
    owner = _args(args, "owner")
    topic = _topic_filter(args)
    if not isinstance(owner, str) or not owner:
        raise LayoutError("sources 需要 owner", "INVALID_ARGUMENT")
    with verified_index(args.root, args.db) as (snapshot, runs, conn, wm):
        selected = _filter_runs(runs, topic)
        matches = []
        for run in selected:
            if owner == "CURRENT":
                if run["is_current"]:
                    matches.append(run)
            elif owner in {f"report:{run['run_key']}", f"run:{run['run_key']}", run["run_id"], run["record_path"]}:
                matches.append(run)
        if not matches:
            return _envelope("sources", snapshot, wm, status="error", authority="unresolved",
                             errors=[{"code": "NOT_FOUND", "detail": f"owner 不存在或没有正文引用: {owner}"}], error_semantic="NOT_FOUND")
        if len(matches) != 1:
            raise LayoutError("owner 跨 topic/run 不唯一", "AMBIGUOUS_VERSION")
        run = matches[0]
        if not run["success"]:
            return _envelope("sources", snapshot, wm, status="fail_closed", authority="unresolved",
                             errors=[{"code": "SOURCE_UNAVAILABLE", "detail": "当前运行没有 final/citation_sources 正文来源"}], error_semantic="SOURCE_UNAVAILABLE")
        items = _selected_sources(run)
        return _envelope("sources", snapshot, wm, items, authority="canonical")


def trace(args):
    entity = _args(args, "entity")
    topic = _topic_filter(args)
    if not isinstance(entity, str) or not entity:
        raise LayoutError("trace 需要 entity", "INVALID_ARGUMENT")
    with verified_index(args.root, args.db) as (snapshot, runs, conn, wm):
        selected = _filter_runs(runs, topic)
        matches = []
        for run in selected:
            if entity == "CURRENT":
                if run["is_current"]:
                    matches.append(run)
            elif entity in {f"report:{run['run_key']}", f"run:{run['run_key']}", run["run_id"], run["record_path"]}:
                matches.append(run)
        if not matches:
            return _envelope("trace", snapshot, wm, status="error", authority="unresolved",
                             errors=[{"code": "NOT_FOUND", "detail": f"entity 不存在: {entity}"}], error_semantic="NOT_FOUND")
        if len(matches) != 1:
            raise LayoutError("trace entity 跨 topic/run 不唯一", "AMBIGUOUS_VERSION")
        run = matches[0]
        if not run["success"]:
            return _envelope("trace", snapshot, wm, status="fail_closed", authority="unresolved",
                             errors=[{"code": "SOURCE_UNAVAILABLE", "detail": "非成功运行没有可追踪报告来源"}], error_semantic="SOURCE_UNAVAILABLE")
        result = [_report_item(run)]
        for paragraph in run["report_claims"]:
            for cid in paragraph["claim_ids"]:
                fact = run["facts"][cid]
                claim = _doc_item(run, "claim", run["prefix"] + run["manifest"]["artifacts"]["knowledge"], suffix=cid,
                                  relation="claims", extra={"claim_id": cid, "text": fact["text"], "citations": fact["citations"]})
                if claim["entity_id"] not in {item["entity_id"] for item in result}:
                    result.append(claim)
                for index, span in enumerate(fact["citations"]):
                    sid = span["source_id"]
                    source = run["clean"][sid]
                    result.append(_doc_item(run, "citation", run["prefix"] + source["clean_path"], suffix=f"{cid}:{index}",
                                            relation="supported_by", extra={
                                                "claim_id": cid, "citation": span,
                                                "clean_path": run["prefix"] + source["clean_path"],
                                                "raw_path": run["prefix"] + source["raw_path"],
                                                "record_path": run["record_path"],
                                                "source_id": sid,
                                            }))
                    result.append(_doc_item(run, "source", run["prefix"] + source["clean_path"], suffix=sid,
                                            content_hash="sha256:" + source["clean_artifact_sha256"], relation="quotes",
                                            extra={"source_id": sid, "raw_path": run["prefix"] + source["raw_path"],
                                                   "body_sha256": "sha256:" + source["body_sha256"]}))
        return _envelope("trace", snapshot, wm, result, authority="canonical")


def history(args):
    topic = _topic_filter(args)
    cutoff_raw = _args(args, "as_of")
    cutoff = _as_of(cutoff_raw)
    with verified_index(args.root, args.db) as (snapshot, runs, conn, wm):
        selected = _filter_runs(runs, topic)
        rows = []
        for run in selected:
            finished = datetime.fromisoformat(run["record"]["finished_at"].replace("Z", "+00:00"))
            if cutoff is not None and finished > cutoff:
                continue
            item = _run_manifest_item(run)
            item["summary"] = {
                "verdict": run["record"]["verdict"], "pipeline_complete": run["record"]["pipeline_complete"],
                "stages_completed": run["record"]["stages_completed"], "stages_skipped": run["record"]["stages_skipped"],
                "failed_stage": run["record"]["failed_stage"], "report_type": run["report_type"],
            }
            rows.append(item)
        rows.sort(key=lambda item: (item["topic_slug"], item["finished_at"], item["run_id"]))
        return _envelope("history", snapshot, wm, rows, authority="canonical", as_of=cutoff_raw)


def impact(args):
    topic = _topic_filter(args)
    return _envelope("impact", Snapshot(args.root), {}, status="fail_closed", authority="unresolved",
                     errors=[{"code": "UNSUPPORTED_OPERATION", "detail": "research-tool v1 没有定义 impact 关系"}],
                     error_semantic="UNSUPPORTED_OPERATION")


def reconcile(args):
    with verified_index(args.root, args.db) as (snapshot, runs, conn, wm):
        return _envelope("reconcile", snapshot, wm, [{"issues": [], "issue_count": 0, "hard_fail": False}], authority="derived")


def generate_index(args):
    with verified_index(args.root, args.db) as (snapshot, runs, conn, wm):
        lines = ["# INDEX — research-tool v1", "", "> SQLite 与此页均为派生物；canonical 真源是 run-record/runtime/envelope。", ""]
        for topic in sorted({run["topic_slug"] for run in runs}):
            lines += [f"## {topic}", ""]
            for run in [r for r in runs if r["topic_slug"] == topic]:
                lines.append(f"- `{run['run_id']}` {run['record']['verdict']} `{run['report_type']}` → `{run['record_path']}`")
            lines.append("")
        content = "\n".join(lines)
        if _args(args, "write_file", True):
            path = Path(args.root) / "index" / "INDEX.md"
            # Navigation is derived, but writing it must not make canonical scan stale.
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return _envelope("status", snapshot, wm, [{"path": "index/INDEX.md", "bytes": len(content.encode())}], authority="derived")


def execute(args):
    if _args(args, "semantic", False):
        return error_result(_args(args, "command", "query"), LayoutError("research-tool layout 不支持 semantic identity/provenance", "UNSUPPORTED_OPERATION"))
    try:
        command = _args(args, "command")
        if command == "query":
            return query(args)
        if command == "sources":
            return sources(args)
        if command == "trace":
            return trace(args)
        if command == "history":
            return history(args)
        if command == "impact":
            return impact(args)
        if command == "reconcile":
            return reconcile(args)
        if command == "generate-index":
            return generate_index(args)
        raise LayoutError(f"research-tool 不支持命令: {command}", "UNSUPPORTED_OPERATION")
    except (LayoutError, OSError, UnicodeError, ValueError) as exc:
        return error_result(_args(args, "command", "query"), exc)


def dispatch(args):
    """Alias kept small for CLI and external tests."""
    return execute(args)
