"""Strict research-tool manifest v1 reader and rebuildable SQLite projection.

The authority is a run-record plus its runtime-pinned stage envelopes, never the
mutable topic summary or a previously built database. No legacy-format guessing.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..indexer import SCHEMA_SQL
from ..schema import QueryResult

STAGES = ("collect", "clean", "extract", "knowledge", "inspect", "targeted", "merge", "qgate", "report")
VERDICTS = {"STOP_SUCCESS", "STOP_ERROR", "STOP_BUDGET", "STOP_CANCELLED"}
DERIVED_DIRS = {".index", "index", ".git", ".researchctl"}
DERIVED_FILES = {"retrieval-index-state.json"}
HEX = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID = re.compile(r"[0-9a-f]{32}\Z")
UTC = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)\Z")
META_COMMENT = re.compile(r"^[ \t]*<!--[ \t]*([A-Za-z_]+)[ \t]*:[ \t]*(.*?)[ \t]*-->[ \t]*$")
REBUILD = "使用 research-tool producer 从 canonical run-record 重建 retrieval-manifest；没有运行快照的遗留九段运行须重跑，不能用当前 summary 回填历史。"
TABLE_COLUMNS = {
    "documents": "id,doc_type,path,version,content_hash,git_commit,status",
    "entities": "id,entity_type,path,current_version,status",
    "runs": "run_id,experiment_ref,status,model,context_length,raw_ref_path,raw_ref_hash,raw_ref_commit",
    "relations": "source,relation,target,source_path,target_path,source_version,target_version",
    "source_refs": "owner,owner_path,ref_path,source_type,reference_scope,content_hash,git_commit,section",
    "research_tool_metadata": "entity_id,data",
}


class LayoutError(ValueError):
    """A closed, machine-readable failure of the layout contract."""

    def __init__(self, detail: str, code: str = "PROVENANCE_BROKEN"):
        super().__init__(detail)
        self.code = code


def require(condition, detail, code="PROVENANCE_BROKEN"):
    if not condition:
        raise LayoutError(detail, code)


def error_result(command, exc):
    code = exc.code if isinstance(exc, LayoutError) else "SOURCE_UNAVAILABLE"
    return QueryResult(
        query_type=command, status="fail_closed", authority="unresolved", results=[],
        source_watermark={"layout": "research-tool", "drift": True},
        errors=[{"code": code, "detail": str(exc)}], error_semantic=code,
    ).to_dict()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def object_value(value, label):
    require(type(value) is dict, f"{label} 必须是 object")
    return value


def text(value, label, empty=False):
    require(type(value) is str and (empty or bool(value.strip())), f"{label} 必须是字符串")
    return value


def digest(value, label, prefixed=False):
    require(type(value) is str, f"{label} hash 类型无效")
    raw = value[7:] if prefixed and value.startswith("sha256:") else value
    require((not prefixed or value.startswith("sha256:")) and HEX.fullmatch(raw),
            f"{label} 必须是 {'sha256:' if prefixed else ''}小写64hex")
    return raw


def utc_time(value, label):
    require(type(value) is str and UTC.fullmatch(value), f"{label} 必须是明确 UTC ISO 时间", "INVALID_ARGUMENT")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LayoutError(f"{label} 时间无效", "INVALID_ARGUMENT") from exc
    require(parsed.utcoffset() == timedelta(0), f"{label} 必须为 UTC", "INVALID_ARGUMENT")
    return parsed


def relative(value):
    text(value, "path")
    require(not value.startswith("/") and "\\" not in value and "\x00" not in value
            and all(part not in ("", ".", "..") for part in value.split("/")),
            f"拒绝绝对路径或 traversal: {value}", "UNSAFE_PATH")
    require(not any(part in DERIVED_DIRS for part in value.split("/")),
            f"canonical 路径指向派生目录: {value}", "UNSAFE_PATH")
    return value


def hash_map(value, label, prefixed=False):
    object_value(value, label)
    return {relative(path): digest(pin, f"{label}.{path}", prefixed) for path, pin in value.items()}


def _json(data, label):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"{label} JSON key 重复: {key}")
            result[key] = value
        return result
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, LayoutError):
            raise
        raise LayoutError(f"{label} 不是有效 UTF-8 JSON") from exc


@contextmanager
def directory_fd(path, create=False):
    """Open every directory component with O_NOFOLLOW, including root ancestors."""
    path = Path(os.path.abspath(path))
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, dir_fd=fd)
                except FileExistsError:
                    pass
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        yield fd
    except OSError as exc:
        raise LayoutError(f"目录缺失、不安全或不可读取: {path}: {exc}", "UNSAFE_PATH") from exc
    finally:
        os.close(fd)


def _inventory(root):
    blobs, identities, directories = {}, {}, set()

    def visit(fd, prefix):
        with os.scandir(fd) as entries:
            names = sorted(entry.name for entry in entries)
        for name in names:
            path = f"{prefix}/{name}" if prefix else name
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(not stat.S_ISLNK(info.st_mode), f"拒绝 symlink: {path}", "UNSAFE_PATH")
            if stat.S_ISDIR(info.st_mode):
                if name in DERIVED_DIRS:
                    continue
                directories.add(path)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    visit(child, path)
                finally:
                    os.close(child)
            else:
                if name in DERIVED_FILES:
                    continue
                require(stat.S_ISREG(info.st_mode), f"拒绝非普通文件: {path}", "UNSAFE_PATH")
                file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                with os.fdopen(file_fd, "rb") as handle:
                    before = os.fstat(handle.fileno())
                    require(stat.S_ISREG(before.st_mode), f"拒绝非普通文件: {path}", "UNSAFE_PATH")
                    data = handle.read()
                    after = os.fstat(handle.fileno())
                token = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
                require(token(info) == token(before) == token(after), f"扫描期间文件变化: {path}", "INDEX_STALE")
                blobs[path] = data
                identities[path] = token(after)
    with directory_fd(root) as fd:
        visit(fd, "")
    return blobs, identities, directories


class Snapshot:
    """One verified byte snapshot; recheck at query/publication boundaries."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        try:
            self.blobs, self.identities, self.directories = _inventory(self.root)
        except OSError as exc:
            raise LayoutError(f"扫描失败: {exc}", "SOURCE_UNAVAILABLE") from exc
        self.fingerprint = "sha256:" + sha(json_text({
            "files": {p: sha(b) for p, b in sorted(self.blobs.items())},
            "directories": sorted(self.directories),
        }).encode())

    def bytes(self, path, pin=None):
        relative(path)
        require(path in self.blobs, f"缺失文件: {path}", "SOURCE_MISSING")
        data = self.blobs[path]
        require(pin is None or sha(data) == pin, f"hash 不匹配: {path}", "HASH_MISMATCH")
        return data

    def json(self, path, pin=None):
        return _json(self.bytes(path, pin), path)

    def unchanged(self):
        current = Snapshot(self.root)
        require(self.fingerprint == current.fingerprint and self.identities == current.identities,
                "canonical 在扫描、查询或索引发布期间变化；请重试", "INDEX_STALE")


def research_tool_fingerprint(root):
    return Snapshot(root).fingerprint


def source_body(data, label):
    """Producer's Markdown body convention (leading comments or YAML metadata)."""
    try:
        markdown = data.decode("utf-8")
    except UnicodeError as exc:
        raise LayoutError(f"来源不是 UTF-8: {label}") from exc
    metadata, position = {}, 0
    if markdown.startswith("---"):
        end = markdown.find("\n---", 3)
        require(end >= 0, f"来源 front matter 不完整: {label}")
        from ..mini_yaml import load
        try:
            metadata = object_value(load(markdown[3:end], strict=True) or {}, label)
        except (ValueError, TypeError) as exc:
            raise LayoutError(f"来源 front matter 无效: {label}") from exc
        return metadata, markdown[end + 4:].lstrip("\r\n")
    for line in markdown.splitlines(keepends=True):
        match = META_COMMENT.fullmatch(line.rstrip("\r\n"))
        if not match:
            break
        metadata[match[1]] = match[2]
        position += len(line)
    body = markdown[position:]
    return metadata, body.lstrip("\r\n") if metadata else body


def _source_identity(snapshot, path, pin, body_pin, source):
    metadata, body = source_body(snapshot.bytes(path, pin), path)
    require(sha(body.encode()) == body_pin, f"正文 hash 不匹配: {path}", "HASH_MISMATCH")
    locator = metadata.get("source", metadata.get("locator", "")) or metadata.get("video_url", "")
    require(locator == source["locator"] and sha(locator.encode())[:16] == source["source_id"],
            f"来源身份与文件不一致: {path}")
    return metadata, body


def _string_list(value, label):
    require(type(value) is list and all(type(v) is str and v for v in value)
            and len(value) == len(set(value)), f"{label} 必须是无重复字符串数组")
    return value


def _record(snapshot, topic_path, slug, rid):
    prefix = f"{topic_path}/" if topic_path else ""
    run = f"runs/{rid}"
    record_path, manifest_path = f"{run}/run-record.json", f"{run}/retrieval-manifest.json"
    for path in (record_path, manifest_path):
        require(prefix + path in snapshot.blobs, f"{prefix + path} 不可用。{REBUILD}", "SOURCE_UNAVAILABLE")
    record = object_value(snapshot.json(prefix + record_path), record_path)
    manifest = object_value(snapshot.json(prefix + manifest_path), manifest_path)
    require(type(record.get("version")) is int and record["version"] == 1, "run-record.version 必须为1")
    require(type(manifest.get("schema_version")) is int and manifest["schema_version"] == 1
            and manifest.get("producer") == "research-tool", "仅支持 research-tool manifest v1")
    for key in ("topic", "topic_slug", "run_id", "verdict", "pipeline_complete", "started_at", "finished_at", "input_fingerprint"):
        require(key in record and manifest.get(key) == record[key], f"manifest/record {key} 不一致")
    require(record["run_id"] == rid and record["topic_slug"] == slug, "运行/主题身份与目录不符")
    text(record["topic"], "topic")
    require(type(record["verdict"]) is str and record["verdict"] in VERDICTS, "verdict 非规范枚举")
    require(type(record["pipeline_complete"]) is bool and type(manifest["pipeline_complete"]) is bool,
            "pipeline_complete 必须是 boolean")
    success = record["verdict"] == "STOP_SUCCESS" and record["pipeline_complete"] is True
    require(record["verdict"] != "STOP_SUCCESS" or success, "STOP_SUCCESS 必须 pipeline_complete=true")
    started = utc_time(record["started_at"], "started_at")
    finished = utc_time(record["finished_at"], "finished_at")
    require(started <= finished, "finished_at 早于 started_at")
    fingerprint = digest(record["input_fingerprint"], "input_fingerprint")
    require(record.get("output_contract") == "nine-stage" and record.get("stages") == list(STAGES), "非规范九阶段运行")
    completed = _string_list(record.get("stages_completed"), "stages_completed")
    skipped = _string_list(record.get("stages_skipped"), "stages_skipped")
    require(set(completed) <= set(STAGES) and set(skipped) <= set(STAGES)
            and not set(completed) & set(skipped), "stage 完成/跳过状态冲突")
    require("failed_stage" in record and (record["failed_stage"] is None or record["failed_stage"] in STAGES), "failed_stage 无效")
    statuses = {s: "completed" if s in completed else "skipped" if s in skipped else "not_completed" for s in STAGES}
    require(manifest.get("stages") == statuses, "manifest stages 与 record 不一致")
    if success:
        require(set(completed + skipped) == set(STAGES) and "report" in completed and record["failed_stage"] is None,
                "成功运行未完成九阶段")
    runtime = object_value(record.get("runtime"), "record.runtime")
    require(set(runtime) == {"version", "run_id", "input_fingerprint", "round", "completed_stages", "latest_digest"},
            "runtime 不是完整 v1 快照")
    require(type(runtime["version"]) is int and runtime["version"] == 1 and runtime["run_id"] == rid
            and runtime["input_fingerprint"] == fingerprint, "runtime 身份不一致")
    require(type(runtime["round"]) is int and runtime["round"] >= 0, "runtime.round 无效")
    committed = object_value(runtime["completed_stages"], "runtime.completed_stages")
    pins, envelopes, stage_names = {}, {}, set()

    def pin(path, value):
        relative(path)
        require(path not in pins or pins[path] == value, f"多个 canonical pin 冲突: {path}")
        snapshot.bytes(prefix + path, value)
        pins[path] = value

    for key, entry in committed.items():
        require(type(key) is str and re.fullmatch(r"[a-z]+(?::[0-9]+)?", key), "runtime stage key 无效")
        stage = key.split(":")[0]
        require(stage in STAGES, f"未知阶段: {stage}")
        stage_names.add(stage)
        object_value(entry, key)
        require(set(entry) == {"artifact_path", "artifact_digest"}, f"runtime stage record 无效: {key}")
        expected_path = f"artifacts/{rid}/{key.replace(':', '-')}.json"
        require(entry["artifact_path"] == expected_path, f"stage envelope 路径不符: {key}", "UNSAFE_PATH")
        envelope_pin = digest(entry["artifact_digest"], key)
        pin(expected_path, envelope_pin)
        envelope = object_value(snapshot.json(prefix + expected_path), expected_path)
        require(type(envelope.get("v")) is int and envelope["v"] == 1 and envelope.get("run_id") == rid
                and envelope.get("stage") == stage and envelope.get("request_id") == key
                and "error" in envelope and envelope["error"] is None, f"stage envelope 身份无效: {key}")
        object_value(envelope.get("result"), f"{key}.result")
        files = hash_map(envelope.get("files"), f"{key}.files")
        for path, value in files.items():
            require(path.startswith(run + "/") and path not in (record_path, manifest_path),
                    f"stage output 不属于本 run: {path}", "UNSAFE_PATH")
            pin(path, value)
        envelopes[key] = envelope
    require(stage_names == set(completed), "runtime 已提交阶段与 run-record 不一致")
    latest = runtime["latest_digest"]
    require((not committed and latest is None) or (committed and latest in [e["artifact_digest"] for e in committed.values()]),
            "runtime.latest_digest 不属于已提交 envelope")
    finals = hash_map(record.get("files"), "record.files")
    for path, value in finals.items():
        require(path.startswith(run + "/final/"), "record.files 不是本 run final 路径", "UNSAFE_PATH")
        require(pins.get(path) == value, f"final 未被 runtime 提交: {path}")
    require(manifest.get("record_path") == record_path, "record_path 不是本 run canonical 路径", "UNSAFE_PATH")
    record_pin = digest(manifest.get("record_sha256"), "record_sha256", True)
    pin(record_path, record_pin)
    manifest_files = hash_map(manifest.get("files"), "manifest.files", True)
    manifest_pins = dict(pins)
    require(manifest_files == manifest_pins,
            "manifest.files 与 run-record/runtime 提交集合不一致")
    artifacts = object_value(manifest.get("artifacts"), "artifacts")
    artifact_hashes = object_value(manifest.get("artifact_hashes"), "artifact_hashes")
    expected = {
        "report": f"{run}/final/report.md",
        "sources": f"{run}/final/sources.json",
        "main_table": f"{run}/final/tree/00-主表.md",
        "knowledge": f"{run}/final/tree/knowledge.json",
    }
    require(set(artifacts) <= set(expected) and set(artifacts) == set(artifact_hashes), "artifacts/hash key 不一致")
    if success:
        require(artifacts == expected, "成功运行必须包含三个规范 final artifacts")
    for name, path in artifacts.items():
        require(path == expected[name], f"artifact 路径无效: {name}", "UNSAFE_PATH")
        require(finals.get(path) == digest(artifact_hashes[name], f"artifact_hashes.{name}", True), f"final pin 不一致: {path}")
    sources = manifest.get("sources")
    require(type(sources) is list, "sources 必须是数组")
    raw_by_path = {}
    for source in sources:
        object_value(source, "source")
        for field in ("source_id", "locator", "title", "source_engine", "fetched_at", "source_tier"):
            text(source.get(field), f"source.{field}", empty=field in {"title", "source_engine", "fetched_at"})
        require(source.get("evidence_kind") in {"body", "snippet", "discovery", "unknown"}, "evidence_kind 非规范枚举")
        path = relative(source.get("raw_path"))
        require(path.startswith(run + "/") and "/raw/" in path and path not in raw_by_path,
                "raw_path 不属于本run或重复", "UNSAFE_PATH")
        raw_pin = digest(source.get("artifact_sha256"), "artifact_sha256", True)
        body_pin = digest(source.get("body_sha256"), "body_sha256", True)
        metadata, _body = _source_identity(snapshot, prefix + path, raw_pin, body_pin, source)
        if "evidence_kind" in metadata:
            require(metadata["evidence_kind"] == source["evidence_kind"], f"来源 evidence_kind 冲突: {path}")
        require(path not in pins or pins[path] == raw_pin, "raw artifact 与已提交 pin 不一致")
        if success:
            require(path in pins, f"成功运行的 raw 来源未提交: {path}")
        raw_by_path[path] = source
    citations = manifest.get("citation_sources")
    require(type(citations) is list, "citation_sources 必须是数组")
    record_data = {
        "topic": record["topic"], "topic_slug": slug, "topic_path": topic_path,
        "run_id": rid, "run_key": f"{slug}:{rid}", "record": record, "manifest": manifest,
        "record_path": prefix + record_path, "record_sha256": "sha256:" + record_pin,
        "manifest_path": prefix + manifest_path, "finished": finished, "success": success,
        "prefix": prefix, "pins": pins, "raw": raw_by_path, "envelopes": envelopes,
        "clean": {}, "facts": {}, "report_claims": [], "nodes": [],
    }
    if success:
        _evidence(snapshot, record_data)
    else:
        require(not citations, "未成功运行不能发布 citation_sources")
    return record_data


def _evidence(snapshot, run):
    manifest, prefix = run["manifest"], run["prefix"]
    graph = object_value(snapshot.json(prefix + manifest["artifacts"]["knowledge"]), "knowledge")
    final_sources = snapshot.json(prefix + manifest["artifacts"]["sources"])
    require(type(final_sources) is list and type(graph.get("sources")) is list, "final/graph sources 必须为数组")
    graph_sources = {}
    for source in graph["sources"]:
        object_value(source, "graph.source")
        sid = text(source.get("source_id"), "source_id")
        require(sid not in graph_sources, "graph source_id 重复")
        text(source.get("locator"), "locator")
        graph_path = text(source.get("path"), "source.path")
        require(os.path.isabs(graph_path), "graph source.path 必须保留绝对旧字段")
        body = text(source.get("text"), "source.text")
        require(digest(source.get("content_sha256"), "source.content_sha256") == sha(body.encode()), "graph 正文 hash 不符", "HASH_MISMATCH")
        graph_sources[sid] = source
    final_map = {}
    for source in final_sources:
        object_value(source, "final.source")
        sid = text(source.get("source_id"), "source_id")
        require(sid not in final_map and graph_sources.get(sid) == source, "final.sources 与 graph source 不一致")
        final_map[sid] = source
    for source in manifest["citation_sources"]:
        object_value(source, "citation_source")
        require({"clean_path", "clean_artifact_sha256", "body_sha256", "source_id", "locator", "title", "raw_path"} <= set(source),
                "citation_source 缺少规范字段")
        sid = text(source.get("source_id"), "citation_source.source_id")
        require(sid in final_map and sid not in run["clean"], "citation_sources 身份重复或不在 final.sources")
        path = relative(source.get("clean_path"))
        raw_path = relative(source.get("raw_path"))
        raw = run["raw"].get(raw_path)
        require(raw is not None and raw["source_id"] == sid and raw["locator"] == source.get("locator"), "clean→raw 来源链断裂")
        require(raw["evidence_kind"] == "body", "snippet/discovery 不能成为正文支持证据")
        require(path.startswith(f"runs/{run['run_id']}/") and "/clean/" in path, "clean_path 越界", "UNSAFE_PATH")
        clean_pin = digest(source.get("clean_artifact_sha256"), "clean_artifact_sha256", True)
        body_pin = digest(source.get("body_sha256"), "citation_source.body_sha256", True)
        require(run["pins"].get(path) == clean_pin, "clean 来源未由 runtime 提交")
        metadata, body = _source_identity(snapshot, prefix + path, clean_pin, body_pin, source)
        require(metadata.get("evidence_kind", "body") == "body", "clean 不是 body")
        require(body == final_map[sid]["text"] and body_pin == final_map[sid]["content_sha256"]
                and source.get("locator") == final_map[sid]["locator"], "clean 正文与 graph/final 不符")
        text(source.get("title"), "citation_source.title", empty=True)
        run["clean"][sid] = {**source, "body": body}
    require(set(run["clean"]) <= set(final_map), "citation_sources 含 final.sources 之外的来源")
    facts = graph.get("facts")
    require(type(facts) is list and facts, "graph facts 必须是非空数组")
    for fact in facts:
        object_value(fact, "fact")
        cid = text(fact.get("claim_id"), "claim_id")
        require(cid not in run["facts"], "claim_id 重复")
        text(fact.get("text"), "fact.text")
        spans = fact.get("citations")
        require(type(spans) is list and spans, "fact 缺少 citations")
        for span in spans:
            _span(span, graph_sources)
        run["facts"][cid] = fact
    nodes = graph.get("nodes")
    require(type(nodes) is list and nodes, "graph nodes 必须是非空数组")
    node_ids = set()
    for node in nodes:
        object_value(node, "node")
        nid = text(node.get("node_id"), "node_id")
        require(nid not in node_ids, "node_id 重复")
        node_ids.add(nid)
        text(node.get("title"), "node.title")
        require(set(_string_list(node.get("claim_ids"), "node.claim_ids")) <= set(run["facts"]), "node 引用未知 claim")
    counts = object_value(graph.get("counts"), "graph.counts")
    for key, values in (("nodes", nodes), ("facts", facts), ("sources", graph_sources)):
        require(type(counts.get(key)) is int and counts[key] == len(values), f"graph.counts.{key} 不符")
    report = run["envelopes"].get("report", {}).get("result", {})
    paragraphs = report.get("claims")
    require(type(paragraphs) is list and paragraphs and type(report.get("headings")) is list, "report envelope 缺少 claims/headings")
    markdown = snapshot.bytes(prefix + manifest["artifacts"]["report"]).decode("utf-8")
    require(report.get("markdown") == markdown, "报告正文与 report envelope 不一致")
    for paragraph in paragraphs:
        object_value(paragraph, "report.claims")
        require(text(paragraph.get("text"), "paragraph.text") in markdown, "报告段落不在 final report")
        ids = _string_list(paragraph.get("claim_ids"), "paragraph.claim_ids")
        require(ids and set(ids) <= set(run["facts"]), "段落引用未知 claim")
        spans = [c for cid in ids for c in run["facts"][cid]["citations"]]
        require(paragraph.get("citations") == spans, "段落引用与 claim citations 不一致")
        for span in spans:
            require(span["source_id"] in run["clean"], "报告引用未绑定 clean/raw 来源")
            _span(span, graph_sources)
    for heading in report["headings"]:
        object_value(heading, "heading")
        require(text(heading.get("text"), "heading.text") in markdown, "heading 不在报告")
        require(set(_string_list(heading.get("claim_ids"), "heading.claim_ids")) <= set(run["facts"]), "heading 引用未知 claim")
    run["report_claims"], run["nodes"] = paragraphs, nodes


def _span(span, sources):
    object_value(span, "citation")
    sid = text(span.get("source_id"), "citation.source_id")
    source = sources.get(sid)
    require(source is not None and span.get("locator") == source["locator"], "citation 来源身份不符")
    require(digest(span.get("content_sha256"), "citation.content_sha256") == source["content_sha256"], "citation body hash 不符", "HASH_MISMATCH")
    start, end = span.get("start_offset"), span.get("end_offset")
    require(type(start) is int and type(end) is int and 0 <= start < end <= len(source["text"]), "citation span offset 无效")
    require(text(span.get("text"), "citation.text") == source["text"][start:end], "citation clean span 与正文不符", "HASH_MISMATCH")


def scan(root):
    snapshot = Snapshot(root)
    topics = []
    if "runs" in snapshot.directories or "run-summary.json" in snapshot.blobs or "runtime-state.json" in snapshot.blobs:
        topics.append(("", Path(snapshot.root).name))
    else:
        for path in sorted(snapshot.directories):
            if "/" not in path and (f"{path}/runs" in snapshot.directories or f"{path}/run-summary.json" in snapshot.blobs
                                    or f"{path}/runtime-state.json" in snapshot.blobs):
                topics.append((path, path))
    require(topics, f"未发现 canonical research-tool topic。{REBUILD}", "SOURCE_UNAVAILABLE")
    runs = []
    for topic_path, slug in topics:
        require(re.fullmatch(r"[\w-]+", slug) and slug not in DERIVED_DIRS, "topic_slug 非规范目录名")
        prefix = f"{topic_path}/" if topic_path else ""
        base = prefix + "runs/"
        ids = [path[len(base):] for path in snapshot.directories if path.startswith(base) and "/" not in path[len(base):]]
        require(ids, f"主题 {slug} 缺少 canonical runs。{REBUILD}", "SOURCE_UNAVAILABLE")
        topic_runs = []
        for rid in sorted(ids):
            require(RUN_ID.fullmatch(rid), f"run_id 必须为32小写hex: {rid}")
            topic_runs.append(_record(snapshot, topic_path, slug, rid))
        require(len({r["finished"] for r in topic_runs}) == len(topic_runs),
                f"主题 {slug} 的 finished_at 有多个候选；拒绝按 UUID/mtime 选择", "AMBIGUOUS_VERSION")
        topic_runs.sort(key=lambda r: r["finished"])
        current = topic_runs[-1]
        successful = [r for r in topic_runs if r["success"]]
        latest_success = successful[-1] if successful else None
        summary_path, state_path = prefix + "run-summary.json", prefix + "runtime-state.json"
        if summary_path in snapshot.blobs or state_path in snapshot.blobs:
            require(summary_path in snapshot.blobs and state_path in snapshot.blobs, "当前 summary/runtime 不完整", "SOURCE_UNAVAILABLE")
            summary = object_value(snapshot.json(summary_path), summary_path)
            state = object_value(snapshot.json(state_path), state_path)
            require(summary.get("run_id") == current["run_id"] and state.get("run_id") == current["run_id"],
                    f"当前运行未完成快照或与最新 record 不一致。{REBUILD}", "SOURCE_UNAVAILABLE")
            for key in ("topic", "topic_slug", "verdict", "pipeline_complete", "stages", "stages_completed", "stages_skipped", "failed_stage", "files"):
                require(key in summary and summary[key] == current["record"][key], f"current summary.{key} 与 record 不符")
            require(state == current["record"]["runtime"], "current runtime 与当前 run-record 不符")
        state_info = {k: current["record"][k] for k in ("run_id", "verdict", "pipeline_complete", "finished_at")}
        for run in topic_runs:
            run["current_run"] = state_info
            run["is_current"] = run is current
            run["is_latest_success"] = run is latest_success
            run["report_type"] = "report_current" if run is current else "report_latest_success" if run is latest_success else "report_historical"
        runs.extend(topic_runs)
    snapshot.unchanged()
    return snapshot, runs


def entity_id(kind, run, suffix=None):
    return f"{kind}:{run['run_key']}" + (f":{suffix}" if suffix is not None else "")


def projection(snapshot, runs):
    tables = {name: [] for name in TABLE_COLUMNS}
    docs = {}

    def document(eid, kind, path, run, extra=None, pin=None):
        require(eid not in docs, f"派生实体身份重复: {eid}")
        data = {"topic": run["topic"], "topic_slug": run["topic_slug"], "run_id": run["run_id"],
                "verdict": run["record"]["verdict"], "pipeline_complete": run["record"]["pipeline_complete"],
                "finished_at": run["record"]["finished_at"], "current_run": run["current_run"], **(extra or {})}
        digest_value = pin or ("sha256:" + sha(snapshot.blobs[path]) if path in snapshot.blobs else None)
        row = (eid, kind, path, run["run_id"], digest_value, None, run["record"]["verdict"])
        docs[eid] = row
        tables["documents"].append(row)
        tables["entities"].append((eid, kind, path, run["run_id"], row[-1]))
        tables["research_tool_metadata"].append((eid, json_text(data)))
        return eid

    def relation(source, kind, target):
        tables["relations"].append((source, kind, target, docs[source][2], docs[target][2], docs[source][3], docs[target][3]))

    for run in runs:
        prefix, record = run["prefix"], run["record"]
        run_eid = document(entity_id("run", run), "run_manifest", run["record_path"], run,
                           {"input_fingerprint": record["input_fingerprint"], "record_sha256": run["record_sha256"], "is_current": run["is_current"]})
        document(entity_id("manifest", run), "retrieval_manifest", run["manifest_path"], run)
        tables["runs"].append((run["run_key"], run["topic_slug"], record["verdict"], None, None, None, None, None))
        raw_ids = {}
        for path, source in run["raw"].items():
            eid = document(entity_id("raw", run, sha(path.encode())[:16]), "raw", prefix + path, run,
                           {**source, "committed": path in run["pins"]}, pin=source["artifact_sha256"])
            raw_ids[path] = eid
            relation(eid, "recorded_in", run_eid)
        if not run["success"]:
            continue
        artifact_ids = {}
        for name, kind in (("report", run["report_type"]), ("sources", "sources_manifest"), ("knowledge", "evidence_graph")):
            path = prefix + run["manifest"]["artifacts"][name]
            extra = {"selection": "current" if run["is_current"] else "latest_success" if run["is_latest_success"] else "historical"}
            artifact_ids[name] = document(entity_id("graph" if name == "knowledge" else name, run), kind, path, run, extra)
        report_id = artifact_ids["report"]
        relation(report_id, "recorded_in", run_eid)
        used = {cid for paragraph in run["report_claims"] for cid in paragraph["claim_ids"]}
        used_sources = {span["source_id"] for cid in used for span in run["facts"][cid]["citations"]}
        clean_ids = {}
        for sid in sorted(used_sources):
            source = run["clean"][sid]
            clean_ids[sid] = document(entity_id("source", run, sid), "citation_source", prefix + source["clean_path"], run,
                                     {k: v for k, v in source.items() if k != "body"}, pin=source["clean_artifact_sha256"])
            relation(clean_ids[sid], "derived_from", raw_ids[source["raw_path"]])
            tables["source_refs"].append((report_id, docs[report_id][2], prefix + source["clean_path"], "file", "historical",
                                          source["clean_artifact_sha256"], None, sid))
        for cid in sorted(used):
            fact = run["facts"][cid]
            claim_id = document(entity_id("claim", run, cid), "claim", docs[artifact_ids["knowledge"]][2], run, fact)
            relation(report_id, "claims", claim_id)
            for number, span in enumerate(fact["citations"]):
                sid = span["source_id"]
                citation_id = document(entity_id("citation", run, f"{cid}:{number}"), "citation", docs[clean_ids[sid]][2], run,
                                       {**span, "claim_id": cid, "raw_path": prefix + run["clean"][sid]["raw_path"]})
                relation(claim_id, "supported_by", citation_id)
                relation(citation_id, "quotes", clean_ids[sid])
                relation(clean_ids[sid], "supports", claim_id)
    return {table: sorted(rows, key=json_text) for table, rows in tables.items()}


def db_location(root, db_path):
    root, db = Path(os.path.abspath(root)), Path(os.path.abspath(db_path))
    require(db.is_relative_to(root / ".index") and db != root / ".index", "DB 只能位于 root/.index 内，不能覆盖 canonical", "UNSAFE_PATH")
    require(db.name not in {"research-tool.lock"} and not db.name.startswith(".research-tool-"), "DB 名称与内部锁/临时文件冲突", "UNSAFE_PATH")
    # Check all existing components, without resolving away symlinks.
    for path in [db, *db.parents]:
        if path.is_symlink():
            raise LayoutError(f"拒绝 DB symlink: {path}", "UNSAFE_PATH")
    if db.exists():
        info = db.stat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "DB 必须是独立普通文件（拒绝 hardlink）", "UNSAFE_PATH")
    return db


@contextmanager
def index_lock(root):
    with directory_fd(Path(root) / ".index", create=True) as fd:
        lock_fd = os.open("research-tool.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            require(os.fstat(lock_fd).st_nlink == 1, "索引锁不能是 hardlink", "UNSAFE_PATH")
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LayoutError("另一个 research-tool 索引写入正在进行", "INDEX_BUSY") from exc
            yield
        finally:
            os.close(lock_fd)


def _publish_db(snapshot, runs, db):
    data = projection(snapshot, runs)
    watermark = {"layout": "research-tool", "schema_version": "1", "index_built_at": datetime.now(timezone.utc).isoformat(),
                 "last_event_id": "", "index_complete": "1", "drift": "0", "scan_fingerprint": snapshot.fingerprint}
    with directory_fd(db.parent, create=True) as fd:
        temporary = f".research-tool-{uuid.uuid4().hex}.sqlite"
        temp_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        os.close(temp_fd)
        conn = sqlite3.connect(str(db.parent / temporary))
        try:
            conn.executescript(SCHEMA_SQL + "\nCREATE TABLE research_tool_metadata(entity_id TEXT PRIMARY KEY, data TEXT NOT NULL);")
            with conn:
                for table, columns in TABLE_COLUMNS.items():
                    placeholders = ",".join("?" for _ in columns.split(","))
                    conn.executemany(f"INSERT INTO {table}({columns}) VALUES({placeholders})", data[table])
                conn.executemany("INSERT INTO index_metadata(key,value) VALUES(?,?)", watermark.items())
            require(conn.execute("PRAGMA integrity_check").fetchone() == ("ok",), "SQLite 构建校验失败", "INDEX_STALE")
        finally:
            conn.close()
        sync_fd = os.open(temporary, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            os.fsync(sync_fd)
        finally:
            os.close(sync_fd)
        snapshot.unchanged()
        db_location(snapshot.root, db)
        os.replace(temporary, db.name, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
        snapshot.unchanged()
    return {**watermark, "index_complete": True, "drift": False, "last_event_id": None}


def build_research_tool_index(root, db_path, git_commit="HEAD"):
    """Validate canonical snapshots, then atomically replace the derived DB.

    Returns QueryResult on both success and failure. git_commit is intentionally
    unused: output snapshots do not have an authenticated historical Git commit.
    """
    try:
        db = db_location(root, db_path)
        snapshot, runs = scan(root)
        with index_lock(snapshot.root):
            watermark = _publish_db(snapshot, runs, db)
        return QueryResult(query_type="reindex", authority="derived", source_watermark=watermark,
                           results=[{"path": str(db), "run_count": len(runs)}]).to_dict()
    except (LayoutError, OSError, sqlite3.Error, UnicodeError) as exc:
        return error_result("reindex", exc)


@contextmanager
def verified_index(root, db_path):
    """Read-only DB access, full canonical validation and projection comparison."""
    db = db_location(root, db_path)
    require(db.is_file(), "索引不存在；请先运行 index（只读查询不会创建 SQLite）", "INDEX_STALE")
    # Check the immutable byte fingerprint against the DB watermark before
    # parsing any manifest. A changed canonical byte is INDEX_STALE, not a
    # newly interpreted provenance error, until the caller explicitly reindexes.
    snapshot = Snapshot(root)
    with directory_fd(db.parent):
        conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        wm = dict(conn.execute("SELECT key,value FROM index_metadata"))
        require(wm.get("layout") == "research-tool" and wm.get("schema_version") == "1" and wm.get("index_complete") == "1",
                "索引不是完整的 research-tool v1 generation", "INDEX_STALE")
        require(wm.get("scan_fingerprint") == snapshot.fingerprint, "索引落后于 canonical；请运行 index", "INDEX_STALE")
        verified_snapshot, runs = scan(root)
        require(verified_snapshot.fingerprint == snapshot.fingerprint, "canonical 在索引校验期间变化", "INDEX_STALE")
        snapshot = verified_snapshot
        expected = projection(snapshot, runs)
        for table, columns in TABLE_COLUMNS.items():
            actual = sorted(conn.execute(f"SELECT {columns} FROM {table}").fetchall(), key=json_text)
            require(actual == expected[table], f"派生索引 {table} 与 canonical 不一致；请重建", "INDEX_STALE")
        wm.update(index_complete=True, drift=False, last_event_id=None)
        yield snapshot, runs, conn, wm
        snapshot.unchanged()
    finally:
        conn.close()


def reconcile_research_tool(root, db_path, gitdir=None):
    from .research_tool_query import execute
    from types import SimpleNamespace
    return execute(SimpleNamespace(root=root, db=db_path, command="reconcile"))


def generate_research_tool_index(root, db_path=None, write_file=True):
    from .research_tool_query import execute
    from types import SimpleNamespace
    return execute(SimpleNamespace(root=root, db=db_path or os.path.join(root, ".index", "research.sqlite"),
                                   command="generate-index", write_file=write_file))
