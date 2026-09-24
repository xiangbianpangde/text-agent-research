---
id: "ISSUE-0165"
title: "判分汇总与合同 §3.4 相冲突：tool-recoverable 越线即打印 meets ≥95%，而三个成员码各不足 §3.2 的 5 个 state"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "aggregate_overrides_persample_floor,instrument_contradicts_own_contract,flattering_direction_bias"
evidence: "首次实跑后 npm run m3:recovery -- --report 打印『tool-recoverable: 21/22 = 95.5%』『tool-recoverable meets ≥ 95%』，而同一份观察按码统计为 SEMANTIC_INDEX_STALE 4、SEMANTIC_NOT_INDEXED 4、SEMANTIC_INDEX_CORRUPT 3，均低于合同 §3.2『每个成员码至少 5 个互相独立的 fixture/state』；§3.4 明文规定不足样本的子项为 inconclusive 且不得被同层其他码平均掉。reportByStratum 原本只报告 uncovered_codes（『该码一个判分场景都没有』），无法表达『有场景但不足 5 个』。修法：新增 MIN_STATES_PER_CODE=5、states_per_code（逐码 judged/unjudged/meets_minimum）与 under_sampled_codes，驱动在 n<20、under_sampled、rate<threshold 三种不可裁决情形中优先报 under_sampled 并列出各码 x/5。另把『unjudged: N』改为『unjudged (condition never appeared): N』，避免与单独统计的超时/空 turn 数看起来矛盾。新增 3 个测试（含反向验证：把 meets_minimum 恒置 true 后测试失败 2 个）"
related: []
fix_ref: null
summary: "判分汇总与合同 §3.4 相冲突：tool-recoverable 越线即打印 meets ≥95%，而三个成员码各不足 §3.2 的 5 个 state"
---

## 现象

测量工具在自身合同已有逐码样本下限的情况下，只按总体比率宣告达标——错误方向恰好是让结果看起来更好的一侧

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
