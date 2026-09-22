---
id: "ISSUE-0053"
title: "v64 DenseRAGAdapter silently abandons indexing because its file path variable is undefined"
status: "verified"
severity: "high"
area: "bench"
discovered_at: "2026-09-17"
discovered_by: "agent"
tags: []
signals:
  - "rag_index_runtime_error"
  - "silent_exception_abstain"
evidence: "commit 5227b03dbf2af80d9abd5d47161483dd2864d519; research-retrieval-benchmark/adapters/rag.py:38-59, /tmp/r51_v64_rag_probe.out SHA-256 80e697236529315da4ba63ecd672374dc533d780c7d6f9b03806b2db57cd6c26"
related: []
fix_ref: "7e9e7fd922b833e7d48f6163f4aea7ccae8abe98"
summary: "DenseRAGAdapter.build_index() references undefined path instead of file_path inside a broad except Exception, so every file is skipped and System B silently abstains."
updated_at: "2026-09-17"
---

## 现象

A direct v64 DenseRAGAdapter probe reports chunks=0, vectors_shape=[0,0], vocab=0, and a schema-shaped NOT_FOUND abstention instead of indexed retrieval.

## 复现

Run PYTHONPATH=<archive>/research-retrieval-benchmark python <probe> against an extracted v64 workspace; inspect adapters/rag.py:44 and /tmp/r51_v64_rag_probe.out.

## 影响

System B's advertised dense retrieval path is unavailable; a false NOT_FOUND response can be mistaken for a valid backend result and any campaign score is non-evidentiary.

## 根因

The repair changed the digest source to file_bytes = path.read_bytes(), but the loop variable is file_path; the broad exception handler converts the NameError into an empty index.

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

Round 51 independent clean-room finding. This is separate from the already-open runtime identity and scoring findings; do not run scored/comparative campaigns until the real pinned backend is repaired and independently verified.

## 处置记录 2026-09-17T18:56:25+0800

Round 52/v65 independent regression verifies the recorded NameError/empty-index symptom fixed: `/tmp/r52_v65_rag_probe.out` SHA-256 2616b72755011c4c4b717b8db9dbd5a19ca0b81de0f4967b2bb3a658ebb22520 reports chunks=1, vectors_shape=[1,4], non-abstaining retrieval, and a cited-file SHA-256. The broader F-06 real-runtime identity gate remains open.
