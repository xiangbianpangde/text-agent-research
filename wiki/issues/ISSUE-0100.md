---
id: "ISSUE-0100"
title: "M1-3 resolveExactRef 在存在排除文件时仍返回已命中的 session"
status: "open"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "m13_resolve_ignores_enumeration_exclusions_with_match"
evidence: "commit 6f7d4cc53eba60e2e3f854d8a213bb34503f6be7; /tmp/r60_m13_resolve_excluded_with_match_probe.out SHA-256 18370f5235d97eeafd5b15d7e44bc39b74c57b227b6f1ec253e67bdbc46cd37b; session-retrieval/query.ts:347-367"
related: []
fix_ref: null
summary: "M1-3 resolveExactRef 在存在排除文件时仍返回已命中的 session"
---

## 现象

sessions root 同时含有效目标 session 与同项目 malformed-header session 时，indexSessionHeaders 产生 excluded，但 resolveExactRef 仅在 matches.length===0 分支检查 indexed.excluded；目标存在时返回 status=ok、coverage=null，无法证明该引用所在语料闭包完整。

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
