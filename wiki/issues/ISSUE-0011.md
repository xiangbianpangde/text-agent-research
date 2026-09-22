---
id: "ISSUE-0011"
title: "computer_use app 名解析仅接受英文名/bundle id，中文应用名报 identity_rejected"
status: "open"
severity: "low"
area: "pi-extension"
discovered_at: "2026-09-16"
discovered_by: "agent（实测）"
tags:
  - "computer-use"
  - "app-resolution"
  - "i18n"
signals: []
evidence: "~/.pi/agent/direct-computer-use/audit/direct-computer-use.jsonl（2026-09-15T23:59:41.497Z, outcome=identity_rejected）"
related: []
fix_ref: null
summary: "computer_use app 名解析仅接受英文名/bundle id，中文应用名报 identity_rejected"
updated_at: "2026-09-16"
---

## 现象

get_app_state(app='文本编辑') 报 Target app could not be resolved to a canonical installed bundle identifier

## 复现

computer_use_get_app_state(app='文本编辑') -> identity_rejected；改用 'TextEdit' 或 'com.apple.TextEdit' 成功

## 影响

在中文系统上按用户口语化名字调用会失败；list_apps 返回的是本地化名（'文本编辑'），直接回填该名字会失败，需回退到 bundle id

## 根因

canonical app resolution 按英文 bundle 显示名 / bundle id 匹配，不匹配本地化显示名；list_apps 输出的中文名不能直接作为 app 参数

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

workaround：优先用 bundle id（list_apps 输出中带 com.* 字段）
