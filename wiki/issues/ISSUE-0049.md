---
id: "ISSUE-0049"
title: "v63 query deadline excludes envelope and CAS construction work"
status: "fixed"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "deadline_postbuild_exclusion,end_to_end_deadline_bypass"
  - "v69_envelope_cas_deadline_bypass"
evidence: "commit 0e9adf49c5c8a89c981432abcf6fea30d6998bfb; /private/tmp/r50_v63_envelope_deadline_reprobe.out SHA-256 0a2d6c8e856875ec3a8e06b7c1f83acc5972ac29c3a2e8c2e3211db8b64d9f24; runner/worker_supervisor.py:1776-1796,2344-2486"
related: []
fix_ref: "df3ce4a"
summary: "v63 query deadline excludes envelope and CAS construction work"
updated_at: "2026-09-22"
---

## 现象

A 50ms query with a 200ms first envelope CAS delay returns schema_valid=true after 259.268ms while envelope timing reports 54.476ms

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

## 处置记录 2026-09-17T16:30:50+0800

Round 51/v64 end-to-end deadline repro: /tmp/r51_v64_deadline_probe.out (SHA-256 cebd99e287ee28e064e0ea92c6279b1ee988789daa7543d3b6db24de18594cb4) delayed cas_put_best_effort and obtained response=true/schema_valid=true after 545.79ms for a 500ms budget while timing_total_ms was 137.158709, and a 10ms budget took 263.32ms in the same probe family. CAS, envelope construction, teardown, and persistence remain outside the monotonic query budget.

## 处置记录 2026-09-17T19:56:39+0800

v66 clean-room recheck /tmp/r53_v66_deadline.out: injecting 200ms CAS delay during envelope construction returns response=True/schema_valid=True with supervisor elapsed 536.02ms for timeout=500ms, while envelope timing_total_ms=130.28 and exit_code=0. worker_supervisor.py still computes wall_ms before _build_envelope and does not recheck end-to-end deadline after CAS/envelope construction. The typed CAS change did not close deadline coverage.

## 处置记录 2026-09-17T21:07:04+0800

v67 clean-room rerun /tmp/r54_v67_deadline.out: 200ms CAS delay during _build_envelope still yields supervisor elapsed=542.31ms for timeout=500ms but response=True/schema_valid=True and envelope timing_total=131.04ms. End-to-end deadline remains bypassable.

## 处置记录 2026-09-18T00:09:01+0800

v69 clean-room fresh repro unchanged: injecting 200ms delay into cas_put_best_effort for envelope calls yields response=true/schema_valid=true after elapsed_ms=550.03 for timeout=500ms, while envelope timing_total_ms=134.305 and exit_code=0. Evidence /tmp/r55_v69_deadline_probe.out SHA-256 13714acabd1aeb44829c862908a149c4de95743c519e7b2323003cf25bbbeacf.

## 处置记录 2026-09-22T17:38:36+0800

envelope/CAS deadline bypass: budget checked before envelope construction whose CAS writes can block
