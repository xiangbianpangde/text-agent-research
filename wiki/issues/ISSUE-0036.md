---
id: "ISSUE-0036"
title: "v62 JSONL restart repair does not validate malformed newline-terminated records"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "jsonl_malformed_tail_persist,crash_recovery_validation"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/campaign.py:43-65; /tmp/r49_v62_event_malformed_tail_probe.out"
related: []
fix_ref: null
summary: "v62 JSONL restart repair does not validate malformed newline-terminated records"
updated_at: "2026-09-17"
---

## 现象

_repair_jsonl_tail() returns immediately whenever events.jsonl ends with newline, preserving malformed complete-looking tail records (NOT-JSON) and truncated records with a newline. Restart then appends after invalid history rather than reconciling/failing closed.

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

## 处置记录 2026-09-17T16:35:13+0800

Round 51/v64 tail probe remains open: /tmp/r51_v64_tail_probe.out (SHA-256 540bff75ba7b9b175df32690ff7bdd2bc222eeccc7956b23ddc4acbbd92e2200) drops a complete no-newline final record, preserves malformed newline-terminated tail text, and truncates malformed no-newline tail. Restart repair still has data-loss and malformed-record acceptance paths.
