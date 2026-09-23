---
id: "ISSUE-0159"
title: "m3:typecheck 用显式 files[] 列表，新文件未加入 → 类型检查静默跳过，0 error 是空结论"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "typecheck_vacuous_due_to_explicit_files_list,driver_untested_until_paid_run"
evidence: "catalog/test/tsconfig.json 使用 'files': [...] 显式列表；新增 catalog/test/recovery.ts、recovery.test.ts、recovery-run.ts 后未加入该列表。npm run m3:typecheck 报告 0 error（实际未读这三个文件）。把三者加入后立刻报出 5 个真实错误：recovery-run.ts(91,3) TS2322 category 'integrity' 不属于 CorpusCategory；recovery-run.ts(183,5) TS2322 error_code undefined 不可赋给 string|null；recovery-run.ts(211,28) TS2339 Property 'ok' does not exist on RecoveryVerdict；recovery-run.ts(211,101) TS2339 Property 'reason' 同上；recovery.ts(818,19) TS2367 比较无交集（src-manifest-deleted 分支内的 dead ternary）。其中 recovery-run.ts 的 judgeRecovery 未 import + judged.ok/reason 读不存在字段，导致 npm run m3:recovery -- --run 在跑完第 1 个真实付费 turn 后于 recovery-run.ts:193 抛 ReferenceError: judgeRecovery is not defined，该 turn 结果为未写盘即丢弃"
related: []
fix_ref: null
summary: "m3:typecheck 用显式 files[] 列表，新文件未加入 → 类型检查静默跳过，0 error 是空结论"
---

## 现象

验收记录里的『m3:typecheck 0 error』对新增文件无约束力：显式 files[] 列表使 tsc 静默跳过未列入的文件，于是存在未被类型检查、也未被任何测试覆盖的驱动文件；它的缺陷在花费真实模型配额后才暴露

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
