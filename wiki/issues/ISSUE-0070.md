---
id: "ISSUE-0070"
title: "v71 retrieval metrics count duplicate document IDs as independent relevant hits"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "retrieval_duplicate_overcount,recall_above_one,ndcg_duplicate_inflation"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; metrics/retrieval.py:precision_at_k,recall_at_k,ndcg_at_k; /tmp/r56_v71_retrieval_duplicate_metrics_probe.out SHA-256 43d496a1f37a0e197b440824413c2489739d9bfa4747a7d764851d89c0a30ac5"
related: []
fix_ref: null
summary: "v71 retrieval metrics count duplicate document IDs as independent relevant hits"
---

## 现象

Duplicate retrieved IDs are counted repeatedly: one gold document retrieved twice yields recall=2.0 and ndcg=1.0, while duplicate slots can inflate recall above one and nDCG remains perfect. The evaluator has no per-query deduplication or duplicate-penalty invariant, so a participant can inflate scores with repeated citations.

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
