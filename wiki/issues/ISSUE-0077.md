---
id: "ISSUE-0077"
title: "v71 EvidenceMaterializer sets byte_start to zero for non-first-line passages"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "materializer_byte_offset_unbound,source_range_provenance_mismatch"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/tools/materializer.py:121-137; BENCHMARK_SPEC.md:1394-1404; /tmp/r56_v71_materializer_byte_offset_probe.out SHA-256 75e084c998a39edbfc5025210917d3a087ced7b605a199e1197c10a542f8afd6"
related: []
fix_ref: null
summary: "v71 EvidenceMaterializer sets byte_start to zero for non-first-line passages"
---

## 现象

Materializing line 2 of a two-line file returns byte_start=0, byte_end=6 although the exact source slice is bytes 6..12. The atom's byte range is not bound to the cited source passage, undermining byte-exact provenance and audit scoring.

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
