---
id: "ISSUE-0027"
title: "v61 CAS write failure still yields schema-valid attempt with zero digests"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "cas_write_loss,raw_bytes_unrecoverable"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/worker_supervisor.py:cas_put_best_effort,_build_envelope; /tmp/r48_v61_cas_write_failure.out"
related: []
fix_ref: null
summary: "v61 CAS write failure still yields schema-valid attempt with zero digests"
updated_at: "2026-09-17"
---

## 现象

after deleting the supervisor CAS directory, a real echo worker query is accepted schema_valid=true and shutdown_ack succeeds, while envelope stdout_sha256 and stderr_sha256 are all-zero sentinels; no CAS bytes are recoverable and the attempt was not invalidated.

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

## 处置记录 2026-09-17T16:34:41+0800

Round 51/v64 direct probes do not close the issue. Permanent CAS failure now yields schema_valid=false plus identity_violations, but /tmp/r51_v64_cas_transient_probe.out (SHA-256 65d6a52f6503936951896fc20b9b93f4b8e8e6babb093529fc40f0bb22b451b1) still reports response=true/schema_valid=true with a failed digest not retrievable. The remaining zero-digest/fail-open behavior is tracked separately as ISSUE-0056.
