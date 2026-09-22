---
id: "ISSUE-0108"
title: "canonical_trace source-binding fix reported 'no repository reachable' as a trace PROBLEM, regressing the shipped P3 audit in a git-less archive"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "trace_source_binding_unverified,trace_unbound_conflated_with_invalid,shipped_audit_archive_regression"
evidence: "commit a7cf04f (fix) -> commit 4d422f0 (repair). Baseline archive at 8296dd5 gave closure 22/2 with failures [p0_root_report_is_explicitly_non_comparative, submitted_pytest_suite_passes]; at a7cf04f the same archive gave 20/4, adding p3_dynamic_queries_are_persisted_as_wire_records (trace_problems: UNBOUND) and p3_lifecycle_events_are_persisted, flipping verdict PASS -> NOT_CLOSED. Outputs /tmp/base_closure.json, /tmp/arc_closure.json, /tmp/c9.json."
related: []
fix_ref: "4d422f0"
summary: "canonical_trace source-binding fix reported 'no repository reachable' as a trace PROBLEM, regressing the shipped P3 aud…"
updated_at: "2026-09-22"
---

## 现象

While fixing ISSUE-0103 I appended the unbound condition to all_problems, so load_canonical_trace returned valid=False whenever git was unavailable, even though internal integrity was intact. Any git-less consumer (an extracted archive) then could not distinguish a good trace from a corrupted one and every P3 trace check failed. The absence of a binding authority is not evidence of a defect; the two axes must be reported separately (valid vs source_bound, with an explicit verdict). Caught only by running the shipped readers INSIDE a git-less archive, not by unit tests.

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

## 处置记录 2026-09-22T19:01:56+0800

Repaired in 4d422f0. Verified by A/B against the baseline archive: failure sets are now IDENTICAL to the v74 baseline (baseline [p0_root_report_is_explicitly_non_comparative, submitted_pytest_suite_passes] vs current same two; 'introduced by me: NONE'), verdict returned to the baseline PASS, and p3_dynamic_queries_are_persisted_as_wire_records passed again. Regression test test_unbound_trace_is_reported_as_unbound_not_as_bound_and_not_as_broken asserts valid=True AND problems==[] for a git-less copy, so the conflation cannot return silently; test_forged_triple_is_still_refused_when_a_repo_is_present guards that separating the axes did not weaken the check into a warning.
