---
id: "ISSUE-0114"
title: "工具触发：英文科研词汇与通用工程词汇重叠，单词命中即路由导致精度塌陷"
status: "open"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "keyword_overlap_precision_routing,generic_engineering_vocabulary,single_token_route"
evidence: "catalog/test/loader.test.ts（keyword-bearing negatives 用例）；catalog/search.ts keywordScore 权重注释；实测：'the transaction handler needs a retry' / 'wrap this in a transaction' / 'update the checkpoint logic' / 'make a digest of this string' 均以 score=3 命中 research_integrity 或 research_journal；变异 'MATCH_THRESHOLD → 0' 起初 35/35 全绿（未被任何用例捕获）"
related: []
fix_ref: null
summary: "工具触发：英文科研词汇与通用工程词汇重叠，单词命中即路由导致精度塌陷"
---

## 现象

research_tools loader 的关键词表里，transaction/journal/checkpoint/digest/query/index/trace 等英文词同时是通用软件工程词汇。原实现给单词精确命中权重 3，高于阈值 2，于是普通编码请求（'wrap this in a transaction'）会被判为科研意图并激活 ResearchCTL 工具。Spec §7.4 Trigger Precision ≥ 90% 与 Wrong-Layer Rate = 0 会被这类误触发直接击穿，且损害发生在最常见的日常任务上。

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

已修复：英文单词命中权重降为 1（低于阈值），仅英文多词短语与 CJK 关键词保留权重 3，因此英文查询需要两个不同 token 才能路由。修复后 12 条 hard negative 全部拒绝、7 条正例全部正确路由。同时补测 parity：'单个英文 token 永不足以路由' 与 'CJK 权重降为 1' 两个变异现在都会变红。
