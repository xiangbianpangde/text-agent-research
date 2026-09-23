---
id: "ISSUE-0133"
title: "corpus 子进程隐式加载全局 skills 与 AGENTS.md，触发率指标混入非 catalog 因素"
status: "fixed"
severity: "medium"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "harness_implicitly_loads_global_context,trigger_metric_confounded_by_skill_description,measurement_validity_unstated"
evidence: "researchctl-product/catalog/test/trigger.ts:159 argv 仅含 --no-session -ne -e <extension>，未含 -ns/-nc；实测子进程 pi 可见 20 个 skills，其中 research-retrieval 的 description 含'当前结论是什么/依据来源/历史演化'与正例 prompt 近逐字重合；对照实验 /tmp/skill-probe.mjs: pos-current-conclusion WITH skills=research_tools,research_query total=9 vs WITHOUT (-ns)=research_tools,research_query total=6；/tmp/ctx-probe.mjs: -ns -nc 与全量加载结果一致（research_status/ research_tools,research_query）"
related: []
fix_ref: "b98410e"
summary: "corpus 子进程隐式加载全局 skills 与 AGENTS.md，触发率指标混入非 catalog 因素"
updated_at: "2026-09-23"
---

## 现象

语料在子进程中带全局 skills 与 AGENTS.md 运行，触发可能部分来自 research-retrieval 技能描述而非 catalog 自身。对照实验显示去掉 skills 后 recall 行为不变（正例仍调用正确工具、neg-smalltalk 仍为零调用），故当前结论不受影响；但 harness 未固定该变量，报告也未说明，读数容易被误读为纯 catalog 效果，且将来 skills 描述改动会静默影响指标。

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

## 处置记录 2026-09-23T01:33:10+0800

runner 现在传 -ns -nc，指标定义固定为'catalog 面对纯编码 prompt'。对照实测：带/不带 skills 时 recall 行为一致，故此前结论不受影响。
