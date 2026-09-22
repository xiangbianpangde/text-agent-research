---
id: "ISSUE-0014"
title: "v60 retention accepts a missing CAS directory and follows CAS symlink targets"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "retention_completeness"
  - "v71_cas_directory_symlink_toc_tou"
  - "v71_cas_temp_symlink_follow"
evidence: "commit c928f356764c5b9b4483aafa339dd2bc24531755; runner/campaign.py:63-137; runner/worker_supervisor.py:699-710; /tmp/r47_v60_retention_missing_probe.out; /tmp/r47_v60_cas_symlink_probe.out"
related: []
fix_ref: null
summary: "v60 retention accepts a missing CAS directory and follows CAS symlink targets"
updated_at: "2026-09-18"
---

## 现象

_persist_raw_retention() silently continues when cas_dir does not exist and writes an empty raw_manifest.json; cas_get() returns bytes through a symlinked digest path.

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

## 处置记录 2026-09-16T13:46:49+0800

v61补充：仅拒绝 CAS 文件 symlink，CAS 目录 symlink 仍被 follow 并把 outside blob 复制到 raw（raw_blob_exists=true）；raw destination symlink 若内容匹配也被接受并写入 manifest；raw_manifest 每次重写，第二次 retention 后第一次 blob 文件仍在但 manifest 不再列出；同一 invalidation 两次 persistence 产生两行，缺少幂等 cursor。证据 /tmp/r48_v61_retention_probe.out。

## 处置记录 2026-09-16T13:47:07+0800

WorkerSupervisor.cas_get() 也未 no-follow：cas_dir/digest symlink 指向外部且外部 bytes 的 sha256 正好匹配时，cas_get 返回外部 bytes（/tmp/r48_v61_cas_get_symlink.out）。

## 处置记录 2026-09-16T14:14:30+0800

v61 crash-restart probe：预置截断 events.jsonl 行后，CampaignRunner.run_quick_ci(num_queries=1) 正常返回但直接 append，结果 6 行中第 1 行仍与新 response 粘连、JSONDecodeError；parsed_lines=5。无 restart reconciliation / partial-tail recovery。证据 /tmp/r48_v61_event_restart_probe.out。

## 处置记录 2026-09-17T16:37:19+0800

Round 51/v64 direct retention probes remain open: /tmp/r51_v64_retention_missing_probe.out (SHA-256 63b81bc171d83a8c8340849558fe6664c2628a62671c600b4824b62281f3a833) shows missing CAS recorded as missing_cas_systems=['A'] while _persist_raw_retention() returns ok and writes a manifest; /tmp/r51_v64_retention_probe.out (SHA-256 004b7120076f914872ffbb407168c1a3f4b310b2741dd9b4758445a8ce9573f9) shows a CAS directory symlink is followed and an outside blob is retained. Recording the absence is not fail-closed retention, and symlink containment is still missing.

## 处置记录 2026-09-17T20:02:47+0800

v66 clean-room probe /tmp/r53_v66_retention_missing.out: _persist_raw_retention still returns ok and writes raw_manifest.json with missing_cas_systems=['A'] when CAS directory is absent. Recording a warning is not a failed retention transaction; no durable attempt failure is emitted. Existing missing-CAS fail-open remains.

## 处置记录 2026-09-17T23:48:19+0800

v69 source remains unchanged at runner/campaign.py:93-99: missing cas_dir is appended to missing_cas_systems and raw_manifest is still published with a successful return. /tmp/r53_v66_retention_missing.out remains applicable; no v69 fail-closed retention transaction was added. v69 cas_get/cas_put also still follow CAS directory/blob symlinks (fresh probes /tmp/r55_v69_cas_dir_symlink.out SHA-256 22a251450d5b59ebb72fb6062e5c598a9f3ce63684d0e4acb3fe4d554df8ec34 and /tmp/r55_v69_cas_blob_symlink.out SHA-256 98a4a2d64433ad2110e3d0e2ac781e98346b2c274515c4227a5551495db5a099).

## 处置记录 2026-09-18T08:18:55+0800

v71 clean-room CAS probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: after replacing the selected cas_dir with a symlink, WorkerSupervisor.cas_put() follows it and writes the digest blob outside the intended tree, returning success; blob-level symlink rejection works only for the immediate target. Evidence /tmp/r56_v71_cas_symlink_probe.out SHA-256 c1e87b9cd524d3e76d04684c137ec540e81253228b4693da8a863cf5ac93cf96. Parent-directory no-follow/atomic directory-fd binding remains absent.

## 处置记录 2026-09-18T08:57:25+0800

v71 clean-room fault injection against commit 1ed201b636302ee095fb6713186f69a56e422ac9: precreating the UUID-selected CAS temp path as a symlink causes cas_put()'s ordinary open(tmp_p, 'wb') to overwrite the external target, then os.replace() publishes the blob and returns success. Evidence /tmp/r56_v71_cas_temp_symlink_probe.out SHA-256 01b2065f7ab6a96deee0878c93607a810e8ea2dc010122960abb75f7636ae0e. Immediate target checks do not protect temporary CAS paths; use O_CREAT|O_EXCL/O_NOFOLLOW and directory-fd anchored writes.
