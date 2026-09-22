---
id: "ISSUE-0109"
title: "Pi extension 的 @earendil-works/pi-tui 在宿主加载器之外不可解析，且 registerEntryRenderer 返回 string 不报错"
status: "open"
severity: "medium"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "host_only_specifier,entry_renderer_component_type,tsc_needed_for_api_drift"
evidence: "journal/extension.ts 首版 return `${theme.fg(...)} ${label}`（string）；tsc --strict 对 @earendil-works/pi-coding-agent dist/core/extensions/types.d.ts:890 EntryRenderer 返回 Component|undefined 报错；node --test 直接 import 该模块报 ERR_MODULE_NOT_FOUND: Cannot find package '@earendil-works/pi-tui'；宿主 dist/core/extensions/loader.js:85 用 resolveWorkspaceOrImport 别名该 specifier；修复见 session-retrieval/test/typebox-hook.mjs 的 ALIASES 与 journal/extension.ts 的 Box/Text"
related: []
fix_ref: null
summary: "Pi extension 的 @earendil-works/pi-tui 在宿主加载器之外不可解析，且 registerEntryRenderer 返回 string 不报错"
---

## 现象

① typebox 是纯类型使用故可只做类型导入，但 pi-tui 的 Box/Text 是**值**导入，在仓库内（private、无 node_modules）无法解析；仓库既有 typebox-hook.mjs 只映射 typebox，不足以加载任何使用 TUI 组件的 extension。② 返回 string 而非 Component 时逻辑上会失败，只有 tsc 能提前发现，纯运行时 stub 测不出来——TTY 之外的测试会静默通过。

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
