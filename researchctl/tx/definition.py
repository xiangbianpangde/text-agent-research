"""Definition 文件操作（P1-B-Contract §1/§4.1）。

定义版本文件的读取、包装、identity validator、structural diff、successor 计算。
"""
from __future__ import annotations

import os
import re
from typing import Optional

from .canonical import canonical_hash, file_canonical_hash


# ---- 版本号处理 ----

_VERSION_RE = re.compile(r"^([A-Z][A-Za-z0-9_-]+)@v(\d+)$")


def successor(version: str) -> str:
    """H003@v1 → H003@v2（只依赖版本字符串，不读 repository state）。"""
    m = _VERSION_RE.fullmatch(version)
    if not m:
        raise ValueError(f"非法版本格式: {version}")
    entity, num = m.group(1), int(m.group(2))
    return f"{entity}@v{num + 1}"


def entity_of(version: str) -> str:
    """H003@v1 → H003。"""
    m = _VERSION_RE.fullmatch(version)
    if not m:
        raise ValueError(f"非法版本格式: {version}")
    return m.group(1)


def version_number(version: str) -> int:
    """H003@v1 → 1。"""
    m = _VERSION_RE.fullmatch(version)
    if not m:
        raise ValueError(f"非法版本格式: {version}")
    return int(m.group(2))


# ---- 定义文件路径 ----

def definition_dir(root: str, entity: str) -> str:
    return os.path.join(root, "definitions", entity)


def definition_path(root: str, entity: str, version: str) -> str:
    return os.path.join(definition_dir(root, entity), f"{version}.yaml")


def approved_path(root: str, entity: str) -> str:
    return os.path.join(definition_dir(root, entity), "APPROVED.yaml")


# ---- 读取 ----

def read_definition(root: str, entity: str, version: str) -> Optional[dict]:
    """读取定义版本文件，解析为 dict。"""
    from ..mini_yaml import load_file
    p = definition_path(root, entity, version)
    if not os.path.exists(p):
        return None
    try:
        return load_file(p, strict=True) or {}
    except Exception:
        return None


def read_approved(root: str, entity: str) -> Optional[dict]:
    """读取 APPROVED.yaml，返回 {definition, ref, approved_at, basis_git_commit}。"""
    from ..mini_yaml import load_file
    p = approved_path(root, entity)
    if not os.path.exists(p):
        return None
    try:
        return load_file(p, strict=True) or {}
    except Exception:
        return None


def read_approved_hash(root: str, entity: str) -> Optional[str]:
    """计算 live APPROVED.yaml 的 canonical hash。"""
    return file_canonical_hash(approved_path(root, entity))


# ---- 包装（body-only input → canonical version file） ----

_RESERVED_KEYS = {"entity_id", "version_ref", "previous", "schema_version"}


def wrap_definition_input(*, entity: str, previous: str, subject: str,
                          body: dict) -> dict:
    """将 body-only input 包装为 canonical 版本文件。

    检查 reserved key（entity_id/version_ref/previous/schema_version 在 body 中出现
    即视为 DEF_PAYLOAD_MISMATCH）。
    """
    for key in _RESERVED_KEYS:
        if key in body:
            raise ValueError(f"input payload 含 reserved key: {key}")
    return {
        "schema_version": 1,
        "entity_id": entity,
        "version_ref": subject,
        "previous": previous,
        "body": body,
    }


def validate_definition_identity(definition_file: dict, *,
                                 entity: str,
                                 expected_previous: str,
                                 candidate_subject: str) -> None:
    """验证 staged definition 文件内部 identity 与 CLI/Event/plan 一致。

    §2.3 j / §4.2 identity invariant。
    任一不一致 → raise ValueError("DEF_IDENTITY_MISMATCH: ...")。
    """
    errors = []
    if definition_file.get("entity_id") != entity:
        errors.append(f"entity_id: {definition_file.get('entity_id')} != {entity}")
    if definition_file.get("version_ref") != candidate_subject:
        errors.append(f"version_ref: {definition_file.get('version_ref')} != {candidate_subject}")
    if definition_file.get("previous") != expected_previous:
        errors.append(f"previous: {definition_file.get('previous')} != {expected_previous}")
    if errors:
        raise ValueError(f"DEF_IDENTITY_MISMATCH: {'; '.join(errors)}")


# ---- Structural diff（只 diff semantic body） ----

def _get_body(doc: dict) -> dict:
    """从定义文档中提取 body（如果 doc 的 body 是 dict，直接返回；否则返回空 dict）。"""
    body = doc.get("body", {})
    return body if isinstance(body, dict) else {}


def _field_paths(d: dict, prefix: str = "") -> list:
    """递归收集 body 中所有 field-path（用于 diff）。"""
    paths = []
    for key in sorted(d.keys()):
        full = f"{prefix}.{key}" if prefix else key
        val = d[key]
        if isinstance(val, dict):
            sub = _field_paths(val, full)
            if sub:
                paths.extend(sub)
            else:
                paths.append(full)
        else:
            paths.append(full)
    return paths


def structural_diff(prev_doc: dict, new_doc: dict) -> list:
    """确定性 structural diff，只 diff semantic body。

    返回 changed_fields 列表（field-path 数组），不包含 version_ref/previous/schema_version 等 metadata。
    prev_doc / new_doc 是完整定义文件（含 body）。
    若 body 为空或无变化，返回 []。
    """
    prev_body = _get_body(prev_doc)
    new_body = _get_body(new_doc)
    if prev_body == new_body:
        return []
    # 收集 changed field-paths
    prev_paths = set(_field_paths(prev_body))
    new_paths = set(_field_paths(new_body))
    added = new_paths - prev_paths
    removed = prev_paths - new_paths
    changed = set()
    for key in sorted(set(list(prev_paths) + list(new_paths))):
        prev_val = _get_value_at_path(prev_body, key)
        new_val = _get_value_at_path(new_body, key)
        if prev_val != new_val:
            changed.add(key)
    result = sorted(added | removed | changed)
    result.sort()
    return result


def _get_value_at_path(d: dict, path: str):
    """按 '.' 分隔的 field-path 取值。"""
    parts = path.split(".")
    current = d
    for p in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(p)
    return current


# ---- Predecessor hash 验证 ----

# 外部 pin 常量名（deployment config；不随仓库变动）
BOOTSTRAP_PIN_ENV = "RESEARCHCTL_BOOTSTRAP_COMMIT"
# 仓库外配置文件（root 的父目录，不在 git 仓库内）
BOOTSTRAP_PIN_FILENAME = "bootstrap-pin.yaml"


def bootstrap_pin_path(root: str) -> str:
    """外部 pin 文件路径：位于仓库之外（root 的父目录），不是 repo 内文件。

    rev11 §5.4 trust root = frozen deployment config 的不可变常量 bootstrap_commit，
    不从 BOOTSTRAP.yaml / repo 自身取得（杜绝 self-reference，Sol rev3 P1-1）。
    """
    parent = os.path.dirname(os.path.abspath(root))
    return os.path.join(parent, BOOTSTRAP_PIN_FILENAME)


def read_bootstrap_pin(root: str):
    """读取外部 pin（不可变常量 bootstrap_git_commit）。

    来源：仓库外配置文件 <root父目录>/bootstrap-pin.yaml（不在 git 仓库内）。
    不读取环境变量（Sol rev4 P1-1：调用者不可覆盖的 immutable trust root；
    env 可被普通 invocation 重定向，不可作为信任锚）。
    返回 {bootstrap_git_commit} 或 None（缺失/损坏 → None，调用方必须 fail-closed）。
    """
    from ..mini_yaml import load_file
    p = bootstrap_pin_path(root)
    if not os.path.exists(p):
        return None
    try:
        doc = load_file(p, strict=True) or {}
        if doc.get("bootstrap_git_commit"):
            return {"bootstrap_git_commit": doc["bootstrap_git_commit"]}
    except Exception:
        return None
    return None


def _git_show_bytes(root: str, commit: str, path: str):
    """git show <commit>:<path> 返回 bytes；失败返回 None。"""
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "-C", root, "show", f"{commit}:{path}"],
            stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None


def _pinned_canonical_hash(root: str, commit: str, path: str):
    """从 pin commit 读取文件并计算 canonical hash。解析失败 → raise TxError。"""
    from .fs import TxError
    from ..mini_yaml import load
    from .canonical import canonical_hash
    out = _git_show_bytes(root, commit, path)
    if out is None:
        raise TxError("PROVENANCE_BROKEN",
                      f"bootstrap pin 中无 {path}（commit {commit[:8]}）")
    try:
        doc = load(out.decode("utf-8"), strict=True) or {}
        return canonical_hash(doc)
    except Exception as e:
        raise TxError("PROVENANCE_BROKEN", f"bootstrap pin bytes 解析失败 {path}: {e}")


def verify_bootstrap_definition(root: str, entity: str, version: str) -> str:
    """bootstrap baseline 验证：从外部 pin 的 commit 读取 v1 bytes 计算 canonical hash，
    与 live 文件比较（Sol rev3 P1-1：fail-closed，缺失 pin 即 PROVENANCE_BROKEN）。

    返回 pinned canonical hash。live 不一致 → raise TxError DEF_POINTER_DIVERGED。
    """
    from .fs import TxError
    pin = read_bootstrap_pin(root)
    if pin is None:
        # 无外部 pin → fail-closed（rev11 §5.4；不允许退化为 live 文件信任）
        raise TxError("PROVENANCE_BROKEN",
                      "bootstrap 无外部 pin（缺 RESEARCHCTL_BOOTSTRAP_COMMIT / 仓库外 bootstrap-pin.yaml）")
    pinned_hash = _pinned_canonical_hash(root, pin["bootstrap_git_commit"],
                                         f"definitions/{entity}/{version}.yaml")
    live_hash = file_canonical_hash(definition_path(root, entity, version))
    if live_hash != pinned_hash:
        raise TxError("DEF_POINTER_DIVERGED",
                      f"bootstrap {version} live bytes 与 external pin 不一致（trust root 被篡改）")
    return pinned_hash


def verify_bootstrap_approved(root: str, entity: str) -> str:
    """bootstrap APPROVED pin 验证（Sol rev3 P1-1 C）：首次 revision 前必须验证
    bootstrap APPROVED bytes 与 external pin commit 一致。

    返回 pinned canonical hash；不一致/无 pin → raise TxError。
    """
    from .fs import TxError
    pin = read_bootstrap_pin(root)
    if pin is None:
        raise TxError("PROVENANCE_BROKEN",
                      "bootstrap 无外部 pin（无法验证 bootstrap APPROVED）")
    pinned_hash = _pinned_canonical_hash(root, pin["bootstrap_git_commit"],
                                         f"definitions/{entity}/APPROVED.yaml")
    live_hash = read_approved_hash(root, entity)
    if live_hash != pinned_hash:
        raise TxError("DEF_POINTER_DIVERGED",
                      f"bootstrap APPROVED live bytes 与 external pin 不一致（trust root 被篡改）")
    return pinned_hash


def verify_bootstrap_metadata(root: str, entity: str) -> None:
    """bootstrap BOOTSTRAP.yaml metadata pin 验证（Sol rev5 P2-1 + rev7 P2）。

    BOOTSTRAP.yaml 是 metadata（非 trust root，Sol rev6 P2-4），但必须与 external pin
    锚定一致（合同 §5.4）。若 entity 目录无 BOOTSTRAP.yaml 则跳过（可选 metadata）。
    存在但与 pin commit 不一致 → raise TxError DEF_POINTER_DIVERGED；
    pin commit 中 BOOTSTRAP.yaml malformed → PROVENANCE_BROKEN（fail-closed，Sol rev7 P2）。
    """
    from .fs import TxError
    from ..mini_yaml import load as _yaml_load
    from .canonical import canonical_hash as _chash
    pin = read_bootstrap_pin(root)
    if pin is None:
        raise TxError("PROVENANCE_BROKEN", "bootstrap 无外部 pin（无法验证 BOOTSTRAP metadata）")
    import subprocess as _sp
    meta_path = f"definitions/{entity}/BOOTSTRAP.yaml"
    live_meta = os.path.join(root, "definitions", entity, "BOOTSTRAP.yaml")
    try:
        out = _sp.check_output(["git", "-C", root, "show",
                                f"{pin['bootstrap_git_commit']}:{meta_path}"],
                               stderr=_sp.DEVNULL)
    except _sp.CalledProcessError:
        # pin commit 中无 BOOTSTRAP.yaml：若 live 也没有 → 两边都没有才可跳过；
        # 若 live 存在 → 报告 divergence（P2-1，Sol rev6：live-only metadata 也 fail-closed）
        if not os.path.exists(live_meta):
            return
        raise TxError("DEF_POINTER_DIVERGED",
                      f"bootstrap BOOTSTRAP.yaml live-only 但 pin 中不存在（{entity}）")
    try:
        pinned_meta = _yaml_load(out.decode("utf-8"), strict=True) or {}
        pinned_hash = _chash(pinned_meta)
    except Exception as e:
        # Sol rev7 P2：pin commit 中 BOOTSTRAP.yaml 存在但 malformed → PROVENANCE_BROKEN（fail-closed）
        raise TxError("PROVENANCE_BROKEN",
                      f"bootstrap pin 中 BOOTSTRAP.yaml 解析失败（{entity}）: {e}")
    if not os.path.exists(live_meta):
        raise TxError("DEF_POINTER_DIVERGED",
                      f"bootstrap BOOTSTRAP.yaml 缺失但 pin 中存在（{entity}）")
    try:
        live_meta_doc = _yaml_load(open(live_meta, encoding="utf-8").read(), strict=True) or {}
        live_hash = _chash(live_meta_doc)
    except Exception as e:
        raise TxError("PROVENANCE_BROKEN", f"bootstrap BOOTSTRAP.yaml 解析失败: {e}")
    if live_hash != pinned_hash:
        raise TxError("DEF_POINTER_DIVERGED",
                      f"bootstrap BOOTSTRAP.yaml 与 external pin 不一致（{entity}）")


def get_previous_hash(root: str, entity: str, previous: str) -> Optional[str]:
    """获取 predecessor 版本文件的 canonical hash 或是 receipt.definition_hash。

    若 previous 是 P1-B committed revision → 从 valid receipt 获取 definition_hash
    （按 **Event.subject == previous** 查找，绝不假设 EV 编号 == 版本编号，Sol rev 实现复审 P1-2）；
    若 previous 是 bootstrap v1（无 committed DefinitionRevised）→ 从 external pin 锚定。

    注意：若存在 subject==previous 的 DefinitionRevised Event 但 receipt 无效，
    返回 None（predecessor authority broken），不降级到 bootstrap（Sol rev8 P2）。
    """
    from ..mini_yaml import load_file
    from .receipt import verify_definition_receipt
    found_event = False
    # 扫描 canonical committed Event/receipt，按 subject == previous 查找
    ev_dir = os.path.join(root, "events")
    if os.path.isdir(ev_dir):
        for fn in sorted(os.listdir(ev_dir)):
            m = re.fullmatch(r"EV-(\d{6})\.yaml", fn)
            if not m:
                continue
            eid = fn[:-5]
            try:
                ev = load_file(os.path.join(ev_dir, fn), strict=True) or {}
            except Exception:
                continue
            if ev.get("subject") != previous:
                continue
            if ev.get("event_type") != "DefinitionRevised":
                continue
            found_event = True
            # 该 Event 的 receipt 必须有效（canonical COMMITTED truth）
            rc = verify_definition_receipt(root, eid)
            if rc.get("valid") is True:
                return rc.get("definition_hash")
            # 找到 Event 但 receipt 无效 → predecessor authority broken（不降级到 bootstrap）
            return None
    # 无 committed DefinitionRevised（真正 bootstrap）→ 从 external pin 锚定
    if not found_event:
        return verify_bootstrap_definition(root, entity, previous)
    return None