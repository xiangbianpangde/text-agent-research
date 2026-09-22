---
id: "ISSUE-0073"
title: "v71 AuditChainEvaluator reads gold_commit bytes instead of each historical atom target_commit"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "audit_historical_commit_mismatch,c6_gold_atom_commit_ignored"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/metrics/audit.py:287-301; oracle/compile_gold.py:640-646; /tmp/r56_v71_auditchain_historical_commit_probe.out SHA-256 2df669a4abd234aafc3032ca0d076bfb53a7dbdf01472cc84eab01e8dbe2563b"
related: []
fix_ref: null
summary: "v71 AuditChainEvaluator reads gold_commit bytes instead of each historical atom target_commit"
---

## 现象

For a T05 historical report atom bound to C0 with exact hash/range and matching participant commit, c5 and all other checks pass but c6 fails because the evaluator loads reports/REPORT-001.md from gold_commit C1, not the atom's target_commit C0; valid historical evidence is rejected.

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
