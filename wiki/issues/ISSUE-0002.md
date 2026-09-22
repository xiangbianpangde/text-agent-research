---
id: "ISSUE-0002"
title: "dev_reload_package 只清入口模块，lib/core/* 仍是旧代码"
status: "fixed"
severity: "high"
area: "dsh-plugin"
discovered_at: "2026-09-15"
discovered_by: "agent（本次接入）"
tags: []
signals: []
evidence: "重载日志：匹配 dsh-researchctl/lib/index.js → 清缓存 1 模块（core 未刷新，limit_ignored 信号不生效）；匹配 dsh-researchctl → 清缓存 6 模块（生效）"
related: []
fix_ref: "try/dsh-super-injector/lib/index.js（reload 自动扩展包目录子树）"
summary: "重载匹配串必须是包目录子串，否则只清入口 1 个模块"
updated_at: "2026-09-15"
---

## 现象

改 lib/core/runner.js 后热重载，行为仍按旧代码执行

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

改核心模块后误以为已生效，浪费两次重载排查；已写进 README 与 AGENTS.md

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-15T19:36:33+0800

已修：reloadPackage 在匹配串只命中入口时，按入口反推包目录纳入整棵模块子树清缓存，并写 auditLog(reload-subtree-expanded)；工具描述同步更新。A/B 验证：同一匹配串 dsh-researchctl/lib/index.js 由「清缓存 1 模块」变为「清缓存 7 模块」（入口 + 6 个 core 模块），修复生效
