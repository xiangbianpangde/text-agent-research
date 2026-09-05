"""Benchmark-owned physical mutations; these change the test world, not Gold."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Mapping

from bench.oracle.manifest import OracleManifest


class MutationError(RuntimeError):
    pass


def _safe_path(workspace: str, relative: str) -> Path:
    root = Path(workspace).resolve()
    candidate = (root / relative).resolve()
    if os.path.commonpath([str(root), str(candidate)]) != str(root):
        raise MutationError("mutation path escapes workspace")
    return candidate


def apply_physical_mutation(workspace: str, manifest: OracleManifest, action: Mapping[str, Any]) -> None:
    kind = action["type"]
    target = action["target"]
    state_objects = {
        row["ref"]: row for row in (*manifest.document["entities"], *manifest.document["artifacts"])
    }
    if kind == "semantic_change":
        return
    if kind == "external_update":
        obj = state_objects.get(target)
        if obj is None or not obj.get("path"):
            raise MutationError(f"external mutation target has no physical path: {target}")
        path = _safe_path(workspace, str(obj["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(action.get("content", "")), encoding="utf-8")
        return
    if kind == "create_version":
        path = _safe_path(workspace, str(action["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(action.get("content", "")), encoding="utf-8")
        return
    if kind == "duplicate_version":
        path = _safe_path(workspace, str(action["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(action.get("content", "")), encoding="utf-8")
        return
    if kind == "raw_invalidation":
        obj = state_objects.get(target)
        if obj is None or not obj.get("path"):
            raise MutationError(f"raw invalidation target has no physical path: {target}")
        directory = _safe_path(workspace, str(obj["path"]))
        directory.mkdir(parents=True, exist_ok=True)
        reason = str(action.get("reason", "benchmark invalidation"))
        (directory / "STATUS.yaml").write_text(
            f"status: invalid\nreason: {reason!r}\n", encoding="utf-8"
        )
        return
    obj = state_objects.get(target)
    if kind in ("delete_file", "tamper_file", "runtime_deviation", "semantic_tamper", "touch_file"):
        if obj is None or not obj.get("path"):
            raise MutationError(f"mutation target has no physical path: {target}")
        path = _safe_path(workspace, str(obj["path"]))
        if kind == "delete_file":
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        elif kind == "touch_file":
            os.utime(path, None)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(str(action.get("content", "\nBENCHMARK_MUTATION\n")))
        return
    if kind == "corrupt_index":
        import sqlite3
        db_path = _safe_path(workspace, ".index/research.sqlite")
        connection = sqlite3.connect(db_path)
        try:
            connection.execute("UPDATE index_metadata SET value='sha256:corrupt' WHERE key='scan_fingerprint'")
            connection.commit()
        finally:
            connection.close()
        return
    if kind == "create_file":
        path = _safe_path(workspace, target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(action.get("content", "")), encoding="utf-8")
        return
    if kind == "delete_tree":
        shutil.rmtree(_safe_path(workspace, target), ignore_errors=True)
        return
    raise MutationError(f"unsupported physical mutation: {kind}")
