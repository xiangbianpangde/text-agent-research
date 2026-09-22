---
id: "ISSUE-0029"
title: "v62 inline trust literal still resolves mutable builtins.frozenset"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "trust_anchor_builtin_rebind,authorization_integrity_confusion"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/sandbox_launcher.py:314-317; /tmp/r49_v62_builtins_frozenset_probe.out"
related: []
fix_ref: null
summary: "v62 inline trust literal still resolves mutable builtins.frozenset"
updated_at: "2026-09-17"
---

## 现象

same-process code replaces builtins.frozenset with a function that adds attacker; verify_declaration() then accepts a signed produced_by=attacker declaration. Moving the helper to an inline call does not make the trust set immutable.

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

## 处置记录 2026-09-17T16:37:59+0800

Round 51/v64's trust set is now an inline frozenset and the original builtins.frozenset substitution probe is no longer the demonstrated path, but F-01 is still not closed: the class-level _DECLARATION_KEY remains rebindable and direct attestation remains same-process forgeable (see ISSUE-0054; /tmp/r51_v64_key_probe.out SHA-256 72e4969c1e97cc71a9ef43f7bfb19adca5e7c34fdf08faa689a9c8fb9b684ee7).
