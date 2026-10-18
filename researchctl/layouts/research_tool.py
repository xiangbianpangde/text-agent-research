"""Research-tool output layout adapter.

The research-tool pipeline keeps canonical output below one directory per
``topic_slug``.  This module projects those canonical files into the existing
ResearchCTL SQLite schema; it does not make SQLite or ``index/INDEX.md`` a
source of truth.

Only the standard library is used.  The adapter intentionally has a small
surface: scan/build, navigation generation, fingerprinting, and reconcile.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..hashing import file_hash
from ..indexer import SCHEMA_SQL
from ..schema import QueryResult


_HASH_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")
_SUCCESS_VERDICTS = {
    "stop_success",
    "success",
    "succeeded",
    "complete",
    "completed",
    "pass",
    "passed",
    "ok",
    "valid",
    "accepted",
    "keep",
}
_DERIVED_DIRS = frozenset({".index", "index", ".git", ".researchctl"})
_EXPECTED_ARTIFACTS = (
    ("report", "final/report.md", "report"),
    ("sources", "final/sources.json", "sources_manifest"),
    ("graph", "final/tree/knowledge.json", "evidence_graph"),
)


class LayoutError(ValueError):
    """The canonical research-tool layout cannot be projected safely."""


def _posix(path: str) -> str:
    return path.replace(os.sep, "/")


def _safe_relative(path: Any) -> Optional[str]:
    """Normalize a relative path without permitting traversal or absolutes."""
    if not isinstance(path, str) or not path.strip():
        return None
    if os.path.isabs(path):
        return None
    normalized = os.path.normpath(path)
    if normalized in ("", "."):
        return None
    if normalized == ".." or normalized.startswith(".." + os.sep):
        return None
    return _posix(normalized)


def _within(root: str, full: str) -> bool:
    root_real = os.path.realpath(root)
    full_real = os.path.realpath(full)
    return full_real == root_real or full_real.startswith(root_real + os.sep)


def _join_relative(root: str, relative: str) -> str:
    full = os.path.join(root, *relative.split("/"))
    if not _within(root, full):
        raise LayoutError(f"路径越界: {relative}")
    return full


def _hash_value(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value:
        return None
    value = value.strip()
    if not _HASH_RE.match(value):
        return None
    return value if value.lower().startswith("sha256:") else "sha256:" + value.lower()


def _actual_hash(root: str, relative: Optional[str]) -> Optional[str]:
    if not relative:
        return None
    return file_hash(_join_relative(root, relative))


def _is_derived_relative(relative: str) -> bool:
    return any(part in _DERIVED_DIRS for part in relative.split("/"))


def research_tool_fingerprint(root: str) -> str:
    """Fingerprint canonical research-tool files, excluding derived indexes."""
    lines: List[str] = []
    if not os.path.isdir(root):
        return "sha256:" + hashlib.sha256(b"").hexdigest()
    for dirpath, subdirs, filenames in os.walk(root):
        subdirs[:] = sorted(d for d in subdirs if d not in _DERIVED_DIRS)
        for filename in sorted(filenames):
            full = os.path.join(dirpath, filename)
            relative = _posix(os.path.relpath(full, root))
            if _is_derived_relative(relative):
                continue
            digest = file_hash(full)
            if digest:
                lines.append(f"{relative}:{digest}")
    return "sha256:" + hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _read_json(path: str, label: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LayoutError(f"{label} 无法解析: {exc}") from exc
    if not isinstance(value, dict):
        raise LayoutError(f"{label} 必须是 JSON object")
    return value


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "complete", "completed", "success"}
    return False


def _is_success(manifest: Dict[str, Any]) -> bool:
    verdict = manifest.get("verdict")
    if isinstance(verdict, dict):
        verdict = verdict.get("status") or verdict.get("value")
    return _truthy(manifest.get("pipeline_complete")) and str(verdict or "").strip().lower() in _SUCCESS_VERDICTS


def _timestamp_value(manifest: Dict[str, Any], manifest_path: str, run_id: str) -> Tuple[str, str, float]:
    for key in ("completed_at", "finished_at", "updated_at", "created_at", "started_at", "timestamp", "date"):
        value = manifest.get(key)
        if value is not None and str(value).strip():
            return str(value), str(run_id), os.path.getmtime(manifest_path)
    return "", str(run_id), os.path.getmtime(manifest_path)


def _candidate_paths(root: str, topic_relative: str, run_relative: str, raw: str) -> Iterable[Tuple[str, str]]:
    """Yield safe root-relative candidates for a manifest-relative path."""
    safe = _safe_relative(raw)
    if not safe:
        return
    bases = [run_relative, topic_relative, ""]
    seen = set()
    for base in bases:
        candidate = _posix(os.path.normpath(os.path.join(base, safe))) if base else safe
        if candidate in seen or _is_derived_relative(candidate):
            continue
        seen.add(candidate)
        full = _join_relative(root, candidate)
        yield candidate, full


def _resolve_existing(root: str, topic_relative: str, run_relative: str, raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    for candidate, full in _candidate_paths(root, topic_relative, run_relative, raw):
        if os.path.isfile(full):
            return candidate
    # Keep a safe canonical candidate for missing-file diagnostics.
    safe = _safe_relative(raw)
    if not safe:
        return None
    return _posix(os.path.normpath(os.path.join(run_relative, safe)))


def _artifact_path_value(value: Any) -> Tuple[Optional[str], Optional[str]]:
    """Read an artifact path, retaining compatibility with old dict values."""
    if isinstance(value, str):
        return value, None
    if not isinstance(value, dict):
        return None, None
    path = value.get("path") or value.get("artifact_path") or value.get("raw_path") or value.get("file")
    digest = (
        value.get("artifact_sha256")
        or value.get("sha256")
        or value.get("content_hash")
        or value.get("hash")
    )
    return path, _hash_value(digest)


def _artifact_aliases(name: Any, path: Any = None) -> set[str]:
    """Return stable aliases for artifact_hashes keys."""
    values = [name, path]
    aliases: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value:
            continue
        normalized = value.replace("\\", "/").lower()
        aliases.add(normalized)
        aliases.add(normalized.replace("-", "_"))
        aliases.add(os.path.basename(normalized))
        aliases.add(os.path.splitext(os.path.basename(normalized))[0])
    joined = " ".join(sorted(aliases))
    if "knowledge" in joined or "graph" in joined:
        aliases.update({"knowledge", "knowledge_json", "graph", "evidence_graph"})
    if "source" in joined:
        aliases.update({"sources", "sources_json", "sources_manifest"})
    if "report" in joined:
        aliases.update({"report", "report_md"})
    return aliases


def _lookup_artifact_hash(hashes: Any, name: Any, path: Any) -> Optional[str]:
    if not isinstance(hashes, dict):
        return None
    aliases = _artifact_aliases(name, path)
    for key, value in hashes.items():
        if _artifact_aliases(key) & aliases:
            if isinstance(value, dict):
                value = value.get("artifact_sha256") or value.get("sha256") or value.get("hash")
            digest = _hash_value(value)
            if digest:
                return digest
    return None


def _artifact_entries(manifest: Dict[str, Any]) -> List[Tuple[str, Optional[str], Optional[str]]]:
    """Normalize ``artifacts`` paths and merge the independent hash map.

    M1 defines ``artifacts`` as ``name -> relative path`` and
    ``artifact_hashes`` as the pin map.  Dict-valued artifacts remain accepted
    for compatibility, but a hash in ``artifact_hashes`` wins over any inline
    value so a reindex cannot replace a canonical pin with a current hash.
    """
    raw = manifest.get("artifacts")
    entries: List[Tuple[str, Optional[str], Optional[str]]] = []
    if isinstance(raw, dict):
        for name, value in raw.items():
            path, inline_digest = _artifact_path_value(value)
            if path:
                digest = _lookup_artifact_hash(manifest.get("artifact_hashes"), name, path) or inline_digest
                entries.append((str(name), path, digest))
    elif isinstance(raw, list):
        for value in raw:
            if not isinstance(value, dict):
                continue
            name = value.get("name") or value.get("kind") or value.get("type") or "artifact"
            path, inline_digest = _artifact_path_value(value)
            if path:
                digest = _lookup_artifact_hash(manifest.get("artifact_hashes"), name, path) or inline_digest
                entries.append((str(name), path, digest))
    return entries


def _validate_manifest(manifest: Dict[str, Any], topic_slug: str, run_id: str, relative: str) -> None:
    required = (
        "topic", "topic_slug", "run_id", "verdict", "pipeline_complete",
        "stages", "artifacts", "artifact_hashes", "sources",
    )
    missing = [key for key in required if key not in manifest]
    if missing:
        raise LayoutError(f"manifest {relative} 缺少字段: {', '.join(missing)}")
    if str(manifest.get("topic_slug")) != topic_slug:
        raise LayoutError(f"manifest {relative} 的 topic_slug 与目录不一致")
    if str(manifest.get("run_id")) != run_id:
        raise LayoutError(f"manifest {relative} 的 run_id 与目录不一致")
    if not isinstance(manifest.get("stages"), (dict, list)):
        raise LayoutError(f"manifest {relative} 的 stages 必须是 object/list")
    if not isinstance(manifest.get("artifacts"), (dict, list)):
        raise LayoutError(f"manifest {relative} 的 artifacts 必须是 object/list")
    if not isinstance(manifest.get("artifact_hashes"), dict):
        raise LayoutError(f"manifest {relative} 的 artifact_hashes 必须是 object")
    if not isinstance(manifest.get("sources"), list):
        raise LayoutError(f"manifest {relative} 的 sources 必须是 list")
    artifact_entries = _artifact_entries(manifest)
    if not artifact_entries:
        raise LayoutError(f"manifest {relative} 的 artifacts 为空")
    for key, canonical_path, _doc_type in _EXPECTED_ARTIFACTS:
        matching = []
        for name, artifact_path, artifact_digest in artifact_entries:
            if _safe_relative(artifact_path) in {
                canonical_path,
                _posix(os.path.join(run_id, canonical_path)),
            } or _artifact_aliases(name, artifact_path) & _artifact_aliases(key, canonical_path):
                matching.append(artifact_digest)
        if not any(matching):
            raise LayoutError(f"manifest {relative} 缺少 {key} 的 artifact_hashes pin")
    for index, source in enumerate(manifest["sources"]):
        if not isinstance(source, dict):
            raise LayoutError(f"manifest {relative} 的 sources[{index}] 必须是 object")
        if not isinstance(source.get("raw_path"), str) or not source.get("raw_path"):
            raise LayoutError(f"manifest {relative} 的 sources[{index}] 缺少 raw_path")
        if not source.get("evidence_kind"):
            raise LayoutError(f"manifest {relative} 的 sources[{index}] 缺少 evidence_kind")
        if not _hash_value(source.get("artifact_sha256")):
            raise LayoutError(f"manifest {relative} 的 sources[{index}] 缺少有效 artifact_sha256")
        body_hash = source.get("body_sha256")
        if body_hash is not None and not _hash_value(body_hash):
            raise LayoutError(f"manifest {relative} 的 sources[{index}] body_sha256 无效")


def _expected_canonical(
    root: str,
    topic_relative: str,
    run_relative: str,
    manifest: Dict[str, Any],
) -> Dict[str, Tuple[str, Optional[str], str]]:
    """Return artifact key -> (root-relative path, pinned hash, doc type)."""
    by_name: Dict[str, Tuple[str, Optional[str], str]] = {}
    artifact_entries = _artifact_entries(manifest)
    for name, raw_path, digest in artifact_entries:
        normalized_name = name.lower().replace("-", "_")
        resolved = _resolve_existing(root, topic_relative, run_relative, raw_path)
        if resolved:
            by_name.setdefault(normalized_name, (resolved, digest, "artifact"))
    for key, raw_path, doc_type in _EXPECTED_ARTIFACTS:
        resolved = None
        for candidate, full in _candidate_paths(root, topic_relative, run_relative, raw_path):
            if os.path.isfile(full):
                resolved = candidate
                break
        if not resolved:
            resolved = _posix(os.path.join(run_relative, raw_path))
        digest = None
        for name, artifact_path, artifact_digest in artifact_entries:
            if _safe_relative(artifact_path) in {raw_path, _posix(os.path.join(run_relative, raw_path)), _posix(os.path.join(topic_relative, raw_path))}:
                digest = artifact_digest
                break
            if name.lower().replace("-", "_") in {key, doc_type}:
                digest = artifact_digest
        by_name[key] = (resolved, digest, doc_type)
    return by_name


def _scan_manifests(root: str) -> List[Dict[str, Any]]:
    if not os.path.isdir(root):
        raise LayoutError(f"research-tool 输出根目录不存在: {root}")
    records: List[Dict[str, Any]] = []
    for dirpath, subdirs, filenames in os.walk(root):
        subdirs[:] = sorted(d for d in subdirs if d not in _DERIVED_DIRS)
        if "retrieval-manifest.json" not in filenames:
            continue
        manifest_full = os.path.join(dirpath, "retrieval-manifest.json")
        run_relative = _posix(os.path.relpath(dirpath, root))
        if os.path.basename(os.path.dirname(dirpath)) != "runs":
            raise LayoutError(f"manifest 不在 <topic>/runs/<run_id> 下: {run_relative}")
        topic_relative = _posix(os.path.dirname(os.path.dirname(run_relative)))
        topic_slug = os.path.basename(topic_relative)
        run_id = os.path.basename(run_relative)
        manifest_relative = _posix(os.path.relpath(manifest_full, root))
        manifest = _read_json(manifest_full, manifest_relative)
        _validate_manifest(manifest, topic_slug, run_id, manifest_relative)
        canonical = _expected_canonical(root, topic_relative, run_relative, manifest)
        source_files: List[Dict[str, Any]] = []
        for source in manifest["sources"]:
            raw_relative = _resolve_existing(root, topic_relative, run_relative, source.get("raw_path"))
            if not raw_relative:
                raise LayoutError(f"manifest {manifest_relative} 的 raw_path 无效: {source.get('raw_path')}")
            source_files.append({
                "path": raw_relative,
                "artifact_sha256": _hash_value(source.get("artifact_sha256")),
                "body_sha256": _hash_value(source.get("body_sha256")),
                "evidence_kind": str(source.get("evidence_kind")),
            })
        topic_name = str(manifest.get("topic") or topic_slug)
        topic_files = {
            "run_summary": _posix(os.path.join(topic_relative, "run-summary.json")),
            "runtime_state": _posix(os.path.join(topic_relative, "runtime-state.json")),
        }
        timestamp = _timestamp_value(manifest, manifest_full, run_id)
        records.append({
            "topic": topic_name,
            "topic_slug": topic_slug,
            "topic_relative": topic_relative,
            "run_id": run_id,
            "run_relative": run_relative,
            "manifest_relative": manifest_relative,
            "manifest": manifest,
            "success": _is_success(manifest),
            "timestamp": timestamp,
            "canonical": canonical,
            "sources": source_files,
            "topic_files": topic_files,
        })
    records.sort(key=lambda item: (item["topic_slug"], item["timestamp"], item["run_id"]))
    if not records:
        raise LayoutError(f"未找到 research-tool retrieval-manifest.json: {root}")
    # Exactly one current successful run per topic; current selection is
    # deterministic even when manifests have identical timestamps.
    by_topic: Dict[str, List[Dict[str, Any]]] = {}
    for record in records:
        by_topic.setdefault(record["topic_slug"], []).append(record)
    for topic_records in by_topic.values():
        successful = [record for record in topic_records if record["success"]]
        latest = max(successful, key=lambda item: item["timestamp"]) if successful else None
        for record in topic_records:
            record["report_type"] = "report_current" if latest is record else "report_historical"
            record["run_key"] = f"{record['topic_slug']}:{record['run_id']}"
    return records


def _document_id(kind: str, record: Dict[str, Any], suffix: str = "") -> str:
    base = f"{record['topic_slug']}:{record['run_id']}"
    return f"{kind}:{base}{(':' + suffix) if suffix else ''}"


def _insert_document(conn: sqlite3.Connection, values: Tuple[Any, ...]) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO documents(id,doc_type,path,version,content_hash,git_commit,status) VALUES(?,?,?,?,?,?,?)",
        values,
    )


def _insert_entity(conn: sqlite3.Connection, values: Tuple[Any, ...]) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO entities(id,entity_type,path,current_version,status) VALUES(?,?,?,?,?)",
        values,
    )


def _add_source_ref(
    conn: sqlite3.Connection,
    owner: str,
    owner_path: str,
    ref_path: str,
    content_hash: Optional[str],
    section: str = "",
) -> None:
    conn.execute(
        "INSERT INTO source_refs(owner,owner_path,ref_path,source_type,reference_scope,content_hash,git_commit,section) VALUES(?,?,?,?,?,?,?,?)",
        (owner, owner_path, ref_path, "file", "current", content_hash or "", "", section),
    )


def _add_relation(
    conn: sqlite3.Connection,
    source: str,
    relation: str,
    target: str,
    source_path: str = "",
    target_path: str = "",
) -> None:
    conn.execute(
        "INSERT INTO relations(source,relation,target,source_path,target_path,source_version,target_version) VALUES(?,?,?,?,?,?,?)",
        (source, relation, target, source_path, target_path, "", ""),
    )


def _write_metadata(conn: sqlite3.Connection, values: Dict[str, Any]) -> None:
    for key, value in values.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        conn.execute("INSERT OR REPLACE INTO index_metadata(key,value) VALUES(?,?)", (key, str(value)))


def build_research_tool_index(root: str, db_path: str, git_commit: str = "HEAD") -> dict:
    """Scan canonical research-tool output and build the shared SQLite schema."""
    records = _scan_manifests(root)
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        for table in ("documents", "entities", "versions", "runs", "relations", "source_refs", "events"):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM index_metadata")
        now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        watermark = {
            "schema_version": "1",
            "layout": "research-tool",
            "index_built_at": now,
            "last_event_id": "",
            "index_complete": "0",
            "drift": "0",
            "scan_fingerprint": research_tool_fingerprint(root),
        }
        topic_seen: Dict[str, Dict[str, Any]] = {}
        for record in records:
            topic_id = f"topic:{record['topic_slug']}"
            topic_path = record["topic_relative"]
            if record["topic_slug"] not in topic_seen:
                topic_seen[record["topic_slug"]] = record
                _insert_document(conn, (topic_id, "topic", topic_path, None, None, git_commit, "valid"))
                _insert_entity(conn, (topic_id, "topic", topic_path, None, "valid"))
            manifest_path = record["manifest_relative"]
            manifest_id = _document_id("run", record)
            manifest_hash = _actual_hash(root, manifest_path)
            verdict = record["manifest"].get("verdict")
            if isinstance(verdict, dict):
                verdict = verdict.get("status") or verdict.get("value")
            run_status = "completed" if record["success"] else str(verdict or "failed")
            _insert_document(conn, (manifest_id, "run_manifest", manifest_path, None, manifest_hash, git_commit, run_status))
            _insert_entity(conn, (manifest_id, "run_manifest", manifest_path, None, run_status))
            _add_relation(conn, topic_id, "contains_run", manifest_id, topic_path, manifest_path)
            conn.execute(
                "INSERT OR REPLACE INTO runs(run_id,experiment_ref,status,model,context_length,raw_ref_path,raw_ref_hash,raw_ref_commit) VALUES(?,?,?,?,?,?,?,?)",
                (record["run_key"], record["topic_slug"], run_status, record["manifest"].get("model"),
                 record["manifest"].get("context_length"), "", "", ""),
            )
            for key, path in record["topic_files"].items():
                doc_type = "run_summary" if key == "run_summary" else "runtime_state"
                if not os.path.isfile(_join_relative(root, path)):
                    continue
                doc_id = _document_id(key, record)
                digest = _actual_hash(root, path)
                _insert_document(conn, (doc_id, doc_type, path, None, digest, git_commit, "valid"))
                _insert_entity(conn, (doc_id, doc_type, path, None, "valid"))

            # Source artifacts are useful even for STOP_BUDGET/STOP_ERROR
            # runs.  Provenance edges to report/graph are added below only
            # when those successful-run entities exist.
            source_rows: List[Tuple[str, str, Optional[str], str]] = []
            for source in record["sources"]:
                raw_path = source["path"]
                raw_hash = source["artifact_sha256"] or _actual_hash(root, raw_path)
                source_id = _document_id("source", record, hashlib.sha256(raw_path.encode("utf-8")).hexdigest()[:16])
                source_status = "valid" if raw_hash else "missing"
                _insert_document(conn, (source_id, "source_artifact", raw_path, record["run_id"], raw_hash, git_commit, source_status))
                _insert_entity(conn, (source_id, "source_artifact", raw_path, record["run_id"], source["evidence_kind"]))
                source_rows.append((source_id, raw_path, raw_hash, source["evidence_kind"]))

            if not record["success"]:
                continue
            canonical = record["canonical"]
            report_path, report_pin, _ = canonical["report"]
            report_id = _document_id("report", record)
            # Keep the manifest pin as the document hash.  Reindexing after a
            # mutation must not bless the mutated bytes as a new canonical
            # artifact.
            report_hash = report_pin or _actual_hash(root, report_path)
            _insert_document(conn, (report_id, record["report_type"], report_path, record["run_id"], report_hash, git_commit,
                                    "fresh" if record["report_type"] == "report_current" else "frozen"))
            _insert_entity(conn, (report_id, record["report_type"], report_path, record["run_id"],
                                  "fresh" if record["report_type"] == "report_current" else "frozen"))
            graph_path, graph_pin, _ = canonical["graph"]
            graph_id = _document_id("graph", record)
            graph_hash = graph_pin or _actual_hash(root, graph_path)
            _insert_document(conn, (graph_id, "evidence_graph", graph_path, record["run_id"], graph_hash, git_commit,
                                    "valid" if graph_hash else "missing"))
            _insert_entity(conn, (graph_id, "evidence_graph", graph_path, record["run_id"], "valid" if graph_hash else "missing"))
            sources_path, sources_pin, _ = canonical["sources"]
            sources_id = _document_id("sources", record)
            sources_hash = sources_pin or _actual_hash(root, sources_path)
            _insert_document(conn, (sources_id, "sources_manifest", sources_path, record["run_id"], sources_hash, git_commit,
                                    "valid" if sources_hash else "missing"))
            _insert_entity(conn, (sources_id, "sources_manifest", sources_path, record["run_id"], "valid" if sources_hash else "missing"))
            _add_relation(conn, report_id, "based_on", graph_id, report_path, graph_path)
            # Preserve the manifest-declared provenance even when the graph
            # has been deleted; reconcile can then report SOURCE_MISSING.
            _add_source_ref(conn, report_id, report_path, graph_path, graph_hash, "evidence_graph")
            for source_id, raw_path, raw_hash, evidence_kind in source_rows:
                _add_relation(conn, report_id, "based_on", source_id, report_path, raw_path)
                _add_relation(conn, graph_id, "based_on", source_id, graph_path, raw_path)
                _add_source_ref(conn, report_id, report_path, raw_path, raw_hash, evidence_kind)
                _add_source_ref(conn, graph_id, graph_path, raw_path, raw_hash, evidence_kind)
        watermark["index_complete"] = "1"
        _write_metadata(conn, watermark)
        conn.commit()
        return watermark
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _read_metadata(conn: sqlite3.Connection) -> Dict[str, Any]:
    return dict(conn.execute("SELECT key,value FROM index_metadata").fetchall())


def _watermark_from_conn(conn: sqlite3.Connection, root: str) -> Dict[str, Any]:
    values = _read_metadata(conn)
    return {
        "layout": values.get("layout", "research-tool"),
        "index_built_at": values.get("index_built_at"),
        "last_event_id": values.get("last_event_id") or None,
        "index_complete": values.get("index_complete") == "1",
        "drift": values.get("drift") == "1",
        "scan_fingerprint": values.get("scan_fingerprint"),
    }


def _layout_is_fresh(root: str, conn: sqlite3.Connection) -> Tuple[bool, Dict[str, Any]]:
    watermark = _watermark_from_conn(conn, root)
    current = research_tool_fingerprint(root)
    drift = not watermark.get("scan_fingerprint") or current != watermark.get("scan_fingerprint")
    watermark["drift"] = drift
    return bool(watermark.get("index_complete")) and not drift, watermark


def _layout_source_status(root: str, path: str, expected: str) -> Tuple[str, str, Optional[str]]:
    full = _join_relative(root, path)
    if not os.path.isfile(full):
        return "SOURCE_MISSING", f"无法定位 source artifact: {path}", None
    actual = file_hash(full)
    if expected and actual != expected:
        return "HASH_MISMATCH", f"{path} hash 不匹配: recorded={expected[:16]} actual={(actual or '')[:16]}", actual
    return "ok", f"{path} 校验通过", actual


def _layout_doc_issues(conn: sqlite3.Connection, root: str) -> List[dict]:
    issues: List[dict] = []
    for doc_id, doc_type, path, expected in conn.execute(
        "SELECT id,doc_type,path,content_hash FROM documents"
    ).fetchall():
        if not path:
            continue
        full = _join_relative(root, path)
        if doc_type == "topic":
            if not os.path.isdir(full):
                issues.append({"issue": "SOURCE_MISSING", "owner": doc_id, "ref": path, "scope": doc_type,
                               "detail": f"主题目录不存在: {path}"})
            continue
        if not os.path.isfile(full):
            issues.append({"issue": "SOURCE_MISSING", "owner": doc_id, "ref": path, "scope": doc_type,
                           "detail": f"索引登记的文件不存在: {path}"})
            continue
        if expected:
            actual = file_hash(full)
            if actual != expected:
                issues.append({"issue": "HASH_MISMATCH", "owner": doc_id, "ref": path, "scope": doc_type,
                               "detail": f"{path} hash 不匹配: recorded={expected[:16]} actual={(actual or '')[:16]}"})
    return issues


def _layout_ref_issues(conn: sqlite3.Connection, root: str) -> List[dict]:
    issues: List[dict] = []
    for owner, ref_path, expected, section in conn.execute(
        "SELECT owner,ref_path,content_hash,section FROM source_refs"
    ).fetchall():
        status, detail, _ = _layout_source_status(root, ref_path, expected or "")
        if status != "ok":
            issues.append({"issue": status, "owner": owner, "ref": ref_path,
                           "scope": section or "provenance", "detail": detail})
    return issues


def reconcile_research_tool(root: str, db_path: str, gitdir: Optional[str] = None) -> dict:
    """Reconcile research-tool canonical files without legacy sidecar rules."""
    if not os.path.isfile(db_path):
        return QueryResult(
            query_type="reconcile", status="fail_closed", authority="unresolved",
            source_watermark={"layout": "research-tool", "drift": True}, results=[{"issues": [{
                "issue": "INDEX_STALE", "owner": None, "ref": None, "scope": "index",
                "detail": f"索引不存在: {db_path}",
            }], "issue_count": 1, "hard_fail": True}],
            errors=[{"code": "INDEX_STALE", "detail": "索引不存在或尚未构建"}], error_semantic="INDEX_STALE",
        ).to_dict()
    conn = sqlite3.connect(db_path)
    try:
        fresh, watermark = _layout_is_fresh(root, conn)
        issues: List[dict] = []
        if not fresh:
            issues.append({"issue": "DRIFT_DETECTED", "owner": None, "ref": None, "scope": "index",
                           "detail": "research-tool 索引 fingerprint 与 canonical 文件不一致（需 reindex）"})
        issues.extend(_layout_doc_issues(conn, root))
        issues.extend(_layout_ref_issues(conn, root))
        hard_codes = {"INDEX_STALE", "DRIFT_DETECTED", "SOURCE_MISSING", "HASH_MISMATCH", "PROVENANCE_BROKEN", "LAYOUT_INVALID"}
        hard_fail = any(issue["issue"] in hard_codes for issue in issues)
        status = "fail_closed" if hard_fail else ("warning" if issues else "success")
        errors = [{"code": issue["issue"], "detail": issue["detail"]} for issue in issues if issue["issue"] in hard_codes]
        error_semantic = errors[0]["code"] if errors else None
        result = [{"issues": issues, "issue_count": len(issues), "hard_fail": hard_fail}]
        return QueryResult(
            query_type="reconcile", status=status, authority="derived", source_watermark=watermark,
            results=result, warnings=[] if not issues else [{"code": i["issue"], "detail": i["detail"]} for i in issues if i["issue"] not in hard_codes],
            errors=errors, error_semantic=error_semantic,
        ).to_dict()
    finally:
        conn.close()


def generate_research_tool_index(root: str, db_path: Optional[str] = None, write_file: bool = True):
    """Generate a deterministic topic/run navigation page after freshness checks."""
    actual_db = db_path or os.path.join(root, ".index", "research.sqlite")
    if not os.path.isfile(actual_db):
        return {"status": "fail_closed", "error_semantic": "INDEX_STALE", "detail": "base index is stale or missing"}
    conn = sqlite3.connect(actual_db)
    try:
        fresh, _ = _layout_is_fresh(root, conn)
        if not fresh:
            return {"status": "fail_closed", "error_semantic": "INDEX_STALE", "detail": "base index is stale or missing"}
        topic_rows = conn.execute("SELECT id,path FROM documents WHERE doc_type='topic' ORDER BY id").fetchall()
        run_rows = conn.execute(
            "SELECT id,doc_type,path,status FROM documents WHERE doc_type='run_manifest' ORDER BY path"
        ).fetchall()
        report_rows = conn.execute(
            "SELECT id,doc_type,path,status FROM documents WHERE doc_type IN ('report_current','report_historical') ORDER BY path"
        ).fetchall()
        graph_rows = conn.execute(
            "SELECT id,path,status FROM documents WHERE doc_type='evidence_graph' ORDER BY path"
        ).fetchall()
        lines = [
            "# INDEX — research-tool 导航（可重建，不是证据）",
            "",
            "> 本文件由 ResearchCTL 从 research-tool canonical 输出生成。",
            "> SQLite 与 INDEX.md 均为派生物；真实性以 manifest 与 canonical artifact 为准。",
            "",
            "## Topics",
            "",
        ]
        if topic_rows:
            lines.extend(f"- `{topic_id}` → `{path}`" for topic_id, path in topic_rows)
        else:
            lines.append("- （暂无主题）")
        lines.extend(["", "## Runs", ""])
        if run_rows:
            for run_id, _doc_type, path, status in run_rows:
                lines.append(f"- `{run_id}` ({status}) → `{path}`")
        else:
            lines.append("- （暂无运行）")
        lines.extend(["", "## Reports", ""])
        if report_rows:
            for report_id, doc_type, path, status in report_rows:
                lines.append(f"- `{report_id}` ({doc_type}, {status}) → `{path}`")
        else:
            lines.append("- （暂无报告）")
        lines.extend(["", "## Evidence graphs", ""])
        if graph_rows:
            for graph_id, path, status in graph_rows:
                lines.append(f"- `{graph_id}` ({status}) → `{path}`")
        else:
            lines.append("- （暂无证据图）")
        content = "\n".join(lines) + "\n"
        if write_file:
            index_path = os.path.join(root, "index", "INDEX.md")
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            with open(index_path, "w", encoding="utf-8") as handle:
                handle.write(content)
        return content
    finally:
        conn.close()
