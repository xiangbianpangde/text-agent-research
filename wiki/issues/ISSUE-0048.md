---
id: "ISSUE-0048"
title: "v63 attested empty declaration coerces non-boolean allow_empty values to true"
status: "verified"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "declaration_bool_coercion,malformed_manifest_acceptance"
evidence: "commit 0e9adf49c5c8a89c981432abcf6fea30d6998bfb; /private/tmp/r50_v63_decl_type_reprobe.out SHA-256 e126eefa02ea6667d31cdfea11244496294f447e961ac922f2f313a788c1cd45; runner/sandbox_launcher.py:288-297"
related: []
fix_ref: "5227b03dbf2af80d9abd5d47161483dd2864d519"
summary: "v63 attested empty declaration coerces non-boolean allow_empty values to true"
updated_at: "2026-09-17"
---

## 现象

Empty entries with allow_empty='false', '0', or 1 are converted by bool() to true and verify as ACCEPT

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

## 处置记录 2026-09-17T16:30:06+0800

Round 51/v64 independent clean-room regression is verified fixed for the recorded symptom: /tmp/r51_v64_static_probe_v2.out (SHA-256 d770ada4bd0abbc0f7d545b37f2464fef4ffbd0370ccfe34bd10183a6c307079) reports SnapshotIntegrityError for allow_empty='false', '0', 1, 0, None, and False; only real True is accepted. This closes the non-boolean bool() coercion defect only; broader declaration authorization remains open under ISSUE-0054 and related F-01 issues.
