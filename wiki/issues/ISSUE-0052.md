---
id: "ISSUE-0052"
title: "v63 campaign scorecard uses global qrels and mislabeled aggregate metrics"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "campaign_qrel_scope,metric_label_mismatch,hardcoded_audit_metric"
evidence: "commit 0e9adf49c5c8a89c981432abcf6fea30d6998bfb; /private/tmp/r50_v63_campaign_scoring_static_reprobe.out SHA-256 79d03af17175ae2630a39d97cc3b68fa070fe0a3ade799e3e7b2fe804b797b4b; runner/campaign.py:196,437-438,491-498"
related: []
fix_ref: null
summary: "v63 campaign scorecard uses global qrels and mislabeled aggregate metrics"
updated_at: "2026-09-17"
---

## 现象

Campaign flattens per-query qrels, hardcodes expected_value=0.8431, reports prov_f1 as ExactProv and arithmetic mean as p50_retrieval_ms

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

## 处置记录 2026-09-17T16:34:04+0800

Round 51/v64 static scoring audit remains negative: /tmp/r51_v64_static_probe_v2.out (SHA-256 d770ada4bd0abbc0f7d545b37f2464fef4ffbd0370ccfe34bd10183a6c307079) still detects global qrel flattening, hardcoded expected_value=0.8431, exact_rate reusing prov_f1, arithmetic mean mislabeled p50_retrieval_ms, and k=10 despite the evidence cap of 8. No scored or comparative run is admissible.
