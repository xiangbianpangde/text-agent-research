---
id: "ISSUE-0150"
title: "语料运行时的 fixture 树不含 semantic 索引（.index 被 gitignore），使 semantic 层调用全部 fail-closed——该层的层级违规在本配置下几乎不可观测"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "fixture_missing_semantic_index,semantic_layer_untestable_in_corpus,fail_closed_calls_excluded_from_layer_denominator,coverage_gap_looks_like_compliance"
evidence: "researchctl-product fixture=researchctl/tests/fixtures/product-v1/tree。实测该树 .index/research.sqlite 仅含 index_metadata/documents/entities/versions/runs/relations/source_refs/events，无 semantic 三表；git check-ignore 确认 .index/ 未入库（.gitignore:37 覆盖整个 tree/）。因此 query --semantic --text 得 status=fail_closed error_semantic=SEMANTIC_NOT_INDEXED（对照：在临时副本上先跑 index --semantic 后同一命令得 status=success retrieval_mode=semantic n=3）。而 layer.ts 只把『给出了答案』（error_code===null）的调用计入 wrong_layer 分母，故该层违规在本配置下基本无法进入分母。需改造：fixture 构建阶段预置语义索引，或语料前置一道 index --semantic。"
related: []
fix_ref: null
summary: "语料运行时的 fixture 树不含 semantic 索引（.index 被 gitignore），使 semantic 层调用全部 fail-closed——该层的层级违规在本配置下几乎不可观测"
---

## 现象

层级门禁会因为『该层根本没被触达』而显示为无可判定（null/N/A），容易被读成『模型没走错层』。

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
