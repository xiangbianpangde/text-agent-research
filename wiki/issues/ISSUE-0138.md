---
id: "ISSUE-0138"
title: "Spec §6.1 强制要求 2 个初始 active 工具，§7.4 却要求 active schema 数量低于 1 工具的单体基线——两条条款互相矛盾"
status: "fixed"
severity: "high"
area: "docs"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "spec_self_contradiction,gate_unreachable_by_design,catalog_count_vs_monolith_count"
evidence: "docs/specs/ResearchCTL-Product-v0.2-Pi-Retrieval-Journal-Spec.md:§6.1 表格强制 research_tools=active 与 research_status=active（行 1-2），即初始 active 数为 2；§7.4 末条要求『相比单体 research(action=...) 基线，平均 active ResearchCTL schema 数量下降』，单体为 1 个工具（.pi/extensions/research.ts 仅注册 1 个 tool，承载 9 个 Type.Literal action）。实测两 arm：catalog 起始 2 个工具 vs 基线 1 个（+1）；激活后 3 vs 1（+2）。字节口径：起始 -6.0%（1879 vs 1998）、激活 1 个后 +86.8%（3733 vs 1998）"
related: []
fix_ref: "docs/specs/ResearchCTL-Product-v0.2-Pi-Retrieval-Journal-Spec.md#7.4.1"
summary: "Spec §6.1 强制要求 2 个初始 active 工具，§7.4 却要求 active schema 数量低于 1 工具的单体基线——两条条款互相矛盾"
updated_at: "2026-09-23"
---

## 现象

G3 已按字面判定该条不通过。但根因不在实现：实现严格遵照 §6.1 的表格，而 §7.4 的『数量下降』对『1 个工具承载全部 action』的单体基线而言，任何满足 §6.1 的实现都必然使数量上升（2 > 1）。该门禁在设计上不可达，除非把 §7.4 的 schema 语义解释为『单个 schema 承载的 action 数』或字节量——而这两种读法在激活后（+86.8%）同样通不过。需裁决：改条款、改基线定义，或明确接受数量上升、以字节/未使用会话成本为收益口径。

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

## 处置记录 2026-09-23T02:16:54+0800

待裁决，非代码修复项。已写入 docs/records/M3-G3-acceptance-record.md §4/§9：§6.1 强制 2 个初始 active 工具 vs §7.4 要求数量低于 1 工具基线，两条条款互斥，门禁不可达。选项：(a) 改 §7.4 度量定义为字节或单 schema action 数；(b) 改基线定义；(c) 明确接受数量上升并以未用会话成本为收益口径。

## 处置记录 2026-09-23T08:03:13+0800

2026-09 裁决：改为「未激活会话的 active schema 字节量不上升」。基线 1998B，catalog 起始 1879B = -6.0%，四轮一致 PASS。原数量口径确认不可达（§6.1 强制 2 个初始 active 工具）。收益边界已写入 Spec：激活 1 个后 +86.8%，优势是「未用会话几乎不付费」而非「更省」。baseline.ts 已按新口径输出并令退出码只反映该门禁。
