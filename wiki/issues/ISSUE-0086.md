---
id: "ISSUE-0086"
title: "P1 已实现但产品元数据与 fixture 仍宣称 P0 只读或占位"
status: "open"
severity: "medium"
area: "docs"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "product_phase_status_and_fixture_drift"
evidence: "paths=researchctl/__init__.py,researchctl/cli.py,researchctl/pyproject.toml,fixture/events/README.md,fixture/tasks/README.md;git_head=01b4cd0;tests=P1A_139_PASS,P1B_85_PASS,P1C_83_PASS"
related: []
fix_ref: null
summary: "P1 已实现但产品元数据与 fixture 仍宣称 P0 只读或占位"
---

## 现象

CLI 描述和包元数据仍写 P0-B 只读，events/tasks README 仍为占位，与已落地的 P1 写入能力及 README 状态不一致。

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
