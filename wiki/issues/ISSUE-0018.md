---
id: "ISSUE-0018"
title: "v61 fresh CampaignRunner run emits no query_request or lifecycle event records despite shipped 736-record trace"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "campaign_trace_incompleteness,stale_artifact"
  - "root_stale_alias_still_readable,legacy_source_identity_misattributed"
  - "v71_fresh_campaign_trace_still_attempt_incomplete"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/campaign.py:397-398; /tmp/r48_v61_quickci.out; /tmp/r48_v61_quickci_root; archive results/events.jsonl"
related: []
fix_ref: null
summary: "v61 fresh CampaignRunner run emits no query_request or lifecycle event records despite shipped 736-record trace"
updated_at: "2026-09-18"
---

## 现象

独立 fresh output 的 one-query events.jsonl 只有 3 participant_response + 3 evaluator_envelope，无 query_request/lifecycle_event；archive 中 736 条 shipped trace 来自旧产物，P0/P3 只检查其存在，未验证当前 CampaignRunner 生成链路

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

## 处置记录 2026-09-17T16:35:40+0800

Round 51/v64 direct validation of the immutable shipped artifact: results/events.jsonl SHA-256 636e58d82dba26740de40753d0586a64b1d1a53b67e04947e7dddb12a8e839c5 has 336 participant_response, 336 evaluator_envelope, 32 lifecycle_event, and 32 query_request records, but all 336 envelopes fail the v64 wire validator because required diagnostic fields are absent; all 2,249 cited retrieval files are absent from the archived workspace and 336 participant responses lack run_uuid (/tmp/r51_v64_shipped_event_validation.out SHA-256 7bd3ede8957a52e0457c6c186d0ed4327f41a7ced60b780826137b3e34b5d791; /tmp/r51_v64_shipped_provenance_audit.out SHA-256 ae1f10ca67519291fd7105db2d12ba19ea7a6330d7efe4f0e48fe9d7ec425a49). Fresh M0/P0 reruns prove plumbing can emit dynamic records, but they do not repair the stale non-replayable shipped artifact.

## 处置记录 2026-09-17T18:58:19+0800

Round 52/v65 archive still carries the exact same shipped `results/events.jsonl` bytes as v64 (SHA-256 636e58d82dba26740de40753d0586a64b1d1a53b67e04947e7dddb12a8e839c5): 736 records including 32 query_request and 32 lifecycle_event, but 336/336 envelopes fail current wire validation, 2,249/2,249 cited files are absent from the archive workspace, and 336/336 participant responses lack run_uuid. This was intentionally retained rather than repaired by deleting required dynamic records; the stale/non-replayable artifact remains open and is tracked with ISSUE-0057's attestation drift finding.

## 处置记录 2026-09-17T21:07:56+0800

v67 adds a correctly hashed legacy copy under results/legacy, but the same 862,397-byte stale events.jsonl remains at the default results/events.jsonl path and is tracked in the commit. That root path is not marked STALE or blocked by any manifest, so a consumer following the conventional path can still mistake it for the current canonical trace. Both hashes are identical; freeze metadata must cover/deny the root alias or the active path must be explicitly versioned.

## 处置记录 2026-09-17T21:12:35+0800

The v67 LEGACY_MANIFEST binds only the legacy file's own byte hash/count; it does not record the source v64 commit/tree/archive hash or a prior-run/run UUID. For an immutable superseded trace, add source identity and a canonical provenance pointer, otherwise the freeze is self-describing but not source-bound.

## 处置记录 2026-09-17T23:58:43+0800

v69 adds results/events.jsonl.STALE and source_commit/source_tree fields, but root results/events.jsonl remains the exact stale bytes and M0_P1_P3_FINAL_INDEPENDENT_AUDIT.py still reads it directly. No read-blocking or canonical trace exists in the v69 archive. LEGACY_MANIFEST source_commit=83f306780e868d64f18020f03f83fbaf646c9afa/source_tree=69c541f3567b0588ee293ef2f599d67dbf0c2b0b identify the v67 copy commit, not the original producer of the bytes (the same hash already existed at v64 commit 5227b03dbf2af80d9abd5d47161483dd2864d519; archive sha256 702e94aa338ef6e10ac4262859f2c741a728c6a6dfb76e8eafd664a5cb6e2b78). This is not sufficient source provenance.

## 处置记录 2026-09-18T00:12:41+0800

Fresh v69 archive path probe: canonical_trace_paths=[]; root_alias_exists=true with SHA-256 636e58d82dba26740de40753d0586a64b1d1a53b67e04947e7dddb12a8e839c5; legacy exists with identical bytes; sidecar exists but does not block ordinary reads. Evidence /tmp/r55_v69_trace_path_probe.out SHA-256 b37bc7826b99973420b342f2d4fdb5e9be331eaa44d230b4877de0ba65f0222b.

## 处置记录 2026-09-18T09:14:04+0800

v71 fresh clean-room CampaignRunner.run_quick_ci(num_queries=1) against commit 1ed201b636302ee095fb6713186f69a56e422ac9 returns ok and writes only 3 participant_response + 3 evaluator_envelope records (8,717 bytes); no query_request or lifecycle_event is emitted. It also writes summary.md/raw_manifest.json, but no end-to-end attempt request/terminal trace. Evidence /tmp/r56_v71_fresh_campaign_trace_probe.out SHA-256 0032f6a8c646782e7ad016d235510823700cbaa102ae7e13be698457e00b2f2d. The shipped canonical trace cannot be attributed to this current campaign path.
