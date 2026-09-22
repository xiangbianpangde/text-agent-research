---
id: "ISSUE-0022"
title: "v61 malformed worker frames emit fabricated placeholder identity"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "transport_identity_placeholder,provenance_fail_closed"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/worker_cli.py:46-57,72-78; /tmp/r48_v61_parse_probe.out"
related: []
fix_ref: null
summary: "v61 malformed worker frames emit fabricated placeholder identity"
updated_at: "2026-09-17"
---

## 现象

array root, invalid UTF-8, and zero-length frames all produce worker_error with session_id=UNKNOWN, message_id=MSG-ERR-0, sequence_number=0, in_reply_to=MSG-UNKNOWN, and an all-zero request digest; this is not runner-transport-owned identity and cannot bind the error to the actual malformed bytes.

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

## 处置记录 2026-09-17T16:35:48+0800

Round 51/v64 identity probe remains open: /tmp/r51_v64_identity_probe.out reports malformed worker payloads produce worker_error frames with session_id=UNKNOWN, message_id=MSG-ERR-0, sequence_number=0, in_reply_to=MSG-UNKNOWN, and an all-zero request_canonical_sha256. These fabricated placeholders are not verified transport identity; identity_violations on a later envelope do not make the worker_error fields truthful.
