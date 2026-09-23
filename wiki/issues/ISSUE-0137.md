---
id: "ISSUE-0137"
title: "loader 激活工具后不写 tool.activated 事件，G3『activation 可从 Journal 重放』实际不成立"
status: "fixed"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "activation_not_journaled,replay_returns_empty_on_real_data,gate_passing_on_synthetic_fixtures_only"
evidence: "catalog/extension.ts 只在 execute 内写 tool.called / tool.succeeded(response 240/331)，全仓无任何 tool.activated 写入点（grep -n 'tool.activated' catalog/*.ts 仅命中类型定义 :58 与读取端 register.ts:150/153/157）。端到端取证：RESEARCHCTL_STATE_HOME=/tmp/replay-state-home 跑一轮真实模型（prompt='检查一下这个研究项目有没有断链。'），turn.tools=research_tools,research_status,research_integrity,bash×17；真实 journal 记录 tool.discovered(tools), tool.called(tools), tool.succeeded(tools), tool.called(research_status), tool.succeeded(research_status), tool.called(research_integrity) —— 无一条 tool.activated。replayActivations(这6条) 返回 activated=[] discrepancies=[]，即静默空结果；而"
related: []
fix_ref: "pending"
summary: "loader 激活工具后不写 tool.activated 事件，G3『activation 可从 Journal 重放』实际不成立"
updated_at: "2026-09-23"
---

## 现象

G3 要求 tool activation 可从 Journal 完整重放，但激活事件从未被写入：loader 在结果 details 里返回 added，extension 只记录 tool.called/succeeded。读取端 replayActivations 因此对真实 journal 返回空数组且不报 discrepancy——空结果与'没有激活发生'不可区分，是静默失败。现有 loader.test.ts 的 replay 用例全部喂synth 事件数组，所以该门禁此前只被合成数据'通过'。真实模型轮次确实激活并调用了 research_integrity，journal 里却只有 called。

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

## 处置记录 2026-09-23T01:37:24+0800

extension.ts 在 execute 内按 details.added 顺序写 tool.activated；真实 journal 端到端复验：replay 得 [research_integrity] 与观测调用一致。loader.test.ts 新增『added == replay』回归用例，移除写入端即变红（41/42）。
