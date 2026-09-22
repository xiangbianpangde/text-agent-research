---
id: "ISSUE-0061"
title: "v69 attestation marks contradicted containment and CAS gates as satisfied"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "attestation_gate_overclaim,v69_attestation_drift"
  - "v71_attestation_gate_overclaim,v71_trace_gate_false_positive"
evidence: "commit cc33db81cc180f8714d2035a12d8badfc09a9591; attestations/M1_worker_protocol_attestation.json:gates_satisfied.escape_sweep_runs_async,lsof_candidates_require_worker_lineage,unrelated_system_processes_never_killed,cas_loss_covers_all_write_sites,cas_symlink_rejected; /tmp/r55_v69_unrelated_cwd_kill.out SHA-256 7437aff8b3730df3d9a6a417b497faa204f21b56f86f5259e3c02ca122945d52; /tmp/r55_v69_campaign_direct_cas_bypass.out SHA-256 0a6a9e90e98b07a45939c97b50bfbb7130d92af3f0ab958b5ea89ef1b8a20432"
related: []
fix_ref: null
summary: "v69 attestation marks contradicted containment and CAS gates as satisfied"
updated_at: "2026-09-18"
---

## 现象

The v69 attestation sets multiple gates_satisfied booleans true although source and independent probes contradict them: sweep is synchronous rather than async; lsof candidates are accepted by cwd without lineage; an unrelated cwd process was killed; the campaign has a direct unrecorded cas_put; CAS symlinks are followed.

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

## 处置记录 2026-09-18T08:27:54+0800

v71 attestation in commit 1ed201b636302ee095fb6713186f69a56e422ac9 still sets contradicted gates true or claims F-04 resolved: clean_shutdown_sweeps_detached_descendants=true, descendant sweep/unclaimed cleanup=true, synchronous_residue_confirmation=true, cas_symlink_nofollow/cas_symlink_rejected=true, cas_loss_covers_all_write_sites=true, canonical_trace_manifest_bound=true, audits_read_canonical_trace_only=true, and F-04 PARTIAL 'RESOLVED' in open_items. Independent v71 evidence: /tmp/r56_v71_no_identity_cwd_escape.out SHA-256 b91b93cbb50f613bb05ddae2718ca1d9ea94d13eb6beb4c56e5f8996eb169c0e (shutdown_ack + live child); /tmp/r56_v71_cas_symlink_probe.out SHA-256 c1e87b9cd524d3e76d04684c137ec540e81253228b4693da8a863cf5ac93cf96 (CAS directory symlink writes outside); /tmp/r56_v71_canonical_loader_failopen.out SHA-256 30118836d80a5226982a3ad7863e55947afc8af67e4ed964b1ccd638af001118 (marker absent, wrong source, tamper accepted). Attestation remains non-authoritative and HOLD.
