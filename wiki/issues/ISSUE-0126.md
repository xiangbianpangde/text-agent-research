---
id: "ISSUE-0126"
title: "trace 与 attestation 缺少终止语义字段：336 个 attempt 全为 exit_code=0 却无任何字段断言 worker 按冻结协议终止"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "no_terminal_semantics_field_in_trace_or_attestation"
  - "reviewer_accepted_sharpened_wording_2026-09-22"
evidence: "archive SHA 7de9414fa01dfac284c029bc37aad9f004bbc04f8b02578bd8c500294de20e04; 我的独立检查（隔离副本 results/traces/TRACE-20260922T100808Z-5b03bd6e/）: grep -c terminal|terminal_status|terminal_response|final_status in TRACE_MANIFEST.json = 0 且 in events.jsonl = 0; record_counts = {evaluator_envelope:336, lifecycle_event:32, participant_response:336, query_request:368}; 全部 336 个 evaluator_envelope 的 exit_code 分布 {0:336}、schema_valid 分布 {True:336}; TRACE_MANIFEST 有 status=COMPLETE、attempt_count=336、atomic_manifest_commit=True; 32 个 lifecycle_event 的 payload 是语料变更事件（event_type=definition_revision 等），非 worker 终态"
related: []
fix_ref: null
summary: "trace 与 attestation 缺少终止语义字段：336 个 attempt 全为 exit_code=0 却无任何字段断言 worker 按冻结协议终止"
updated_at: "2026-09-22"
---

## 现象

COMPLETE 只证明 marker 存在与计数自洽；没有任何字段断言 worker 已按冻结协议终止、Host 已收齐最终结果，也没有 failure/timeout 终态记录。评审者据此判定「0 个可接受终端记录」并列为发布阻断。注意措辞须精确：并非「没有任何记录」——成功路径证据丰富（336 个 envelope 全部 exit_code=0 且 schema_valid=True，且 cardinality 闭合），缺的是**终止语义**字段与失败/超时终态。

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

## 处置记录 2026-09-22T21:42:26+0800

ORIGIN AND SCOPE OF THIS REGISTRATION. I registered this after independently verifying a finding in the reviewer's NO-GO adjudication (/private/tmp/M1_P4A_ROUND52_ADJUDICATION.md, section 'TERMINAL RECORD GAP'), because it was a confirmed release blocker with no existing issue page -- my earlier greps for 'terminal' in wiki/issues/ matched unrelated issues (0018/0020/0056/0064/0065). The reviewer's claim as written is '0 acceptable terminal records'. My independent verification CONFIRMS the gap but sharpens the wording, and the sharpening matters for whoever fixes it: the trace is NOT short of success evidence. It has TRACE_MANIFEST.status=COMPLETE, attempt_count=336, full record_counts, atomic_manifest_commit=True, and all 336 evaluator_envelope records carry exit_code=0 and schema_valid=True with cardinality closure. What is absent is any field asserting TERMINATION SEMANTICS -- terminal / terminal_status / terminal_response / final_status all return grep count 0 in both TRACE_MANIFEST.json and events.jsonl -- and there are no failure or timeout terminal records at all. So the correct statement of the defect is 'the trace records success outcomes but cannot express or attest a terminal protocol state, and has no failure/timeout terminal path', not 'nothing is recorded'. Consequence for remediation (the reviewer's 'Top-up condition'): a fresh archive must write and independently verify terminal records, marker binding, cardinality, hashes, and failure/timeout terminal states, then re-run the archive-mode audit. Not fixable inside the frozen v77; requires a new version.

## 处置记录 2026-09-22T21:49:07+0800

复核者裁定（2026-09-22 13:48Z，intercom seq 12）接受本 issue 的精确表述：『成功证据完整，但无 terminal 语义字段 / 失败超时终态』。即原判『0 acceptable terminal records』已按此措辞收敛，不再表述为『没有任何记录』。补齐条件仍为：在 fresh archive 中写入并独立校验 terminal records、marker binding、cardinality、hash 与 failure/timeout 终态，再重跑 archive-mode audit。v77 内不可修复。
