---
id: "ISSUE-0131"
title: "acceptance corpus 的 hard negative 要求真实开发工作，8/25 用例在 240s 上限处被截断"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "corpus_prompt_requests_real_dev_work,case_measures_task_completion_not_routing,truncation_rate_32pct"
evidence: "researchctl-product/catalog/test/trigger-results.jsonl: 8/25 timeout. Prompt of neg-index-keyword='数据库索引太慢了，帮我加一个复合索引。' → tool sequence read,bash×4,read,bash×20+,read,edit,edit,edit,bash... (model implements the index); neg-journal-keyword='我们自己的应用日志文件太大了，怎么轮转？' likewise; pos-impact-downstream='如果我把 ORG-EXP101@v4 改成 v5，会影响哪些下游的东西？'→research_impact called then 45+ bash calls"
related: []
fix_ref: "dff4d9e"
summary: "acceptance corpus 的 hard negative 要求真实开发工作，8/25 用例在 240s 上限处被截断"
updated_at: "2026-09-23"
---

## 现象

语料把'模型会不会伸手拿 ResearchCTL'和'模型能否在 240s 内完成一个实现任务'混在同一个用例里。请求真实开发工作的 hard negative 会进入 bash/edit 长循环而非给出简短回答，达到超时上限；这些用例无法测出路由行为，只测出截止时间。截断率 32% 使 precision 与 recall 建立在 17 个完整观测上，且 Mutation Safety 的 n 从 4 降到 2。

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

三个派活式 hard negative 改为同关键词提问式；截断 8/25 → 3/25，四个负例全部保持干净；默认超时 240s → 150s。
