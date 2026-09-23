---
id: "ISSUE-0140"
title: "验收记录把含未测量条目的门禁 #1 标为 PASS：把「我修订的两条已解决」误当成「该门禁已满足」"
status: "fixed"
severity: "critical"
area: "docs"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "gate_marked_pass_with_unmeasured_items,scope_error_partial_closure,record_internally_contradictory"
evidence: "docs/records/M3-G3-acceptance-record.md §1 门禁表第 1 行，判定列写『PASS（依 2026-09 裁决修订后的口径）』，同一行证据列却写『Wrong-Layer 与 Fail-Closed 仍未测量（§5）』。§7.4 共 7 条：Wrong-Layer Rate = 0、identity/version/causality 落到 exact/structured/provenance、Fail-Closed Recovery ≥ 95% 三条未测量；§5 与 §8 均自述未完成。Spec §8.3 G3 首条为『达到 §7.4 阈值』。由执行者-2 独立复核发现（intercom a8669331，seq 10）。"
related: []
fix_ref: "researchctl-product@681f431"
summary: "验收记录把含未测量条目的门禁 #1 标为 PASS：把「我修订的两条已解决」误当成「该门禁已满足」"
updated_at: "2026-09-23"
---

## 现象

我把注意力集中在正在修订的两条子句（数量条、成功率条），裁决完成后直接把 Gate #1 提升为 PASS，未回头确认该门禁还包含另外三条未测量条目。同一表格行内『判定=PASS』与『证据=仍未测量』并存，属自相矛盾的记录。根因是把「部分条目的闭环」当作「整条门禁的满足」，即范围错误而非数据错误。正确判定为 Gate #1 未满足、G3 整体 PARTIAL/HOLD。修复：记录改写并明确三条未测量条目不得由裁决顺带豁免——豁免需单独的用户批准。

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

## 处置记录 2026-09-23T08:53:36+0800

已修复并只读复核。溯源：错误由 780c5ba 引入（把门禁 1 由『不通过』改为『PASS（依 2026-09 裁决修订后的口径）』，而同一行证据列仍写『Wrong-Layer 与 Fail-Closed 仍未测量』，行内自相矛盾），由 681f431 改正为『不满足（PARTIAL）』。复核证据：(1) §1 门禁表第 1 行现为『不满足（PARTIAL）』且列出 4 条达标 / 3 条未测量，不再有 PASS；(2) 全文已无『门禁 1=PASS』残留（唯一命中是 §9.1 主动保留的错误修订记录）；(3) 结论三处一致（第 9 行、第 65 行、第 305 行均为 PARTIAL / HOLD，5 通过 1 不满足）；(4) §9.1 明确写出三条未测量条目不被裁决顺带豁免、豁免需单独用户批准与 Spec 修订。该 issue 的实质是范围错误而非数据错误，修复方式为记录改写 + 保留错误痕迹以防复现，不涉及代码。
