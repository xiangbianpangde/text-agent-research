---
id: "ISSUE-0096"
title: "真实 Pi 会话库中 branch_summary 顶层 entry 数为 0：验收若以「生成 branch_summary」为前置将无法取证"
status: "open"
severity: "high"
area: "docs"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "fixture-shape-drift,branch-summary-absent-in-real-store"
evidence: "扫描 872 个真实 session 文件（~/.pi/agent/sessions，文件名匹配 YYYY-MM-DDThh-mm-ss-SSSZ_<uuid>.jsonl）解析全部顶层 entry：message=549092 custom=26507 custom_message=12339 model_change=2694 thinking_level_change=1667 compaction=619 branch_summary=0。同一扫描中 164 个 session 含 compaction（单文件最多 47）。先前 grep -c branch_summary 报出的 81/16/9 命中来自消息正文中的字符串，而非 entry。"
related: []
fix_ref: null
summary: "真实 Pi 会话库中 branch_summary 顶层 entry 数为 0：验收若以「生成 branch_summary」为前置将无法取证"
---

## 现象

单元测试 fixture 会生成 branch_summary entry（fixture.ts branchSummaryEntry），但真实 Pi 0.84.4 存储里从未出现该类型；仅靠合成 fixture 的 G1 验收会声称覆盖 fork/branch 回链而实际未接触真实形态

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
