---
id: "ISSUE-0067"
title: "v71 _terminate_worker overwrites the caller deadline with grace-period deadline"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "v71_teardown_deadline_shadow,v71_error_path_sweep_skipped"
evidence: "v71 commit 1ed201b636302ee095fb6713186f69a56e422ac9; runner/worker_supervisor.py:_terminate_worker lines 2473-2595; /tmp/r56_v71_teardown_deadline_shadow_probe.out SHA-256 da24cb18691319be1235a57065023338f1d6b0a6ee719ddd33e345ce953327ae"
related: []
fix_ref: null
summary: "v71 _terminate_worker overwrites the caller deadline with grace-period deadline"
---

## 现象

Independent probe calls _terminate_worker(hard=False, grace_period=0.05, deadline=now+5s) and records the argument passed to _can_afford_sweep: it is only ~0.038s in the future (the grace deadline), not the caller's 5s budget. The function reassigns parameter deadline at line 2558 before the residue sweep, so graceful error paths mark residue_unconfirmed and skip a sweep even when the actual attempt budget could afford it; untracked descendants can remain.

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
