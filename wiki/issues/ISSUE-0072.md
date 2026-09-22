---
id: "ISSUE-0072"
title: "v71 AuditChainEvaluator rejects valid exact byte ranges for files without a trailing newline"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "audit_no_trailing_newline_phantom_byte"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/metrics/audit.py:319-327; /tmp/r56_v71_auditchain_no_newline_probe.out SHA-256 7d96a4ace8e555894be40702d03b2c2933e8726ee78b972526f8349cebd44b07"
related: []
fix_ref: null
summary: "v71 AuditChainEvaluator rejects valid exact byte ranges for files without a trailing newline"
---

## 现象

A valid one-line file with no trailing newline and exact Gold byte_end is marked c6_raw_evidence_verified=false while all other AuditChain checks pass; the verifier adds one phantom newline byte per split line when reconstructing offsets.

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
