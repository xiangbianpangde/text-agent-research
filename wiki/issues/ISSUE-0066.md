---
id: "ISSUE-0066"
title: "v71 residue sweep treats a reused root PID as worker lineage"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "v71_pid_reuse_lineage_authorization,v71_stale_root_override"
evidence: "v71 commit 1ed201b636302ee095fb6713186f69a56e422ac9; runner/worker_supervisor.py:_has_worker_lineage/_reap_escaped_processes; /tmp/r56_v71_pid_reuse_lineage_probe.out SHA-256 ba766d74e7928d5ca760fe676a2d20a04cb6b6f957fde87fe217b23e3e190374"
related: []
fix_ref: null
summary: "v71 residue sweep treats a reused root PID as worker lineage"
---

## 现象

Independent source-guided probe models the original root as reaped and PID 4242 reused: _lineage_root_override=4242, recorded _root_identity=(111,222), candidate 5678 reports PPID 4242 and has a different identity. _has_worker_lineage returns true and _reap_escaped_processes admits candidate 5678 without checking the original root incarnation; downstream cleanup may signal a process attached to the reused PID. The current lineage guard proves only a bare PPID chain, not the spawned root identity.

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
