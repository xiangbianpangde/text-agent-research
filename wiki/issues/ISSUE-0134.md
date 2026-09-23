---
id: "ISSUE-0134"
title: "§7.4 基线对照的 schema 度量两侧口径不一致，-37.5% 是错误结论；一致口径下初值仅 -6% 而激活后 +87%"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "inconsistent_measurement_basis_across_arms,schema_bytes_vs_schema_count,activation_cost_not_accounted"
evidence: "researchctl-product/catalog/test/baseline.ts 原 catalogSchemaBytes() 只累加 describeCapability(entry).length（纯描述），baselineSchemaBytes() 累加 description 字面量 + parameters 块（描述+参数）。一致口径（拦截 registerTool，description+JSON.stringify(parameters)）：catalog 8 工具共 11123 bytes，其中初始激活 2 工具=1879；baseline 1 工具=1998。【/tmp/schema-measure.mjs 实测】原报告 -37.5%（1596 vs 2553）源于两侧口径不同；同口径下初始 -6.0%，激活 1 个工具后 3 工具=3733 bytes 即 +86.8%，全载 +456.7%"
related: []
fix_ref: "486477b"
summary: "§7.4 基线对照的 schema 度量两侧口径不一致，-37.5% 是错误结论；一致口径下初值仅 -6% 而激活后 +87%"
updated_at: "2026-09-23"
---

## 现象

两个 arm 的 schema 成本用不同口径测量：catalog 侧只算 capability 描述文本，baseline 侧算描述加 Type.Object 参数块。差值因此不是'catalog 更省'，而是'两侧统计范围不同'。且对照只报 session 起始状态（catalog 最便宜的状态），未计 lazy activation 的常驻成本——一旦用过 ResearchCTL，激活的工具在整个会话内持续付费。§7.4 字面要求的是 schema 数量下降，数量在起始为 2 vs 1（上升），字节在激活后为 +87%。

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

两个 arm 均改为拦截 registerTool 实测（描述+参数）。一致口径结果：起始 -6.0%、激活 1 个后 +86.8%、全载 +456.7%。§7.4 数量条据此判为不通过并写入 G3 记录。
