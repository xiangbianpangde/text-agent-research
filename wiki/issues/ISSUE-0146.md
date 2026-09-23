---
id: "ISSUE-0146"
title: "catalog 的 defaultBackend 把 PYTHONPATH 设为 fixture root 而非仓库根，使 6 个走 Python 的工具全部 spawn_error——但 M3 harness 只看工具名，故 §7.2/§7.4 从未观测到工具其实全都失败"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "backend_pythonpath_points_at_fixture_not_package,all_python_backed_tools_fail_silently,harness_ignores_tool_results,metric_measures_choice_not_success,tool_call_scored_as_reached_when_it_failed"
evidence: "researchctl-product（HEAD=fa7ea21）。catalog/tools.ts:60-68 的 defaultBackend 执行 ，且  —— PYTHONPATH 被设为**研究项目根**（fixture 树），而 product 包 researchctl/ 位于仓库根，不在 fixture 树内。实测三态：(A) PYTHONPATH=仓库根 → status=success results=1；(B) PYTHONPATH=fixture 树（即现行代码）→ ；(C) 无 PYTHONPATH → 同样失败。端到端复现（精确复刻 harness 的 spawn 参数与 cwd，扩展=.pi/extensions/catalog/index.ts）：提示『ORG-EXP101 和 R101 分别是什么？』→ research_query 返回 ，而 isError=false（不存在）。对照 Pi 侧 research.ts:42-43 用 / 正确解析包目录。该行由 c509f60（M3-1 首个提交）引入，非后续回归。影响面：7 个 Python-backed runner 中 research_query/research_trace/research_impact/research_integrity/research_mutate 全部不可用；仅 research_status/research_journal（纯 Node journal projection）与 research_tools（loader）可用。语料 25 例中 allows 非空的 14 例里 7 例仅允许 Python 工具、4 例混合、3 例仅 Node。已实证候选修复：PYTHONPATH 改为  → status=success results=1。"
related: []
fix_ref: null
summary: "catalog 的 defaultBackend 把 PYTHONPATH 设为 fixture root 而非仓库根，使 6 个走 Python 的工具全部 spawn_error——但 M3 harness 只看工具名，故 §7.2/…"
updated_at: "2026-09-23"
---

## 现象

§7.2 的 Trigger Recall 定义为『成功发现并调用正确工具』，但 judge() 只读工具名（turn.tools），不读返回值（trigger.ts:340-360 的 judge 与 778 行 rejudge 均传 text: ""），故一次返回 spawn_error 的 research_query 与一次真正取到 4 条记录的 research_query 得分为**完全相同**。后果：G3 门禁 1 的四条『达标』指标中，凡依赖 Python 工具的（Recall 的 7 例、正确工具判定）测的是模型的路由选择，而非检索是否真的成功——而在这套环境下它从未成功过。这不是 harness 的判据错误（路由确实是 M3 的目标），而是**环境配置错误被测量盲区掩盖**：若 harness 读过返回值，第一次运行就会暴露。故 G3 的门禁 1 判定必须重新评估，且 §5『无法测量』的论证需要修正为『可以测量，但必须先修此缺陷』。

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

## 处置记录 2026-09-23T09:40:45+0800

证据字段因 shell 命令替换导致反引号内容被吞，此处补全原文（本 note 为准）。

(1) 代码位置：catalog/tools.ts:60-68。defaultBackend 执行 execFileAsync("python3", ["-m", "researchctl", "--root", root, ...args], { cwd: root, env: { ...process.env, PYTHONPATH: root } })。即 PYTHONPATH 被设为**研究项目根**（fixture 树），而 product 包 researchctl/ 位于仓库根 /Users/xbpd/Projects/researchctl-product，不在 fixture 树内。

(2) 三态实测：
    A) PYTHONPATH=仓库根        → JSON status=success results=1
    B) PYTHONPATH=fixture 树（现行代码）→ 'No module named researchctl'
    C) 无 PYTHONPATH            → 同样 'No module named researchctl'

(3) 端到端复现：精确复刻 harness 的 spawn 参数与 cwd（cwd=fixture 树, PYTHONPATH=仓库根, -e .pi/extensions/catalog/index.ts），提示『ORG-EXP101 和 R101 分别是什么？给我它们的记录。』。实际 JSON 事件流（tool_execution_end）：
    END research_query isError=false → 'Fail-Closed: spawn_error | Command failed: python3 -m researchctl --root <fixture-tree> query --entity ORG-EXP101 | No module named researchctl'
注意 isError=false —— 工具未抛错，而是以文本形式返回 Fail-Closed，因此调用方（与 harness）都不会把它当失败。

(4) 对照：Pi 侧 .pi/extensions/research.ts:42-43 用 REPO_ROOT / MODULE_ROOT 正确解析包目录（MODULE_ROOT = 含 researchctl/__init__.py 的仓库根），故单体 research(action=...) 基线不受影响——这使两 arm 的对照处于不对称环境。

(5) 归因：该行由 c509f60（M3-1 首个提交）引入，非后续回归；`git log -S 'PYTHONPATH: root' --oneline -- catalog/tools.ts` 仅命中 c509f60。

(6) 影响面：7 个 Python-backed runner 中 research_query / research_trace / research_impact / research_integrity / research_mutate 全部不可用；仅 research_status / research_journal（纯 Node journal projection）与 research_tools（loader）可用。语料 25 例中 allows 非空的 14 例：7 例仅允许 Python 工具、4 例混合、3 例仅 Node。

(7) 候选修复已实证：PYTHONPATH 改为 '<repo>:<root>' → status=success results=1。
