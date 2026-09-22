---
id: "ISSUE-0045"
title: "v62 supervisor-owned CAS is deleted before campaign retention"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "cas_lifetime_cleanup_order,retention_after_cas_delete"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/worker_supervisor.py:484-498,1959-1963; runner/campaign.py:455-458; /tmp/r49_v62_cas_lifetime_probe.out"
related: []
fix_ref: null
summary: "v62 supervisor-owned CAS is deleted before campaign retention"
---

## 现象

When workspace/.benchmark_cas is unavailable, supervisor falls back to auto-created supervisor_cwd/cas. shutdown() removes auto-created supervisor_cwd before CampaignRunner._persist_raw_retention(); CAS disappears and retention publishes only missing_cas_systems with empty blobs.

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
