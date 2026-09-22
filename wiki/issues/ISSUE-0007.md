---
id: "ISSUE-0007"
title: "bench/tests 有 4 个环境相关失败（基线即失败）"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-15"
discovered_by: "agent（ISSUE-0001 回归时发现）"
tags: []
signals:
  - ""
evidence: "python3 -m pytest bench/tests -q → 4 failed, 148 passed；test_p0_3_oracle::test_timeout_kills_participant_process_group、test_p0_4_controls::test_unicode_gold_path_is_blocked_by_os_sandbox、test_p1b_canary::test_all_16_blocked、test_p1b_canary::test_transcript_digest_matches_contract_formula；把本次 limit 改动 git stash 后同样 4 failed → 与本改动无关"
related: []
fix_ref: null
summary: "需要判定是沙箱/环境差异还是真实回归"
---

## 现象

本机跑 bench 套件固定有 4 个失败

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

无法用『pytest bench/tests 全绿』作为回归门禁，需人工区分环境性失败

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
