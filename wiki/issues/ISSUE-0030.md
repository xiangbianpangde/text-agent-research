---
id: "ISSUE-0030"
title: "v62 CHILD_PID quota is session-lifetime and attacker-exhaustible"
status: "verified"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "claim_quota_lifetime,claim_flood_starvation"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/worker_supervisor.py:1036-1058; /tmp/r49_v62_claim_lifetime_probe.out"
related: []
fix_ref: "5227b03dbf2af80d9abd5d47161483dd2864d519"
summary: "v62 CHILD_PID quota is session-lifetime and attacker-exhaustible"
updated_at: "2026-09-17"
---

## 现象

worker emits 64 invalid CHILD_PID:1 lines in query 1, then a new claim in query 2; query 2 claim is dropped (claims=64,dropped=1) although it is a later attempt. A worker can exhaust the session-wide quota with fake claims and starve future descendant admission.

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

## 处置记录 2026-09-17T17:16:24+0800

Round 51/v64 independent selected regression passed: tests/security/test_worker_isolation.py::test_f02_child_pid_quota_is_per_attempt_not_session completed 1/1 in 0.61s; output `/tmp/r51_v64_claim_quota_probe.out` SHA-256 bd6b4929bea02a709f7515ea8ae0e732b8d4f4c4c6af411d5abc23ccdc34617d. The recorded session-lifetime starvation symptom is fixed, but split-marker parsing and kernel-owned process scope remain open.
