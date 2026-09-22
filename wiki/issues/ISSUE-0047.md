---
id: "ISSUE-0047"
title: "v63 campaign persists adapter chunk digests as file provenance and drops missing-field diagnostics"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "campaign_digest_unbound,missing_provenance_not_persisted"
  - "v71_pilot_workspace_digest_is_commit_string_hash"
evidence: "commit 0e9adf49c5c8a89c981432abcf6fea30d6998bfb; /private/tmp/r50_v63_campaign_provenance_check.out SHA-256 16ce6837dafc7a24d2e5bbb954e987c37d3d8df9b1063696cab68ba21548addd; runner/campaign.py:314-315,458-460"
related: []
fix_ref: null
summary: "v63 campaign persists adapter chunk digests as file provenance and drops missing-field diagnostics"
updated_at: "2026-09-18"
---

## 现象

B 8/8 persisted citation sha256 values differ from cited workspace file hashes; computed missing_provenance_fields is assigned only after events.jsonl writes and is absent from all stored envelopes

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

## 处置记录 2026-09-17T16:28:51+0800

Round 51/v64 persistence/provenance audit: /tmp/r51_v64_shipped_provenance_audit.out (SHA-256 ae1f10ca67519291fd7105db2d12ba19ea7a6330d7efe4f0e48fe9d7ec425a49) found 336 participant responses, 2,249 retrieval items, 2,249/2,249 cited files absent from the immutable package workspace, 336/336 participant responses without run_uuid, and 336/336 envelopes missing the required identity/provenance diagnostic fields. The fresh code assigns missing_provenance_fields after transformation, but the shipped events artifact is not a replayable byte-bound record. F-03/F-04 remains open.

## 处置记录 2026-09-18T09:23:18+0800

v71 clean-room Pilot probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: _evaluate_track() records workspace_tree_digest as sha256(commit_sha.encode()), not a digest of the materialized workspace. For a controlled empty workspace, reported sha256:e33cdf... equals the hash of the 40-character commit string, while compute_workspace_tree_digest() is sha256:4ea7af...; reported_matches_tree=false. Evidence /tmp/r56_v71_pilot_workspace_digest_probe.out SHA-256 d2f924cb0ac3a49ee3ba34bad080ca7ebeaeec034733996a9c0bebaf624cc69a. This envelope field cannot prove snapshot identity.
