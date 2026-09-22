---
id: "ISSUE-0062"
title: "v71 attestation hash map is stale for the committed isolation test"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "v71_attestation_hash_mismatch,archive_attestation_stale"
evidence: "archive /Users/xbpd/Projects/benchmark/.pi/sol-staging/review_v71.zip SHA-256 6e0b53fb27aed2973eb7113d02db3992601000c60cd3533baa157c407b536bf1; commit 1ed201b636302ee095fb6713186f69a56e422ac9; attestations/M1_worker_protocol_attestation.json; /tmp/r56_v71_integrity_probe.out SHA-256 faa5c02e814c74981d465691f9b8b42a8d4528eb86c070683f342c564b9fe439"
related: []
fix_ref: null
summary: "v71 attestation hash map is stale for the committed isolation test"
updated_at: "2026-09-18"
---

## 现象

Independent recomputation finds 1/20 attestation artifact hash mismatch: tests/security/test_worker_isolation.py expected sha256:6a1032f921e8c021dbddcd2db19f8bbafbe85ac4183f035878761bef49d0a750 but archived bytes hash sha256:bc8ca779cca9ffcafc12f2fa7baf4610cda3dbae227facd162793e3cbae142d5. The v71 claim of 20/20 matches is false.

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

## 处置记录 2026-09-18T09:06:00+0800

Independent v71 artifact recomputation output /tmp/r56_v71_attestation_recompute.out SHA-256 816623d5b0a53b0d912508e174bcec5c8f0588eab89fda8a4ac46619d22ca3c7 confirms exactly 1 mismatch (tests/security/test_worker_isolation.py actual sha256:bc8ca779cca9ffcafc12f2fa7baf4610cda3dbae227facd162793e3cbae142d5 versus expected sha256:6a1032f921e8c021dbddcd2db19f8bbafbe85ac4183f035878761bef49d0a750).
