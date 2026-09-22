---
id: "ISSUE-0003"
title: "pi 在 DSH 沙箱下启动即 EPERM（trust.json.lock）"
status: "wontfix"
severity: "medium"
area: "env"
discovered_at: "2026-09-15"
discovered_by: "agent（本次接入）"
tags: []
signals: []
evidence: "pi --help / pi -p 报 EPERM: mkdir '/Users/xbpd/.pi/agent/trust.json.lock'；需 danger-full-access 才能启动"
related: []
fix_ref: null
summary: "pi 启动要写 ~/.pi/agent，沙箱需放行"
updated_at: "2026-09-15"
---

## 现象

workspace-write 模式下任何 pi 调用立即崩溃

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

验证 pi 集成必须额外授权；agent 无法自证 pi 侧改动

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-15T19:37:06+0800

判定为策略使然而非缺陷：DSH file sandbox=workspace-write 会 fail-closed 拒绝工作区外写入，符合预期；pi 启动即写 ~/.pi/agent 属其正常行为。处置：需要时一次性提权（sandbox_permissions=danger-full-access + 理由），或在系统层给 ~/.pi/agent 放行；已记入 PAT-20260915-002
