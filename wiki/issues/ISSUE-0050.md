---
id: "ISSUE-0050"
title: "v63 RSS sampler sums per-process lifetime peaks instead of concurrent job peak"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "rss_lifetime_peak_overcount,non_cgroup_peak_accounting"
  - "v71_sequential_live_child_peak_sum_overcount"
evidence: "commit 0e9adf49c5c8a89c981432abcf6fea30d6998bfb; /private/tmp/r50_v63_rss_overcount_reprobe.out SHA-256 90a5a63ecc6a341bb8a3d5ed115eb3dc1ce05d69fb6f9ee1c0475edf695b7c38; runner/worker_supervisor.py:847-878,2376-2390"
related: []
fix_ref: null
summary: "v63 RSS sampler sums per-process lifetime peaks instead of concurrent job peak"
updated_at: "2026-09-18"
---

## 现象

Sequential 64MiB child peaks yield envelope max_rss=143.548MiB although response-time ps shows children at 12144 and 77472 KiB

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

## 处置记录 2026-09-17T16:31:20+0800

Round 51/v64 evidence remains open. The first complete pytest run (/tmp/r51_v64_pytest.out, SHA-256 61369d001cc8cbfb7b7adc837d89f8b824135869624c11c6f5e58bea123ad594) failed test_f03_repeated_exited_children_keep_being_attributed at attempt 9 with max_rss=19.3917MiB (<20MiB), while later attempts were ~36MiB; the same selected test passed in three 2.32-2.40s reruns (/tmp/r51_v64_f03_repeat_1.out, _2.out, _3.out). This run-to-run instability does not establish reliable per-attempt accounting; v64's own attestation still marks kernel/per-attempt RSS claims false.

## 处置记录 2026-09-18T08:50:32+0800

v71 independent physical probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: one 48MiB child that remains alive reports max_rss_bytes=66,225,136; two 48MiB children run sequentially (child 1 releases before child 2 allocates, both remain alive) reports 113,083,424, ratio 1.708x. The peak code sums each live descendant's lifetime high-water (`_sample_tree_new_peak_rss`) even though the peaks were non-concurrent; the instantaneous concurrent upper bound is approximately the one-child case. Evidence /tmp/r56_v71_rss_sequential_peak_probe.out SHA-256 20555c5d88cff96814dca1081f923ae48991d476319d7b5f9b87aa9c0474c64a. Both runs also ended with typed shutdown_error for unattributed detached children, confirming the probe's children were alive but not concurrent at peak.
