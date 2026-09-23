---
id: "ISSUE-0156"
title: "catalog 把 INDEX_NOT_BUILT 列为可恢复码，但生产代码从不发出它（触发合同漂移）"
status: "open"
severity: "medium"
area: "researchctl-cli"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "closed_set_code_drift,catalog_claims_unemitted_code,recoverable_codes_mismatch,harness_product_contract_drift,index_not_built_phantom"
evidence: "grep -rn INDEX_NOT_BUILT 全仓仅 catalog/tools.ts:138 与 catalog/test/layer.ts:249 两处，researchctl/ 0 处；无索引树实测 query --entity CURRENT → error_semantic=INDEX_STALE（非 INDEX_NOT_BUILT）；语义码实测 query --semantic --text 无索引 → error_semantic=SEMANTIC_NOT_INDEXED，存在语义索引后注入 drift → SEMANTIC_INDEX_STALE，两者均不在 catalog 闭集；语义 fail-closed envelope 以 exit=0 + stdout 返回，非 stderr"
related: []
fix_ref: null
summary: "catalog 把 INDEX_NOT_BUILT 列为可恢复码，但生产代码从不发出它（触发合同漂移）"
---

## 现象

`INDEX_NOT_BUILT` 出现在 catalog 两处闭集（catalog/tools.ts:138 CLOSED_SET_CODES、catalog/test/layer.ts:249 RECOVERABLE_CODES），但 `researchctl/` 全仓 **0 次**出现。实测：无 `.index/` 时 query 走 `index_required_envelope()`（queries.py:41），返回的 error_semantic 是 `INDEX_STALE` 而非 `INDEX_NOT_BUILT`。后果有二：(1) recovery 指标会把一个永不出现的码当作可达恢复机会，虚增可覆盖的错误类型；(2) 反向漂移同时存在——生产会发出的 `SEMANTIC_INDEX_STALE` 与 `SEMANTIC_NOT_INDEXED` 不在任一闭集内，故语义路径遇到可恢复错误时**不计入** fail-closed 恢复机会（漏计方向相反）。生产 P0 闭集见 researchctl/schema.py::ERROR_SEMANTICS（10 个码）。

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
