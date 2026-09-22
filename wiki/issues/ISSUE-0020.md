---
id: "ISSUE-0020"
title: "v61 successful shutdown appends the same ack payload twice to session_frames"
status: "fixed"
severity: "medium"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "session_trace_duplicate,protocol_provenance"
  - "v69_duplicate_terminal_frame"
  - "v71_shutdown_ack_stored_twice"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/worker_supervisor.py:1868-1889; /tmp/r48_v61_shutdown_duplicate.out"
related: []
fix_ref: "df3ce4a"
summary: "v61 successful shutdown appends the same ack payload twice to session_frames"
updated_at: "2026-09-22"
---

## 现象

valid shutdown_ack 后 session_frames 从 4 增至 7，last_two_equal=true；持久化/后续 session digest 若消费该列表会包含重复 terminal frame，破坏逐帧 provenance

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

## 处置记录 2026-09-16T16:00:49+0800

v62 current valid shutdown: session_frames 4→7 and last_two_equal=true (/tmp/r49_v62_shutdown_duplicate_probe.out). shutdown_ack is appended at worker_supervisor.py:1868 and again at :1889.

## 处置记录 2026-09-17T19:50:25+0800

v66 retains the duplicate terminal-frame append: worker_supervisor.py appends raw_ack at lines 1944 and 1965. Clean-room source audit confirms unchanged behavior; issue remains open.

## 处置记录 2026-09-17T19:58:03+0800

v66 clean-room probe /tmp/r53_v66_shutdown_duplicate.out: normal valid shutdown has session_frames before=4, after=7, last_two_equal=true; raw_ack remains appended at lines 1944 and 1965.

## 处置记录 2026-09-17T23:57:45+0800

v69 clean-room valid shutdown remains duplicated: before=4, after=7, last_two_equal=true, record_type=shutdown_ack, evidence /tmp/r55_v69_shutdown_duplicate.out SHA-256 c7cc581df52ec9c0c2c9aaacfb17f673e30efd342258239d498dc51e18fa8dc6.

## 处置记录 2026-09-18T08:59:30+0800

v71 clean-room roundtrip against commit 1ed201b636302ee095fb6713186f69a56e422ac9: WorkerSupervisor.session_frames grows from 6 to 9 on shutdown and contains the exact shutdown_ack frame twice (count=2, 399 bytes), despite the ack digest being computed before the first append. Evidence /tmp/r56_v71_shutdown_duplicate_ack_probe.out SHA-256 e4757146a9355166ef7845c902a8fe71910a4b8ec697786591209979648a472b. This duplicates terminal protocol provenance and can distort session replay.

## 处置记录 2026-09-22T17:38:36+0800

shutdown ack appended twice to session_frames (session payload covered a duplicated frame)
