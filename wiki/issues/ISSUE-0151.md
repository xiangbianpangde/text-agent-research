---
id: "ISSUE-0151"
title: "catalog 语料 harness 按工具名回溯配对 tool_result，并行调用下把结果错接到另一个调用（实测两条 args/outcome 互斥）"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "tool_result_paired_by_tool_name,parallel_tool_call_result_misattribution,event_stream_ordering_assumed_sequential,tool_call_id_ignored,call_args_outcome_mutually_exclusive"
evidence: "catalog/test/trigger-results.jsonl pos-impact-downstream（修复前）；catalog/test/archive/trigger-results.pre-0146-*.jsonl 与 .midfix-0146-*.jsonl；修复 commit 见 catalog/test/trigger.ts:applyEvent 使用 call_id；单例重跑日志 catalog/test/archive/corpus-post-0146-20260923T101455.log；扫描脚本命中 2 条互斥记录"
related: []
fix_ref: null
summary: "catalog 语料 harness 按工具名回溯配对 tool_result，并行调用下把结果错接到另一个调用（实测两条 args/outcome 互斥）"
---

## 现象

catalog/test/trigger.ts 的 applyEvent 处理 tool_execution_end 时，从 calls 数组末尾按工具名回溯找最近一次同名未配对调用。Pi 的事件序并非如此：tool_execution_start 按模型发出顺序，tool_execution_end 按完成顺序；并行同名调用完成次序可倒置，于是结果被接到先发出但后完成的那次调用上。落盘证据：trigger-results.jsonl 中 pos-impact-downstream 出现两条结构上不可能的 args/outcome 组合——{"entity":"ORG-EXP101"} → SEMANTIC_NOT_INDEXED（判别链优先于 semantic，带 entity 的调用不可能返回该错误码）与 {"semantic":true,"text":"ORG-EXP101"} → success（fixture 无 semantic 索引，必返回 SEMANTIC_NOT_INDEXED）。改用 toolCallId 配对后，单例重跑该 case 的层级违规由 3 降至 0，两条不可能组合同时消失。

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
