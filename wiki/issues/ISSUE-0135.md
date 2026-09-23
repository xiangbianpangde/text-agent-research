---
id: "ISSUE-0135"
title: "baseline.ts 用固定 250 bytes/工具估算参数开销，与它刚替换掉的'只用描述'属同类错误"
status: "fixed"
severity: "medium"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "estimated_constant_reported_as_measurement,activation_cost_approximated"
evidence: "researchctl-product/catalog/test/baseline.ts 的 catalogBytesAfterActivation(activated) 原实现为 describeCapability(entry).length + 250（每工具固定加 250）。实测同一工具的 JSON.stringify(parameters) 差异极大：research_status=33、research_tools=250、research_query=814、research_mutate=1135 bytes。修正后改为传入 measureArm() 的 perTool 实测字节。实测值对比：3 工具 3386（估算）vs 3733（实测）"
related: []
fix_ref: "486477b"
summary: "baseline.ts 用固定 250 bytes/工具估算参数开销，与它刚替换掉的'只用描述'属同类错误"
updated_at: "2026-09-23"
---

## 现象

修正了两侧口径不一致之后，激活后成本仍由常数 250 bytes/工具 估算，而真实参数的序列化长度在 33–1135 bytes 之间相差 34 倍。该数字会与实测数字并排打印，读者无法区分哪个是量出来的、哪个是猜的——正是 ISSUE-0134 的成因在新的位置复发。

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

## 处置记录 2026-09-23T01:33:10+0800

catalogBytesAfterActivation 改为使用 measureArm() 的 perTool 实测字节，不再用固定 250 bytes/工具。
