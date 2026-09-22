---
id: "ISSUE-0111"
title: "product worktree 的 journal/test/tsconfig.json 为单行 JSON：自动重序列化会把 1 行改动放大成 30 行 diff"
status: "open"
severity: "low"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "tsconfig_single_line_reserialize_diff,json_tooling_format_drift,reviewer_noise_in_config_edit"
evidence: "researchctl-product/journal/test/tsconfig.json@HEAD:1 为单行 JSON；python3 json.load+dumps 编辑 'files' 数组后 git diff 由 +4 行变为 30 行（-1/+32），原 2 空格缩进与多行结构全部丢失。复现命令：git show HEAD:journal/test/tsconfig.json | head -3（多行）vs git show :journal/test/tsconfig.json | head -3（单行，已 staged 的坏版本）。"
related: []
fix_ref: null
summary: "product worktree 的 journal/test/tsconfig.json 为单行 JSON：自动重序列化会把 1 行改动放大成 30 行 diff"
---

## 现象

任何用 JSON 解析器读写该文件的任务（如向 'files' 追加新模块）都会把整份配置重排成单行，diff 与真实改动无关；reviewer 需要 diff 才能确认只加了 4 个文件，而 diff 无法提供该信息。本次 M2-3 追加 projection/commands/command-run/digest-store 时已实际发生一次，需 git checkout 回滚重做。

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
