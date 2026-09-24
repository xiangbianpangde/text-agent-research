---
id: "ISSUE-0180"
title: "M3 recovery 的 --run 可绕过必须先通过的 containment preflight"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "run_bypasses_preflight"
evidence: "/Users/xbpd/Projects/researchctl-product/catalog/test/recovery-run.ts:328 将 wantsRun 仅设为 args.includes('--run')；:348-359 的 containmentPreflight() 只在显式 args.includes('--preflight') 分支执行并 return；`rg -n 'containmentPreflight\(' catalog/test/recovery-run.ts` 仅命中 :352；模型执行路径 :558 调用 runTurnWithRetry，未检查 preflight 结果。故 `--run` 可在未运行/未通过 preflight 时启动模型回合。静态审查当前 HEAD 64f076d；本次未运行模型。"
related: []
fix_ref: "c30ae59"
summary: "M3 recovery 的 --run 可绕过必须先通过的 containment preflight"
updated_at: "2026-09-24"
---

## 现象

命令文档与授权要求 preflight 在首个模型回合前测量，但运行器把它做成独立可选参数，--run 不会强制检查；若 worktree discovery 或 sandbox probe 失效，调用者跳过 preflight 仍可消费预算并产出不可采信观测。

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

## 处置记录 2026-09-24T10:01:29+0800

已修复： 抽出 ， 路径在任何 staging/seeding/模型回合之前调用它，失败则 stderr 输出 REFUSING TO RUN 并以 exit 3 退出。验证：把 git 桩为 exit 1 使 discovery 返回 null 时， 实测 exit=3 且 pi 桩未被触达（测试断言 'STUB PI INVOKED' 不出现）；变异验证：门禁改为 false && → 测试失败。preflight 本体仍可由 --preflight 单独查看。

## 处置记录 2026-09-24T10:01:34+0800

已修复（commit c30ae59）：recovery-run.ts 抽出 runPreflight({quiet}) 辅助函数，--run 路径在任何 staging/seeding/模型回合之前调用它；失败则 stderr 输出 REFUSING TO RUN 并以 exit 3 退出。preflight 本体仍可由 --preflight 单独查看（同一条代码路径，无重复实现）。验证：把 git 桩为 exit 1 使 worktree discovery 返回 null（containment fail-closed）时，实跑 `node --import .../typebox-register.mjs catalog/test/recovery-run.ts --run --only rec-stale-nested-subdir-doc` → exit=3，且 pi 桩未被触达（测试断言 'STUB PI INVOKED' 不出现）。变异验证：门禁条件改为 false && → 测试失败。注意：该变异测试暴露出第二个缺陷（测试可写付费归档），已登记 ISSUE-0182 一并修复。
