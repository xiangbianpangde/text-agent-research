---
id: "ISSUE-0174"
title: "两个 floors 缺口场景的提示词用『相对上文的场景』描述状态：子进程没有那个上下文，只能去搜文件系统（6/6 全部 timeout）"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "prompt_references_sibling_scenario"
  - "dangling_reference_in_prompt"
  - "child_searches_filesystem_for_nonexistent_state"
  - "timeout_never_produced_verdict"
  - "floor_blocked_by_prompt_defect"
evidence: "catalog/test/recovery.ts:362 rec-semantic-rebuilt-before-p0 的 distinct_state='semantic rebuilt BEFORE P0 on a drifted tree — the repair order is wrong, so the mismatch is inverted relative to the cases above'；:464 rec-semantic-metadata-value-not-text 的 distinct_state='a metadata VALUE is stored as a non-text SQLite type, exercising the typeof check rather than the grammar'。promptOf() 直接把 distinct_state 插进提示词，故子进程读到『relative to the cases above』时没有任何上文。结果文件证据：这两个场景各有 3 行、全部 error='timeout after 240000ms'，judged=None —— 6/6 从未产出判决。搜索形态调用：rebuilt-before-p0 16 次调用中 8 次是 grep/find（含 ls -la /var/folders/.../m3-recovery-rec-semantic-rebuilt-before-p0-dApyMO/ 与 find / -name '*.sqlite*'）；metadata-value-not-text 含 find / -name '*.sqlite*' -not -path /System/*。横切统计：4 个 distinct_state 含装置内部指代（the cases above / scenario above / no other scenario / exercising the / rather than the grammar）的场景中，2 个 timeout、2 个无判决；另 35 个『平实描述』场景 0 个 timeout。"
related:
  - "ISSUE-0171"
fix_ref: null
summary: "两个 floors 缺口场景的提示词用『相对上文的场景』描述状态：子进程没有那个上下文，只能去搜文件系统（6/6 全部 timeout）"
---

## 现象

提示词把被测状态描述成『与上文那些场景相比』，但被测子进程只拿到这一个场景、没有上文，于是它无法判断自己该找什么，转而 grep 整个文件系统找线索，直到超时。这两个场景恰好是 §3.2 floors 的两个缺口。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

floors 缺口并非判据能力不足，而是装置缺陷：SEMANTIC_INDEX_STALE 与 SEMANTIC_INDEX_CORRUPT 各差 1 个样本，唯一缺的就是这两个场景，而它们 6/6 从未跑出结果。若不修提示词就重跑，是拿付费回合去撞一个已知会失败的提示词。

## 根因

distinct_state 同时承担两个职责：给人看的场景区分说明（可以引用兄弟场景）与给模型看的提示词（不得引用自身世界之外的东西）。promptOf() 把后者当前者使用。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
