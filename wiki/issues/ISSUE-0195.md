---
id: "ISSUE-0195"
title: "被检查之物与检查相差一次乘法：上限数值溢出为 Infinity，而预检门 2 因 Infinity===Infinity 判绿"
status: "open"
severity: "critical"
area: "pi-extension"
discovered_at: "2026-09-24"
discovered_by: "执行者-1"
tags: []
signals:
  - "numeric_overflow_infinite_request_ceiling"
  - "self_comparing_validation_check"
  - "derived_quantity_unvalidated"
  - "check_and_checked_differ_by_one_operation"
evidence: "命令：npm run m3:recovery -- --preflight --max-turns 1e308 → exit 0，preflight 15/15，输出「ceiling armed at Infinity upstream request(s)」。根因：recovery-run.ts 旧判据 !Number.isFinite(authorizedTurns) || authorizedTurns <= 0 对 1e308 为假（它有限且为正）→ authorizedTurns * 100 溢出为 Infinity → setBudget(Infinity) 原样存入 budgetLimit → trigger.ts 门②判据 typeof budgetLimit === 'number' && budgetLimit > 0 && (expected===undefined || budgetLimit===expected) 被 Infinity === Infinity 满足。修复 commit 4ab5275（四处：解析改 Number.isSafeInteger、推导自验乘积、setBudget 拒绝任何不可用上限、门②先判 finite）。复测：1e308/Infinity/-1/0/1.5/abc 全 exit 2；setBudget(Infinity|NaN|1e308|1.5|0|-5) 全拒、setBudget(500) 仍接受；--max-turns 5 → 门②绿 armed 500。反向验证：变异掉门② finite 判据 → 1 fail；还原 → 242/242。"
related:
  - "ISSUE-0189"
  - "PAT-20260924-003"
fix_ref: null
summary: "被检查之物与检查相差一次乘法：上限数值溢出为 Infinity，而预检门 2 因 Infinity===Infinity 判绿"
---

## 现象

一个上限控制的「数值」从未被验证，只验证了它的存在与正负：输入有限、为正，但经一次乘法后变成不可表示的值（Infinity），执行处原样接收，而门禁通过与自身派生的期望值比较来判定正确性——于是 Infinity === Infinity 成立，整套前置条件 15/15 全绿，同时一个「不设限」的上限已被 arm。表现为：预算/安全类门禁在「值不可表示」的输入下 fail-open，且所有自比较式检查同时失效。

## 复现

npm run m3:recovery -- --preflight --max-turns 1e308  # 修前 exit 0 且 armed Infinity；修后 exit 2 并说明原因

## 影响

影响所有以「派生值 == 期望派生值」形式实现的门禁：只要输入能让派生溢出/饱和/截断，门禁即恒真。本例的影响是在一个用于「限制被测方消耗」的预算控制上 fail-open。同类风险点：任何 safe-margin 计算、超时换算（如 --timeout 秒×1000）、指数退避重试次数上限。

## 根因

三件事叠加，任缺其一都不成立：① 输入校验与使用之间隔着一次算术（有限 × 100 → Infinity），校验的是输入而非被使用的派生量；② 执行处 setBudget 无独立性校验，信任调用方；③ 门禁判据的形式是「实际值 == 我算出的期望值」，当两侧由同一表达式溢出而来时，该等式退化为自比较（x == x），恒真。深层系统性原因：期望值与实际值同源。门禁无法发现「两者一起错」，因为它没有第三方参考（如一个由独立推导得到的上界）。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
