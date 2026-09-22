---
id: "ISSUE-0078"
title: "v71 Pilot lifecycle event binding uses assert and disappears under Python -O"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "assertion_based_lifecycle_binding,python_optimized_gate_bypass"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/runner/pilot.py:480-482; /tmp/r56_v71_pilot_assert_optimized_probe.out SHA-256 21eacd908525e59b0fdc2a06dbdc91850975856dace8f56330648e3574b92f4c"
related: []
fix_ref: null
summary: "v71 Pilot lifecycle event binding uses assert and disappears under Python -O"
---

## 现象

Under python3 -O, _apply_lifecycle_event accepts event_type=stale_index_state with event_id=EVIL and emits a lifecycle record carrying the wrong ID; the assert enforcing the canonical registry is removed by optimization. Binding checks must be explicit runtime failures.

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
