---
id: "ISSUE-0188"
title: "报告的逐码底线只有「是否达标」而无可数的分子分母，导致操作者两次手工推导缺额并两次得出错误的付费预算"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "hand_derived_number_drifted wrong_paid_budget_request operator_recount_disagrees_with_tool tool_prints_verdict_not_counts under_specified_report_output"
evidence: "同一读数两次被手工推导成不同的错误数字，且两次都用于真实的付费申请：（1）验收记录 §10.10 手工表 → 7 码缺额 / 申请 9 回合；（2）恢复上下文后我用最新一行观测 + “缺 sandboxed 即受污” 的**自造规则**重数 → 4 码 / 5 回合合格，但另一次更宽的口径得到 31 回合（`clean=0` for 5 个码）。工具权威读数（`npm run m3:recovery -- --report`，免费）：`tool-recoverable: 23/24 = 95.8%`、`source-integrity: 8/8 = 100.0%`，逐码 `SEMANTIC_NOT_INDEXED 4/5`、`SEMANTIC_INDEX_CORRUPT 3/5`、`SOURCE_MISSING 4/5`、`HASH_MISMATCH 4/5`，缺额 **4 码 / 5 场景**。差异原因已定位：受污规则在 `recovery.ts::readGradingDesign`（第 1863 行起）——`sandboxed` 缺失**不**等于受污，受污要求 `calls` 的 args 实际命中 `GRADING_DESIGN_PATTERNS`；我自造的规则把 51 个缺字段的行全部判为受污。修复：`recovery-run.ts` 现直接打印 `§3.2 per-code states (authoritative; copy from here, not by hand)`，输出与工具内部 `states_per_code` 逐格一致。"
related:
  - "ISSUE-0187"
fix_ref: null
summary: "报告的逐码底线只有「是否达标」而无可数的分子分母，导致操作者两次手工推导缺额并两次得出错误的付费预算"
---

## 现象

`--report` 打印的是**判定结论**（`INCONCLUSIVE — §3.2 floor applies to this stratum too: X (4/5)`），没有打印可直接引用的**逐码分子/分母明细表**。于是「缺多少」这个问题在工具侧没有单一可复制答案，操作者只能自己从 59 行归档重新推导——而推导需要正确复现三个不平凡的口径：（a）同一 scenario 多行时取最新（`readLatestRows`，11 个 scenario 有多行，最多的 6 行）；（b）受污规则要求 args 命中判分路径，而非缺 `sandboxed` 字段；（c）底线按**码**计而非按**行**计（受污行失效的是观测，不是该码的一个状态）。三处任一弄错都会得到一个看似合理的错误数字，且**没有任何输出会与之矛盾**——这正是它在两次独立推导中都被弄错、且两次都写进付费申请的机制。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

实测已产生两次不正确的付费预算申请（9 回合、以及我中途另一个口径的 31 回合），而真实需要是 5 回合。属于**在不利方向上高估欠账**，会导致申请被驳回或浪费额度；同时也使 §10.10/§11.2 这类逐码表不可复算——读者无从判断表里的数字是否按同一口径得出。反过来说，这也是「数字必须由拥有它的命令打印」这条纪律的又一例证：报告可以打印结论，但结论背后的可复算明细必须能一键复制。

## 根因

报告层的抽象层级选错了：打印的是**经过规则聚合后的判定**（是否达标），而操作者需要的是**该判定的输入**（每码 分子/分母）。把 `states_per_code` 算对但没有打印，等于让消费者去重建一个已经存在的中间结构；重建时必然重新实现口径，而口径的每一处都驻留在不同函数里、都是不平凡的。结构性修法：让打印器输出与内部结构同构的明细行（已做），并在记录里明写「不要手工誊抄，从此处复制」——使下一次修订不必再重现第二次推导。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
