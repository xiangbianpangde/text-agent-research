---
id: "ISSUE-0005"
title: "溯源闭集动作上的 semantic 请求（规则误用信号样例）"
status: "wontfix"
severity: "low"
area: "wiki"
discovered_at: "2026-09-15"
discovered_by: "agent（验证用例）"
tags: []
signals:
  - "semantic_on_closed_command"
evidence: "calls-2026-09-15.jsonl ts=18:33:47 action=sources argv=['sources','CURRENT'] semantic_requested=true → signals=['semantic_on_closed_command']"
related: []
fix_ref: null
summary: "验证用例产生的信号，wontfix 留档以免 suggest 反复提示"
updated_at: "2026-09-15"
---

## 现象

suggest 报出未登记的 semantic_on_closed_command

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

（待评估：影响面 / 是否有 workaround）

## 根因

该次调用是插件接入验证时人为触发（构造规则误用用例），非缺陷

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

保留作为规则误用信号的可复现样例；信号本身工作正常

## 处置记录 2026-09-15T19:18:48+0800

补登 signals（登记时漏填导致 suggest 反复提示）
