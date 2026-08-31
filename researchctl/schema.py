"""查询结果 Envelope 与错误语义（P0-Contract §2.2 / §3）。"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional


# ---- 错误语义枚举（P0-Contract §2.2） ----
ERROR_SEMANTICS = {
    "NOT_FOUND",              # 查询的 entity ID 不存在
    "AMBIGUOUS_VERSION",      # 同一 source 存在两个候选版本
    "SOURCE_MISSING",         # 指定 path / git_commit+path 无法定位
    "HASH_MISMATCH",          # 定位成功但字节 hash 不匹配
    "DRIFT_DETECTED",         # 派生索引与文件系统状态不一致
    "CURRENT_CONFLICT",       # CURRENT.md 与 sources.yaml 冲突
    "SOURCE_UNAVAILABLE",     # 有 locator/hash，但无法恢复字节
    "INDEX_STALE",            # 索引落后于文件系统（scan fingerprint 不一致）
    "PROVENANCE_BROKEN",      # 来源链某环断裂
    "SOURCE_CHANGED_SINCE_PIN",  # 历史版本可恢复，但当前路径已变化（drift warning）
}

# ---- 六轴状态（P0-Contract §5） ----
AXES = ["execution", "data", "research", "scientific", "task", "review"]


def empty_state() -> dict:
    """未适用轴为 None（P0 只验证实际使用的轴）。"""
    return {a: None for a in AXES}


class QueryResult:
    """P0-Contract §3 查询结果 Envelope。"""

    def __init__(
        self,
        query_type: str,
        status: str = "success",
        authority: str = "canonical",
        source_watermark: Optional[dict] = None,
        results: Optional[list] = None,
        warnings: Optional[list] = None,
        errors: Optional[list] = None,
        error_semantic: Optional[str] = None,
        as_of: Optional[str] = None,
    ) -> None:
        self.query_id = uuid.uuid4().hex[:12]
        self.query_type = query_type
        self.as_of = as_of or time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self.status = status            # success | warning | error | fail_closed
        self.authority = authority      # canonical | derived | unresolved
        self.source_watermark = source_watermark or {}
        self.results = results or []
        self.warnings = warnings or []
        self.errors = errors or []
        self.error_semantic = error_semantic

    def to_dict(self) -> dict:
        return {
            "query_id": self.query_id,
            "query_type": self.query_type,
            "as_of": self.as_of,
            "status": self.status,
            "authority": self.authority,
            "source_watermark": self.source_watermark,
            "results": self.results,
            "warnings": self.warnings,
            "errors": self.errors,
            "error_semantic": self.error_semantic,
        }


def result_item(
    entity_id: str,
    path: str,
    content_hash: Optional[str] = None,
    versioned_ref: Optional[str] = None,
    git_commit: Optional[str] = None,
    section: Optional[str] = None,
    status: Optional[dict] = None,
    relation_type: Optional[str] = None,
    is_stale: bool = False,
    is_available: bool = True,
) -> dict:
    """P0-Contract §3 ResultItem。"""
    return {
        "entity_id": entity_id,
        "versioned_ref": versioned_ref,
        "path": path,
        "content_hash": content_hash,
        "git_commit": git_commit,
        "section": section,
        "status": status or empty_state(),
        "relation_type": relation_type,
        "is_stale": is_stale,
        "is_available": is_available,
    }
