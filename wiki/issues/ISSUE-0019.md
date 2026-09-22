---
id: "ISSUE-0019"
title: "v61 CHILD_PID parser drops claims split across stderr chunks"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "stderr_claim_fragmentation,claim_admission_loss"
  - "v71_child_pid_fragmentation_still_open"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/worker_supervisor.py:_append_stderr lines 1032-1067; /tmp/r48_v61_claim_split.out"
related: []
fix_ref: null
summary: "v61 CHILD_PID parser drops claims split across stderr chunks"
updated_at: "2026-09-18"
---

## 现象

_append_stderr(b'CHILD_PID:') followed by _append_stderr(b'12345\\n') records claims=0 although stderr preserves the full line; split at marker/digits loses the PID and can miss short-lived legitimate descendants

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

## 处置记录 2026-09-16T15:49:49+0800

v62 current probe split CHILD_PID: marker and digits across stderr chunks; both query responses succeed but claims remains 0/dropped 0 (/tmp/r49_v62_claim_split_probe.out). Parser is chunk-local, not line-buffered.

## 处置记录 2026-09-17T16:26:58+0800

Round 51/v64 independent clean-room repro: /tmp/r51_v64_claim_split_probe.out (SHA-256 3d83d57ca280a3b4987ceaf4a1aca14b9f2060792d29fcbef12bd47595706f89) split CHILD_PID: and the digits across stderr chunks; response/schema_valid remained true but attempt_claims=0 and session_claims=0 while tracked contained the child PID. The parser remains chunk-local, so legitimate descendant admission is still lossy.

## 处置记录 2026-09-18T08:58:41+0800

v71 clean-room parser probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9 feeds _append_stderr(b'CHILD_PID:') then _append_stderr(b'12345\\n'); captured stderr contains the complete claim but _child_pid_claims and _attempt_child_pid_claims remain zero. Evidence /tmp/r56_v71_child_pid_fragment_probe.out SHA-256 bcc6d8558998e7e025fec22061248dc592c2b982e0b4cec023b584469d5b43b6. Claims must be line-buffered across stderr chunks or independently discovered by kernel scope.
