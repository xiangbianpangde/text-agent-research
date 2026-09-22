---
id: "ISSUE-0101"
title: "M1-3 historicalSearch 不拒绝跨文件重复 session id，发出不可唯一回链的引用"
status: "open"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "m13_historical_duplicate_session_identity"
evidence: "commit 6f7d4cc53eba60e2e3f854d8a213bb34503f6be7; /tmp/r60_m13_historical_duplicate_session_probe.out SHA-256 a199b3612880ae14277579dccb21cf8a61e05487200e8d5a44f24b7451155fb8; session-retrieval/scanner.ts:433-435,449-603; query.ts:347-375"
related: []
fix_ref: null
summary: "M1-3 historicalSearch 不拒绝跨文件重复 session id，发出不可唯一回链的引用"
---

## 现象

同一 sessions root 中两个文件 header id 都是 s-duplicate 时，historicalSearch 返回 status=ok、coverage.complete=true，并发出两个同 session_id 的 source_ref；但 resolveExactRef 对同一 session_id 会因 matches.length>1 返回 PROVENANCE_BROKEN，故检索结果不可唯一回链。

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
