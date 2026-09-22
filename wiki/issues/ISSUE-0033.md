---
id: "ISSUE-0033"
title: "v62 zero query timeout silently widens to default"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "zero_timeout_default_widening,deadline_input_validation"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/worker_supervisor.py:1505; /tmp/r49_v62_zero_timeout_probe.out"
related: []
fix_ref: null
summary: "v62 zero query timeout silently widens to default"
updated_at: "2026-09-17"
---

## 现象

WorkerSupervisor.query(timeout_seconds=0) uses timeout_seconds or default_timeout_seconds, sends an effective 0.15s budget and returns a successful response (~141ms) instead of rejecting or enforcing the explicit zero deadline. One end-to-end deadline is not guaranteed for invalid/zero caller inputs.

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

## 处置记录 2026-09-17T16:34:51+0800

Round 51/v64 strict validator probe passes for query/handshake timeout inputs (True, '0', NaN, Inf, -1 rejected and numeric 0/0.5 accepted), but /tmp/r51_v64_shutdown_timeout_probe.out (SHA-256 f3fc051878b81f4530e7f1a52e52f88f9a36e1e48323228ee4d5fdbb482a4aad) shows shutdown still bypasses the validator; timeout_seconds='0' strands an active worker and accepts True. The query-specific zero-widening symptom is fixed, while lifecycle-wide timeout validation remains ISSUE-0055.
