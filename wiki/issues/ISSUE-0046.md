---
id: "ISSUE-0046"
title: "v62 prebuilt declaration enforcement boolean is caller-mutable"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "mutable_declaration_enforced_flag,prebuilt_gate_bypass"
  - "v71_prebuilt_effective_workspace_rebind"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/worker_supervisor.py:555-561; /tmp/r49_v62_prebuilt_flag_mutation_probe.out"
related: []
fix_ref: null
summary: "v62 prebuilt declaration enforcement boolean is caller-mutable"
updated_at: "2026-09-18"
---

## 现象

An undeclared prebuilt SandboxLauncher has declaration_enforced=False. Setting the public instance flag to True lets WorkerSupervisor constructor accept it, although undeclared_snapshot remains true and raw/doc.txt reaches the effective workspace. The claimed prebuilt default check trusts a mutable status boolean.

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

## 处置记录 2026-09-16T15:59:31+0800

Same mutable-instance boundary: after a declared launcher prepared a snapshot, rebinding public effective_workspace_root to an outside directory let WorkerSupervisor accept and set workspace_root outside; secret.txt was visible (/tmp/r49_v62_prebuilt_workspace_rebind_probe.out). Prebuilt path trusts mutable launcher state beyond declaration_enforced.

## 处置记录 2026-09-17T16:38:31+0800

Round 51/v64 constructor source still trusts getattr(launcher, 'declaration_enforced', False) for a prebuilt launcher (runner/worker_supervisor.py:548-561); the public instance boolean is not a cryptographic or capability-bound authorization fact. The new ISSUE-0054 probes show the adjacent declaration key/entries mutation path also remains exploitable.

## 处置记录 2026-09-18T09:03:42+0800

v71 clean-room prebuilt-launcher probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: after prepare_sandbox() materializes a declared read-only snapshot at .../sandbox_A_*/workspace_ro, rebinding launcher.effective_workspace_root to the original host source is accepted by WorkerSupervisor. The supervisor then uses the host root and embeds it in the wrapped command/profile while declaration_enforced remains true. Evidence /tmp/r56_v71_prebuilt_effective_root_rebind_probe.out SHA-256 9b3924ca87ef2fa7821aff74a401c38fc96a410243b25e5f0031e93e179dac96. Prebuilt launcher state and effective boundary must be immutable or revalidated before use.
