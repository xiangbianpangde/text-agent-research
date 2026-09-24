---
id: "ISSUE-0172"
title: "--only 重跑同一场景时 run 路径会产出两行同一场景：控制台与 --report 对同一次测量给出相反判决"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "duplicate_scenario_row_in_report"
  - "run_path_seeds_from_stored_then_pushes_same_scenario"
  - "console_contradicts_report"
  - "opposite_verdicts_same_measurement"
  - "unreconcilable_by_auditor"
evidence: "catalog/test/recovery-run.ts：rows 由 readLatestRows() 初始化（第382行 const rows = latest.filter(usableObservation)），--only 分支又绕过 resume 规则重跑同一场景并 rows.push(row)。实测：rec-semantic-version-mismatch 在 jsonl 中有两行（line index 24 与 47），旧行 judged=null（unjudged: no research_* tool was called），新行 PASS。run 结束时控制台打印 'UNJUDGED rec-semantic-version-mismatch [SEMANTIC_INDEX_CORRUPT]: no research_* tool was called'，而同一文件执行 npm run m3:recovery -- --report 打印 'unjudged: 0'。判据重算证据：/tmp/recompute.mjs 对两行分别重算，row#0 calls=30 research_* 工具 0 个、row#1 calls=25 research_* 工具 4 个。"
related:
  - "ISSUE-0170"
fix_ref: null
summary: "--only 重跑同一场景时 run 路径会产出两行同一场景：控制台与 --report 对同一次测量给出相反判决"
---

## 现象

同一次测量在两条读出口径下得出相反结论（run 结束时的汇总 vs --report 对同一 jsonl 的重算），且差异成因（重复行）不出现在任何输出里。审计者按合同「读数必须能从磁盘复算」去核对时会得到与控制台不同的数字，且无从判断哪个是权威。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

授权重跑的 3 个回合中，version-mismatch 的 PASS 一度被报告为 UNJUDGED；若按控制台读数结项，会把一个通过的场景写成未判（下偏），也会让地板缺口数目算错。

## 根因

文件是 append-only（每行是一次付费回合的记录，必须保留），但内存中的报告列表被当成 append-only 使用；readLatestRows 的『每场景取最新』语义只在读盘时成立，未在写入路径上维持。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
