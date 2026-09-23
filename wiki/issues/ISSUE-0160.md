---
id: "ISSUE-0160"
title: "已推送提交禁止 amend：本地 amend 造成 remote/local 分叉，只能 reset --hard 回退"
status: "open"
severity: "low"
area: "env"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "amended_pushed_commit_causes_divergence;git_add_directory_sweeps_concurrent_session_files"
evidence: "R68: git push -q private main => 'hint: See the Note about fast-forwards'（拒绝）; git rev-parse 0a1b72b^{tree} = 4b40abf^{tree} = d07051217a5d; git diff --stat 0a1b72b 4b40abf 为空; git reset --hard 0a1b72b 后 HEAD == private/main == 0a1b72b"
related: []
fix_ref: null
summary: "已推送提交禁止 amend：本地 amend 造成 remote/local 分叉，只能 reset --hard 回退"
---

## 现象

对已推送的 main 执行 git commit --amend（仅为修正提交信息）后 git push 被拒（fast-forward 失败），本地 HEAD 与 private/main 分叉。经比对两者 tree 完全相同（d07051217a5d），仅提交信息不同，最终以 git reset --hard 0a1b72b 接受远端版本收场。另有并发现象：git add wiki/ 会把同目录另一会话正在写入的 ISSUE-0129..0159（31 个 issue）一并纳入提交，提交信息与实际内容不符（lint 通过、记录有效、无损失）。

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
