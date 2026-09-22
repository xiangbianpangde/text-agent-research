---
id: "ISSUE-0084"
title: "ResearchCTL 两套 P0-P6 阶段命名对 TaskSlice 与 Handoff 归属冲突"
status: "open"
severity: "high"
area: "docs"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "researchctl_phase_namespace_collision"
evidence: "path=docs/contracts/P0-Contract.md section=13 P1-05..P1-08;path=fixture/tasks/README.md claim=TaskSlice/Handoff属P3;path=docs/specs/超长程实验 Agent 技术方案.md section=13.2 claim=P0合同含TaskSlice/Handoff且P2为Pi单worker"
related: []
fix_ref: null
summary: "ResearchCTL 两套 P0-P6 阶段命名对 TaskSlice 与 Handoff 归属冲突"
---

## 现象

旧检索内核路线与新执行Harness路线复用 P0/P1/P2 名称且含义不同，无法无歧义定义当前阶段、分支名和退出门槛。

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
