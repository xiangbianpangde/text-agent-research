---
id: "ISSUE-0089"
title: "Pi 项目级扩展加载需项目 trust；未 trust 时静默不加载且无报错，验证脚本易误判为通过"
status: "open"
severity: "medium"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "project_local_extension_silent_skip,trust_gate_no_error"
evidence: "cwd=/tmp/piload;command=pi --mode rpc --no-session --no-builtin-tools -e <probe.ts> (probe 在扩展顶层写文件);stdout=仅 extension_ui_request,无扩展报错,_probe.json 未生成;对比 command=pi --mode rpc --no-session -ne -e .pi/extensions/research.ts;stdout=stderr 空(加载成功);负向对照 command=-e <broken.ts>;stdout=Error: Failed to load extension … intentional probe failure;根因=docs/extensions.md:113 'Project-local .pi/extensions entries load only after the project is trusted'"
related: []
fix_ref: null
summary: "Pi 项目级扩展加载需项目 trust；未 trust 时静默不加载且无报错，验证脚本易误判为通过"
---

## 现象

项目未 trust 时 .pi/extensions 下的扩展被静默跳过：不加载、不报错，导致'扩展是否可加载'的验证脚本可能得到假阴性（看起来无错但实际未运行）

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
