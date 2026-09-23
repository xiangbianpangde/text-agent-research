---
id: "ISSUE-0153"
title: "判分 harness 的空 turn 被计为『模型未调用工具』，使 harness 故障归因给模型（recall 90% 中 1 例由此而来）"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "empty_turn_scored_as_model_miss,harness_failure_attributed_to_model,zero_token_turn_no_error,no_retry_on_empty_turn,inconclusive_state_missing"
evidence: "catalog/test/trigger-results.jsonl 中 pos-integrity 记录（input_tokens=0/output_tokens=0/tools=[]/error=null）；单独重跑同一用例正常；修复：新增 isEmptyTurn() + runTurnWithRetry()（有界重试 2 次），仍空则标记 inconclusive 并从所有比率中排除、按 id 报告；inconclusive 字段同时持久化并在 rejudge 中回读（否则重判会把空 turn 静默提升为计分项）；测试 catalog/test/judge.test.ts M3-6 组 5 项"
related: []
fix_ref: null
summary: "判分 harness 的空 turn 被计为『模型未调用工具』，使 harness 故障归因给模型（recall 90% 中 1 例由此而来）"
---

## 现象

pos-integrity 在全量运行落盘为 tools=[] / calls=[] / input_tokens=0 / output_tokens=0 / error=null，其判分只产出 notes=['no ResearchCTL tool was called']，于是被计入 Trigger Recall 分母（9/10=90%）。零 token、零工具、无错误三条同时成立说明子进程根本没产出响应，是 harness/子进程层偶发，而非模型选择不调工具；单独重跑即正常（28 次调用、drift 注入生效）。危害被放大：该用例恰是 DRIFT_INJECTED_CASES 的唯一成员，空 turn 使 fail_closed_recovery 的分母为 1 却无事可判。

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
