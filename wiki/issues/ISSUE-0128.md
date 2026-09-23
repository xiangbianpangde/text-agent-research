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
  - "rescue_executed_456_of_456_preserved;gitignore_unignore_rule_had_zero_matching_files;nested_git_sealed_workspaces_packed_deterministically"
  - "stale_bench_copy_holds_unique_unrecoverable_evidence;old_layout_scorecard_exists_at_exactly_one_path_on_disk"
evidence: "R68 RAW-20260922-007; git hash-object/git cat-file -e over 460 stale-only files => present 4 / absent 456; find /Users/xbpd /private/tmp -name PILOT_SCORECARD_REPORT.md => old-layout digest 35d389453c0c5c5b appears at exactly one path; du -sh results/pilot_campaign = 2.4M; unzip -l review_v77.zip | grep -c pilot_workspace = 0"
related: []
fix_ref: null
summary: "过期 benchmark 副本内含 456 个 git 中不存在的唯一文件（含 old-layout PILOT_SCORECARD），删除会永久销毁证据"
updated_at: "2026-09-23"
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

## 处置记录 2026-09-23T16:37:50+0800

R68 处置（选项 A 执行完毕，见 RAW-20260923-001）：

证据已全部抢救并纳入版本控制：
- 目标边界：results/pilot_campaign/ —— 复用仓库既有约定（该路径在 .gitignore:37 已有 !results/pilot_campaign/ 未忽略规则，注释写明 'they must be tracked, because an ignored file can never be attested'；但迁移后零文件匹配该规则）。
- 内容：PILOT_SCORECARD_REPORT.md (2789B, sha256:35d38945…) + events.jsonl (532542B, 456 行) + native_sealed.tar (501760B, 300 文件) + neutral_sealed.tar (235520B, 154 文件) + PILOT_EVIDENCE_MANIFEST.json (legacy.pilot_evidence.freeze/v1) + README.md。
- 密封工作区因内嵌 .git（HEAD 819a89e / 0168893）无法直接入库，改用确定性 tarball（PAX_FORMAT、名称排序、uid=gid=0、mtime=0），实测两次重打包摘要一致。

验证：覆盖 456/456（tar 454 + 复制 2），UNCOVERED=0；454 个打包文件逐个字节比对 mismatch=0；manifest 与 README 摘要全部自校验通过。
提交与推送：rescue/pilot-dryrun-evidence c5a202c → private 远端；灾备演练仅从私有远端 clone 后 4 个 artifact 摘要全部匹配。
冻结态未受影响：benchmark 分支仍 468d9fc，v77 归档 SHA 仍 7de9414fa01dfac2，独立 worktree 已移除并 prune。

剩余待办（需用户确认）：物理清理 /Users/xbpd/Projects/文字Agent检索系统/research-retrieval-benchmark/（515 文件）。因唯一内容已全部入库且有离机副本，该目录现已可安全删除。
