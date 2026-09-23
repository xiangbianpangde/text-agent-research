---
id: "ISSUE-0148"
title: "M3 两项门禁被误判为『harness 无法测量』：wrong_layer 与 fail_closed_recovery 实际可由调用实参与注入式错误同轮观测，原文错误推理已致 §7.4 三条长期挂空"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "metric_declared_unmeasurable_without_attempt,layer_inferred_from_tool_name,recovery_assumed_to_need_second_turn,fixture_controlled_condition_never_injected"
evidence: "researchctl-product docs/records/M3-G3-acceptance-record.md §5（2026-09-23 重写前）称 Wrong-Layer『需要读取答案内容』、Fail-Closed Recovery『需要真实错误之后的第二轮』。两点均不成立：(1) 层由调用实参决定——真实 CLI 实测 --semantic --entity CURRENT 得 status=success retrieval_mode=None（走 exact），--semantic --text 得 retrieval_mode=semantic，--semantic 单独出现被 cli.py:46 标注『忽略该开关』；故层是调用的属性，不需要读答案。(2) 恢复序列『错误→research_integrity→重试成功』三段可在同一轮内发生，缺的是初始错误，而 fixture 由 harness 控制。已实现 catalog/test/layer.ts（判别链 entity→doc_type→status→raw→text）与 catalog/test/drift.ts（注入 m3-drift-probe.sqlite，因命中 .gitignore 故对 git status 隐形、不污染 Mutation Safety 观测），并接线 trigger.ts。变异验证 5/5 被捕获。另：原文用 forbids 含 semantic 工具作为『二者重合』的桥梁，但 research_query 一个工具可服务五个层，该桥不成立。"
related: []
fix_ref: null
summary: "M3 两项门禁被误判为『harness 无法测量』：wrong_layer 与 fail_closed_recovery 实际可由调用实参与注入式错误同轮观测，原文错误推理已致 §7.4 三条长期挂空"
---

## 现象

门禁被标为『N/A—无法测量』并非因为真的不可测，而是因为未构造观测条件；这类结论会长时间阻挡里程碑判定，且看起来像诚实（返回 null 而非伪造通过）。

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
