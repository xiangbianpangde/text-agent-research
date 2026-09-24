---
id: "ISSUE-0194"
title: "转折上限只写进了控制台文案：场景循环不按 authorizedTurns 截断，干净跑最多花 39 回合"
status: "open"
severity: "high"
area: "researchctl"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "cap_is_a_phrase_not_a_quantity"
  - "loop_has_no_turn_accounting"
  - "default_from_voided_authorization"
evidence: "catalog/test/recovery-run.ts：authorizedTurns 仅用于 requestCeiling = authorizedTurns * 100 与两处 console.log，场景循环 for (const scenario of ALL_SCENARIOS) 的停止条件只有 judged.tainted / turn.error / turn.inconclusive（grep 证实循环体内无 authorizedTurns 引用）。故干净跑最多花 39 回合，而控制台同时打印「The authorization caps this run at 9 turns」。复核方（执行者-1，seq 8）指出此点，并指出默认 9 来自已作废授权、cap=5 属当前未获批申请。实测修复后：新增 turnsSpent 计数器与循环顶部 guard（偏移校验：guard 在首个 runTurnWithRetry 之前），--run 无 --max-turns 时 exit 2 且 0 provider 请求；--preflight 仍 15/15（--max-turns 5 → armed 500）。"
related: []
fix_ref: null
summary: "转折上限只写进了控制台文案：场景循环不按 authorizedTurns 截断，干净跑最多花 39 回合"
---

## 现象

同一缺陷在 0189 修复后仍存在于上一层：请求（每回合）×回合（每跑）两个维度里只锁了前者。authorizedTurns 在被用于乘法与打印的地方看起来像被使用过，实际没有任何执行路径读它来限制花费——与 ISSUE-0189 原文点名的「cap=5 是流程约束而非技术控制」是同一形态，故该措辞当时只被应用到了 request 层。附带风险：默认值来自已作废的 9 回合授权（记录 §11.2），使 --run 可凭一个过期数字自行开跑。

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
