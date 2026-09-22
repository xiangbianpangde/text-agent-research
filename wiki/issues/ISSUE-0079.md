---
id: "ISSUE-0079"
title: "v72 attestation freshness test accepts a map with omitted artifact hashes"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "attestation_artifact_omission,attestation_completeness_bypass"
  - "attestation_static_allowlist_omits_new_files"
evidence: "commit 3eb82461f2f9fe0dd4eb68c889fd7f431d5fbace; research-retrieval-benchmark/tests/security/test_worker_isolation.py:4487-4503; /tmp/r57_v72_attestation_omission_probe.out SHA-256 7ab4fbf6157ec5b9a930865d2d2c027f25dcc74233348f210e27c3bb746cf451"
related: []
fix_ref: "fd9c64a"
summary: "v72 attestation freshness test accepts a map with omitted artifact hashes"
updated_at: "2026-09-22"
---

## 现象

The new freshness test iterates only the artifact keys present in the attestation and never compares them with the required ARTIFACTS set. Removing adapters/rag.py from a copied attestation leaves the file present but makes the test predicate pass (predicate_result=PASS, attested_artifact_count=19). A stale/incomplete map can therefore be reported fresh.

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

## 处置记录 2026-09-22T14:39:36+0800

Independent v72 repro: ARTIFACTS in tools/refresh_attestation.py contains 20 static paths while 65 non-trace/non-corpus package files are outside the attested set, including adapters/file_search.py. Appending to that unlisted file then running refresh_attestation.py prints success (20 artifacts, 12 corpus, 0 stale), and test_attestation_hashes_are_current still passes. Evidence: /tmp/r58_refresh_unlisted.out SHA-256 823cb6767f2cf75e322b18dcc4042129631be278f7067f9f7378918d0d3a1e95; /tmp/r58_attestation_unlisted.out SHA-256 b66b027abd486ac379c44c31159132f8495341d3573dbdfa43a6883e8656363d.

## 处置记录 2026-09-22T17:38:36+0800

attestation required set was a static 20-entry allowlist; now derived from the git tree
