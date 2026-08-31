"""内容 hash 计算（P0-Contract §4 / §7 / §11）。

- file hash:      SHA-256(file bytes)
- directory hash: 对排序后的文件 manifest（相对路径 + 各文件 SHA-256）整体 SHA-256
  - 按 POSIX 相对路径排序（UTF-8 字典序）
  - 每行格式: <relative_path>:<sha256_hex>
  - 换行符: LF (0x0a)，无尾随空行
"""
from __future__ import annotations

import hashlib
from typing import Dict, Tuple


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def file_hash(path: str) -> str:
    """读取文件字节并返回 file hash。文件不存在返回 None。"""
    try:
        with open(path, "rb") as f:
            return sha256_bytes(f.read())
    except FileNotFoundError:
        return None


def dir_manifest_hash(files: Dict[str, bytes]) -> Tuple[str, str]:
    """按合同 §4 序列化规则计算目录 manifest hash。

    files: {相对路径(UTF-8): 字节内容}
    返回 (manifest 字符串, "sha256:..." 目录 hash)
    """
    lines = []
    for rel in sorted(files.keys(), key=lambda s: s.encode("utf-8")):
        h = hashlib.sha256(files[rel]).hexdigest()
        lines.append(f"{rel}:{h}")
    manifest = "\n".join(lines)  # LF 换行，无尾随空行
    return manifest, "sha256:" + hashlib.sha256(manifest.encode("utf-8")).hexdigest()
