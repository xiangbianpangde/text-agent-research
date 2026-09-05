"""Strict loader for the independent oracle-manifest/v1 contract."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

from .time import TimestampError, parse_rfc3339


class ManifestError(ValueError):
    """The authored Oracle manifest is malformed or ambiguous."""


TOP_KEYS = frozenset({
    "schema_version", "universe_id", "clock", "fixture", "event_ids", "queries", "entities",
    "artifacts", "facts", "evidence_atoms", "relations", "snapshots",
    "external_sources",
})
FIXTURE_KEYS = frozenset({"source_archive", "source_hash", "archive", "format", "content_hash"})
QUERY_KEYS = frozenset({
    "query_id", "operation", "target_ref", "text", "as_of", "participant_locator",
    "predicates", "relation_types", "route_sequence", "ranking_authority", "change_type",
})
OBJECT_KEYS = frozenset({
    "ref", "kind", "entity_id", "version_ref", "path", "status",
    "content_hash", "lifecycle_start", "git_commit",
})
FACT_KEYS = frozenset({"fact_id", "subject", "predicate", "value", "occurred_at"})
EVIDENCE_KEYS = frozenset({
    "atom_id", "kind", "artifact_ref", "row_key", "column", "value_type",
    "value", "argv",
})
RELATION_KEYS = frozenset({"source_ref", "target_ref", "relation"})
SNAPSHOT_KEYS = frozenset({"snapshot_id", "as_of", "paths"})
EXTERNAL_KEYS = frozenset({
    "ref", "pinned_content_hash", "pinned_value", "latest_content_hash", "latest_value",
})


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _exact_keys(value: Any, keys: Iterable[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{label} must be an object")
    expected = set(keys)
    actual = set(value)
    if actual != expected:
        raise ManifestError(f"{label} keys mismatch: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")
    return value


def _allowed_keys(value: Any, allowed: Iterable[str], required: Iterable[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{label} must be an object")
    actual = set(value)
    allowed_set = set(allowed)
    required_set = set(required)
    if actual - allowed_set or required_set - actual:
        raise ManifestError(
            f"{label} keys mismatch: missing={sorted(required_set-actual)}, extra={sorted(actual-allowed_set)}"
        )
    return value


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{label} must be a non-empty string")
    return value


def _unique(rows: Iterable[Mapping[str, Any]], key: str, label: str) -> None:
    seen = set()
    for row in rows:
        value = row[key]
        if value in seen:
            raise ManifestError(f"duplicate {label}: {value}")
        seen.add(value)


@dataclasses.dataclass(frozen=True)
class OracleManifest:
    document: Mapping[str, Any]
    digest: str
    path: str

    @property
    def refs(self) -> Tuple[str, ...]:
        return tuple(row["ref"] for row in (*self.document["entities"], *self.document["artifacts"]))

    def query(self, query_id: str) -> Mapping[str, Any]:
        matches = [row for row in self.document["queries"] if row["query_id"] == query_id]
        if len(matches) != 1:
            raise ManifestError(f"unknown or ambiguous query_id: {query_id}")
        return matches[0]


def validate_manifest(document: Any, *, path: str = "<memory>") -> OracleManifest:
    doc = _exact_keys(document, TOP_KEYS, "oracle manifest")
    if doc["schema_version"] != "oracle-manifest/v1":
        raise ManifestError("unsupported oracle manifest schema_version")
    _nonempty(doc["universe_id"], "universe_id")
    _nonempty(doc["clock"], "clock")
    try:
        parse_rfc3339(doc["clock"], "clock")
    except TimestampError as exc:
        raise ManifestError(str(exc)) from exc
    if not isinstance(doc["event_ids"], list) or any(not isinstance(value, str) or not value for value in doc["event_ids"]):
        raise ManifestError("event_ids must be a non-empty string array")
    fixture = _exact_keys(doc["fixture"], FIXTURE_KEYS, "fixture")
    _nonempty(fixture["source_archive"], "fixture.source_archive")
    source_hash = _nonempty(fixture["source_hash"], "fixture.source_hash")
    if not source_hash.startswith("sha256:") or len(source_hash) != 71:
        raise ManifestError("fixture.source_hash must be a sha256 digest")
    _nonempty(fixture["archive"], "fixture.archive")
    if fixture["format"] != "tar":
        raise ManifestError("fixture.format must be tar")
    content_hash = _nonempty(fixture["content_hash"], "fixture.content_hash")
    if not content_hash.startswith("sha256:") or len(content_hash) != 71:
        raise ManifestError("fixture.content_hash must be a sha256 digest")
    for field in ("queries", "entities", "artifacts", "facts", "evidence_atoms", "relations", "snapshots", "external_sources"):
        if not isinstance(doc[field], list):
            raise ManifestError(f"{field} must be an array")

    objects = []
    for field in ("entities", "artifacts"):
        for index, raw in enumerate(doc[field]):
            row = _exact_keys(raw, OBJECT_KEYS, f"{field}[{index}]")
            for key in ("ref", "kind", "entity_id", "status"):
                _nonempty(row[key], f"{field}[{index}].{key}")
            for key in ("version_ref", "path", "content_hash", "git_commit"):
                if row[key] is not None and not isinstance(row[key], str):
                    raise ManifestError(f"{field}[{index}].{key} must be string or null")
            try:
                parse_rfc3339(row["lifecycle_start"], f"{field}[{index}].lifecycle_start")
            except TimestampError as exc:
                raise ManifestError(str(exc)) from exc
            objects.append(row)
    _unique(objects, "ref", "object ref")
    known_refs = {row["ref"] for row in objects}

    queries = []
    for index, raw in enumerate(doc["queries"]):
        row = _allowed_keys(raw, QUERY_KEYS, QUERY_KEYS - {"change_type"}, f"queries[{index}]")
        for key in ("query_id", "operation"):
            _nonempty(row[key], f"queries[{index}].{key}")
        if row["target_ref"] is not None:
            _nonempty(row["target_ref"], f"queries[{index}].target_ref")
        for key in ("text", "as_of", "participant_locator", "ranking_authority", "change_type"):
            if row.get(key) is not None and not isinstance(row.get(key), str):
                raise ManifestError(f"queries[{index}].{key} must be string or null")
        for key in ("predicates", "relation_types", "route_sequence"):
            if not isinstance(row[key], list) or any(not isinstance(value, str) for value in row[key]):
                raise ManifestError(f"queries[{index}].{key} must be a string array")
        if row["operation"] == "query_text_semantic" and row["target_ref"] is not None:
            raise ManifestError("semantic queries derive relevance from facts and cannot declare target_ref")
        if row.get("as_of") is not None:
            try:
                parse_rfc3339(row["as_of"], f"queries[{index}].as_of")
            except TimestampError as exc:
                raise ManifestError(str(exc)) from exc
        if row["target_ref"] in known_refs and row["participant_locator"] is not None:
            obj = next(item for item in objects if item["ref"] == row["target_ref"])
            aliases = {obj["ref"], obj["entity_id"], obj.get("version_ref"), obj.get("path")}
            if row["participant_locator"] not in aliases:
                raise ManifestError(
                    f"queries[{index}] participant_locator does not identify target_ref"
                )
        queries.append(row)
    _unique(queries, "query_id", "query_id")

    facts = []
    for index, raw in enumerate(doc["facts"]):
        row = _exact_keys(raw, FACT_KEYS, f"facts[{index}]")
        for key in ("fact_id", "subject", "predicate", "occurred_at"):
            _nonempty(row[key], f"facts[{index}].{key}")
        if row["subject"] not in known_refs:
            raise ManifestError(f"facts[{index}].subject is unknown")
        try:
            parse_rfc3339(row["occurred_at"], f"facts[{index}].occurred_at")
        except TimestampError as exc:
            raise ManifestError(str(exc)) from exc
        if row["predicate"] == "introduced_event" and row["value"] not in doc["event_ids"]:
            raise ManifestError(f"facts[{index}] references an unknown event id")
        if row["predicate"] == "authority_source" and row["value"] not in {
            source["ref"] for source in doc["external_sources"]
        }:
            raise ManifestError(f"facts[{index}] references an unknown external source")
        if row["predicate"] == "bound_version" and row["value"] not in {
            obj.get("version_ref") for obj in objects if obj.get("version_ref")
        }:
            raise ManifestError(f"facts[{index}] references an unknown version")
        if row["predicate"] == "lifecycle_start":
            obj = next(item for item in objects if item["ref"] == row["subject"])
            if parse_rfc3339(row["value"], f"facts[{index}].value") != parse_rfc3339(obj["lifecycle_start"]):
                raise ManifestError(f"facts[{index}] lifecycle_start conflicts with object authority")
        facts.append(row)
    _unique(facts, "fact_id", "fact_id")

    atoms = []
    for index, raw in enumerate(doc["evidence_atoms"]):
        row = _exact_keys(raw, EVIDENCE_KEYS, f"evidence_atoms[{index}]")
        _nonempty(row["atom_id"], f"evidence_atoms[{index}].atom_id")
        if row["kind"] not in ("metric_cell", "command"):
            raise ManifestError("evidence atom kind must be metric_cell or command")
        _nonempty(row["artifact_ref"], f"evidence_atoms[{index}].artifact_ref")
        if row["artifact_ref"] not in known_refs:
            raise ManifestError(f"evidence_atoms[{index}].artifact_ref is unknown")
        if not isinstance(row["row_key"], list):
            raise ManifestError("evidence row_key must be an array")
        if row["argv"] is not None and (not isinstance(row["argv"], list) or any(not isinstance(v, str) for v in row["argv"])):
            raise ManifestError("evidence argv must be a string array or null")
        atoms.append(row)
    _unique(atoms, "atom_id", "atom_id")

    for index, raw in enumerate(doc["relations"]):
        row = _exact_keys(raw, RELATION_KEYS, f"relations[{index}]")
        for key in RELATION_KEYS:
            _nonempty(row[key], f"relations[{index}].{key}")
        if row["source_ref"] not in known_refs or row["target_ref"] not in known_refs:
            raise ManifestError(f"relations[{index}] references an unknown object")

    snapshots = []
    for index, raw in enumerate(doc["snapshots"]):
        row = _exact_keys(raw, SNAPSHOT_KEYS, f"snapshots[{index}]")
        _nonempty(row["snapshot_id"], f"snapshots[{index}].snapshot_id")
        _nonempty(row["as_of"], f"snapshots[{index}].as_of")
        try:
            parse_rfc3339(row["as_of"], f"snapshots[{index}].as_of")
        except TimestampError as exc:
            raise ManifestError(str(exc)) from exc
        if not isinstance(row["paths"], list) or any(not isinstance(v, str) or not v for v in row["paths"]):
            raise ManifestError("snapshot paths must be non-empty strings")
        snapshots.append(row)
    _unique(snapshots, "snapshot_id", "snapshot_id")

    externals = []
    for index, raw in enumerate(doc["external_sources"]):
        row = _exact_keys(raw, EXTERNAL_KEYS, f"external_sources[{index}]")
        for key in ("ref", "pinned_content_hash", "latest_content_hash"):
            _nonempty(row[key], f"external_sources[{index}].{key}")
        externals.append(row)
    _unique(externals, "ref", "external source ref")

    return OracleManifest(document=dict(doc), digest=digest_json(doc), path=path)


def load_manifest(path: str | Path) -> OracleManifest:
    source = Path(path)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot load oracle manifest {source}: {exc}") from exc
    return validate_manifest(document, path=str(source))
