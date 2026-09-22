---
id: "ISSUE-0117"
title: "P0/P1 closure 与 M0 审计消费 canonical trace 时只查 found&&valid，不要求 VERIFIED_BOUND"
status: "duplicate"
severity: "critical"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "canonical_trace_unbound_consumer_valid_only,m0_handwritten_summary_failopen"
evidence: ":sol/3/P0P1_CLOSURE_AUDIT.py:301-305 (if trace.get('found') and trace.get('valid'): ev = trace['records']); /tmp/r61_v75_unbound_consumer_probe.out SHA d7b30216a5fa60449fd57be53143d849f861f918f34c75c5d04186dd56a6170f; /tmp/r61_v75_m0_manifest_probe.out SHA 2e9d0b52cf754fbb1a278d9d77200ee74a3505589965dd69556972448b7a1953"
related: []
fix_ref: null
summary: "P0/P1 closure 与 M0 审计消费 canonical trace 时只查 found&&valid，不要求 VERIFIED_BOUND"
updated_at: "2026-09-22"
---

## 现象

loader 在无 git 归档对 forged-but-internally-consistent 三元组返回 valid=True/source_bound=False/verdict=INTERNALLY_VALID_UNBOUND，而 shipped gate 只查 found&&valid，于是 source identity 缺失被当成通过。M0 审计仍是手写 fail-open summary（status=BROKEN/record_count=0/source_commit=not-a-commit 但 events hash 不变时 manifest_ok=True）。这是 gate 消费面缺陷，位于 :sol 独立审计工具而非被审包内。

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

## 处置记录 2026-09-22T19:47:38+0800

Duplicate of ISSUE-0112 (registered by 执行者-2 with the same evidence: /tmp/r61_v75_unbound_consumer_probe.out SHA d7b30216...). Kept for the additional M0 hand-written-summary arm (/tmp/r61_v75_m0_manifest_probe.out SHA 2e9d0b52..., appended to ISSUE-0064 by the reviewer), which ISSUE-0112 does not cover.
