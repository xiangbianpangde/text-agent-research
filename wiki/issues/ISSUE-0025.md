---
id: "ISSUE-0025"
title: "v61 arbitrary system_name is silently relabeled as system A"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "system_identity_coercion,provenance_label_forgery"
  - "v71_invalid_system_reported_not_relabelled"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/worker_supervisor.py:_build_envelope system field; /tmp/r48_v61_system_identity.out"
related: []
fix_ref: null
summary: "v61 arbitrary system_name is silently relabeled as system A"
updated_at: "2026-09-18"
---

## 现象

WorkerSupervisor(system_name='ATTACKER') completes a schema-valid query, but evaluator envelope reports system='A' rather than rejecting the invalid identity; unknown caller labels can be misattributed as A.

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

## 处置记录 2026-09-18T08:30:37+0800

v71 clean-room probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: system_name='ATTACKER' now returns no accepted response and an envelope with system='INVALID', schema_valid=false, identity_violations=["system:'ATTACKER'"] rather than silently relabelling to A. Evidence /tmp/r56_v71_invalid_system_envelope_probe.out SHA-256 d56dedc5a32bc2a36eb85c8f25882a5bd6ee6bbae4a33397117cc920fd1acd66. Original coercion symptom is narrowed, but the envelope schema intentionally permits INVALID and the broader runtime/system identity gate remains open.
