---
id: "ISSUE-0074"
title: "v71 retrieval worker converts adapter exceptions into schema-valid abstentions"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "adapter_exception_laundered_as_not_found,worker_error_to_abstain"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/workers/retrieval_worker.py:319-325,340-352; runner/campaign.py:375-382; /tmp/r56_v71_worker_adapter_error_probe.out SHA-256 6fc785a109b71d0436c2ba78d089096d0fb6fc6cd28f8e42232963ae31083a1d"
related: []
fix_ref: null
summary: "v71 retrieval worker converts adapter exceptions into schema-valid abstentions"
---

## 现象

A RuntimeError from adapter.query is caught, returned as participant_response with abstained=true, no failure_semantic, and process exit 0; CampaignRunner maps it to failure_semantic=NOT_FOUND instead of a typed crash/failure, allowing backend failures to enter a valid-looking trace.

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
