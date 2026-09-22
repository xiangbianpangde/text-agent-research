---
id: "ISSUE-0076"
title: "v71 EvidenceMaterializer accepts line_end beyond EOF and preserves a false citation range"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "materializer_line_end_overrun,range_provenance_forgery"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/tools/materializer.py:105-122; /tmp/r56_v71_materializer_end_overrun_probe.out SHA-256 aaf515d07a09df95e61590dfca216f1ac068ad6e71bc163c4558317c2d34e784"
related: []
fix_ref: null
summary: "v71 EvidenceMaterializer accepts line_end beyond EOF and preserves a false citation range"
---

## 现象

A one-line file materialized with line_start=1,line_end=20 returns text from line 1, no OUT_OF_RANGE/blocked marker, and an EvidenceAtom retaining line_end=20. Downstream persistence can accept a non-existent line range as if it were an exact citation.

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
