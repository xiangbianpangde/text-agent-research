---
id: "ISSUE-0102"
title: "M1-3 historicalSearch 对不存在或不可读 root 报告为空且覆盖完整"
status: "open"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "m13_historical_missing_root_failopen"
evidence: "commit 6f7d4cc53eba60e2e3f854d8a213bb34503f6be7; /tmp/r60_m13_missing_root_probe.out SHA-256 9a2f25719ebce549e4aa9acfbf4b60f38d8365b3946282bf49cd4c6d4f120d9a; session-retrieval/scanner.ts:327-332; query.ts:149-173"
related: []
fix_ref: null
summary: "M1-3 historicalSearch 对不存在或不可读 root 报告为空且覆盖完整"
---

## 现象

historicalSearch 的 indexSessionHeaders 在 root realpath 失败时返回 rootReal=null、excluded=[]，scanSessions 不传播 rootReal，最终返回 status=ok、coverage.complete=true、scanned_files=0、results=[]，把来源不可用误报为空且完整。

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
