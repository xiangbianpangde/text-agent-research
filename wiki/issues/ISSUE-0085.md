---
id: "ISSUE-0085"
title: "researchctl/pyproject.toml 使用 JSON 导致 pytest 收集与 pip 安装失败"
status: "fixed"
severity: "high"
area: "researchctl-cli"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "invalid_pyproject_blocks_install_and_pytest"
evidence: "command=python3 -m pytest researchctl/tests -q;error=TOMLDecodeError Invalid statement line 1 column 1;path=researchctl/pyproject.toml;command=python3 -m pip install --dry-run ./researchctl;same_error=true"
related: []
fix_ref: "researchctl-product@M0: root pyproject.toml (legit TOML, v0.2.0, packages=[researchctl, researchctl.tx]); deleted researchctl/pyproject.toml"
summary: "researchctl/pyproject.toml 使用 JSON 导致 pytest 收集与 pip 安装失败"
updated_at: "2026-09-22"
---

## 现象

名为 pyproject.toml 的文件实际是 JSON；pytest 在收集前失败，pip 无法安装产品包。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

（待评估：影响面 / 是否有 workaround）

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-22T16:50:23+0800

M0 第一刀已修：仓库根建立唯一权威 pyproject.toml（合法 TOML，setuptools>=61，version=0.2.0，显式只打包 researchctl/researchctl.tx，wheel 36 文件、bench 条目 0）；删除非法 researchctl/pyproject.toml，仓库内不留第二份 Python 发行元数据。验证证据：python3 -m venv + pip install -e . 成功（researchctl-0.2.0）；python3 -m researchctl --version → researchctl 0.2.0，与 pyproject version 及 pip show 一致；pytest 收集不再阻断（product 套件 23 passed）。产品测试固化该不变量：researchctl/tests/product/test_m0_baseline.py::test_root_pyproject_is_valid_toml / test_single_python_distribution_metadata / test_bench_is_not_packaged。
