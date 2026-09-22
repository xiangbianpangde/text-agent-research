---
id: "ISSUE-0060"
title: "v69 cwd-based escape sweep admits and kills unrelated host processes"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-17"
discovered_by: "agent"
tags: []
signals:
  - "default_scratch_cwd_false_ownership"
  - "escape_sweep_cwd_false_ownership,unrelated_process_kill"
evidence: "commit cc33db81cc180f8714d2035a12d8badfc09a9591; runner/worker_supervisor.py:1159-1204,2368-2408; /tmp/r55_v69_unrelated_cwd_kill.out SHA-256 7437aff8b3730df3d9a6a417b497faa204f21b56f86f5259e3c02ca122945d52"
related: []
fix_ref: null
summary: "v69 cwd-based escape sweep admits and kills unrelated host processes"
updated_at: "2026-09-18"
---

## 现象

A process not descended from the worker but whose cwd is under supervisor_cwd/workspace_root is admitted by _cwd_inside_scratch and killed by the teardown sweep; probe observed unrelated PID 4565 returncode -9 and shutdown_error residue=1.

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

## 处置记录 2026-09-18T00:21:41+0800

Stronger default-path repro: WorkerSupervisor(auto_sandbox=False) first creates its own supposedly private random supervisor_cwd; the host then launches an unrelated start_new_session sleep with cwd=sup.supervisor_cwd before start_and_handshake. v69 shutdown sweep admits and kills it (outsider PID 15096 returncode=-9) and returns shutdown_error residue=1. Evidence /tmp/r55_v69_default_cwd_unrelated_kill.out SHA-256 12c98f81708710fdafbfdeb3f90a39a9b52955d1175430897c00c131005872ea.

## 处置记录 2026-09-18T00:22:21+0800

Production-default variant also reproduces: auto_sandbox=True with require_participant_declaration=False, outsider launched by host in sup.supervisor_cwd after SandboxLauncher.prepare_sandbox and before worker start; handshake succeeds, v69 sweep kills outsider PID 29293 (-9), then shutdown_error residue=1. Evidence /tmp/r55_v69_auto_sandbox_cwd_unrelated_kill.out SHA-256 57a53f81fec7386f6777b8939aafd141581634a31e7c2b44eb5d44e7ce5402b9.
