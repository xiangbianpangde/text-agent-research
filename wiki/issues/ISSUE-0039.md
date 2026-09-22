---
id: "ISSUE-0039"
title: "v62 crash-repair temp-file symlink is followed"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "repair_temp_symlink_follow,no_follow_persistence"
  - "v71_retention_temp_symlink_follow,v71_raw_dir_symlink_follow"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/campaign.py:57-63; /tmp/r49_v62_repair_tmp_symlink_probe.out"
related: []
fix_ref: null
summary: "v62 crash-repair temp-file symlink is followed"
updated_at: "2026-09-18"
---

## 现象

_repair_jsonl_tail opens events.jsonl.repair.tmp with wb without O_NOFOLLOW. A pre-existing symlink to external.log receives the repaired bytes before os.replace removes the symlink (external content changed from ORIGINAL to VALID\\n). Similar temp-path opens exist in raw retention.

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

## 处置记录 2026-09-16T15:38:17+0800

/tmp/r49_v62_retention_tmp_symlink_probe.out also shows raw_manifest.json.tmp symlink to external file receives full manifest bytes before replace. raw retention temp_dest has same open-without-O_NOFOLLOW pattern.

## 处置记录 2026-09-16T15:56:57+0800

/tmp/r49_v62_raw_dir_symlink_probe.out: output/raw directory symlink to outside is followed; retention writes external raw_manifest.json and blob while raw_is_symlink remains true.

## 处置记录 2026-09-18T08:18:20+0800

v71 clean-room probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: runner/campaign.py still opens repair/retention temp paths with ordinary write APIs and does not reject output/raw symlinks. /tmp/r56_v71_retention_symlink_probe.out SHA-256 9c6158b96bf4e2a85414eeb2045a427bf89e6ba6da4dc17ee4f3dc46f7de2125 shows events.jsonl.repair.tmp symlink overwrote external target, output/raw symlink received blob and raw_manifest, and raw_manifest.json.tmp symlink overwrote an external target. Existing no-follow/retention containment defect remains open.
