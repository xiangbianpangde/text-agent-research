---
id: "ISSUE-0023"
title: "v61 worker protocol accepts retrieval atoms without content or run provenance"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "atom_provenance_optional,worker_provenance_forgery"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; contracts/worker_protocol.json:participant_response.retrieval; runner/campaign.py:265-277; /tmp/r48_v61_f04_incomplete_probe.out; archive results/events.jsonl"
related: []
fix_ref: null
summary: "v61 worker protocol accepts retrieval atoms without content or run provenance"
updated_at: "2026-09-16"
---

## 现象

a schema-valid participant_response with only evidence_id, canonical_path, line_start, line_end is accepted; campaign copies worker run_ids/claim_id without independent binding, hardcodes raw_source_ids=[], and 2249 shipped atoms have empty run_ids/null claim_id.

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

## 处置记录 2026-09-16T15:52:03+0800

v62 source inspection confirms root cause: retrieval_worker.py:291-304 intentionally reconstructs each adapter hit with only evidence_id/canonical_path/line_start/line_end, dropping entity_id/version/commit/sha256/run_ids/raw_source_ids/claim_id/claim_value/status and adapter failure/freshness/provenance metadata before campaign sees it. Campaign then hardcodes raw_source_ids=[] and only copies absent worker run/claim fields. Archive result: 2249 atoms empty run_ids/claim_id.

## 处置记录 2026-09-16T15:56:11+0800

v62 EvidenceAtom contract probe: canonical_path='../../gold/answer.json' is silently rewritten to 'gold/answer.json' rather than rejected, and ConfigDict(extra='allow') retains arbitrary top-level 'unexpected' field (/tmp/r49_v62_evidence_atom_probe.out). Internal atom model is not a closed provenance schema.
