---
id: "ISSUE-0038"
title: "v62 campaign can persist a post-query-invalidated envelope"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "postquery_invalidation_ignored,campaign_envelope_recheck_gap"
  - "v71_campaign_late_accept_after_watchdog"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/campaign.py:369-389; runner/worker_supervisor.py:1008-1017; /tmp/r49_v62_campaign_late_accept_probe.out"
related: []
fix_ref: null
summary: "v62 campaign can persist a post-query-invalidated envelope"
updated_at: "2026-09-18"
---

## 现象

A worker emits a valid response, then late unframed stdout after supervisor query's stability sniff. Idle watchdog invalidates the same envelope and terminates the worker, but campaign's post-query check only inspects sup.proc and session_invalidated (never rechecks envelope schema_valid/state). Probe's exact check says campaign_would_persist=true while envelope schema_valid=false, state=FAILED, proc=None, invalidation=1.

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

## 处置记录 2026-09-18T08:39:13+0800

v71 clean-room probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9 reproduces the campaign guard gap. After a valid query, delayed unframed stdout is consumed by the idle watchdog: response_object_returned=true, envelope_schema_valid_now=false, state=FAILED, invalidations=1, proc still alive, session_invalidated attribute absent, and no readable stdout remains. Reimplementing runner/campaign.py's post-query guard yields campaign_guard_would_reject=false and campaign_would_persist=true. Evidence /tmp/r56_v71_campaign_late_accept.out SHA-256 62430d5e52316d63f1bdb59448f1e8ac218f45ce5ecfedab2caddb84609b4aa7. Campaign must re-check envelope/state/invalidation before persistence and must terminate the idle watchdog failure.
