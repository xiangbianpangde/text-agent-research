---
id: "ISSUE-0051"
title: "v63 campaign allows materializer error sentinels and worker path escapes into valid records"
status: "verified"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "materializer_sentinel_fail_open,worker_path_containment_gap"
evidence: "commit 0e9adf49c5c8a89c981432abcf6fea30d6998bfb; /private/tmp/r50_v63_materializer_sentinel_reprobe.out SHA-256 3aec9a8e12ac5d8089057818ae50d91e63a965be57e2ec895d817dcf486fbf2; /private/tmp/r50_v63_worker_path_escape_reprobe.out SHA-256 e655e4634abc58e5896c93714013ebe03856d3b86c7895cc25386de85725ab81; runner/campaign.py:341-346; contracts/worker_protocol.json:372-375"
related: []
fix_ref: "5227b03dbf2af80d9abd5d47161483dd2864d519"
summary: "v63 campaign allows materializer error sentinels and worker path escapes into valid records"
updated_at: "2026-09-17"
---

## 现象

[FILE_NOT_FOUND_IN_COMMIT] and [OUT_OF_RANGE] do not trigger campaign fail-closed check; WorkerSupervisor accepts ../outside.txt with schema_valid=true

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

## 处置记录 2026-09-17T16:33:19+0800

Round 51/v64 independent regression verifies the two recorded symptoms are fixed: /tmp/r51_v64_static_probe_v2.out (SHA-256 d770ada4bd0abbc0f7d545b37f2464fef4ffbd0370ccfe34bd10183a6c307079) reports all four materializer sentinels checked and supervisor path/range containment true; the v64 M0 audit also passed its sentinel/path checks. This does not close the broader F-04 provenance/identity gate (see ISSUE-0047, ISSUE-0022, and the attestation open_items).
