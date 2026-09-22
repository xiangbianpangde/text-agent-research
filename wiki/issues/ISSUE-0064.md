---
id: "ISSUE-0064"
title: "v71 canonical trace loader accepts tampered CAS bytes and chain fields"
status: "verified"
severity: "critical"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "canonical_trace_terminal_record_absent"
  - "v71_canonical_loader_cas_failopen,v71_canonical_loader_chain_failopen"
  - "v71_canonical_loader_invalid_json_failopen"
  - "v71_canonical_loader_malformed_record_crash"
  - "v71_canonical_loader_trace_symlink_follow"
  - "v71_m0_audit_manifest_precedence_failopen"
  - "v73_canonical_role_payload_mismatch_failopen"
  - "v73_canonical_wrapper_payload_identity_mismatch_failopen"
evidence: "v71 commit 1ed201b636302ee095fb6713186f69a56e422ac9; tools/canonical_trace.py:load_canonical_trace; /tmp/r56_v71_canonical_loader_failopen.out SHA-256 30118836d80a5226982a3ad7863e55947afc8af67e4ed964b1ccd638af001118"
related: []
fix_ref: "15dc0b9"
summary: "v71 canonical trace loader accepts tampered CAS bytes and chain fields"
updated_at: "2026-09-22"
---

## 现象

Independent copy-only probe: baseline load_canonical_trace(valid=true); appending one byte to a raw/CAS blob still returns valid=true with no problems; changing record 11 prev_record_sha256 to an all-zero digest and rehashing only manifest.events_sha256 still returns valid=true. The loader checks only the event-file digest/status and ignores CAS, raw-manifest, chain, marker, record bindings, and per-attempt invariants.

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

## 处置记录 2026-09-18T08:37:06+0800

v71 copy-only probe adds a symlinked trace directory results/traces/AAA-EXTERNAL -> external_trace containing an otherwise valid trace. load_canonical_trace() follows the symlink (trace_dir.is_dir()/events.is_file()), returns valid=true, and does not require manifest.trace_id to equal the directory name. Evidence /tmp/r56_v71_trace_symlink_loader_probe.out SHA-256 87caefc44579ec4c39849c8a55b6b20713a2c04bf817c737032976e8b82372e. Loader must reject symlinked trace roots and verify physical regular-file containment.

## 处置记录 2026-09-18T08:37:39+0800

v71 copy-only probe appends a truncated JSON line and updates only events_sha256/events_bytes; load_canonical_trace() returns valid=true with problems=[] while invalid_json_count=1. Evidence /tmp/r56_v71_trace_invalid_tail_loader_probe.out SHA-256 2d5a1e0cd7490a77fe51fdc2ec4642fdb0f7cfc07ddddca8a1c9740a57045726. The loader computes invalid_json diagnostics but does not promote them to validity failure.

## 处置记录 2026-09-18T08:54:41+0800

v71 copy-only loader probe appends scalar `1`, array `[]`, or object `{"unexpected":1}` after recomputing events_sha256. Scalar/array inputs crash load_canonical_trace() with AttributeError instead of returning invalid; the unknown object returns valid=true with problems=[] and a <missing> record type. Evidence /tmp/r56_v71_trace_malformed_record_loader_probe.out SHA-256 04071fbd09a81962d87396934f0acb2795f367c1b08bb6180e1aa1ee7551838c. Canonical loading must fail closed and structurally validate every record.

## 处置记录 2026-09-18T09:12:40+0800

The shipped M0_P1_P3_FINAL_INDEPENDENT_AUDIT.py has an independent fail-open canonical_trace_summary() check: with events bytes unchanged but manifest status changed to BROKEN, record_count=0, and source_commit='not-a-commit', it still returns found=true/manifest_ok=true because `or manifest.events_sha256 == actual_sha` bypasses all other predicates. Evidence /tmp/r56_v71_m0_audit_manifest_precedence_probe.out SHA-256 a38184bcd6248d3490a90c5c25aaf9e197860a69eee0503e62d5a6e63ac04a5a. Thus the M0 reader can overclaim a non-COMPLETE, wrong-source trace even aside from the weaker shared loader.

## 处置记录 2026-09-22T14:39:49+0800

Independent v72 archive repro: tools.canonical_trace.load_canonical_trace(review_v72 package) returns found=True, valid=True, problems=[] for the shipped trace despite no physical COMPLETE/COMPLETE.json, stale source_commit, null session IDs, campaign-only query requests, and no terminal record kind. Evidence: /tmp/r58_v72_canonical_trace_probe.out SHA-256 74c6a7fe5edb0e7e2e11664a3a9c09ae5f0fadcc94388eab13c639e68667c31c.

## 处置记录 2026-09-22T18:00:00+0800

Independent v73 archive repro: replacing the package's `results/traces` directory with a symlink to an external directory leaves the otherwise valid trace unchanged; `load_canonical_trace()` follows the symlink and returns `found=True, valid=True, problems=[]`. Evidence: /tmp/r59_v73_trace_root_symlink_probe.out SHA-256 d0974b33e14d46e9a78ac6c5ca704101c577c265be1edb6d297af5ac765e1a66. The loader's `traces_root.is_dir()/iterdir()` and realpath-based verification do not reject a symlinked canonical root.

## 处置记录 2026-09-22T18:12:00+0800

Independent v73 semantic mutation: swapping only the wrapper roles of the first `query_request` and `participant_response` (payloads, CAS frames, payload hashes, chain, event hash, manifest, and COMPLETE marker all recomputed consistently) leaves `load_canonical_trace()` at `valid=True, problems=[]`. The loader checks that each role is one of request/response/envelope and counts role cardinality, but never enforces role ↔ payload `record_type` correlation. Evidence: /tmp/r59_v73_trace_role_kind_probe.out SHA-256 9ac704dacd1119d0edd0ecea318925d804dd7d4977ad9cbdd59b23c887b1e160.

A second v73 mutation swaps the wrapper `run_uuid`, `session_id`, and `attempt_id` of two complete three-record attempts while leaving payload identities, CAS frames, payload hashes, chain, manifest, and marker consistently bound. The loader still returns `valid=True, problems=[]`; it validates wrapper-group cardinality but never cross-checks wrapper identity against payload identity. Evidence: /tmp/r59_v73_trace_identity_swap_probe.out SHA-256 887594926529168ffa40211a12c997da32adfedf0aedd1389be3735475c2d80d.

## 处置记录 2026-09-22T17:38:36+0800

canonical trace lacked attempt-level query_request/terminal/session bindings

## 处置记录 2026-09-22T18:18:31+0800

Two additional fail-opens reproduced and fixed in commit 15dc0b9, both verified fail-open before the fix: (1) swapping two wrappers' roles and recomputing the hash chain + events digest + COMPLETE marker digest verified valid, because role was never checked against payload.record_type on load; (2) swapping two complete attempts' wrapper run_uuid/session_id/attempt_id with payloads untouched verified valid, so a wrapped record could be attributed to another attempt. Loader now enforces both. Also: a SYMLINKED results/traces root (and a symlinked entry inside it) was followed and verified valid -- now refused. All probes REFUSED; control (unmutated copy) still valid. Tests: tests/security/test_canonical_trace_loader.py (8 pass), each mutation paired with a passing control so no refusal is vacuous. Self-caught regression while fixing: my first role check wrongly rejected the legitimate 'campaign' role; covered by test_campaign_role_is_accepted.

## 处置记录 2026-09-22T19:26:10+0800

v75 target tree 复核旧的 shipped `:sol/5/M0_P1_P3_FINAL_INDEPENDENT_AUDIT.py:95-128`：复制 v75 package，仅将 TRACE_MANIFEST status=BROKEN、record_count=0、source_commit=not-a-commit（events bytes/hash 不变），其 `canonical_trace_summary()` 仍返回 found=True, manifest_ok=True，因 `or manifest.events_sha256 == actual_sha` 绕过全部 predicates。证据 /tmp/r61_v75_m0_manifest_probe.out SHA-256 2e9d0b52cf754fbb1a278d9d77200ee74a3505589965dd69556972448b7a1953。

## 处置记录 2026-09-22T20:25:38+0800

v77 independent recheck: archive 7de9414fa01dfac284c029bc37aad9f004bbc04f8b02578bd8c500294de20e04 trace has 1072 records / 336 attempts with record_counts query_request=368, participant_response=336, evaluator_envelope=336, lifecycle_event=32 and zero terminal record kinds. tools/canonical_trace.py still enforces request/response/envelope attempt groups but has no terminal-record requirement; /tmp/r62_v77_trace_cas_independent_probe.out baseline output records the same loader verdict. Keep the canonical trace integrity fixes verified, but retain terminal-record closure as a separate acceptance gate.
