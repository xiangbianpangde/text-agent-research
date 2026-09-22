---
id: "ISSUE-0091"
title: "schema.ERROR_SEMANTICS 是死代码且与运行时 error_semantic vocabulary 漂移"
status: "open"
severity: "medium"
area: "researchctl"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "error_semantics_dead_enum,error_vocabulary_drift,no_error_code_validation"
evidence: "researchctl/schema.py: ERROR_SEMANTICS 定义 10 个码 (NOT_FOUND,AMBIGUOUS_VERSION,SOURCE_MISSING,HASH_MISMATCH,DRIFT_DETECTED,CURRENT_CONFLICT,SOURCE_UNAVAILABLE,INDEX_STALE,PROVENANCE_BROKEN,SOURCE_CHANGED_SINCE_PIN); 全仓仅 researchctl/queries.py:18 import, grep 无任何其他引用/校验点 => 死代码; 运行时实际发出的值含 DEF_CHANGE_TYPE_INVALID,DEF_VERSION_MISSING,IMPACT_INVALID (query 层校验) 与 TX_LOCKED,BASELINE_UNSUPPORTED (bench), 均不在枚举内; 另 PROVENANCE_BROKEN 已被 P0/P1-A/P1-B 合同 + bench 方案 errors=[PROVENANCE_BROKEN,NOT_FOUND] 逐字断言 + reconciler.py:172/207/208 + tx/definition.py + tx/recover.py + queries.py:114 依赖, 故不可扩写顶层枚举 (M1 Rev3 §4.4.3 据此裁决)"
related: []
fix_ref: null
summary: "schema.ERROR_SEMANTICS 是死代码且与运行时 error_semantic vocabulary 漂移"
---

## 现象

错误码枚举既未被任何代码校验（无强制力），又与运行时实际 vocabulary 不一致；新增产品错误码时若不先收全并启用校验，会出现『枚举说有、运行时不发』与『运行时发、枚举没有』两个方向的分歧，且无法在 P0 冻结合同上安全扩写顶层枚举

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
