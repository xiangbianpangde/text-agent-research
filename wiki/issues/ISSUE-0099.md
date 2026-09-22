---
id: "ISSUE-0099"
title: "M1-3 session header enumeration 静默丢弃 dangling symlink 并错误报告完整覆盖"
status: "open"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "m13_session_enumeration_dangling_candidate_omission"
evidence: "commit 6f7d4cc53eba60e2e3f854d8a213bb34503f6be7; /tmp/r60_m13_dangling_candidate_probe.out SHA-256 39f9218128e8ef82fda1c3f6b31d7e61d41ffaa329be94dc1754a61752fe4224; session-retrieval/scanner.ts:indexSessionHeaders catch/continue around realpath candidate"
related: []
fix_ref: null
summary: "M1-3 session header enumeration 静默丢弃 dangling symlink 并错误报告完整覆盖"
---

## 现象

sessions root 含匹配的 dangling `ghost.jsonl` symlink 时，indexSessionHeaders 捕获 realpath 错误直接 continue，historicalSearch 返回 status=ok、errors=[]、coverage.complete=true、scanned_files=0；不可验证的候选文件未进入 excluded，精确 resolve 也可能把不可验证来源当作 NOT_FOUND。

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
