---
id: "ISSUE-0130"
title: "corpus/judge 把超时截断的轮次当作完整观测计分，指标随之偏移"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "corpus_truncation_scored_as_observation,error_field_not_reaching_judge,hard_negative_prompt_requests_real_dev_work"
evidence: "researchctl-product/catalog/test/trigger-results.jsonl: 25 unique cases, 8 with error='timeout after 240000ms' (pos-impact-downstream, fuzzy-remember-error, neg-journal-keyword, neg-index-keyword, neg-git-commit, boundary-recall-and-fact, safety-freeze-vague, safety-clean-up); researchctl-product/catalog/test/trigger.ts:122 sets result.error, :616 persists error, but judge() at :222-270 never reads TurnResult.error"
related: []
fix_ref: "dff4d9e"
summary: "corpus/judge 把超时截断的轮次当作完整观测计分，指标随之偏移"
updated_at: "2026-09-23"
---

## 现象

TurnResult.error 在 runTurn 写入、在 results.jsonl 持久化、在 main 打印，却从不进入 judge()。超时轮次因此按'模型没有调用任何工具'计分：hard_negative 被截断反而判为 clean，positive 被截断判为 recall miss。8/25 用例受影响，precision 与 recall 均按不可控方向偏移。

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

## 处置记录 2026-09-23T01:33:07+0800

TurnResult.error 现在进入 judge()，truncated 例按存在性/缺失性分别处理；rejudge 不再丢弃持久化的 error。judge.test.ts 断言该字段改变指标，变异测试 1 个失败。
