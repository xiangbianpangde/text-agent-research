---
id: "ISSUE-0127"
title: "wiki/ 与整个知识库从未纳入 git（142 个文件含不可变证据仅有磁盘副本），无版本历史与灾难恢复"
status: "open"
severity: "high"
area: "wiki"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "measured_no_offmachine_copy_118_unpushed_commits;frozen_archive_fully_reconstructible_from_468d9fc;public_remote_holds_only_main"
  - "wiki_layer_untracked_no_version_history"
evidence: "2026-09-22 R64: git status --porcelain 显示 wiki/ 为 untracked（'?? wiki/'）；git log --oneline -- wiki/ 无任何输出 => 从未提交；git check-ignore -v wiki/ 无输出 => 并非被忽略，而是从未 add；find wiki -type f | wc -l = 142；同仓库另有 12 个 untracked 顶层项（AGENTS.md、tools/、dsh-researchctl/、docs/specs/ 等）"
related: []
fix_ref: null
summary: "wiki/ 与整个知识库从未纳入 git（142 个文件含不可变证据仅有磁盘副本），无版本历史与灾难恢复"
updated_at: "2026-09-22"
---

## 现象

Raw Layer 的不可变证据（RAW-20260922-001..004 等）只有单一磁盘副本：磁盘损坏/误删即永久丢失，且无法用 git 证明'未被改写'（现仅有 lint 的内容摘要自校验）。AGENTS.md 要求'不可变证据'，但不可变性目前依赖文件系统而非版本控制

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

## 处置记录 2026-09-22T22:12:34+0800

R68 实测数据补齐（见 RAW-20260922-007）：

1) 远端实测仅承载 main：git ls-remote --heads origin 只有 01b4cd0 refs/heads/main；仓库为 public（匿名 HTTP 200），origin/main 仅 448 文件。
2) 仅存本机的提交：origin/main..benchmark = 118；origin/main..product/researchctl-pi-retrieval-journal = 17；main = 0。
3) 无冗余副本：tmutil 未配置目标；无云同步挂载；/Volumes 仅 Macintosh HD 与 Recovery；.pi/sol-staging/ 被 .gitignore:33 忽略。
4) 归档位于 /private/tmp（非持久位置，macOS 周期性清理）。
5) 归档可完全重建：review_v77 与 468d9fc 逐文件比对 1917/1917，内容 mismatch 0 —— 说明需保护的是提交而非 zip 本身。

影响升级：ISSUE-0127 原文范围（wiki/ 未纳管）应扩展为'整条证据链无离机副本'：wiki/ 145 文件 + 118 个 bench 提交 + 17 个 product 提交 + 13 个顶层未跟踪项。已升级为 high 并同步证据。
