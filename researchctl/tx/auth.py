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
