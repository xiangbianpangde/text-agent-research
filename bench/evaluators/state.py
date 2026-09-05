"""Independent canonical-path snapshots for crash/recovery checks."""
from __future__ import annotations

import hashlib
import json
import os
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


def tx_residue_empty(workspace: str) -> bool:
    tx_dir = Path(workspace) / ".index" / "tx"
    if not tx_dir.exists():
        return True
    ignored_suffixes = (".lock",)
    for path in tx_dir.rglob("*"):
        if path.is_file() and not path.name.endswith(ignored_suffixes):
            return False
    return True
