---
id: "ISSUE-0032"
title: "v62 SandboxLauncher policy class attributes remain mutable"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "mutable_policy_allowlist,snapshot_boundary_rebind"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/sandbox_launcher.py:82-108, 680-732; /tmp/r49_v62_policy_mutation_probe.out"
related: []
fix_ref: null
summary: "v62 SandboxLauncher policy class attributes remain mutable"
updated_at: "2026-09-17"
---

## 现象

same-process caller assigns SandboxLauncher.ALLOWED_TOP_LEVEL to include secret and clears DENIED_NAME_KEYWORDS; prepare_sandbox then copies secret/hidden.txt into effective snapshot. Metaclass origin sealing does not protect the actual policy allowlists.

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

## 处置记录 2026-09-17T16:38:18+0800

Round 51/v64 source audit still finds ALLOWED_TOP_LEVEL, ALLOWED_EXTENSIONS, and DENIED_NAME_KEYWORDS as mutable SandboxLauncher class attributes consumed directly by classification/purge (runner/sandbox_launcher.py:195,205,415-425,500-517). The new declaration HMAC does not freeze these policy inputs; the same-process policy mutation risk remains independent of the inline trusted-origin literal.
