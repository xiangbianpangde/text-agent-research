---
id: "ISSUE-0179"
title: "同类错误第三次：答案键在第三棵 git worktree（/Users/xbpd/Projects/benchmark）中可读，且文件系统扫描器的 needle 搜的是格式标签而非答案内容"
status: "fixed"
severity: "critical"
area: "researchctl"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "hand_written_deny_list_incomplete third_worktree_uncovered worktree_not_discovered needle_matches_label_not_content scanner_green_while_leaking control_states_its_own_answer"
  - "tilde_alias_not_matched_by_discovered_root_pattern"
evidence: "实测：第三棵 worktree `/Users/xbpd/Projects/benchmark`（`git -C researchctl-product worktree list` 显示该仓共 3 棵：文字Agent检索系统[main]、benchmark、researchctl-product）。用当时 profile（SHA c5ac02997503199a）直接 `sandbox-exec -f <profile> /bin/sh -c 'cat /Users/xbpd/Projects/benchmark/docs/contracts/P1-C-Contract.md'` → **rc=0，31566 字节**；`grep -c SEMANTIC_INDEX_CORRUPT` → 命中 140/144/344 行。对照组同一 profile：本仓库 catalog/test/recovery.ts rc=1（Operation not permitted）、兄弟仓库 rc=1。即『8 roots denied』为真而隔离为假。扫描器盲点实测：旧 needle `expects_code` 在第三棵树中出现 **0** 次，而该树中错误码出现 13 次——搜的是场景表的**格式标签**而非**答案内容**。修复后：answerKeyRoots 由 `git worktree list` 发现（不再手写），同仓 worktree 一律整棵 deny；新增测试 'denies every worktree git knows about' 与改写后的文件系统扫描测试；变异测试三项目均被捕获：移除 worktree 发现 → 测试 4/5 失败；把 needle 改回 expects_code → 测试 4 失败；把兄弟树改为按 grading path deny → 测试 5 失败。per-worktree preflight 探针改为遍历**每一个**发现的 worktree（探针此前只点名已泄漏的那一棵，故新树从未被尝试）。"
related:
  - "ISSUE-0174"
  - "ISSUE-0176"
  - "ISSUE-0178"
fix_ref: "c30ae59"
summary: "同类错误第三次：答案键在第三棵 git worktree（/Users/xbpd/Projects/benchmark）中可读，且文件系统扫描器的 needle 搜的是格式标签而非答案内容"
updated_at: "2026-09-24"
---

## 现象

preflight 报『9 roots denied / All preconditions hold』且 test:catalog 全绿，但沙箱内仍能读到写有全部答案码的合同文件。护栏连续三次（0174 docs/specs、0176 兄弟仓、0179 第三棵 worktree）在『看起来完整』的手写清单上失效；扫描器连续两次搜错了目标。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

评分回合可在『已遏制』读数下读到答案键，使 5-state 底线与 stratum 率均为不可信读数——这正是 G3 层门禁要判的东西。更广的教训：手写清单的缺失项与完整项外观相同，故清单的完备性不能靠人复核，只能靠发现机制 + 变异测试。

## 根因

两层原因。(1) 隔离清单手写枚举，遗漏一棵从未被尝试过的树——preflight 探针此前只点名已经泄漏过的那一棵，所以新树天然不被测。(2) 文件系统扫描器的 needle 用场景表的格式标签（expects_code）而非答案内容（场景→码的映射）；标签在泄漏树中出现 0 次，答案出现 13 次，于是扫描通过。二者同族：判据测的是『我有没有看』而不是『东西在不在』。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-24T09:55:44+0800

独立审查 HEAD 64f076d 与其工作树中的未提交 `catalog/test/recovery.ts` 变更时发现：动态根模式只匹配 `answerKeyRoots()` 的绝对路径。对 `readGradingDesign` 做无模型合成观测，结果为 `{absolutePathTainted:true, tildePathTainted:false}`，其中两条调用分别是 `cat /Users/xbpd/Projects/benchmark/docs/contracts/P1-C-Contract.md` 与 `cat ~/Projects/benchmark/docs/contracts/P1-C-Contract.md`，且传 `sandboxed=false` 以判定历史未遏制行。现有显式别名 `/文字Agent检索系统/` 只覆盖日文主仓，未覆盖 `~/Projects/benchmark`。因此历史行若用 tilde 别名读取第三棵树，动态发现的根模式仍可能漏判 TAINTED；需对每个 root 生成/规范化 shell 别名并加回归测试。

## 处置记录 2026-09-24T10:01:30+0800

裁决方补充的 tilde 别名盲点已修： 现对每个发现根同时生成绝对形式与  形式（分隔符接受 / 与 \\），因为同一行记录里两种写法并存且 shell 更常写波浪号形式。裁决方的合成探针实测由 absolute=true/tilde=false 变为 absolute=true/tilde=true，覆盖全部 3 棵 worktree × 2 种写法。变异验证：删掉 tilde 分支 → 测试 'counts a call naming a discovered worktree as a read' 失败。

## 处置记录 2026-09-24T10:01:34+0800

裁决方补充的 tilde 别名盲点已修（commit c30ae59）：discoveredGradingRootPatterns() 现对每个发现的根同时生成**绝对形式**与**波浪号形式**（`~/...`，分隔符接受正斜杠与反斜杠），因为同一行记录里两种写法并存，且 shell 更常写波浪号形式。裁决方的合成探针实测由 absolute=true / tilde=false 变为 **absolute=true / tilde=true**，并覆盖全部 3 棵 worktree × 2 种写法（含 path 参数路由）。变异验证：删掉 tilde 分支 → 测试 'counts a call naming a discovered worktree as a read' 失败。
