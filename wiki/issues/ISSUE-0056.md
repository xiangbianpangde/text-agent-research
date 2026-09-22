---
id: "ISSUE-0056"
title: "v64 CAS degradation can return an accepted response or a zero-digest envelope instead of a typed failed attempt"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-17"
discovered_by: "agent"
tags: []
signals:
  - "cas_direct_call_bypass,campaign_cas_untracked"
  - "cas_durability_loss"
  - "cas_transient_fail_open"
  - "cas_zero_digest_sentinel"
evidence: "commit 5227b03dbf2af80d9abd5d47161483dd2864d519; research-retrieval-benchmark/runner/worker_supervisor.py:623-710,2468-2476; /tmp/r51_v64_cas_transient_probe.out SHA-256 65d6a52f6503936951896fc20b9b93f4b8e8e6babb093529fc40f0bb22b451b1; /tmp/r51_v64_static_probe_v2.out SHA-256 d770ada4bd0abbc0f7d545b37f2464fef4ffbd0370ccfe34bd10183a6c307079"
related: []
fix_ref: null
summary: "The envelope path treats CAS as best-effort and substitutes sha256 followed by 64 zeroes when durable storage fails; a transient CAS failure can leave response=true and schema_valid=true even when the failed digest cannot be retrieved."
updated_at: "2026-09-18"
---

## 现象

The transient probe reports response=true, schema_valid=true, failed_digest_retrievable=false, and no identity violation. The direct failure path emits a zero stdout digest plus an identity_violations marker; the marker does not make the content address recoverable.

## 复现

Run the transient CAS probe and the static CAS probe against the extracted v64 package. Also inspect _build_envelope() fallback at worker_supervisor.py:2468-2476.

## 影响

Accepted records can reference bytes that are not durable or retrievable, and a zero digest is a fabricated identity that can collide semantically with a real content-addressed reference; downstream scoring/provenance cannot recover the raw frame.

## 根因

cas_put_best_effort() swallows storage errors; _build_envelope() converts None to a zero digest, while some response paths do not propagate the failed CAS operation into schema_valid=false or a persisted failed-attempt envelope.

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

Round 51 independent clean-room finding. CAS failure must produce a typed invalid/failed attempt and block accepted envelopes, or use an explicit nullable/failed-reference field; never use UNKNOWN, zero digests, or an identity_violations side marker as successful evidence.

## 处置记录 2026-09-17T18:58:08+0800

Round 52/v65 independently reruns the transient CAS probe: `/tmp/r52_v65_cas_transient_probe.out` SHA-256 3ca3990d3d1ee65a4e73128c170589e57e2a5a342babaed041e96e13959cf8ba reports response=true, schema_valid=true, failed_digest_retrievable=false, and identity_violations=[]; the zero-digest fallback and CAS/retention symlink behavior remain in source.

## 处置记录 2026-09-17T19:51:28+0800

v66 typed CAS fix only covers CAS failures during _build_envelope. Clean-room call matrix /tmp/r53_v66_cas_call_matrix.out against c87d1a1: failing cas_put call 1 (query request) or call 2 (raw response) still returns response=True, schema_valid=True, cas_status=ok while failed digest is unretrievable; only calls 3/4 are detected as CAS_UNAVAILABLE. Thus any raw-frame durability failure before envelope construction remains fail-open.

## 处置记录 2026-09-17T19:56:13+0800

Additional v66 probe /tmp/r53_v66_cas_state_probe.out: when CAS directory is removed, query returns resp=None/schema_valid=false/CAS_UNAVAILABLE but supervisor remains state=IDLE with live worker (proc.poll=None), releases guard, and deletes auto-created cwd; a second query is still dispatched to that live worker. Invalid durability state is not terminalized and cleanup races a live participant.

## 处置记录 2026-09-17T20:03:20+0800

v66 source is unchanged for CAS no-follow: /tmp/r53_v66_cas_dir_symlink.out shows cas_dir set to a symlink and cas_put writes the blob into the outside target while returning a digest. CAS directory symlink traversal remains.

## 处置记录 2026-09-17T20:09:28+0800

v66 also ignores CAS loss during handshake: /tmp/r53_v66_handshake_cas_probe.out fails the first hello-frame cas_put, then restores CAS; later query returns response=True/schema_valid=True/cas_status=ok while failed_digest is unretrievable. Handshake raw-frame durability is not carried into the attempt CAS status.

## 处置记录 2026-09-17T20:10:55+0800

v66 also follows a symlinked CAS blob: /tmp/r53_v66_cas_blob_symlink.out preplaces cas_dir/sha256_<digest> as a symlink to outside.bin with matching bytes; cas_put returns the digest and cas_get reads outside.bin. Blob-level no-follow/regular-file ownership is not enforced, in addition to CAS-directory symlink traversal.

## 处置记录 2026-09-17T21:00:16+0800

v67 still fails open on successful shutdown CAS loss: /tmp/r54_v67_shutdown_cas_probe.out fails cas_put at shutdown request (call 5) or shutdown_ack (call 6); both return shutdown_ack with no envelope, state=SHUTDOWN, proc_none=True, while failed digest is unretrievable. _cas_lost is only consulted by _build_envelope, which successful shutdown never invokes. Cumulative CAS tracking therefore does not cover acceptance of shutdown_ack.

## 处置记录 2026-09-17T21:06:20+0800

v67 closes the prior IDLE/reusable-query symptom (state becomes FAILED), but still leaves the worker process alive after CAS invalidation: /tmp/r54_v67_cas_state_probe.out shows state=FAILED, proc_exists=True, proc_poll=None, cwd_exists=False after CAS directory removal; a later query is rejected but the participant continues running against a deleted cwd until caller explicitly shuts down. CAS loss should terminalize and synchronously terminate/reap the worker, not only flip state.

## 处置记录 2026-09-17T21:06:40+0800

v67 re-run confirms successful-shutdown bypass unchanged: /tmp/r54_v67_shutdown_cas_probe.out SHA 87684aeade29173c8b5f56298c536799e2b193f7be41ee12ae36220a38be7a6a; failing shutdown or shutdown_ack CAS writes still yields shutdown_ack and last_envelope=None.

## 处置记录 2026-09-17T21:08:26+0800

v67 lifecycle-only probe /tmp/r54_v67_lifecycle_cas_probe.out (SHA 07507f8...): failing any handshake CAS write (hello, hello_ack, initialize, initialize_ack; calls 1–4), then performing no query and clean shutdown, still returns shutdown_ack with last_envelope=None. _cas_lost is not consulted by start_and_handshake success or shutdown success.

## 处置记录 2026-09-17T21:11:54+0800

v67 misses CAS failures from _drain_pipes(): delayed unframed stdout probe /tmp/r54_v67_unsolicited_stdout_cas_delayed.out fails the direct cas_put(chunk) at call 7; result is shutdown_error with schema_valid=false but cas_status=ok, identity_violations=[], and failed digest unretrievable. This direct write site is not wrapped by _record_cas_outcome; the claimed 'all 8' coverage is incomplete (source has at least 10+ write sites).

## 处置记录 2026-09-17T23:44:44+0800

v69 static audit: runner/campaign.py:431-434 still calls sup.cas_put(raw_final_frame) directly, outside _record_cas_outcome()/cas_put_best_effort(). If this write fails, the supervisor-wide _cas_lost flag is not set and the campaign's finally shutdown can still accept a clean shutdown_ack after the failed CAS call. This remains an uncovered write site in addition to the frame/drain gaps.

## 处置记录 2026-09-18T00:07:54+0800

Fresh v69 direct-call probe confirms the campaign path bypass: replacing sup.cas_put with a failing writer at the exact runner/campaign.py:431-434 call raises OSError while _cas_lost remains false and _cas_failures=[]; output /tmp/r55_v69_campaign_direct_cas_bypass.out SHA-256 0a6a9e90e98b07a45939c97b50bfbb7130d92af3f0ab958b5ea89ef1b8a20432.
