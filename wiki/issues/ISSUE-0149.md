---
id: "ISSUE-0149"
title: "catalog/test/trigger.ts 长期不在 typecheck 列表内，潜伏两个真类型错误：TurnResult 重复声明 error、Metrics 缺 truncated_cases"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "measurement_code_excluded_from_typecheck,duplicate_interface_field,schema_used_but_undeclared"
evidence: "researchctl-product catalog/test/tsconfig.json 在 2026-09-23 前未包含 trigger.ts/corpus.ts（npm run m3:typecheck 仅覆盖部分测试文件）。加入后 tsc 立刻报错：(a) TurnResult 在 HEAD:catalog/test/trigger.ts 中 error 字段声明两次（:189 与 :204 附近），tsc 报 duplicate identifier；(b) Metrics 接口（HEAD:408-421）无 truncated_cases，但 computeMetrics 返回对象含该字段、main() 在 :886-889 读取它，tsc 报 excess property / property does not exist。修复：加入 tsconfig，去重 error，补声明 truncated_cases: string[]。注：这解释为何此前的『typecheck clean』并不覆盖测量器本身。"
related: []
fix_ref: null
summary: "catalog/test/trigger.ts 长期不在 typecheck 列表内，潜伏两个真类型错误：TurnResult 重复声明 error、Metrics 缺 truncated_cases"
---

## 现象

声称类型检查通过的代码其实从未被检查；测量器的字段增删不会被任何工具发现，只能靠人读。

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
