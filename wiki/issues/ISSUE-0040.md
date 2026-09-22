---
id: "ISSUE-0040"
title: "v62 run_benchmark_campaign writes summaries without creating parent directory"
status: "verified"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "campaign_output_dir_missing,scorecard_persistence_crash"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; run_benchmark_campaign.py:53-57; source inspection"
related: []
fix_ref: "5227b03dbf2af80d9abd5d47161483dd2864d519"
summary: "v62 run_benchmark_campaign writes summaries without creating parent directory"
updated_at: "2026-09-17"
---

## 现象

After run_quick_ci() the script writes results/summaries/scorecard.md and results.json but never creates results/summaries; a clean results tree raises FileNotFoundError after campaign execution, preventing scored output publication.

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

## 处置记录 2026-09-17T16:39:00+0800

Round 51/v64 independent source probe verified the recorded directory-creation symptom fixed: /tmp/r51_v64_static_probe_v2.out (SHA-256 d770ada4bd0abbc0f7d545b37f2464fef4ffbd0370ccfe34bd10183a6c307079) reports cli_creates_summary_dir=true, and the v64 CLI code creates results/summaries before writing. This only closes the output-directory defect; score/provenance/runtime gates remain open.
