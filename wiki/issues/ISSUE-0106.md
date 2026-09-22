---
id: "ISSUE-0106"
title: "v74 canonical trace loader accepts malformed unreferenced CAS manifest entries"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "canonical_trace_unreferenced_cas_manifest_integrity"
evidence: "commit 8296dd5530600fd0554f6b4d68c5707b87851932; /tmp/r60_v74_trace_cas_probe.out SHA-256 d2b78b72d58296abefd607b9d497cb1f078d38dbfe699a419b487a98dc05534e; tools/canonical_trace.py:422-469"
related: []
fix_ref: "120ac20"
summary: "v74 canonical trace loader accepts malformed unreferenced CAS manifest entries"
updated_at: "2026-09-22"
---

## 现象

在 raw/ 新增未被任何 record 引用的 frame，并在 raw_manifest.entries 添加 `sha256=not-a-digest,size=not-an-int`，同步 raw_manifest_sha256/raw_bytes 后 `load_canonical_trace()` 仍返回 valid=True/problems=[]；loader 仅校验被 records 引用的 frame，未校验每个 declared CAS entry 的名称、摘要、size 与字节。

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

## 处置记录 2026-09-22T18:39:24+0800

追加：被 record 引用的 raw_manifest entry 的 `size` 改为实际值+12345，并同步 raw_manifest_sha256 后 loader 仍 valid=True；/tmp/r60_v74_trace_cas_size_probe.out SHA-256 2c926057095e8201cc225d6673816d003f442658c81e63bd5ef6027ceaf58adc。_verify_cas 比对 digest 但不比对 manifest size。

## 处置记录 2026-09-22T19:14:13+0800

v75 复核同样未闭合：/tmp/r61_v75_trace_cas_probe.out SHA-256 d2b78b72d58296abefd607b9d497cb1f078d38dbfe699a419b487a98dc05534e；未引用 malformed raw_manifest entry 仍 valid=True；/tmp/r61_v75_trace_cas_size_probe.out SHA-256 2c926057095e8201cc225d6673816d003f442658c81e63bd5ef6027ceaf58adc；被引用 entry 的 size 错写仍 valid=True。

## 处置记录 2026-09-22T19:30:35+0800

追加 v75：未引用 raw frame 置为指向包外的 symlink，raw_manifest 记录同样 malformed，loader 仍 valid=True/problems=[]；/tmp/r61_v75_trace_cas_unreferenced_symlink_probe.out SHA-256 2c926057095e8201cc225d6673816d003f442658c81e63bd5ef6027ceaf58adc。_verify_cas 只对 records 引用项调用 _read_nofollow，未引用项可逃过 no-follow。

## 处置记录 2026-09-22T19:47:29+0800

Every DECLARED raw_manifest entry is now validated (name containment/bareness, digest shape, non-negative int size, exact key set) and bound to the bytes on disk by digest AND size -- not only the entries a record happens to reference. Unreferenced malformed/traversal/false-digest/false-size entries are all refused; 4 parametrized regression cases, mutation kills 3 when reverted.
