---
id: "ISSUE-0037"
title: "v62 out-of-range evidence citations remain schema-valid and are persisted"
status: "verified"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "out_of_range_citation_accepted,materializer_validator_gap"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/campaign.py:339-355; tools/materializer.py:105-118; /tmp/r49_v62_out_of_range_probe.out"
related: []
fix_ref: "5227b03dbf2af80d9abd5d47161483dd2864d519"
summary: "v62 out-of-range evidence citations remain schema-valid and are persisted"
updated_at: "2026-09-17"
---

## 现象

A worker citing existing raw/x.txt lines 999-1000 materializes to [OUT_OF_RANGE], but campaign blocks only [BLOCKED]/[FILE_NOT_FOUND]; SemanticConformanceValidator returns no errors. Final participant response could be persisted as valid with no actual cited bytes.

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

## 处置记录 2026-09-17T17:03:01+0800

Round 51/v64 independent source/static audit verifies the recorded out-of-range/sentinel symptom fixed: campaign now checks [OUT_OF_RANGE] and [FILE_NOT_FOUND_IN_COMMIT] in addition to the prior markers, and supervisor enforces line/byte range ordering. Evidence `/tmp/r51_v64_static_probe_v2.out` SHA-256 d770ada4bd0abbc0f7d545b37f2464fef4ffbd0370ccfe34bd10183a6c307079 and v64 M0 `50/50`. Broader provenance/identity closure remains open.
