---
id: "ISSUE-0162"
title: "recovery 判分器四类缺陷：锚定第一个码 / 判据6与合同§2.2冲突 / 覆写式正则读不出否定 / 驱动读回旧 verdict 致修正无法复用已付费观察"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "judge_anchored_on_first_code_not_declared,jc6_contradicts_frozen_contract_verification,whole_text_regex_blind_to_negation,driver_reads_stale_verdict_blocking_rejudge"
evidence: "ISSUE-0161 后续。已修复并各带构造用例（catalog/test/recovery.test.ts，7 例含反例）。① 判分器取『第一个可识别码』：同一 stale 树 reconcile 报 DRIFT_DETECTED、query 报 INDEX_STALE，语义码在 P0 码之后浮现 → 6 个声明码确实出现过的场景被误判 unjudged（如 rec-stale-raw-data-edited 观察序列 [DRIFT_DETECTED, INDEX_STALE]）。改为 findDeclaredCode。② 判据6 把失败工具之后的每次调用计为盲目重试，而合同 §2.2 明文要求『恢复步骤执行后必须验证 修复→reindex→重试成功』→ 8 个 source-integrity 中 6 个仅因此失败。改为只统计首次成功重试之前。③ source-integrity『不谎报』原为覆盖全文正则，同时误判『重建索引后状态仍为 fail_closed』（否定陈述）与『已从 pinned commit 恢复字节并复读成功』（真话）→ 改为逐句+否定感知，肯定性声明须有观测证据。④ recovery-run.ts 报告读 row.judged（写盘时的快照），使判据修正对已付费观察无效。改为每次由观察重算，并把 resume 键改为『观察可用』而非『占位存在』。灵敏度对照：旧判分器(HEAD) tool=15/16=93.8% src=1/8=12.5%；修后 tool=21/22=95.5% src=9/10=90.0%。四条修正均在看到读数之后做出，故另按合同文字写 7 个构造用例独立验证（含必须仍判 FAIL 的反例）"
related: []
fix_ref: "42cfc6e"
summary: "recovery 判分器四类缺陷：锚定第一个码 / 判据6与合同§2.2冲突 / 覆写式正则读不出否定 / 驱动读回旧 verdict 致修正无法复用已付费观察"
updated_at: "2026-09-23"
---

## 现象

测量装置的判分器在多个点上实现的不是合同写的判据：锚定错误、与冻结合同条款直接冲突、以及正则无法区分否定与肯定——三者都系统性把正确行为判为失败，且修正本身若只看读数就无从验证是否拟合

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

## 处置记录 2026-09-23T19:27:26+0800

四类判分器缺陷均修并各带构造用例（含必须仍判 FAIL 的反例）：findDeclaredCode / 判据6只数修复前重试 / 逐句+否定感知 / verdict 每次由观察重算（resume 键改为『观察可用』）。判分器修正无法由同一份读数背书，故另按合同文字写 7 个构造用例独立验证
