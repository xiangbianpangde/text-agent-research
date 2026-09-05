"""Strict loader for the independent oracle-manifest/v1 contract."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple


class ManifestError(ValueError):
    """The authored Oracle manifest is malformed or ambiguous."""


TOP_KEYS = frozenset({
    "schema_version", "universe_id", "clock", "entities", "artifacts",
    "facts", "evidence_atoms", "relations", "snapshots", "external_sources",
})
OBJECT_KEYS = frozenset({
    "ref", "kind", "entity_id", "version_ref", "path", "status",
    "content_hash", "git_commit",
})
FACT_KEYS = frozenset({"fact_id", "subject", "predicate", "value"})
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


def validate_manifest(document: Any, *, path: str = "<memory>") -> OracleManifest:
    doc = _exact_keys(document, TOP_KEYS, "oracle manifest")
    if doc["schema_version"] != "oracle-manifest/v1":
        raise ManifestError("unsupported oracle manifest schema_version")
    _nonempty(doc["universe_id"], "universe_id")
    _nonempty(doc["clock"], "clock")
    for field in ("entities", "artifacts", "facts", "evidence_atoms", "relations", "snapshots", "external_sources"):
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
            objects.append(row)
    _unique(objects, "ref", "object ref")

    facts = []
    for index, raw in enumerate(doc["facts"]):
        row = _exact_keys(raw, FACT_KEYS, f"facts[{index}]")
        for key in ("fact_id", "subject", "predicate"):
            _nonempty(row[key], f"facts[{index}].{key}")
        facts.append(row)
    _unique(facts, "fact_id", "fact_id")

    atoms = []
    for index, raw in enumerate(doc["evidence_atoms"]):
        row = _exact_keys(raw, EVIDENCE_KEYS, f"evidence_atoms[{index}]")
        _nonempty(row["atom_id"], f"evidence_atoms[{index}].atom_id")
        if row["kind"] not in ("metric_cell", "command"):
            raise ManifestError("evidence atom kind must be metric_cell or command")
        _nonempty(row["artifact_ref"], f"evidence_atoms[{index}].artifact_ref")
        if not isinstance(row["row_key"], list):
            raise ManifestError("evidence row_key must be an array")
        if row["argv"] is not None and (not isinstance(row["argv"], list) or any(not isinstance(v, str) for v in row["argv"])):
            raise ManifestError("evidence argv must be a string array or null")
        atoms.append(row)
    _unique(atoms, "atom_id", "atom_id")

    known_refs = {row["ref"] for row in objects}
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
