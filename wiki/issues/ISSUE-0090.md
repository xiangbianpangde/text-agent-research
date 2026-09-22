---
id: "ISSUE-0090"
title: "product 工作区与主工作区同注册 research 工具：project scope 同时加载两者导致 pi 启动失败（退出码 1，整个会话不可用）"
status: "open"
severity: "high"
area: "env"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "duplicate_tool_name_cross_worktree,pi_startup_abort,global_package_shadow"
evidence: "cwd=/tmp/reloadtest(已放置 research.ts+skills);command=pi --mode rpc --no-session -a --no-builtin-tools(未隔离 PI_CODING_AGENT_DIR);exit=1;stderr=Error: Failed to load extension '/Users/xbpd/Projects/文字Agent检索系统/.pi/extensions/research.ts': Tool 'research' conflicts with /private/tmp/reloadtest/.pi/extensions/research.ts;根因: ~/.pi/agent/settings.json packages 含 '../../Projects/文字Agent检索系统';隔离后 PI_CODING_AGENT_DIR=/tmp/pi-clean 同命令 exit=0 且 probe 输出 session_start reason=startup tools=…,research"
related: []
fix_ref: null
summary: "product 工作区与主工作区同注册 research 工具：project scope 同时加载两者导致 pi 启动失败（退出码 1，整个会话不可用）"
---

## 现象

同一台机器上主工作区与 researchctl-product 工作区各自注册名为 research 的扩展工具。因主工作区被全局安装(packages)，在 product 工作区再加载 project-local research 工具时冲突，pi 直接启动失败退出 1，整个会话不可用（非仅研究功能不可用）

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
