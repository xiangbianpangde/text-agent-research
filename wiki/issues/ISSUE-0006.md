---
id: "ISSUE-0006"
title: "wiki CLI 的 --json 只能在子命令之前使用，工具调用踩坑"
status: "fixed"
severity: "low"
area: "wiki"
discovered_at: "2026-09-15"
discovered_by: "agent（宿主侧验证）"
tags: []
signals:
  - "wiki_error"
evidence: "wiki(action=issue_list,args=['--status','open','--json']) → exit=2 usage 报错；日志 signals=['wiki_error']"
related: []
fix_ref: "tools/wiki.py（parents=[json_parent]）"
summary: "argparse 全局选项位置陷阱；已修复并回归"
updated_at: "2026-09-15"
---

## 现象

按 action 追加参数时 --json 被 argparse 判定为非法位置

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

（待评估：影响面 / 是否有 workaround）

## 根因

argparse 全局选项只在顶层解析；工具/Agent 只能把参数追加在子命令之后

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

已修：tools/wiki.py 为所有子解析器挂 parents=[json_parent]（默认 SUPPRESS，不覆盖顶层值）；两种位置各验证一次

## 处置记录 2026-09-15T19:18:48+0800

已修复并回归：--json 在子命令前后均可

## 处置记录 2026-09-15T19:18:53+0800

补登 signals
