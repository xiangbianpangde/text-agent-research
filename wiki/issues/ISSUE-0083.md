---
id: "ISSUE-0083"
title: "research query 在仓库根目录无法打开 SQLite 数据库"
status: "open"
severity: "medium"
area: "env"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "research_sqlite_unopenable_root"
evidence: "research(action=query, root='.', entity='CURRENT') 与 text='P0' 均返回 stderr: error: unable to open database file"
related: []
fix_ref: null
summary: "research query 在仓库根目录无法打开 SQLite 数据库"
---

## 现象

research 工具在当前仓库根目录执行只读 query 失败，无法按既定科研检索路径读取 CURRENT/P0

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
