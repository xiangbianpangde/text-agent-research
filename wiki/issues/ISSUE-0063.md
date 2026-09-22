---
id: "ISSUE-0063"
title: "v71 idle watchdog raises NameError instead of terminating a worker after late stdout"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "v71_idle_watchdog_undefined_deadline,late_stdout_worker_survives"
evidence: "v71 commit 1ed201b636302ee095fb6713186f69a56e422ac9; runner/worker_supervisor.py:_start_idle_watchdog references undefined deadline; /tmp/r56_v71_idle_watchdog_deadline_bug.out SHA-256 a9fec78a67d029ce5270273f9469592df0bf619ddfdee69ca89bec0ea80dfb37"
related: []
fix_ref: null
summary: "v71 idle watchdog raises NameError instead of terminating a worker after late stdout"
updated_at: "2026-09-18"
---

## 现象

Independent runtime probe: valid query returned IDLE, delayed unframed stdout set state=FAILED and emitted invalidation, but watchdog thread exited and worker PID 1538 remained alive (poll=None) until an explicit later shutdown. The NameError is swallowed by watchdog's broad exception handler.

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

## 处置记录 2026-09-18T09:18:16+0800

Ruff F821 scan of the v71 package also reports exactly the watchdog undefined-name defect (plus the independent Python 3.10 f-string syntax finding): /tmp/r56_v71_ruff_f821_all.out SHA-256 ff62f32514b67b10ee9941c3b106bde1f16d14ae0ec30b3d5ea74cfaf4c7c63f.
