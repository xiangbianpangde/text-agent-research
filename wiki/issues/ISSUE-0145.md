---
id: "ISSUE-0145"
title: "catalog 的静态 authority 字段是工具『最强层』而非『本次调用实际层』，因此单看 tool.authority 判 Wrong-Layer 恒为通过——必须按调用实参逐次解析"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "static_authority_conflated_with_per_call_layer,identity_safe_check_would_always_pass,measurement_would_be_vacuous"
evidence: "researchctl-product（fa7ea21）。catalog/catalog.ts:224 给 research_query 声明 authority: 'exact'，但同一工具在实参不同时由不同层作答——实证（fixture 副本，PYTHONPATH=文字Agent检索系统）：query --entity CURRENT → 1 条；query --semantic --text current → 10 条；query --semantic → 13 条。后端 researchctl/queries.py 的 cmd_query 以显式 if/elif 链分派：semantic+text 且无其它判别参数 → 走 query_semantic（semantic 层）；否则按 entity → doc_type → status → raw → text 顺序（exact / structured / structured / structured / lexical），全空则列出全部 documents。故 research_query 声明 exact 是其**可达最强层**，而--semantic 调用实际落在 semantic 层。"
related: []
fix_ref: null
summary: "catalog 的静态 authority 字段是工具『最强层』而非『本次调用实际层』，因此单看 tool.authority 判 Wrong-Layer 恒为通过——必须按调用实参逐次解析"
---

## 现象

若按『工具声明层是否 identity-safe』来测 §7.4「identity/version/causality 全部落到 exact/structured/provenance」，则每次 research_query 调用都会被判为 exact，该门禁**恒通过**——包括用 --semantic 做身份判定这一该条专门要抓的错误。即：接线方式本身可以制造一个看似有测量、实则空转的门禁，与 ISSUE-0144『写了 API 却从未调用』同源，但更隐蔽——这次 API 会被调用，只是判据用错。正确判据必须 (a) 先按实参解析本次调用的实际层，(b) 再套 isIdentitySafe 检查。已实测后端优先级链，作为冻结矩阵依据。

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
