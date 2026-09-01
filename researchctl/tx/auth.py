"""授权 registry（P1-A-Contract §6.3）。

fixture/.auth/registry.yaml（Git 管理，fixture 副本内）。
gate 验证三件事：存在性 / 格式 / 作用域。
"""
from __future__ import annotations

import os
import re
from typing import Optional


def load_registry(root: str) -> dict:
    from ..mini_yaml import load_file
    p = os.path.join(root, ".auth", "registry.yaml")
    if not os.path.exists(p):
        return {"schema_version": 1, "authorizations": []}
    try:
        doc = load_file(p, strict=True) or {}
        return doc
    except Exception:
        return {"schema_version": 1, "authorizations": []}


def validate_authorization(root: str, actor: str, authorization_ref: str) -> dict:
    """freeze gate 授权校验。返回 {ok, error_semantic?, detail}。"""
    if not authorization_ref:
        return {"ok": False, "error_semantic": "AUTH_REQUIRED", "detail": "缺 authorization_ref"}
    if not re.fullmatch(r"AUTH-\d+", authorization_ref):
        return {"ok": False, "error_semantic": "AUTH_INVALID", "detail": f"授权格式非法: {authorization_ref}"}
    reg = load_registry(root)
    for auth in reg.get("authorizations", []):
        if auth.get("ref") == authorization_ref:
            if not all(k in auth for k in ("grantee", "scope", "valid")):
                return {"ok": False, "error_semantic": "AUTH_INVALID", "detail": f"授权字段不完整: {authorization_ref}"}
            if auth.get("grantee") != actor:
                return {"ok": False, "error_semantic": "AUTH_SCOPE_DENIED",
                        "detail": f"grantee 不匹配: {authorization_ref}"}
            if "freeze-report" not in (auth.get("scope") or ""):
                return {"ok": False, "error_semantic": "AUTH_SCOPE_DENIED",
                        "detail": f"scope 不含 freeze-report: {authorization_ref}"}
            if auth.get("valid") is not True:
                return {"ok": False, "error_semantic": "AUTH_SCOPE_DENIED",
                        "detail": f"授权未生效 valid!=true: {authorization_ref}"}
            return {"ok": True, "authorization_ref": authorization_ref}
    return {"ok": False, "error_semantic": "AUTH_NOT_FOUND", "detail": f"授权引用不在 registry: {authorization_ref}"}


# ---- P1-B：revise-definition 授权 + approval（§6.3） ----

def validate_authorization_scope(root: str, actor: str, authorization_ref: str,
                                 scope: str) -> dict:
    """通用 scope 授权校验（P1-B：scope='revise-definition'）。

    返回 {ok, error_semantic?, detail}。scope 为空则检查默认 'freeze-report'。
    """
    if not authorization_ref:
        return {"ok": False, "error_semantic": "AUTH_REQUIRED", "detail": "缺 authorization_ref"}
    if not re.fullmatch(r"AUTH-\d+", authorization_ref):
        return {"ok": False, "error_semantic": "AUTH_INVALID", "detail": f"授权格式非法: {authorization_ref}"}
    reg = load_registry(root)
    for auth in reg.get("authorizations", []):
        if auth.get("ref") == authorization_ref:
            if not all(k in auth for k in ("grantee", "scope", "valid")):
                return {"ok": False, "error_semantic": "AUTH_INVALID", "detail": f"授权字段不完整: {authorization_ref}"}
            if auth.get("grantee") != actor:
                return {"ok": False, "error_semantic": "AUTH_SCOPE_DENIED",
                        "detail": f"grantee 不匹配: {authorization_ref}"}
            if scope and scope not in (auth.get("scope") or ""):
                return {"ok": False, "error_semantic": "AUTH_SCOPE_DENIED",
                        "detail": f"scope 不含 {scope}: {authorization_ref}"}
            if auth.get("valid") is not True:
                return {"ok": False, "error_semantic": "AUTH_SCOPE_DENIED",
                        "detail": f"授权未生效 valid!=true: {authorization_ref}"}
            return {"ok": True, "authorization_ref": authorization_ref}
    return {"ok": False, "error_semantic": "AUTH_NOT_FOUND", "detail": f"授权引用不在 registry: {authorization_ref}"}


def resolve_approval_digest(root: str, basis_git_commit: str, approval_ref: str) -> dict:
    """从 basis_git_commit 读取 approval artifact 的 canonical hash。

    返回 {ok, digest?, error_semantic?, detail?}。
    authority = (basis_git_commit, approval_ref, approval_digest) 三元组（§6.3）。
    """
    import subprocess
    if not re.fullmatch(r"APR-\d+", approval_ref or ""):
        return {"ok": False, "error_semantic": "APPROVAL_REQUIRED", "detail": f"approval_ref 格式非法: {approval_ref}"}
    path = f".auth/approvals/{approval_ref}.yaml"
    try:
        out = subprocess.check_output(
            ["git", "-C", root, "show", f"{basis_git_commit}:{path}"],
            stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return {"ok": False, "error_semantic": "APPROVAL_BINDING_MISMATCH",
                "detail": f"approval 不在 basis commit: {approval_ref}@{basis_git_commit[:8]}"}
    from ..mini_yaml import load
    from .canonical import canonical_hash
    try:
        doc = load(out.decode("utf-8"), strict=True) or {}
    except Exception as e:
        return {"ok": False, "error_semantic": "APPROVAL_BINDING_MISMATCH",
                "detail": f"approval 解析失败: {e}"}
    return {"ok": True, "digest": canonical_hash(doc), "doc": doc}


def validate_approval_binding(root: str, basis_git_commit: str, approval_ref: str,
                              *, definition: str, previous: str,
                              proposed_definition_hash: str, change_type: list) -> dict:
    """approval 内容绑定校验（§6.3，Sol rev9 P1-1 三元组模型）。

    返回 {ok, error_semantic?, digest?, detail?}。
    """
    res = resolve_approval_digest(root, basis_git_commit, approval_ref)
    if not res.get("ok"):
        return res
    doc = res.get("doc", {})
    if doc.get("valid") is not True:
        return {"ok": False, "error_semantic": "APPROVAL_BINDING_MISMATCH",
                "detail": f"approval valid!=true: {approval_ref}"}
    if doc.get("definition") != definition:
        return {"ok": False, "error_semantic": "APPROVAL_BINDING_MISMATCH",
                "detail": f"approval.definition={doc.get('definition')} != {definition}"}
    if doc.get("previous") != previous:
        return {"ok": False, "error_semantic": "APPROVAL_BINDING_MISMATCH",
                "detail": f"approval.previous={doc.get('previous')} != {previous}"}
    if doc.get("proposed_definition_hash") != proposed_definition_hash:
        return {"ok": False, "error_semantic": "APPROVAL_BINDING_MISMATCH",
                "detail": "approval.proposed_definition_hash 不匹配"}
    # change_type 集合比较（去重+排序后）
    exp_ct = sorted(set(change_type or []))
    app_ct = sorted(set(doc.get("change_type") or []))
    if app_ct != exp_ct:
        return {"ok": False, "error_semantic": "APPROVAL_BINDING_MISMATCH",
                "detail": f"approval.change_type={app_ct} != {exp_ct}"}
    return {"ok": True, "digest": res["digest"], "detail": "approval binding OK"}
