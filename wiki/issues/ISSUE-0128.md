---
id: "ISSUE-0128"
title: "过期 benchmark 副本内含 456 个 git 中不存在的唯一文件（含 old-layout PILOT_SCORECARD），删除会永久销毁证据"
status: "open"
severity: "high"
area: "wiki"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "stale_bench_copy_holds_unique_unrecoverable_evidence;old_layout_scorecard_exists_at_exactly_one_path_on_disk"
evidence: "R68 RAW-20260922-007; git hash-object/git cat-file -e over 460 stale-only files => present 4 / absent 456; find /Users/xbpd /private/tmp -name PILOT_SCORECARD_REPORT.md => old-layout digest 35d389453c0c5c5b appears at exactly one path; du -sh results/pilot_campaign = 2.4M; unzip -l review_v77.zip | grep -c pilot_workspace = 0"
related: []
fix_ref: null
summary: "过期 benchmark 副本内含 456 个 git 中不存在的唯一文件（含 old-layout PILOT_SCORECARD），删除会永久销毁证据"
---

## 现象

/Users/xbpd/Projects/文字Agent检索系统/research-retrieval-benchmark/ 是 515 文件的旧副本（受管 1923 文件，最新 mtime 2026-09-09 vs 受管 2026-09-22）。按名比较有 460 个文件仅存于此；对全部 460 做 blob 存在性测试（git hash-object + git cat-file -e）得：内容在 git 中存在 4 个，缺失 456 个。其中 results/pilot_campaign/PILOT_SCORECARD_REPORT.md（2789B，blob 508768501c39b0e6）全盘搜索确认仅此一处存在，且旧新布局评分卡内容不同（旧 35d38945… ≠ 新 c4049b0e…）。该路径正是 open 的 ISSUE-0120 中门禁探测却缺失的路径。

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
