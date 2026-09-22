---
id: "ISSUE-0001"
title: "researchctl --limit 对结构化查询不生效"
status: "fixed"
severity: "low"
area: "researchctl-cli"
discovered_at: "2026-09-15"
discovered_by: "dsh-researchctl 调用日志"
tags: []
signals:
  - "limit_ignored"
evidence: "calls-2026-09-15.jsonl argv=['query','--limit','2'] → 13 条"
related: []
fix_ref: "researchctl/queries.py:cmd_query + researchctl/cli.py（--limit 默认 None）"
summary: "researchctl --limit 对结构化查询不生效"
updated_at: "2026-09-15"
---

## 现象

传 limit=2 仍返回 13 条

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

## 处置记录 2026-09-15T19:08:12+0800

已确认：researchctl/queries.py 只在 query_semantic 路径消费 limit；结构化查询路径未切片。

## 处置记录 2026-09-15T19:35:37+0800

已修：显式 --limit 才截断，且 Envelope 里标注 total_results/limit_applied 并追加 warning（绝不静默少返回）；缺省返回全量。语义检索路径仍默认 50。回归：node --test 8/8、researchctl 脚本套件 360 项全通过
