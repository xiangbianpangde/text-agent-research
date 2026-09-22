---
id: "ISSUE-0059"
title: "v66 residue shutdown_error can return without the mandatory EvaluatorEnvelope"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-17"
discovered_by: "agent"
tags: []
signals:
  - "shutdown_failure_envelope_omission,residue_failure_provenance"
evidence: "commit c87d1a13ef4f3243dc585901e40af79b4a8f288a; runner/worker_supervisor.py:2034-2044; /tmp/r53_v66_post_ack_details.out; /tmp/r53_v66_async_probe.out"
related: []
fix_ref: null
summary: "v66 residue shutdown_error can return without the mandatory EvaluatorEnvelope"
updated_at: "2026-09-17"
---

## 现象

A valid shutdown_ack followed by a detached child returns shutdown_error while child is still alive at return; result has only record_type/error, last_envelope=None, proc=None, _sweep_outstanding=False. This violates M1 acceptance that every attempt including failures produces an EvaluatorEnvelope and leaves the failure without durable envelope evidence.

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

## 处置记录 2026-09-17T20:01:45+0800

The v66 attestation itself is internally stale: gates_satisfied.escape_sweep_runs_async=true although source now calls _sweep_surviving_descendants synchronously; gates_satisfied.every_failed_attempt_has_runner_owned_evaluator_envelope=true is contradicted by the clean-room residue shutdown_error (last_envelope=None).
