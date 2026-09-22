---
id: "ISSUE-0042"
title: "v62 campaign reruns append duplicate query/system records without run identity"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "event_rerun_duplicate,no_campaign_idempotency"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/campaign.py:227-229,423-431; /tmp/r49_v62_event_rerun_probe.out"
related: []
fix_ref: null
summary: "v62 campaign reruns append duplicate query/system records without run identity"
updated_at: "2026-09-17"
---

## 现象

Two successful run_quick_ci(num_queries=1) calls to the same output produce 12 records; each Q-CI-001/system participant pair appears twice. No campaign/run ID or deduplication binds an event set, so restart/retry can double-count results.

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

## 处置记录 2026-09-17T16:35:30+0800

Round 51/v64 source and shipped-artifact audit remain open: CampaignRunner repairs a tail and opens events.jsonl in append mode but has no campaign/run idempotency key or duplicate suppression. Re-running appends duplicate query/system records; the immutable v64 shipped events.jsonl already has 736 historical records unrelated to the package's current physical files.
