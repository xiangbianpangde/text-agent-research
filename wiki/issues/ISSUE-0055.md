---
id: "ISSUE-0055"
title: "v64 shutdown accepts/coerces invalid timeout inputs and can leave an active worker and locked guard"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-17"
discovered_by: "agent"
tags: []
signals:
  - "shutdown_timeout_validation_bypass"
  - "cleanup_on_timeout_type_error"
  - "default_timeout_coercion"
evidence: "commit 5227b03dbf2af80d9abd5d47161483dd2864d519; research-retrieval-benchmark/runner/worker_supervisor.py:452,1837-1881; /tmp/r51_v64_shutdown_timeout_probe.out SHA-256 f3fc051878b81f4530e7f1a52e52f88f9a36e1e48323228ee4d5fdbb482a4aad; /tmp/r51_v64_default_timeout_probe.out SHA-256 da389e8831c93bea783cce6ad7b98a56de646d67a1e2217faeafed1596333432"
related: []
fix_ref: null
summary: "The new _validated_timeout() is used by handshake/query but not by shutdown(), and constructor default_timeout_seconds is still coerced with float()."
updated_at: "2026-09-17"
---

## 现象

shutdown(timeout_seconds='0') raises a TypeError while leaving state SHUTDOWN_ACTIVE, proc alive, and _stdout_guard locked; shutdown(True) is accepted. The constructor accepts True, '0', NaN, Inf, and -1 as default values and _validated_timeout(None) returns them.

## 复现

Run the shutdown timeout and default-timeout probes against the extracted v64 package. The recorded TypeError and state/guard fields are in /tmp/r51_v64_shutdown_timeout_probe.out; constructor coercion is in /tmp/r51_v64_default_timeout_probe.out.

## 影响

Malformed API input can strand a worker and permanently block later supervisor operations; NaN/Inf/negative defaults bypass the intended deadline contract and can make timeout enforcement undefined.

## 根因

shutdown computes time.monotonic() + timeout_seconds before its try/cleanup path, while __init__ converts the default before strict validation; the shared validator is not the single entry point for every timeout budget.

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

Round 51 independent clean-room finding. Query/handshake strict type probes pass, but F-02/F-04 timeout closure is not established until shutdown and default budgets validate before any state/lock mutation and use one monotonic end-to-end deadline.

## 处置记录 2026-09-17T18:57:59+0800

Round 52/v65 independently verifies the narrow shutdown input fix: `/tmp/r52_v65_shutdown_timeout_probe.out` SHA-256 6377d1b01ca257bd7505b09693d081e893a0e69dbea6aadbee1889565e0d4145 reports ValueError for '0', True, and NaN with state=SHUTDOWN, proc_none=true, guard_locked=false. The issue remains open because constructor/default_timeout_seconds still accepts True, '0', NaN, Inf, and -1 and `_validated_timeout(None)` returns the coerced values (`/tmp/r52_v65_default_timeout_probe.out` SHA-256 da389e8831c93bea783cce6ad7b98a56de646d67a1e2217faeafed1596333432).
