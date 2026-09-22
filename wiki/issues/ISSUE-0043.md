---
id: "ISSUE-0043"
title: "v62 invalid snapshot_commit is silently replaced with zero identity"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "commit_identity_coercion,provenance_identity_fail_open"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/worker_supervisor.py:2390-2394; /tmp/r49_v62_commit_identity_probe.out"
related: []
fix_ref: null
summary: "v62 invalid snapshot_commit is silently replaced with zero identity"
updated_at: "2026-09-17"
---

## 现象

WorkerSupervisor(snapshot_commit='ATTACKER-COMMIT') still returns response=true/schema_valid=true; envelope snapshot_commit is all-zero rather than rejecting the invalid provenance input. Zero is a schema-valid placeholder and can hide missing or forged revision identity.

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

## 处置记录 2026-09-17T16:36:41+0800

Round 51/v64 static/source repro remains open: _build_envelope() still coerces an invalid snapshot_commit to 40 zeroes and only records identity_violations, rather than rejecting the attempt before accepted evidence. The direct v64 static probe includes the zero-identity fallback path.
