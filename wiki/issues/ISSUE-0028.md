---
id: "ISSUE-0028"
title: "v62 JSONL tail repair deletes a complete final record lacking newline"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "jsonl_repair_data_loss,tail_recovery_heuristic"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/campaign.py:54-79; /tmp/r49_v62_tail_complete_loss.out"
related: []
fix_ref: null
summary: "v62 JSONL tail repair deletes a complete final record lacking newline"
updated_at: "2026-09-16"
---

## 现象

events.jsonl containing valid records {"a":1}\n{"b":2} (no final newline) is treated as partial; _repair_jsonl_tail() truncates the complete second record, leaving only one record. Tail repair cannot distinguish incomplete JSON from a complete record without newline.

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

## 处置记录 2026-09-16T15:47:01+0800

v62 confirms valid final record without newline is still deleted (before two records, after only first: /tmp/r49_v62_tail_complete_loss.out). Malformed newline-terminated tail is also preserved rather than parsed/reconciled (/tmp/r49_v62_event_malformed_tail_probe.out).
