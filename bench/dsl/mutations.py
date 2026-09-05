"""Benchmark-owned physical mutations; these change the test world, not Gold."""
from __future__ import annotations

import os
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
    raise MutationError(f"unsupported physical mutation: {kind}")
