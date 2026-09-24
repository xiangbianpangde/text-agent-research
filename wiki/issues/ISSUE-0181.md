---
id: "ISSUE-0181"
title: "taint 检测器本身是手写清单，与被它审计的 deny 列表同源同类缺陷（第三处『枚举而非发现』）"
status: "open"
severity: "high"
area: "researchctl"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "hand_written_list_in_detector auditor_shares_defect_of_audited detector_drifts_from_containment latent_false_negative enumerate_instead_of_discover"
evidence: "commit 64f076d 修好 deny 列表（新增第三棵 worktree `/Users/xbpd/Projects/benchmark` 的 deny），但 `catalog/test/recovery.ts` 的 `GRADING_DESIGN_PATTERNS` 未同步。实测：`readGradingDesign([{args:{command:'cat /Users/xbpd/Projects/benchmark/docs/contracts/P1-C-Contract.md'}}])` 在修复前返回 **false**（判为干净）。修复后返回 true。现有语料影响实测为 **零**：4 条 `sandboxed=true` 行中命名 `/Users/xbpd/Projects/benchmark` 的次数均为 **0**，故读数仍为 22/23，缺口仍为 3 个码。变异测试：把检测器改回手写清单 → 新增测试 'counts a call naming a discovered worktree as a read' 失败。附带发现：把子串模式直接换成绝对根正则**会漏掉** `~/Projects/文字Agent检索系统/...` 的波浪号写法（同一行内两种写法并存），故改为叠加而非替换。test:catalog 215/215；commit 9cb3b17。"
related:
  - "ISSUE-0179"
  - "ISSUE-0176"
  - "ISSUE-0174"
  - "ISSUE-0175"
fix_ref: null
summary: "taint 检测器本身是手写清单，与被它审计的 deny 列表同源同类缺陷（第三处『枚举而非发现』）"
---

## 现象

隔离清单修好后，判定『这条读数算不算数』的检测器仍停留在旧的手写清单上。它没有导致今天的读数出错，但只要有一个回合提到第三棵树，同一条已判为干净的读数就会把『读过答案』记成『没读过』——而检测器是决定证据有效性的那一环，它的缺陷不会报错，只会让不合格证据看起来合格。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

这是同一缺陷族的第三处实例：deny 列表、文件系统扫描器、taint 检测器，三者都是手写枚举，且都在『补了其中一处』之后继续漏。真实教训是修复必须沿着**同一条发现链**贯穿所有消费方——只修被点名的那一处，等于把漏洞搬到下游。今天无影响不代表该修：它决定的是证据资格而非某个数字。

## 根因

修 0179 时只更新了 deny 列表（被裁决方点名的那一处），没有追踪『还有谁在枚举同一组根』。检测器与 deny 列表消费的是同一概念（答案可读位置），却各写一份清单，二者必然漂移。已改为由 `answerKeyRoots()` 单一发现派生。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
