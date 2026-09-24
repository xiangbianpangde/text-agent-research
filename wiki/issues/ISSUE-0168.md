---
id: "ISSUE-0168"
title: "任务提示不约束工具面：38/39 回合改用 bash 直调 CLI，判分只能把「未触达受测面」的回合排除出分母，而提示未要求用工具"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "prompt_does_not_constrain_tool_surface,off_tool_cli_path_unjudged,measured_surface_optional"
evidence: "promptOf 只写『研究项目根目录是当前工作目录…请先复现该问题的错误码，然后按工具指引先行处置，再重新读取你原本要读的目标』，没有任何一句要求经 research_* 工具操作。实测统计 39 个已跑场景：38 个至少一次用 bash 直调 CLI 或 sqlite（含 researchctl --help/index/query 与 sqlite3 .index/*.sqlite 直查），只有 rec-semantic-version-mismatch 完全没调用 research_*（research_*=0，bash 直调 18 次，30 次调用中 30 次非 research_*）。该回合最终回答正确复现了 SEMANTIC_INDEX_CORRUPT 并按 §4.7 有序两步 index → index --semantic 恢复成功、重试成功——即它把任务做对了，但因判分只认 research_* 链路而被判 unjudged 并排除出分母。后果一：分母被一个提示未禁止的行为选择缩小；后果二：判分口径实际测的是『是否恰好经由工具』而非『是否恢复』。修法优先级：(a) 提示明确要求经由 research_* 工具处置（改变被测行为，最干净）；或 (b) 判分承认经 CLI 的同构路径（但 CLI 不是受测接口，会把『绕过工具』记成工具能力，方向是虚高）。当前采取的是 (a) 方向但未改提示——本轮只把 unjudged 的理由改为如实陈述（no research_* tool was called: the turn never engaged the graded surface），不谎称『条件从未出现』，并在 --report 中逐条列出理由；提示与判据的最终口径需在下一轮定。"
related: []
fix_ref: null
summary: "任务提示不约束工具面：38/39 回合改用 bash 直调 CLI，判分只能把「未触达受测面」的回合排除出分母，而提示未要求用工具"
---

## 现象

测量的是『模型是否经工具恢复』，但提示没要求使用工具，于是模型用 bash 直调同一个 CLI 就被判为未触达受测面并排除出分母——既缩小了分母，也让『做对了的回合』在读数里消失

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
