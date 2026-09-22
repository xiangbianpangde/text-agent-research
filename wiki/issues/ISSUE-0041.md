---
id: "ISSUE-0041"
title: "v62 campaign omits failed-attempt envelopes from events.jsonl"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "failed_attempt_event_omission,envelope_not_persisted"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/campaign.py:215-227,316-324,397-431; source inspection"
related: []
fix_ref: null
summary: "v62 campaign omits failed-attempt envelopes from events.jsonl"
updated_at: "2026-09-17"
---

## 现象

run_quick_ci writes response+envelope only after a successful query/transformation. Any startup/query/schema/materialization/generation failure raises before events_f.write; finally persists raw CAS only, never sup.last_envelope. Failed attempts therefore lack durable evaluator envelopes despite the claimed every-failed-attempt contract.

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

## 处置记录 2026-09-16T15:53:37+0800

Physical forced-startup probe monkeypatched campaign.WorkerSupervisor to raise before events log opens; run_quick_ci failed, output had only raw/raw_manifest.json and events_exists=false (/tmp/r49_v62_failed_envelope_probe.out).

## 处置记录 2026-09-17T16:35:22+0800

Round 51/v64 source audit still finds events_f.write() only on the successful path after CAS and provenance work (runner/campaign.py:434,482-483); exceptions before those writes are handled in finally without appending a runner-owned failed-attempt evaluator envelope. The attestation's every_failed_attempt_has_runner_owned_evaluator_envelope claim is therefore not independently supported.
