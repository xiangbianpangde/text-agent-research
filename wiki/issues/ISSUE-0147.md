---
id: "ISSUE-0147"
title: "corpus runner 的 rejudge 丢弃 mutated_files/drift_injected，重新判定时 safety_tree_mutations 恒为 0（ISSUE-0137 同型：字段在管道里但没进判定）"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "rejudge_drops_persisted_fields,safety_metric_optimistic_on_rejudge,field_written_but_never_read_back"
evidence: "researchctl-product HEAD=fa7ea21。catalog/test/trigger.ts:402 的 appendResult 写入 mutated_files: turn.mutated_files ?? []，:335 TurnResult 声明该字段，:603 computeMetrics 读 safetyTreeMutations 并汇入 metrics.safety_tree_mutations；但 HEAD 版 rejudge（:778）只把 {tools, activations, text, first_useful_ms, error} 交给 judge()，mutated_files 不在其中，也不存在 drift_injected。后果：对已有 jsonl 重判时 safety_tree_mutations 恒为 0，而 real runner 路径可为非 0（safety-* 用例模型写树时）。修复：git diff HEAD -- catalog/test/trigger.ts 显示 rejudge 改为透传 mutated_files/drift_injected/calls，并引入 PersistedTurn 形状约束两侧。已加测试：catalog/test/judge.test.ts 断言重判后 safety 计数与首次判定一致。"
related: []
fix_ref: null
summary: "corpus runner 的 rejudge 丢弃 mutated_files/drift_injected，重新判定时 safety_tree_mutations 恒为 0（ISSUE-0137 同型：字段在管道里但没进判定）"
---

## 现象

用 --rejudge 复算历史结果时，Mutation Safety 相关的树改写计数永远显示 0，即使原始运行真的改过树；结论在安全维度上系统性偏乐观。

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
