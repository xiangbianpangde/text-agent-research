---
id: "ISSUE-0031"
title: "v62 event pairs have no shared session or attempt identity beyond query_id/system"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "event_pair_unbound,run_uuid_not_propagated"
  - "v71_canonical_wrapper_payload_identity_mismatch"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/campaign.py:391-431; archive review_v62/results/events.jsonl; /tmp/r49_v62_quickci_probe.out"
related: []
fix_ref: "d514505"
summary: "v62 event pairs have no shared session or attempt identity beyond query_id/system"
updated_at: "2026-09-22"
---

## 现象

participant_response records omit session/message/run UUID while evaluator_envelope generates a separate run_uuid; repeated runs with same query_id/system cannot cryptographically or structurally bind response to its envelope except adjacency/order.

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

## 处置记录 2026-09-18T08:39:40+0800

v71 canonical trace inspection against commit 1ed201b636302ee095fb6713186f69a56e422ac9: all 336 attempt groups are keyed by wrapper-assigned run_uuid/attempt_id, but every wrapper session_id is null; participant_response payloads have no run_uuid/session_id, while evaluator_envelope payload run_uuid differs from the wrapper run_uuid for all 336 pairs. 64 campaign records have null run_uuid/attempt_id. Evidence /tmp/r56_v71_trace_validation.out (SHA-256 4c? see prior file) and the independent trace validation output: wrapper_payload_run_uuid_mismatch=336, wrapper_session_none=672, payload_session_missing=672. The canonical builder's synthetic grouping is not a bound session identity.

## 处置记录 2026-09-18T08:40:00+0800

Correction: the independent canonical-trace validation output cited above is /tmp/r56_v71_trace_validation.out SHA-256 64e30f6ad6d4ff99f762cef3aac1e02b77b0ae83f37c6127ce5d84a67f8d4a32.

## 处置记录 2026-09-22T14:52:00+0800

Independent v72 identity recheck: all 672 attempt wrappers use synthetic non-UUID `RUN-<16hex>` values; all 336 evaluator payload UUIDs differ from their wrapper `run_uuid`; all 336 participant payloads omit `run_uuid`; all 736 wrapper `session_id` values are null; and all 32 campaign records have null wrapper `run_uuid`/`attempt_id`. Every one of the 336 response/envelope groups matches the builder's deterministic `(system, query_id)` hash formula rather than an actual transport identity. Evidence: `/tmp/r58_v72_identity_reprobe.out` SHA-256 `8977837f142076ad31231fc2262f0a1454eb2f3d6ae9048dcf132e17de0dc5c9`; implementation: `tools/build_canonical_trace.py` run-UUID assignment block.

## 处置记录 2026-09-22T17:38:36+0800

trace identity synthesised from hash((system,query_id)); runner now mints real per-attempt identity
