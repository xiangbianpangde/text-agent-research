---
id: "ISSUE-0191"
title: "wiki 演化日志与 issue 文件可互相矛盾：logs.md 记录 open→fixed 而 HEAD 里 issue 仍为 open，且 fix_ref 指向的提交不含该修复"
status: "open"
severity: "high"
area: "wiki"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "sync_log_asserts_state_absent_from_issue_frontmatter"
  - "fix_ref_points_at_commit_that_does_not_carry_the_fix"
  - "issue_frontmatter_and_log_updated_by_different_uncommitted_sessions"
evidence: "git status --porcelain wiki/ 在 2026-09-24 显示：M wiki/issues/ISSUE-0158.md、M wiki/issues/ISSUE-0159.md、M wiki/logs.md 均未提交（另一会话在飞），而 git diff wiki/logs.md 新增 52 行中 2 行断言 ISSUE-0158/0159「status open → fixed」并各带 fix_ref 42cfc6e。HEAD 侧核对：git show HEAD:wiki/issues/ISSUE-0158.md | grep '^status:' → status: 'open'（0159 同）。fix_ref 核验（在 researchctl-product 仓库）：git show --name-only 42cfc6e 的文件清单为 catalog/test/{.final.mjs,recovery-run.ts,recovery.test.ts,recovery.ts,trigger.ts,tsconfig.json} + docs/records/M3-G3-acceptance-record.md，不含 catalog/catalog.ts；git show 42cfc6e -- catalog/catalog.ts | grep -c research_integrity → 0。同一句 recovery 文本的实际变更提交为 9815966（git log -L343,343:catalog/catalog.ts 显示 'This is the recovery tool. After reconcile...' → 'Use action="reconcile" to DIAGNOSE...'），而已纳版控制的 ISSUE-0158 正引用 9815966。同批次中 0159 的 fix_ref 42cfc6e 经核验**正确**（git show 42cfc6e -- catalog/test/tsconfig.json 确实新增 ../test/recovery.ts、recovery.test.ts、recovery-run.ts），故两行须分别判定，不能整批否定。"
related: []
fix_ref: null
summary: "wiki 演化日志与 issue 文件可互相矛盾：logs.md 记录 open→fixed 而 HEAD 里 issue 仍为 open，且 fix_ref 指向的提交不含该修复"
---

## 现象

logs.md（演化日志）与 issues/*.md（frontmatter 状态）由同一工具写入但不受同一事务保护：多会话并发时，日志可先落盘并断言某 issue 已 fixed，而该 issue 文件仍是 open 且未提交。更糟的是 fix_ref 可指向一个不承该修复的提交，此时「已修复」既无状态一致、也无提交可查——按日志审计会得出仓库并不具备的状态。因为 issue 文件的改动与 logs.md 的改动可能分属不同会话且各自未提交，单看任一侧都自洽。

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
