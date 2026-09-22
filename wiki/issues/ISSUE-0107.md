---
id: "ISSUE-0107"
title: "v74 canonical trace loader 不校验 COMPLETE marker 的 record/attempt counts"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "canonical_trace_complete_marker_count_unbound"
evidence: "commit 8296dd5530600fd0554f6b4d68c5707b87851932; /tmp/r60_v74_trace_marker_count_probe.out SHA-256 2c926057095e8201cc225d6673816d003f442658c81e63bd5ef6027ceaf58adc; tools/canonical_trace.py:245-259"
related: []
fix_ref: "120ac20"
summary: "v74 canonical trace loader 不校验 COMPLETE marker 的 record/attempt counts"
updated_at: "2026-09-22"
---

## 现象

把物理 COMPLETE marker 的 record_count 与 attempt_count 改为 0、同步 marker hash 后，trace loader 仍 valid=True/problems=[]；marker schema/status/events/source 字段被检查，但 counts 未与 manifest/实际 records 绑定。

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

## 处置记录 2026-09-22T19:14:23+0800

v75 loader 复核同样未闭合：/tmp/r61_v75_trace_marker_count_probe.out SHA-256 2c926057095e8201cc225d6673816d003f442658c81e63bd5ef6027ceaf58adc；marker record_count/attempt_count 改为 0、同步 marker hash 后仍 valid=True。

## 处置记录 2026-09-22T19:47:29+0800

The COMPLETE marker's record_count/attempt_count must now be integers equal to the records/attempts actually walked AND agree with the manifest. Zeroed, halved and inflated counts are all refused; 4 parametrized regression cases (0/0, 1/1, 536/168, 99999/99999 -- the middle ones defeat a check that only rejected zeros), mutation kills all 4 when reverted.
