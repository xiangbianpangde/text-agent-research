---
id: "ISSUE-0095"
title: "skill 触发描述与能力描述混写在同一 description 字段，导致 SKILL.md frontmatter 解析失败"
status: "open"
severity: "medium"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "skill-frontmatter-unloadable,description-colon-yaml-break"
evidence: "pi runtime loadSkillsFromDir(.pi/skills) 实测：diagnostics 非空、skill 不可加载。修复前 .pi/skills/research-retrieval/SKILL.md 的 description 含 ': '，YAML 视为键值分隔。修复后 loadSkillsFromDir 返回 1 skill / 0 diagnostics / disableModelInvocation=false。"
related: []
fix_ref: null
summary: "skill 触发描述与能力描述混写在同一 description 字段，导致 SKILL.md frontmatter 解析失败"
---

## 现象

description 里写 'Use when ...: xxx' 形式时整份 frontmatter 失效，技能静默不可发现，且校验器与加载器报错口径不同

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
