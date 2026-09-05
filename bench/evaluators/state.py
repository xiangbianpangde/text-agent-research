"""Independent canonical-path snapshots for crash/recovery checks."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable


class StateObservationError(RuntimeError):
    pass


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def snapshot_paths(workspace: str, paths: Iterable[str]) -> Dict[str, Any]:
    root = Path(workspace).resolve()
    files: Dict[str, str] = {}
    for relative in paths:
        base = (root / relative).resolve()
        if os.path.commonpath([str(root), str(base)]) != str(root):
            raise StateObservationError("snapshot path escapes workspace")
        if base.is_file():
            files[relative] = _hash_file(base)
        elif base.is_dir():
            for path in sorted(p for p in base.rglob("*") if p.is_file() and not p.is_symlink()):
                files[path.relative_to(root).as_posix()] = _hash_file(path)
    payload = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"files": files, "canonical_digest": "sha256:" + hashlib.sha256(payload).hexdigest()}


# Frozen by the public benchmark specification §6.7. Do not substitute the
# participant's current columns or dynamically omit missing fields.
CLE_PROFILE = (
    ("documents", ("id", "doc_type", "path", "content_hash", "git_commit", "section", "parent_id", "status", "meta_json"), ("id",)),
    ("entities", ("id", "entity_type", "version", "path", "content_hash", "spec_ref", "status"), ("id", "version")),
    ("relations", ("source_id", "target_id", "relation_type", "authority"), ("source_id", "target_id", "relation_type")),
    ("runs", ("run_id", "experiment_id", "experiment_ref", "model", "context_length", "seed", "status", "reason"), ("run_id",)),
    ("source_refs", ("owner_id", "ref_path", "ref_commit", "content_hash", "relation_type"), ("owner_id", "ref_path", "content_hash")),
    ("events", ("event_id", "event_type", "timestamp", "actor", "payload_json"), ("event_id",)),
)


def _normalize_sql(value: Any) -> Any:
    if value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StateObservationError("CLE rejects NaN and Infinity")
        if value == 0:
            value = 0.0
        return f"{value:.6f}"
    if isinstance(value, bytes):
        return "hex:" + value.hex()
    return unicodedata.normalize("NFC", str(value))


def canonical_index_digest(db_path: str) -> Dict[str, Any]:
    """Fixed-profile logical dump; no dynamic column omission or physical DB hash."""
    if not os.path.isfile(db_path):
        return {"index_present": False, "cle_digest": None}
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        lines = []
        for table, columns, sort_keys in CLE_PROFILE:
            existing = {
                row[1] for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            }
            missing = set(columns) - existing
            if missing:
                raise StateObservationError(f"CLE schema mismatch in {table}: missing {sorted(missing)}")
            select = ",".join(f'"{column}"' for column in columns)
            ordering = ",".join(f'"{column}" ASC' for column in sort_keys)
            for row in connection.execute(f'SELECT {select} FROM "{table}" ORDER BY {ordering}'):
                payload = {column: _normalize_sql(value) for column, value in zip(columns, row)}
                lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        data = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        return {"index_present": True, "cle_digest": "sha256:" + hashlib.sha256(data).hexdigest()}
    finally:
        connection.close()


def tx_residue_empty(workspace: str) -> bool:
    tx_dir = Path(workspace) / ".index" / "tx"
    if not tx_dir.exists():
        return True
    ignored_suffixes = (".lock",)
    for path in tx_dir.rglob("*"):
        if path.is_file() and not path.name.endswith(ignored_suffixes):
            return False
    return True
