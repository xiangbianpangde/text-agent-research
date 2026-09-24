---
id: "ISSUE-0176"
title: "沙箱 deny 列表按本仓库路径枚举，但答案键在第二棵树（兄弟仓库及其 wiki）里同样可读：封住一扇门不等于封住答案"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "answer_key_duplicated_in_sibling_tree"
  - "answer_key_present_in_uncovered_benchmark_worktree"
  - "containment_defeated_by_copy"
  - "deny_list_repo_scoped"
  - "same_file_present_in_two_trees"
  - "sandbox_scoped_to_one_checkout"
evidence: "catalog/test/trigger.ts gradingDenyProfile(repoRoot=REPO_ROOT) 的 profile 中全部 subpath 均以本仓库根为前缀，故只拒绝对 researchctl-product 的读取。实测（sandbox-exec -f <profile> 复算，/tmp/leak2.mjs）：沙箱内 grep -rn 'SEMANTIC_INDEX_CORRUPT' '~/Projects/文字Agent检索系统/wiki' 返回 wiki/logs.md 命中；grep -c 'SEMANTIC_INDEX_STALE' '~/Projects/文字Agent检索系统/docs/specs/'*.md 返回 2；grep -c '文字Agent检索系统' <profile> 返回 0（该树根本不在 deny 范围内）。决定性证据：docs/specs/超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench).md 在两棵树中都存在且大小完全相同（55913 字节），即本仓库内被拒绝的那份答案键，在兄弟树里有内容相同的副本。已发生的泄漏：本次授权 4 个回合中 rec-stale-untracked-probe-root call#26 'cat ~/Projects/文字Agent检索系统/wiki/issues/ISSUE-0148.md' 成功返回（写有 drift 注入机制与层判别链）；rec-semantic-document-added call#38 成功返回 ISSUE-0167（写有 observable_codes 判据与场景→码映射）。两者均为真实成功的读取，不是被拒绝的尝试。"
related:
  - "ISSUE-0171"
  - "ISSUE-0174"
  - "ISSUE-0175"
fix_ref: null
summary: "沙箱 deny 列表按本仓库路径枚举，但答案键在第二棵树（兄弟仓库及其 wiki）里同样可读：封住一扇门不等于封住答案"
updated_at: "2026-09-24"
---

## 现象

被测子进程能读到另一棵仓库树，那棵树内有同一份 Benchmark 方案（含期望错误码表）与本仓库 wiki（含场景 id、期望码、判据与注入机制）。故『判分设计对子进程不可读』这一断言为假，且与首轮（ISSUE-0174，deny 漏 docs/specs）同类：不是沙箱没生效，而是列表没有穷尽答案的可达副本。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

readGradingDesign 只匹配本仓库路径模式，故对兄弟树的成功读取不计为 taint：回合可读到答案却被判为干净 PASS，方向是虚高（与 ISSUE-0175 的虚低相反，两个方向都错）。本次 4 个回合中 2 个存在真实泄漏（1 个仍被声明为干净 PASS，1 个已因超时出局），故 tool-recoverable 23/24=95.8% 与 §10.9 的逐码读数建立在含污染的观测上，必须重算。

## 根因

deny 列表把『答案在哪里』当成『本仓库内的路径』这一有限集合，而答案的可达性是文件系统的性质：同一份规格被复制到另一棵树，枚举式封堵就整体失效。readGradingDesign 的判分路径模式同样只按本仓库路径书写，使该泄漏在分类层不可见。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

fix-ref: c3aebde 记录了 digest，但列表本身未覆盖兄弟树

## 处置记录 2026-09-24T00:55:07+0800

2026-09-23（独立复核 product worktree 2a619ac）：新增第三棵可读 worktree `/Users/xbpd/Projects/benchmark` 未包含在 `catalog/test/trigger.ts:answerKeyRoots()`；当前 sandbox preflight 报 `8 roots denied`，未 probe 该根。`catalog/test/recovery.test.ts:1276-1290` 的 filesystem scan 只用 `needle = "expects_code"`，因此漏检该树直接写明映射/码义的文件：`/Users/xbpd/Projects/benchmark/docs/contracts/P1-C-Contract.md:140-141`（SEMANTIC_INDEX_CORRUPT/STALE）；`docs/specs/超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench).md:747-751,804-808`（期望码表）。`rg -n -F` 在该未被 deny 的 worktree 命中这些内容；故当前 deny/扫描闭集仍不完整，clean rerun 暂不可执行。回归要求：测试从源码特征扫描而非单一内部标记，并对该 worktree 的实际读取执行 sandbox probe / deny。

## 处置记录 2026-09-24T00:56:03+0800

闭合验证：在 product worktree 运行 `node --import ./session-retrieval/test/typebox-register.mjs --input-type=module -e 'import { spawnSync } from "node:child_process"; import { gradingProfilePath } from "./catalog/test/trigger.ts"; const p="/Users/xbpd/Projects/benchmark/docs/contracts/P1-C-Contract.md"; const r=spawnSync("/usr/bin/sandbox-exec",["-f",gradingProfilePath(),"/bin/sh","-c",`grep -n -m 1 SEMANTIC_INDEX_CORRUPT "${p}"`],{encoding:"utf8"}); console.log(r.status,r.stdout,r.stderr);'`，结果 `status=0` 且返回 `140: 任一失败 → SEMANTIC_INDEX_CORRUPT`。这是用当前 c5ac02997503199a profile 对 grading child 的直接读取，不是仅从未沙箱化 grep 推断。
