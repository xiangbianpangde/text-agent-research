---
id: "ISSUE-0071"
title: "v71 Pilot track writes adapter responses without invoking schema/conformance validation"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "pilot_adapter_validation_bypass,invalid_response_persisted"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; runner/pilot.py:_evaluate_track and _execute_dynamic_timeline; adapters/protocol.py:run_and_validate; /tmp/r56_v71_pilot_adapter_validation_bypass_probe.out SHA-256 3e23634211006bb492a3d2748de730ac350ccdc65b9d4566c222699965dbab56"
related: []
fix_ref: null
summary: "v71 Pilot track writes adapter responses without invoking schema/conformance validation"
---

## 现象

A fake adapter returning record_type=not_a_participant_response is accepted by _evaluate_track, three invalid participant records are written to events.jsonl, and a normal summary is returned. Pilot instantiates SemanticConformanceValidator but never calls it or BaseAdapter.run_and_validate. Invalid in-process SUT outputs can therefore enter the scored trace.

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
