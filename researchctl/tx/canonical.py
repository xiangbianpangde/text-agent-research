"""Canonical JSON 序列化与 canonical hash（P1-A-Contract §6.1）。

机器生成文件（Event/plan/marker/receipt/state/sources_manifest）统一：
  canonical_hash = sha256(canonical JSON bytes of parsed document)

序列化规则（§6.1）：
  1. 键按 UTF-8 字节字典序排序（递归）
  2. 数组保持原始顺序（source_refs 等由调用方先按全序排序）
  3. null 值字段省略（schema 约定「缺字段 ≡ 显式 null」）
  4. 空数组保留为 []
  5. 字符串 UTF-8 编码，不修改内容（不 trim）
  6. 布尔/数字不带引号
  7. 文件末尾无尾随换行
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _sort_key(key: str) -> bytes:
    """UTF-8 字节字典序排序键。"""
    return key.encode("utf-8")


def canonical_json(doc: Any) -> str:
    """将解析后的文档序列化为 canonical JSON 字符串。"""
    return _serialize(doc)


def _serialize(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for key in sorted(value.keys(), key=_sort_key):
            item = value[key]
            if item is None:
                continue  # null 省略（缺字段 ≡ 显式 null）
            parts.append(f'"{key}":{_serialize(item)}')
        return "{" + ",".join(parts) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_serialize(v) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    raise TypeError(f"unsupported type: {type(value)!r}")


def canonical_hash_bytes(data: bytes) -> str:
    """对给定字节计算 canonical hash 前缀。"""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_hash(doc: Any) -> str:
    """对解析后的文档计算 canonical hash。"""
    return canonical_hash_bytes(canonical_json(doc).encode("utf-8"))


def file_canonical_hash(path: str) -> str | None:
    """读取机器生成文件并计算其 canonical hash（解析 → canonical JSON → sha256）。"""
    from ..mini_yaml import load_file as yaml_load_file
    try:
        doc = yaml_load_file(path, strict=True)
    except FileNotFoundError:
        return None
    except Exception:
        return None
    return canonical_hash(doc)


def raw_bytes_hash(path: str) -> str | None:
    """人维护文件（report.md/CURRENT.md）按原始 bytes 计算 SHA-256。"""
    try:
        with open(path, "rb") as f:
            return canonical_hash_bytes(f.read())
    except FileNotFoundError:
        return None
