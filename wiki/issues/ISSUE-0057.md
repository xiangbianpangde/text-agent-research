---
id: "ISSUE-0057"
title: "v65 attestation artifact digests still name v64 sources after changed code is archived"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-17"
discovered_by: "agent"
tags: []
signals:
  - "attestation_artifact_hash_drift"
  - "stale_attestation_binding"
evidence: "commit 7e9e7fd922b833e7d48f6163f4aea7ccae8abe98; research-retrieval-benchmark/attestations/M1_worker_protocol_attestation.json; /tmp/r52_v65_attestation_hash_probe.out SHA-256 5562874fd2143dadba872701017ec9232f7d59f85759926997a0aed4615fadaf"
related: []
fix_ref: null
summary: "The v65 archive changes adapters/rag.py, runner/sandbox_launcher.py, runner/worker_supervisor.py, and tests/security/test_worker_isolation.py, but the archived attestation artifact map still contains the v64 digests for all four paths."
---

## 现象

Independent recomputation reports artifact_count=14 and mismatch_count=4: the attested hashes for adapters/rag.py, runner/sandbox_launcher.py, runner/worker_supervisor.py, and tests/security/test_worker_isolation.py differ from the bytes in review_v65.

## 复现

Extract review_v65, load attestations/M1_worker_protocol_attestation.json, SHA-256 each path under research-retrieval-benchmark, and compare with artifacts values; see /tmp/r52_v65_attestation_hash_probe.out.

## 影响

The attestation cannot bind the claimed v65 implementation and must not be used as an integrity receipt; stale claims can make a changed implementation appear to satisfy v64 gates.

## 根因

The attestation JSON was carried forward without regenerating its artifact hash map after the v65 four-file commit.

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

Round 52 independent clean-room finding. The archive/commit byte match remains true, but the attestation artifact map itself is stale; this is an integrity failure separate from the behavioral gate findings.
