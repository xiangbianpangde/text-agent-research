---
id: "ISSUE-0157"
title: "语义索引恢复是两步且顺序敏感：P0 落后时 index --semantic 自身 fail-closed，而指引只说『run research_integrity (reconcile/index)』"
status: "open"
severity: "high"
area: "researchctl"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "recovery_sequence_order_dependent,index_semantic_refuses_when_p0_stale,guidance_omits_prerequisite_step,recovery_measured_as_guessing,base_index_not_fresh"
evidence: "P0 落后（内容改后仅重建语义）时 index --semantic → {status: fail_closed, error_semantic: INDEX_STALE, errors:[{code:INDEX_STALE, detail:'base index is not fresh'}]}, exit=0；改为 index 然后 index --semantic → query --semantic 返回 success。无 .index 目录时 index --semantic → exit=1, stderr='error: unable to open database file', stdout 空（无 envelope）。db 文件被删（目录在）与 db 为空文件时同样得 'base index is not fresh'。已登记 ISSUE-0156 的指引修正仅覆盖 semantic=true，不含顺序前置。"
related: []
fix_ref: null
summary: "语义索引恢复是两步且顺序敏感：P0 落后时 index --semantic 自身 fail-closed，而指引只说『run research_integrity (reconcile/index)』"
---

## 现象

语义类错误（SEMANTIC_INDEX_STALE / SEMANTIC_NOT_INDEXED）在 P0 索引落后时无法用 index --semantic 单步修复：该命令自身返回 fail_closed + INDEX_STALE（detail: 'base index is not fresh'），exit=0。实测正确顺序是**先 index 重建 P0，再 index --semantic**；顺序颠倒或只做后者均停在原错。更早的实测还发现反向顺序（先 --semantic 再 P0）同样无效。此外在 .index 目录完全不存在时，index --semantic 直接 exit=1 + stderr 'unable to open database file'（无 JSON envelope），即恢复动作本身会以非结构化方式失败。影响：catalog 给模型的 research_query 恢复指引原文只说『run research_integrity (reconcile/index)』，未提语义路径需要 semantic=true，更未提前置顺序；若按此口径测量 recovery，模型即便完全照做也无法恢复，测到的是『能否猜出指引没写的两步』而非『是否照建议恢复』。

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
