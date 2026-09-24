---
id: "ISSUE-0167"
title: "场景按『声明的 failing_call 产出声明码』自证，但模型可经 §4.3 的另一入口观测到同一状态并被判 unjudged"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "scenario_self_certification_single_entry,sibling_code_rejected_as_unjudged,entry_point_punished"
evidence: "场景接口把 expects_code 与 failing_call 绑定，assertScenarioAchievable 也只在 failing_call 这一个入口断言。但合同 §4.3 明说同一棵漂移树 query 报 INDEX_STALE、reconcile 报 DRIFT_DETECTED，§4.9 又说同一处损坏随是否重建索引换码——即一个场景在自然界里对应的不是一个码而是一个码集。实测（seedAll 后按多入口取样）：rec-stale-untracked-probe-organized / rec-stale-organized-doc-edited / rec-stale-organized-doc-removed 的树在 query 报 INDEX_STALE、在 reconcile 报 DRIFT_DETECTED；rec-semantic-index-dir-absent 的树在 query 报 INDEX_STALE、在 semantic 入口报 SEMANTIC_NOT_INDEXED。模型正是从另一入口观测的：前三个回合里出现的是 research_integrity[DRIFT_DETECTED]，第四个是 research_query[INDEX_STALE]。判据只认声明码，于是这 4 个回合被判『met X but never Y』=unjudged——罚的是模型选了哪个入口，不是它有没有恢复。修法：judgeRecovery 接受 observable_codes（该树在各合法入口实测产出的码集，由 observableCodesFor 跑真实 CLI 求得，不手写映射），任一成员出现即满足场景不变量；声明码仍优先锚定链路。已在实跑前记录进结果行（模型修好树之后再算会采到已修复状态，静默把可接受码集缩成空集）。修正后 4 个场景全部可判（24/26），且新判出的 2 个 FAIL 经逐条复核为真实失败（模型未按路径恢复），不是放宽判据导致的。"
related: []
fix_ref: null
summary: "场景按『声明的 failing_call 产出声明码』自证，但模型可经 §4.3 的另一入口观测到同一状态并被判 unjudged"
---

## 现象

场景不变量用单一入口自证，而模型可以用同样合法的另一入口看到同一状态；判据于是把『走了另一扇门』记成『条件从未出现』，读数偏差方向是系统性偏低

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
