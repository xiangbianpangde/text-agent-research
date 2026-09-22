---
id: "ISSUE-0021"
title: "v61 resource envelope attributes unrelated supervisor children to the worker attempt"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "resource_scope_contamination,job_owned_accounting"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/worker_supervisor.py:query/_build_envelope; /tmp/r48_v61_unrelated_rss_probe.out; /tmp/r48_v61_unrelated_cpu_probe.out"
related: []
fix_ref: null
summary: "v61 resource envelope attributes unrelated supervisor children to the worker attempt"
updated_at: "2026-09-18"
---

## 现象

worker idle while unrelated child launched by same supervisor allocates 96 MiB and burns ~180ms CPU during query; envelope reports max_rss_bytes=112082944 (106.891 MiB) and cpu_nanoseconds=191951999. Accounting uses global RUSAGE_CHILDREN rather than a kernel-owned attempt scope.

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

## 处置记录 2026-09-18T08:51:43+0800

Correction: the first v71 CPU probe showed a large child-attributed value, but the follow-up inclusive-counter probe found root_cpu_ns=18,114,041 and child_cpu_ns=382,924,000 while live; the root's reported `ri_child_*` contribution was not observed as inclusive on this host. Do not treat the earlier double-count hypothesis as an independent finding. The existing global-RUSAGE / non-job-owned accounting issue remains open. Follow-up evidence /tmp/r56_v71_cpu_inclusive_values_probe.out SHA-256 7cbc18ff7e0dfb1cedcaff9a1ec0bd4a9bfb32f772b919793b8e700490454dd2.
