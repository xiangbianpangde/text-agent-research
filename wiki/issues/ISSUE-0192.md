---
id: "ISSUE-0192"
title: "0189 修复的校验只测「上限为正」，不测「上限合规」——系数改 100→100000 全绿"
status: "fixed"
severity: "medium"
area: "researchctl"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "assertion_compares_value_to_itself"
  - "mutation_of_calibrated_constant_passes_suite"
  - "bound_asserted_as_sign_not_as_value"
evidence: "commit 4678a26 的 preflight 断言为 typeof proxy.budgetLimit === 'number' && proxy.budgetLimit > 0（catalog/test/trigger.ts），期望值由调用方 recovery-run.ts 的 authorizedTurns * UPSTREAM_REQUESTS_PER_AUTHORIZED_TURN 派生。实测：sed 把 UPSTREAM_REQUESTS_PER_AUTHORIZED_TURN 由 100 改为 100000 后，npm run test:catalog 全绿、--preflight 15/15 全过、exit 0——因为被断言值与期望值同源（同一个常量），任其取值如何都自洽。修后（catalog/test/recovery.test.ts 新增 'pins the ceiling calibration'）：同一变异下 not ok 7 'the per-turn request allowance changed'，# fail 1。对照变异 B（setBudget(999999) 与派生值 900 不一致）在修前即被捕获（exit 3，detail 'CEILING IS NOT THE AUTHORIZED ONE'），说明缺的不是「一致性检查」而是「取值本身无人断言」。"
related: []
fix_ref: "(this commit)"
summary: "0189 修复的校验只测「上限为正」，不测「上限合规」——系数改 100→100000 全绿"
updated_at: "2026-09-24"
---

## 现象

ISSUE-0189 的第二道门（请求上限）是本次修复唯一的真边界（门①nonce 按构造挡不住被测方）。但对该边界的校验只断言了「已 armed 且为正数」，未断言其取值。后果：系数被静默放宽 1000 倍（100→100000）时，套件与 preflight 全绿——上限仍在、类型正确、派生自洽，只是不再约束任何东西。该类缺口的成因是**断言与期望同源**：修复方与校验方读同一个常量，故「一致」成为恒真，无法检出漂移。

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

## 处置记录 2026-09-24T18:49:55+0800

修复：① preflight 的 gate-2 断言现在接受调用方传入的 expectedRequestCeiling，与「授权回合数派生出的值」比较，而不只是与 0 比较——变异 B（setBudget(999999) vs 派生 900）实测 exit 3 且 detail 明写 'CEILING IS NOT THE AUTHORIZED ONE: armed at 999999, but the run derived 900'；未传期望值时不再静默退化为符号检查，detail 行会明说 'positivity only -- caller supplied no expected value, so this run did NOT verify the ceiling matches its authorization'。② 新增 recovery.test.ts 'pins the ceiling calibration' 钉住系数取值本身（并断言 100 > 60，即超过历史最忙回合的 60，避免上限在合法回合上误触发）。变异 A（100→100000）在修前全绿、修后 not ok 7。两条断言互补且互不蕴含：前者防「上限偏离授权」，后者防「授权本身被悄悄放大」。同时导出 CEILING_CALIBRATION 常量供测试引用。
