---
id: "ISSUE-0013"
title: "v60 teardown sweep misses late unclaimed descendants and drops an unprovable live root on graceful cleanup"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "error_path_escape_sweep_bypass"
  - "lsof_timeout_fail_open"
  - "process_scope_escape"
  - "v69_no_identity_shutdown_ack_live_child"
  - "v71_identity_loss_root_handle_survives"
  - "v71_lsof_nonzero_return_failopen"
  - "v71_no_identity_cwd_escape_shutdown_ack"
  - "v71_no_identity_fail_closed_but_residue_survives,v71_lsof_failure_typed_shutdown_error"
  - "v71_post_ack_exit_race_fail_closed"
evidence: "commit c928f356764c5b9b4483aafa339dd2bc24531755; runner/worker_supervisor.py:2021-2089,2170-2220; /tmp/r47_v60_teardown_probe3.out; /tmp/r47_v60_startup_probe.out; /tmp/r47_v60_unprovable_grace_probe.out"
related: []
fix_ref: null
summary: "v60 teardown sweep misses late unclaimed descendants and drops an unprovable live root on graceful cleanup"
updated_at: "2026-09-18"
---

## 现象

A valid shutdown_ack with an unclaimed child spawned after the pre-shutdown update returns shutdown_ack while the child remains alive; startup EOF leaves a detached child alive; graceful _terminate_worker clears self.proc although root remains alive when root identity cannot be proven.

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

## 处置记录 2026-09-16T13:46:03+0800

v61复现补充：shutdown round-trip 无 on_poll；worker 收到 shutdown 后创建 1 个 unclaimed child，合法 shutdown_ack 后 5/5 存活。80-child 实验 reported_lines=80，claims=64，dropped=16，tracked_after_refresh=1，tracked_after_shutdown=64，alive_after_shutdown=61；证明 MAX_CHILD_PID_CLAIMS=64 在 spawn/discovery race 下导致合法后代遗漏。证据 /tmp/r48_v61_shutdown_roundtrip_probe.out 与 /tmp/r48_v61_claim_80_probe.out

## 处置记录 2026-09-16T14:18:11+0800

v61 rerun of unprovable graceful teardown: forged _root_identity, _terminate_worker(hard=False, grace_period=.03) returns with supervisor_proc_none=true, proc_poll_after_grace=null, last_returncode=null, os_kill0_after_grace=true, unterminated_root=false (/tmp/r48_v61_unprovable_grace_probe.out). Root handle still dropped despite no death proof.

## 处置记录 2026-09-16T16:00:27+0800

v62 direct unprovable-root graceful probe: after replacing _root_identity, _terminate_worker(hard=False, grace_period=.01) returned supervisor_proc_none=true while saved Popen handle poll=null (root still alive); last_returncode=null, unterminated_root=false (/tmp/r49_v62_unprovable_grace_probe.out).

## 处置记录 2026-09-17T16:26:36+0800

Round 51/v64 independent clean-room probe: /tmp/r51_v64_async_sweep_probe.out (SHA-256 73408747ab58e7aa6990305b0316de0f355c463931b7503bcee08b336d5e0de5) produced a valid-looking shutdown_ack in 8/8 trials while a detached child was alive at return and at 0.5s/2.5s; _sweep_outstanding=true and proc_none=true in every trial. The daemon sweep therefore is not synchronous residue closure and releasing proc/cleaning the cwd hides the live residue. v64 remains open, not fixed.

## 处置记录 2026-09-17T18:57:46+0800

Round 52/v65 independent valid-ack repro: `/tmp/r52_v65_async_post_ack_probe.out` SHA-256 a3c724525e4f07bc792a15ff03a2bc221c142e13a716a193d4d875340ef5960f uses a correct session_payload_digest, writes shutdown_ack before spawning a start_new_session child, and still reports 6/6 children alive at return and 2.5s; `_sweep_outstanding=true`, `proc_none=true`, and cwd already removed. The prior v64-semantic probe also remains 8/8 survivors. v65's 0/6 regression claim is not reproduced under a valid clean shutdown.

## 处置记录 2026-09-17T19:55:09+0800

v66 clean-room recheck: Darwin valid post-ack child yields shutdown_error but child is still alive at return in 6/6; /tmp/r53_v66_async_probe.out. More severe non-Darwin branch: forcing the actual _libproc=None fallback (ps enumeration, no PID identity) in /tmp/r53_v66_no_identity_probe.out yields a successful shutdown_ack with live detached child, ever=False/tracked=[]/proc_none=True; _admit_descendant rejects every PID without identity and _sweep_surviving_descendants fast-paths. Thus Linux/non-Darwin remains fail-open absent kernel-owned cgroup/job scope.

## 处置记录 2026-09-17T21:05:53+0800

v67 clean-room stress still reproduces the original race: worker writes valid shutdown_ack, immediately spawns start_new_session child, then os._exit(0); 4/100 trials return shutdown_ack with alive child, ever_had_descendants=False, tracked=0, proc_none=True (the rest fail closed). Evidence /tmp/r54_v67_post_ack_exit_race.out SHA 45bca91dd7bc9b91d259a10b225c3da55ba42d41d18a84e5cd3a3ced4f629583. The new .05s positive test does not cover this fork→exit race. Non-Darwin end-to-end fallback also remains shutdown_ack+live child in /tmp/r54_v67_no_identity_probe.out SHA 36a44b654af76c9ff82588d6e4e9bdace958abbcc1e6edda6522b082b25aced3.

## 处置记录 2026-09-17T23:56:19+0800

v69 clean-room repro: monkeypatch runner.worker_supervisor._libproc/_BSDInfo=None, valid shutdown_ack worker spawns post-ack detached child; shutdown returns record_type=shutdown_ack while alive_return=true, ever=False, tracked=[], sweep=False, proc_none=True, last_envelope=None. Evidence /tmp/r55_v69_no_identity_probe.out SHA-256 910055c0d2676f210eabc051778eb7883c858531160e56e9ac0508247142d40e. The new cwd fallback cannot help when _pid_identity is unavailable because _admit_descendant rejects all candidates; platform still fails open.

## 处置记录 2026-09-18T00:07:16+0800

v69 also swallows lsof sweep failures: _reap_escaped_processes catches all subprocess.run exceptions and returns the candidate set unchanged; _sweep then treats empty set as zero residue. Forced no-lineage race plus injected lsof TimeoutExpired on a valid post-ack detached child returned shutdown_ack with alive_return=true, ever=false, tracked=[], sweep_outstanding=false, proc_none=true, no envelope. Evidence /tmp/r55_v69_lsof_timeout_forced_untracked.out SHA-256 d89f23ff8891dc8e9504c2d1f0e0ecb4c5b864cb149387fabfa991377b3502c1.

## 处置记录 2026-09-18T00:10:43+0800

v69 source still gates _reap_escaped_processes in _terminate_worker graceful teardown on (survivors or _tracked_descendants), so an invalid shutdown-ack path with no tracked PID skips the new unconditional _sweep_surviving_descendants entirely. Fresh 50-trial clean-room probe: malformed shutdown ack followed immediately by detached child left alive_return=true in 31/50 trials, with result=shutdown_error, ever=false, tracked=0, proc_none=true. Evidence /tmp/r55_v69_invalid_ack_orphan.out SHA-256 a262d70c3c1c54ff383bca0780f86be9858d5f9acfba568aaea0870b4fc48884.

## 处置记录 2026-09-18T08:16:43+0800

v71 clean-room probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9 (evidence /tmp/r56_v71_no_identity_lsof_probe.out SHA-256 7a4ab830776904518691f67ef22b53f21764c0d15f4cee0e029c824d200ed8e5): forcing _libproc/_BSDInfo=None or lsof TimeoutExpired now returns shutdown_error with a runner-owned envelope and records residue_unattributed/residue_unconfirmed; it does not signal the detached child, which remains alive at return. This is safer than v69 fail-open but F-02 is still open because no kernel/job-owned scope can prove or clean the residue.

## 处置记录 2026-09-18T08:19:51+0800

v71 clean-room direct probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: forcing post-spawn identity loss (_pid_identity returns None with a nonmatching recorded root identity) makes _terminate_worker(hard=True) return with proc_handle_retained=true, proc_poll=null, last_returncode=null, unterminated_root=true, supervisor_killed=true. The fail-safe avoids signalling an unproven PID but leaves a live worker; callers must not discard its handle or remove its cwd and must provide kernel/job scope for cleanup. Evidence /tmp/r56_v71_identity_loss_root_probe.out SHA-256 6fbd2367f5a593f5ea8a006b97fe3b45f39f23030b94f742603ef2e000261450.

## 处置记录 2026-09-18T08:21:41+0800

v71 30-trial clean-room post-ack fork/exit stress against commit 1ed201b636302ee095fb6713186f69a56e422ac9: all 30 returned typed shutdown_error with runner-owned envelopes and no shutdown_ack; each recorded unattributed residue and unconfirmed state. Evidence /tmp/r56_v71_post_ack_exit_race.out SHA-256 9ee9ee29afb4a09d4a8317458aa251a4d46b3327a40bce1d2a3d0db9077847ad. This narrows the former fail-open race on this host but does not close F-02: the architecture still has no kernel/job-owned scope and cannot prove or synchronously clean a reparented child.

## 处置记录 2026-09-18T08:25:51+0800

v71 clean-room no-identity probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: with _libproc/_BSDInfo forced unavailable, a valid post-ack child launched in an external cwd is neither descendant-admitted nor found by the scratch-only lsof sweep. shutdown returns shutdown_ack, proc_none=true, no envelope, ever=false/tracked=[], while child PID 82369 is alive at return. Evidence /tmp/r56_v71_no_identity_cwd_escape.out SHA-256 b91b93cbb50f613bb05ddae2718ca1d9ea94d13eb6beb4c56e5f8996eb169c0e. This is a direct v71 fail-open escape; cwd rollback/location cannot substitute for kernel-owned job scope.

## 处置记录 2026-09-18T08:48:39+0800

v71 clean-room fault injection against commit 1ed201b636302ee095fb6713186f69a56e422ac9: _reap_escaped_processes() receives lsof CompletedProcess(returncode=1, stderr='permission denied', stdout='') and returns extra=[] with sweep_incomplete=false, unattributed=[], residue_unattributed=false. It checks only stdout and catches timeout/exception, never treats a nonzero lsof return as inability to prove zero residue. Evidence /tmp/r56_v71_lsof_nonzero_sweep_probe.out SHA-256 ca80c3686d6abd41f8319c222977450f554d5a9384ada3848431f3b4b4ee72e0. A failed discovery command must invalidate teardown, not report/permit clean success.
