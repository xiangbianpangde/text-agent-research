---
id: "ISSUE-0152"
title: "语料偶发空 turn（0 tokens、0 工具、无 error）被静默计为『recall 未达成』，且正好落在唯一的 recovery 用例上"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "empty_turn_scored_as_model_miss,zero_token_turn_no_error_field,flake_masquerades_as_model_failure,no_empty_turn_retry,single_recovery_case_flakes"
evidence: "catalog/test/trigger-results.jsonl（allfix 全量运行）pos-integrity：input_tokens=0 output_tokens=0 tools=[] error=null；同一文件追加的单独重跑记录：drift_injected=true、28 次调用、research_integrity 返回 DRIFT_DETECTED；日志 catalog/test/archive/corpus-allfix-20260923T110219.log 第 15 行『(no research tool)』；判分逻辑 catalog/test/trigger.ts judge() 对空 turn 无守卫"
related: []
fix_ref: null
summary: "语料偶发空 turn（0 tokens、0 工具、无 error）被静默计为『recall 未达成』，且正好落在唯一的 recovery 用例上"
---

## 现象

全量重跑中 pos-integrity 记录为 tools:[]、calls:[]、input_tokens:0、output_tokens:0、error:null。该 turn 既没有任何工具调用，也没有任何 token 消耗——即子进程根本没产出响应，属 harness/子进程层面的偶发空 turn，而不是模型选择不调工具。然而 judge() 对此只产出 notes=['no ResearchCTL tool was called']，把它计入 Trigger Recall 分母（9/10=90%），于是确定性失败被归因成模型行为。单独重跑同一用例即正常（28 次工具调用、drift 注入生效），证明其为非确定性 flake。危害被放大：该用例恰是 DRIFT_INJECTED_CASES 的唯一成员，空 turn 使 fail_closed_recovery 的分母虽为 1 但事件流为空，从而不可能判定恢复——n=1 的脆弱性由此从『样本太少』升级为『唯一那一个还会偶发失效』。

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
