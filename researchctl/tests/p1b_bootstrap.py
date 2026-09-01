#!/usr/bin/env python3
"""P1-B 测试 bootstrap：在 fixture 副本中搭建 P1-B 环境。

- definitions/H003/H003@v1.yaml（bootstrap v1，外部受控流程创建）
- definitions/H003/APPROVED.yaml（指向 v1）
- .auth/approvals/APR-000001.yaml（approval artifact，basis-pinned）
- registry.yaml 增加 AUTH-0002（revise-definition scope）
- git commit 使全部进入 basis

仅操作 fixture 副本，不碰 fixture 原始树。
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE = os.path.join(ROOT, "fixture")

BOOTSTRAP_V1 = """schema_version: 1
entity_id: H003
version_ref: H003@v1
previous: null
body:
  kind: Hypothesis
  population: text_agent_long_context
  outcome: retrieval_recall
  threshold: 0.9
  method: index_scan
"""

BOOTSTRAP_APPROVED = """definition: H003
ref: H003@v1
approved_at: 2026-08-01T00:00:00+08:00
basis_git_commit: bootstrap
"""

DEFAULT_BODY = {
    "kind": "Hypothesis",
    "population": "text_agent_long_context",
    "outcome": "retrieval_recall",
    "threshold": 0.95,
    "method": "hybrid_scan",
}


def wrap_hash(entity: str, previous: str, body: dict) -> str:
    """计算 proposed definition hash（与 revise.py 相同的包装规则）。"""
    from researchctl.tx.definition import wrap_definition_input
    from researchctl.tx.canonical import canonical_hash
    subject = f"{entity}@v{int(previous.rsplit('@v', 1)[1]) + 1}"
    wrapped = wrap_definition_input(entity=entity, previous=previous,
                                    subject=subject, body=body)
    return canonical_hash(wrapped)


def write_bootstrap(root: str, change_type=None, definition="H003",
                    expected_previous="H003@v1", proposed_hash=None,
                    approval_valid=True, approval_definition=None,
                    approval_previous=None, approval_change_type=None,
                    include_approval=True) -> None:
    """在 root（fixture 副本）中写入 P1-B bootstrap 数据并 commit。

    默认批准 H003@v1→v2（scope_change）。参数可覆盖以构造故障场景。
    include_approval=False：不写 approval 文件（用于 U53：approval 仅在工作树）。
    """
    from researchctl.mini_yaml import dump

    # definitions
    ddir = os.path.join(root, "definitions", definition)
    os.makedirs(ddir, exist_ok=True)
    v1_path = os.path.join(ddir, f"{expected_previous}.yaml")
    with open(v1_path, "w", encoding="utf-8") as f:
        f.write(BOOTSTRAP_V1)
    app_path = os.path.join(ddir, "APPROVED.yaml")
    with open(app_path, "w", encoding="utf-8") as f:
        f.write(BOOTSTRAP_APPROVED)
    # BOOTSTRAP.yaml metadata（可选；存在则 reconcile 会锚定 external pin，Sol rev5 P2-1）
    meta_path = os.path.join(ddir, "BOOTSTRAP.yaml")
    if not os.path.exists(meta_path):
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"schema_version: 1\nentity: {definition}\nrole: bootstrap-metadata\n"
                    f"created_by: external-controlled-bootstrap\n")

    # approval artifact（basis-pinned）
    apdir = os.path.join(root, ".auth", "approvals")
    os.makedirs(apdir, exist_ok=True)
    if proposed_hash is None:
        proposed_hash = wrap_hash(definition, expected_previous, DEFAULT_BODY)
    if include_approval:
        apr = {
            "approval_id": "APR-000001",
            "definition": approval_definition or definition,
            "previous": approval_previous or expected_previous,
            "proposed_definition_hash": proposed_hash,
            "change_type": approval_change_type or (change_type or ["scope_change"]),
            "approved_by": "scientist-1",
            "valid": approval_valid,
        }
        with open(os.path.join(apdir, "APR-000001.yaml"), "w", encoding="utf-8") as f:
            f.write(dump(apr))

    # registry：增加 AUTH-0002（revise-definition scope）
    reg_path = os.path.join(root, ".auth", "registry.yaml")
    reg = open(reg_path, encoding="utf-8").read()
    if "AUTH-0002" not in reg:
        reg += """
  - ref: AUTH-0002
    grantee: text-agent
    scope: revise-definition
    valid: true
"""
        with open(reg_path, "w", encoding="utf-8") as f:
            f.write(reg)

    # git commit（basis）
    subprocess.run(["git", "-C", root, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", root, "commit", "-m", "P1-B bootstrap"], capture_output=True)
    # 外部 pin：把刚提交的 commit 记录为 bootstrap_git_commit（trust root）
    # 写入仓库外（root 的父目录），而非 repo 内文件（杜绝 self-reference，Sol rev3 P1-1）
    from researchctl.tx.definition import bootstrap_pin_path, BOOTSTRAP_PIN_ENV
    head = subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip()
    pin_file = bootstrap_pin_path(root)
    os.makedirs(os.path.dirname(pin_file), exist_ok=True)
    with open(pin_file, "w", encoding="utf-8") as f:
        f.write(f"schema_version: 1\nbootstrap_git_commit: {head}\n")


def commit_all(root: str, msg="tx"):
    subprocess.run(["git", "-C", root, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", root, "commit", "-m", msg], capture_output=True)


if __name__ == "__main__":
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "f")
    shutil.copytree(FIXTURE, dst, symlinks=False,
                    ignore=shutil.ignore_patterns(".index", "*.sqlite", "__pycache__"))
    write_bootstrap(dst)
    print(f"bootstrap OK: {dst}")
    print(open(os.path.join(dst, "definitions", "H003", "H003@v1.yaml"), encoding="utf-8").read())


def write_approval(root: str, approval_ref: str, *, definition: str, previous: str,
                   proposed_hash: str, change_type: list, valid=True) -> None:
    """写入指定 ref 的 approval artifact（basis-pinned，随后 commit 生效）。"""
    from researchctl.mini_yaml import dump
    apdir = os.path.join(root, ".auth", "approvals")
    os.makedirs(apdir, exist_ok=True)
    apr = {
        "approval_id": approval_ref,
        "definition": definition,
        "previous": previous,
        "proposed_definition_hash": proposed_hash,
        "change_type": change_type,
        "approved_by": "scientist-1",
        "valid": valid,
    }
    with open(os.path.join(apdir, f"{approval_ref}.yaml"), "w", encoding="utf-8") as f:
        f.write(dump(apr))
