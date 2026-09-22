---
id: "ISSUE-0115"
title: "工具参数 schema 标注 Optional 但实现直接解引用，导致 TypeError 崩溃"
status: "open"
severity: "medium"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "optional_field_unguarded_deref,schema_impl_mismatch,runtime_crash_on_valid_input"
evidence: "catalog/backend.ts buildMutationArgs；实测 TypeError: Cannot read properties of undefined (reading 'idempotency_key') at buildMutationArgs；触发输入 {operation:'freeze-report', authorization_ref:'a', actor:'u'}（target 未提供，符合 schema）"
related: []
fix_ref: null
summary: "工具参数 schema 标注 Optional 但实现直接解引用，导致 TypeError 崩溃"
---

## 现象

research_mutate 的 TypeBox schema 把 target 标为 Optional，但 buildMutationArgs 里 const { operation, target } = params 之后直接读 target.idempotency_key。对一次完全合法（schema 校验通过）的调用，函数抛 TypeError 而不是返回拒绝——异常穿过 execute 会让整个工具调用失败，错误信息与 Fail-Closed 语义无关。

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

已修复：target 在函数入口统一 const target = params.target ?? {}，使所有字段读取全定义。补用例 'accepts target=undefined rather than crashing'。同类风险面：任何 Optional 对象参数（target/root/params 嵌套）都应在入口归一化，而不是在使用点判空。
