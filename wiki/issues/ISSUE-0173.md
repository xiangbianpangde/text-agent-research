---
id: "ISSUE-0173"
title: "dry-run 在 --only 选择器下仍按全集陈述剩余场景数与成本：3 个选择集被印成「2 x 1 turn」"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "dry_run_cost_understated"
  - "selector_ignored_in_cost_line"
  - "budget_quote_wrong_direction"
  - "cost_shown_before_spend_wrong"
evidence: "catalog/test/recovery-run.ts dry-run 分支：needTurn 由 ALL_SCENARIOS 而非选择集求得；成本行 filter 掉已有 usable row 的场景，故 rec-semantic-version-mismatch（有 row 但无判决，正是要重跑它的原因）被从成本中减去。实测输出：'Scenarios without a verdict: 3' 与 'Cost: 2 x 1 turn minimum' 同时打印，而 --only 选了 3 个场景。修正后同一命令打印 'Cost: 3 x 1 turn minimum'。"
related: []
fix_ref: null
summary: "dry-run 在 --only 选择器下仍按全集陈述剩余场景数与成本：3 个选择集被印成「2 x 1 turn」"
---

## 现象

在做花费决策的那一行数字上，选择器被忽略：列出的待跑场景数与报价的成本数不一致，且报价偏小（看起来更便宜）。与真实花费（3 回合）相比少 1 回合。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

预算决策依据错误，方向是低估花费；裁决要求「记录成本」，而工具在花费前给出的成本本身是错的。

## 根因

成本行沿用全集口径的 resume 规则（usable row 即跳过），与 --only 的语义（绕过 resume、显式重跑）相反；两处改动未同步。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
