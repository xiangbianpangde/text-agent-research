---
id: "ISSUE-0144"
title: "catalog 已为每条 §7.4 层级判据写好 API（authority 标注 / AUTHORITY_RANK / isIdentitySafe），但无任何测量代码调用，故 Wrong-Layer 与 identity-safe 两条门禁长期返回 null"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "layer_judgement_api_declared_but_never_invoked,wrong_layer_unmeasured_despite_available_machinery,written_but_never_read_metric_field,gate_returns_null_with_measurement_close_at_hand"
evidence: "researchctl-product（fa7ea21）。catalog/catalog.ts 定义 AuthorityLayer（8 值）、AUTHORITY_RANK（exact0<lexical1<structured2<provenance3<semantic4）、IDENTITY_SAFE_LAYERS=['exact','structured','provenance']、isIdentitySafe()，且每个 ToolCapability 都带 authority 字段（catalog.ts:101）。穷举调用点： 除定义处（catalog.ts:54-58）外零命中；./dsh-researchctl/lib/core/runner.js:240:  summary.authority = typeof envelope.authority === 'string' ? envelope.authority : null ./researchctl/schema.py:52:        self.authority = authority      # canonical | derived | unresolved ./researchctl/schema.py:65:            'authority': self.authority, 仅命中 loader.test.ts:463-464（断言值在枚举内）与其他 operational 断言，无一处参与 §7.4 测量。同时 catalog/test/corpus.ts 对全部 25 例标注 expects_layer（8 值，分布 exact3/operational4/provenance6/none12），但  零命中；requires_fail_closed 同样零读取点。trigger.ts:426-431 的 computeMetrics 注释自述『工具序列 harness 看不到哪一层产出了答案』并据此返回 null——但同一工具序列的**参数**其实携带该信息：research_query 的参数决定层级（--entity/--trace/--impact = exact/structured/provenance 层，--semantic = semantic 层），而 trigger.ts:231-234 只把 event.args 用于 research_tools 的 query，对 research_query 丢弃。可测规模：25 例中 9 例 expects_layer ∈ {exact,provenance} 属该 §7.4 条范围。"
related: []
fix_ref: null
summary: "catalog 已为每条 §7.4 层级判据写好 API（authority 标注 / AUTHORITY_RANK / isIdentitySafe），但无任何测量代码调用，故 Wrong-Layer 与 identity-safe 两…"
updated_at: "2026-09-23"
---

## 现象

门禁被判定为「无法测量」，但使其可测的判据 API 早已写好且从未接线，缺口是接线而非能力。三条未测量 §7.4 条目中至少两条（Wrong-Layer Rate = 0、identity/version/causality 落到 exact/structured/provenance）只需在 TurnResult 记录 research_query 的实参即可判定，属小改动；只有 Fail-Closed Recovery 确需跨轮观测（真实错误后的第二轮）而单轮 harness 结构上不产生该观测。因此把三条一并按「harness 能力不足」豁免是过度概括：一条确需新观测，两条是接线遗漏。危险在于写好的 API 会被读成「已有能力」，而零调用点说明它从未参与任何判定——与 judge.test.ts 开篇自述的『写了但没人读的字段看起来和能用的功能一模一样』完全同形。

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

## 处置记录 2026-09-23T08:56:42+0800

接线可行性已实证（非推断）。catalog/extension.ts 的 research_query 参数表确含 semantic: Type.Optional(Type.Boolean({description: 'Layer 5 fallback, candidate discovery only. Never use for identity/version/causality.'}))，即层级选择是显式入参。因此判定链完整：TurnResult 记录 research_query 的实参 → 若 semantic===true 而该例 expects_layer ∈ {exact,provenance} 则记一次 wrong-layer → 用已有的 isIdentitySafe() 判 identity-safe 条。三条未测项归类：(a) Wrong-Layer Rate = 0 与 (b) identity/version/causality 落到 exact/structured/provenance 属接线遗漏，判据 API 齐备（AuthorityLayer/AUTHORITY_RANK/isIdentitySafe 已定义且每工具带 authority），仅缺 TurnResult.args 与一次比对；(c) Fail-Closed Recovery ≥ 95% 确需跨轮观测——语料中 5 例标 requires_fail_closed 但 privateFixture 不注入任何错误（无 INDEX_STALE/HASH_MISMATCH/SOURCE_MISSING 触发条件），故单轮内不产生恢复路径观测。结论：不应把三条一并按『harness 能力不足』豁免，属过度概括。尚未实施接线，本 issue 仅登记现状。

## 处置记录 2026-09-23T08:58:05+0800

精度收窄（避免把两条子句混为一谈）。子句 (a) Wrong-Layer Rate = 0 可**完全**由实参判定：semantic 是布尔显式入参，无歧义——在 expects_layer ∈ {exact,provenance} 的例子上传了 semantic=true 即记一次 wrong-layer。子句 (b) identity/version/causality 落到 exact/structured/provenance 只能**部分**由实参判定：单参数调用可唯一映射（entity→exact、doc_type/status→structured、trace→provenance、text→lexical），但一次调用同时给多个判别参数时（如 text + doc_type）落到哪一层取决于后端优先级策略，属策略裁决而非接线。故 (b) 的接线还须先定一个显式优先级，不能仅凭已有 API 断言可测；我此前把 (b) 一并归入『小改动』是过宽的表述。另核实 §5 的论证框架有实质错误：§5 以『语料把 semantic 工具放入 forbids』为重合条件，但语料中不存在 semantic 工具（grep session_retrieval 命中 0；semantic 只是 research_query 的参数），故该论证把「层级路由」当作「工具选择」来推理，与 §7.2/§7.4 的定义（路由到 semantic/session）不匹配。
