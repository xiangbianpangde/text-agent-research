---
id: "ISSUE-0132"
title: "corpus harness 复用同一个 fixture 目录，用例的写入会泄漏到后续用例"
status: "fixed"
severity: "medium"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "fixture_shared_across_cases,case_writes_leak_into_later_cases,no_per_case_isolation"
evidence: "researchctl-product/catalog/test/trigger.ts:55 fixtureRoot 是单一目录，:93 cwd: fixtureRoot 对每个用例相同；实跑后 git -C researchctl/tests/fixtures/product-v1/tree status 显示 ' M index/INDEX.md'（由 neg-index-keyword 触发的 generate-index 写入，git diff --stat = 1 file changed, 56 insertions(+), 5 deletions(-)）；第 2 轮用例的工具序列中出现的 read,edit,edit,edit,bash 表明模型确实在 fixture 内改文件"
related: []
fix_ref: "dff4d9e"
summary: "corpus harness 复用同一个 fixture 目录，用例的写入会泄漏到后续用例"
updated_at: "2026-09-23"
---

## 现象

25 个用例共用一棵 fixture 树。任何写类用例（generate-index、以及模型自行发起的 edit）都会改到后续用例看到的状态，使用例之间不再独立；实测 fixture 的 index/INDEX.md 被前一用例改写并保留。行序敏感的用例（索引新鲜度、git commit 状态）会因此得到依赖运行顺序的结果，重跑不再可复现。

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

每例一个私有 fixture 副本（实测 copy 24ms / 368KB），turn 结束含超时路径一律 dispose；探针验证共享树在写类用例后仍为干净。
