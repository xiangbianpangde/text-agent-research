---
id: "ISSUE-0075"
title: "v71 DenseRAG returns zero-score citations while abstained, so retrieval metrics can report perfect recall"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "abstention_retrieval_score_inflation,zero_score_retrieval"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/adapters/rag.py:92-126; metrics/retrieval.py:20-44; /tmp/r56_v71_dense_zero_score_probe.out SHA-256 1e460121eff9c4e64fe64b498bf67385c918c533026cb07a0f4733aff2cd9dfc"
related: []
fix_ref: null
summary: "v71 DenseRAG returns zero-score citations while abstained, so retrieval metrics can report perfect recall"
---

## 现象

For a query with no vocabulary overlap, DenseRAGAdapter returns a cited document with score=0.0 and abstained=true; scoring those paths against a one-document qrel yields recall@10=1.0 and nDCG@10=1.0. The campaign counts retrieval items without excluding abstained/zero-score results.

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
