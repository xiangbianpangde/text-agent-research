---
id: "ISSUE-0058"
title: "v65 late-child regression test invalidates the shutdown ack and does not exercise a valid clean shutdown"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-17"
discovered_by: "agent"
tags: []
signals:
  - "invalid_positive_control"
  - "shutdown_test_false_green"
  - "suite_flaky_physical_cleanup"
evidence: "commit 7e9e7fd922b833e7d48f6163f4aea7ccae8abe98; tests/security/test_worker_isolation.py:3527-3590; /tmp/r52_v65_selected_tests.out SHA-256 efbc212ac0b3c2b25b52e1e2edf32a4d689da19780b479614ed0ff1ebb31114f; /tmp/r52_v65_async_post_ack_probe.out SHA-256 a3c724525e4f07bc792a15ff03a2bc221c142e13a716a193d4d875340ef5960f"
related: []
fix_ref: null
summary: "The v65 regression test claims a clean-shutdown survivor sweep but sends an all-zero session_payload_digest, causing shutdown to reject the ack and hard-teardown the still-live descendant; the valid shutdown_ack path remains untested."
updated_at: "2026-09-17"
---

## 现象

The selected v65 test passes, but its worker emits session_payload_digest=sha256: followed by 64 zeroes. A valid post-ack detached-child probe instead returns shutdown_ack with the child alive at return and 2.5s in 6/6 trials while _sweep_outstanding=true and proc_none=true.

## 复现

Run tests/security/test_worker_isolation.py::test_f02_unclaimed_late_child_is_swept_on_clean_shutdown and compare the worker's all-zero session digest with /tmp/r52_v65_async_post_ack_probe.py, which computes session_payload_digest before sending a valid ack and spawns the child after the ack is fully written.

## 影响

A green regression test can mask the exact accepted-success residue failure that blocks F-02, allowing asynchronous cleanup to be mistaken for synchronous containment.

## 根因

The test uses an intentionally invalid shutdown correlation digest, so WorkerSupervisor enters its failure/hard-kill path; it does not assert a valid shutdown_ack followed by a detached child.

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

Round 52 independent clean-room finding. The v65 code still launches _sweep_surviving_descendants_async(); waiting for _sweep_outstanding to clear after an invalid-ack teardown is not evidence for the valid-ack case.

## 处置记录 2026-09-17T20:11:49+0800

v66 replaced the zero digest with a valid digest but the regression remains incomplete: test_f02_post_ack_child_invalidates_shutdown_within_budget() does not assert result.record_type=shutdown_error or alive=False at return; it only waits 0.5s. v66 clean-room /tmp/r53_v66_async_probe.out reproduces alive_return=True in 6/6 while test still passes, so _sweep_outstanding=False is not proof of synchronous zero-residue.

## 处置记录 2026-09-17T23:54:47+0800

v69 clean-room full pytest is not deterministically green in an independent run: env -u PYTHONPATH python3 -m pytest -q collected 155 and produced 154 passed/1 failed at test_f02_unclaimed_late_child_is_swept_on_clean_shutdown (child 49238 alive after _sweep_outstanding=False); an isolated rerun of that test passed in 0.28s. This test still uses an invalid all-zero shutdown digest and is not evidence for valid shutdown_ack containment; full-suite green claim is environment/scheduling-sensitive. Full-run output was observed directly; isolated output /tmp/r55_v69_f02_test.out SHA-256 9a102d4c42732f66659d3ed7d12307e5b93965b7f41864270c71b0e5d6e61bdf.
