---
id: "ISSUE-0004"
title: "全局技能副本与项目版漂移（~/.pi/agent/skills/task/research-retrieval）"
status: "fixed"
severity: "low"
area: "pi-extension"
discovered_at: "2026-09-15"
discovered_by: "agent（本次接入）"
tags: []
signals: []
evidence: "全局副本 2026-09-03（4903B）vs 项目版已含 Tools/Self-improvement loop/CHANGELOG 1.1.0；settings.json 用 '+skills/task/research-retrieval/SKILL.md' 强制启用"
related: []
fix_ref: "~/.pi/agent/skills/task/{research-retrieval,researchctl-wiki} 符号链接 + ~/.agents/skills/ 同名链接"
summary: "全局副本应改为指向项目的符号链接，避免第二份真源"
updated_at: "2026-09-15"
---

## 现象

pi 可能加载旧技能文本，与项目内技能不一致

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

技能行为漂移；本次已改为符号链接指向项目版

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-15T19:37:06+0800

已修：旧副本（2026-09-03）归档到 ~/.pi/agent/skills-archive/，目录改为指向项目版符号链接；DSH 技能目录同样挂上，researchctl-wiki 已出现在 DSH 技能目录中
