---
id: "ISSUE-0069"
title: "v71 runner/campaign.py import block is unsorted under Ruff"
status: "open"
severity: "low"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "campaign_import_order_warning"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/runner/campaign.py:15-44; /tmp/r56_v71_campaign_import_order.out SHA-256 6430dfdfc721486b371cf35116259aa8fda31412bb1307a4d096b91567fb6c04"
related: []
fix_ref: null
summary: "v71 runner/campaign.py import block is unsorted under Ruff"
---

## 现象

ruff check --select I reports I001 for the campaign import block. This does not itself change benchmark validity but leaves the committed runner outside the declared lint baseline.

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
