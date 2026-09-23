---
id: "ISSUE-0129"
title: "lazy loader 缺少 promptSnippet/promptGuidelines，模型缺少发现新能力的信号"
status: "fixed"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "loader_not_advertised_in_prompt,missing_prompt_metadata,discovery_signal_absent"
evidence: "catalog/catalog.ts CATALOG[research_tools] 无 promptSnippet/promptGuidelines；catalog/test/extension.test.ts 断言全部工具都不得携带这两个字段；对照 Pi 官方参考实现 dist 文档 docs/extensions.md 的 search_tools 示例同时给出 promptSnippet 与 promptGuidelines；实测 acceptance corpus 25 例：pos-entity-by-id（'ORG-EXP101 和 R101 分别是什么'）6 次 bash/read、0 次 ResearchCTL 调用"
related: []
fix_ref: "69dac74"
summary: "lazy loader 缺少 promptSnippet/promptGuidelines，模型缺少发现新能力的信号"
updated_at: "2026-09-23"
---

## 现象

我把 §6.2.5『lazy 工具不应携带 active-only prompt metadata』这条规则**过度泛化**到了所有工具，包括从 session 一开始就 active 的 research_tools。后果是 system prompt 的 Available tools 段落里完全没有 loader 的条目——而 promptSnippet 正是『让你的工具出现在该段落』的唯一手段，没有它自定义工具会被整段省略。模型因此只在巧合下才发现 loader；对 identity 类问题干脆转向文件系统。

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

修正方向：仅对**初始 active** 的工具（research_tools/research_status）补 promptSnippet，lazy 工具维持不带（对它们来说 §6.2.5 与缓存论点才成立：激活时才进入 prompt）。我的原注释用『M3-3 基线对比需要在 prompt 文本上保持单一差异』为此辩护，但该对比的判据是 active schema 数量，与 prompt 文本无关，所以该理由不成立。属于 §7.1 要求的『关联 corpus 证据后再改描述』，改前/改后窗口见 M3-G3 记录。

## 处置记录 2026-09-23T01:33:07+0800

改为 per-entry 断言：lazy 工具不得携带 promptSnippet/promptGuidelines，始终 active 的工具必须携带；两侧均有断言。复跑确认 pos-entity-by-id 现在调用 research_tools,research_query。
