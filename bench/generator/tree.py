"""Physical tree specification and bench-tree/v1 hash calculation (§19.4)."""
from __future__ import annotations

import hashlib
import os
import stat
import unicodedata
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .frame import encode_frame, encode_string_frame, encode_u16_frame


ALLOWED_MODES = frozenset({0o644, 0o755})


def normalize_tree_path(raw_path: str) -> str:
    """Validate and normalize a relative POSIX file path for bench-tree/v1."""
    if not raw_path:
        raise ValueError("empty path is forbidden")
    if raw_path.startswith("/") or raw_path.startswith("\\"):
        raise ValueError(f"leading slash forbidden in tree path: {raw_path!r}")
    if "\x00" in raw_path:
        raise ValueError(f"NUL byte in path: {raw_path!r}")

    parts = raw_path.split("/")
    norm_parts: List[str] = []
    for part in parts:
        if part in ("", ".", ".."):
            raise ValueError(f"invalid path component {part!r} in path {raw_path!r}")
        # AppleDouble forbidden
        if part.startswith("._"):
            raise ValueError(f"AppleDouble file forbidden in tree: {raw_path!r}")
        nfc_part = unicodedata.normalize("NFC", part)
        norm_parts.append(nfc_part)

    norm_path = "/".join(norm_parts)

    # §19.4 Reserved Namespace rule:
    # "严禁包含子串 .tmp. 或以 .tmp 结尾"
    if ".tmp." in norm_path or norm_path.endswith(".tmp"):
        raise ValueError(f"reserved namespace path forbidden in tree: {norm_path!r}")

    return norm_path


def validate_tree_paths(paths: Sequence[str]) -> List[str]:
    """Validate uniqueness and prefix conflict freedom on a collection of paths."""
    seen: Dict[str, str] = {}
    normalized: List[str] = []

    for p in paths:
        norm = normalize_tree_path(p)
        if norm in seen:
            raise ValueError(f"duplicate or NFC-colliding path in tree: {norm!r} (from {p!r} and {seen[norm]!r})")
        seen[norm] = p
        normalized.append(norm)

    # Check prefix conflict: no file path can be a directory prefix of another
    # e.g., 'a' and 'a/b' is a prefix conflict
    sorted_paths = sorted(normalized)
    for i in range(len(sorted_paths) - 1):
        curr = sorted_paths[i]
        nxt = sorted_paths[i + 1]
        if nxt.startswith(curr + "/"):
            raise ValueError(f"prefix conflict in tree between file {curr!r} and {nxt!r}")

    return sorted_paths


def build_tree_record(path: str, mode: int, content: bytes) -> bytes:
    """Build a bench-tree/v1 binary record for one regular file."""
    norm_path = normalize_tree_path(path)
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported mode {oct(mode)}: only 0o644 and 0o755 are allowed")
    return (
        encode_string_frame("path", norm_path)
        + encode_u16_frame("mode", mode)
        + encode_frame("content", content)
    )


def compute_bench_tree_digest_from_entries(entries: Mapping[str, Tuple[int, bytes]]) -> str:
    """Compute bench-tree/v1 digest from in-memory file entries {rel_path: (mode, content)}."""
    norm_paths = validate_tree_paths(list(entries.keys()))
    # Sort paths strictly by UTF-8 bytes ascending
    sorted_norm_paths = sorted(norm_paths, key=lambda p: p.encode("utf-8"))

    hasher = hashlib.sha256()
    for norm_path in sorted_norm_paths:
        mode, content = entries[norm_path]
        record = build_tree_record(norm_path, mode, content)
        hasher.update(record)

    return f"sha256:{hasher.hexdigest()}"


def compute_bench_tree_digest_from_dir(root_dir: Union[str, Path]) -> str:
    """Walk a local directory, validate all regular files, and compute bench-tree/v1 digest."""
    root = Path(root_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"root_dir must be an existing directory: {root}")

    entries: Dict[str, Tuple[int, bytes]] = {}
    found_any = False

    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        rel_dir = current_dir.relative_to(root)

        # Check for empty directories
        if not dirnames and not filenames and current_dir != root:
            raise ValueError(f"empty directory forbidden in bench tree: {rel_dir.as_posix()!r}")

        for fname in filenames:
            file_path = current_dir / fname
            # Check for symlinks or other non-regular files
            if file_path.is_symlink():
                raise ValueError(f"symbolic links forbidden in bench tree: {file_path}")
            st = file_path.stat()
            if not stat.S_ISREG(st.st_mode):
                raise ValueError(f"non-regular file forbidden in bench tree: {file_path}")

            # Normalize mode to 0o755 or 0o644
            mode = 0o755 if (st.st_mode & 0o111) else 0o644
            rel_file = file_path.relative_to(root).as_posix()
            content = file_path.read_bytes()
            entries[rel_file] = (mode, content)
            found_any = True

    return compute_bench_tree_digest_from_entries(entries)
