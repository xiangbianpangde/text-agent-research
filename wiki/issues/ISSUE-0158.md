---
id: "ISSUE-0158"
title: "research_integrity 自身的 recovery 文本仍教 reconcile，而 drift 下只有 index 能修复（ISSUE-0156 只修了 query 那一处）"
status: "open"
severity: "high"
area: "researchctl"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "guidance_instructs_ineffective_recovery"
evidence: "实测：drift→query=INDEX_STALE；drift→reconcile=DRIFT_DETECTED(fail_closed)；drift→reconcile→query=INDEX_STALE（仍未修复）；drift→index→query=success。原文本在 researchctl-product catalog/catalog.ts 的 research_integrity.recovery='This is the recovery tool. After reconcile, re-read the original target'；回归断言 catalog/test/recovery.test.ts（repairing a stale index requires index）"
related: []
fix_ref: null
summary: "research_integrity 自身的 recovery 文本仍教 reconcile，而 drift 下只有 index 能修复（ISSUE-0156 只修了 query 那一处）"
---

## 现象

产品指引把诊断动作(reconcile)写成修复动作，模型照指引执行后目标仍 fail-closed；ISSUE-0156 修了 research_query 的 recovery 文本但漏掉 research_integrity 自身的 recovery 文本，而后者是模型被指向恢复工具后最先读到的内容

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
