"""Source Reference 解析与校验（P0-Contract §4）。

定位与验证分离：
  path / git_commit 负责定位（找到字节的来源）
  content_hash 负责验证（确认字节未被篡改）

Current source:      path → 读取当前字节 → 校验 content_hash
Historical source:   git_commit + path → 恢复历史字节 → 校验 content_hash
                     （当前路径变化只记录 SOURCE_CHANGED_SINCE_PIN，不判历史损坏）
Directory source:    按合同 §4 目录 manifest hash 计算/校验
"""
from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional

from .hashing import dir_manifest_hash, file_hash, sha256_bytes


# ---- 底层字节获取 ----

def _git_show(gitdir: str, commit: str, path: str) -> Optional[bytes]:
    """git show <commit>:<path> 恢复历史字节。失败返回 None。"""
    try:
        out = subprocess.run(
            ["git", "-C", gitdir, "show", f"{commit}:{path}"],
            capture_output=True, check=True,
        )
        return out.stdout
    except subprocess.CalledProcessError:
        return None


def _git_list_files(gitdir: str, commit: str, dirpath: str) -> List[str]:
    """git ls-tree -r 列出目录下所有文件路径（相对 git root）。"""
    try:
        out = subprocess.run(
            ["git", "-C", gitdir, "ls-tree", "-r", "--name-only", commit, dirpath],
            capture_output=True, check=True, text=True,
        )
        return [p for p in out.stdout.splitlines() if p.strip()]
    except subprocess.CalledProcessError:
        return []


# ---- 目录 manifest 计算 ----

def _dir_files_from_fs(root: str, dirpath: str) -> Dict[str, bytes]:
    """从文件系统读取目录下所有文件（相对路径 → 字节）。"""
    files = {}
    base = os.path.join(root, dirpath)
    if not os.path.isdir(base):
        return {}
    for dirname, _subdirs, filenames in os.walk(base):
        for fn in filenames:
            full = os.path.join(dirname, fn)
            rel = os.path.relpath(full, base)
            with open(full, "rb") as f:
                files[rel] = f.read()
    return files


def _dir_files_from_git(gitdir: str, commit: str, dirpath: str) -> Dict[str, bytes]:
    """从 git 历史读取目录下所有文件（相对路径 → 字节）。"""
    files = {}
    for full in _git_list_files(gitdir, commit, dirpath):
        data = _git_show(gitdir, commit, full)
        if data is None:
            continue
        rel = os.path.relpath(full, dirpath)
        files[rel] = data
    return files


# ---- Source Reference 校验 ----

def verify_source_ref(ref: dict, root: str, gitdir: str) -> dict:
    """校验一条 source_ref。返回状态与详情。

    ref 字段: path, source_type(file|directory), content_hash,
              reference_scope(current|historical), git_commit(可选), section(可选)

    返回:
      status: ok | SOURCE_MISSING | HASH_MISMATCH | SOURCE_CHANGED_SINCE_PIN | SOURCE_UNAVAILABLE
      computed_hash: 计算得到的 hash
      current_changed: 当前路径文件与 pinned hash 是否已变化（历史引用）
      note: 说明
    """
    path = ref.get("path")
    source_type = ref.get("source_type", "file")
    scope = ref.get("reference_scope", "current")
    expected = ref.get("content_hash")
    commit = ref.get("git_commit")

    # 1. 定位：取目标字节（current 用文件系统，historical 用 git）
    if scope == "historical":
        if not commit:
            return {"status": "SOURCE_UNAVAILABLE", "note": "historical 引用缺少 git_commit"}
        if source_type == "file":
            data = _git_show(gitdir, commit, path)
        else:
            files = _dir_files_from_git(gitdir, commit, path)
            data = b"DIR" if files else None
    else:
        if source_type == "file":
            full = os.path.join(root, path)
            try:
                with open(full, "rb") as f:
                    data = f.read()
            except FileNotFoundError:
                data = None
        else:
            files = _dir_files_from_fs(root, path)
            data = b"DIR" if files else None

    if data is None:
        return {"status": "SOURCE_MISSING", "note": f"无法定位 {path}"}

    # 2. 计算实际 hash
    if source_type == "file":
        actual = sha256_bytes(data)
    else:
        files = _dir_files_from_git(gitdir, commit, path) if scope == "historical" else _dir_files_from_fs(root, path)
        if not files:
            return {"status": "SOURCE_MISSING", "note": f"目录为空或不存在 {path}"}
        _manifest, actual = dir_manifest_hash(files)

    # 3. 校验 hash
    if expected and actual != expected:
        return {"status": "HASH_MISMATCH", "computed_hash": actual,
                "note": f"{path} hash 不匹配: recorded={expected[:16]} actual={actual[:16]}"}

    # 4. 历史引用：检查当前路径是否已变化（drift warning，不判损坏）
    current_changed = False
    if scope == "historical":
        if source_type == "file":
            cur = file_hash(os.path.join(root, path))
            # 当前文件不存在也算已变化（从存在变为消失）
            current_changed = (cur is None) or (cur != expected)
        else:
            cur_files = _dir_files_from_fs(root, path)
            if not cur_files:
                current_changed = True
            else:
                _m, cur_h = dir_manifest_hash(cur_files)
                current_changed = (cur_h != expected)
        if current_changed:
            return {"status": "SOURCE_CHANGED_SINCE_PIN", "computed_hash": actual,
                    "current_changed": True,
                    "note": f"历史版本可恢复(@{commit[:8]})，但当前路径 {path} 已变化（含删除）"}

    return {"status": "ok", "computed_hash": actual, "current_changed": False,
            "note": f"{path} 校验通过 ({scope}, {source_type})"}
