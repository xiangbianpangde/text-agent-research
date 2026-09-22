---
id: "ISSUE-0093"
title: "skill-authoring 校验器无法自动定位 Pi 包：npm root -g 指向 ~/.local 而 Pi 装在 Homebrew"
status: "open"
severity: "medium"
area: "env"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "skill-validator-pi-locate,env-npm-root-mismatch"
evidence: "npm root -g => /Users/xbpd/.local/lib/node_modules（无 @earendil-works）；which pi => /Users/xbpd/.local/bin/pi（软链指向 Homebrew）；实际包在 /opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent/dist/index.js。运行 python3 ~/.pi/agent/skills/task/skill-authoring/scripts/validate.py --strict .pi/skills/research-retrieval 报 ERROR [target-invalid]: cannot locate the installed @earendil-works/pi-coding-agent dist/index.js；加 PI_CODING_AGENT_PACKAGE 覆盖后通过。"
related: []
fix_ref: null
summary: "skill-authoring 校验器无法自动定位 Pi 包：npm root -g 指向 ~/.local 而 Pi 装在 Homebrew"
---

## 现象

严格校验在无显式环境变量时直接 ERROR exit，报 target-invalid，与 skill 内容无关；容易误判成 skill 有问题

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
