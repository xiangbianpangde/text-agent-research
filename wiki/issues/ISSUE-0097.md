---
id: "ISSUE-0097"
title: "M1-3 resolve/current retrieval 仍可在过滤后或类型不同时接受重复 entry id"
status: "open"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "m13_duplicate_identity_filter_gap"
evidence: "commit 6f7d4cc53eba60e2e3f854d8a213bb34503f6be7; /tmp/r60_m13_current_duplicate_filter_probe.out SHA-256 68767438ff77e7133dccef4e529e738f624bdaba3b9f40cc49005e997cbf20a4; /tmp/r60_m13_resolve_mixed_duplicate_probe.out SHA-256 dd359f2ea4ea1bfde31c081f42bd0042e2be0f93e80d40799546d86e0842bd8e"
related: []
fix_ref: null
summary: "M1-3 resolve/current retrieval 仍可在过滤后或类型不同时接受重复 entry id"
---

## 现象

currentSessionSearch 对第一个不命中 query 的重复 id 不记录 seen，返回 status=ok 且发出不可唯一回链的 pi-session://live/dup；resolveExactRef 对同文件中同 id 的 message+compaction 仅计入匹配 qualifier 的一条，返回 status=ok 而非 provenance mismatch。

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
