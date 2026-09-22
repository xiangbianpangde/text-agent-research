---
id: "ISSUE-0080"
title: "v71 retrieval worker ignores max_evidence_items and hard-codes an eight-item adapter request"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "worker_evidence_cap_bypass,max_evidence_items_not_propagated,retrieval_budget_violation"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9 (unchanged at HEAD 3eb82461f2f9fe0dd4eb68c889fd7f431d5fbace); research-retrieval-benchmark/runner/worker_supervisor.py:1682-1687; workers/retrieval_worker.py:322-345; contracts/worker_protocol.json query_request schema; /tmp/r56_v71_worker_limit_probe.out SHA-256 d0f263e274f3bfd89888ca723d507b1892fa88ae9e19c61f4fc3295b4ab5e0e2"
related: []
fix_ref: null
summary: "v71 retrieval worker ignores max_evidence_items and hard-codes an eight-item adapter request"
---

## 现象

A query request with max_evidence_items=1 is serialized by the supervisor, but retrieval_worker reads msg.get('max_items', 8), calls the adapter with max_items=8, and returns 8 retrieval items. The independent probe recorded adapter_max_items_seen=[8], response_retrieval_count=8, response_record_type=participant_response, return_code=2. The end-to-end evidence cap is not binding.

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
