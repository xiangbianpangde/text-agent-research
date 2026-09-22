---
id: "ISSUE-0035"
title: "v62 semantic conformance validator crashes on schema-invalid types"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "v71_validator_type_crash"
  - "validator_type_crash,fail_closed_exception_path"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; contracts/conformance.py:77-115; /tmp/r49_v62_validator_crash_probe.out"
related: []
fix_ref: null
summary: "v62 semantic conformance validator crashes on schema-invalid types"
updated_at: "2026-09-18"
---

## 现象

validate_record() raises AttributeError/TypeError instead of returning validation errors for malformed answer, retrieval path, score, or line fields. A caller that expects fail-closed diagnostics can crash before recording a bounded invalid result.

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

## 处置记录 2026-09-17T16:35:03+0800

Round 51/v64 validator repro remains open: /tmp/r51_v64_validator_probe.out (SHA-256 1e653983d17f90eefb32cb5cb83c2534397525c2b5b6aec9187b52fbdcf2e9e1) raises TypeError for a string score/line and AttributeError for non-string edge sources instead of returning structured validation errors. This is fail-closed by crash, not a valid validator contract.

## 处置记录 2026-09-18T08:29:18+0800

v71 clean-room validator probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9 remains crash-prone: answer int -> AttributeError, string line_start -> TypeError, string score -> TypeError, None path -> AttributeError, None edge source -> AttributeError. Evidence /tmp/r56_v71_validator_crash_probe.out SHA-256 47458f9e5630f3b63618cef2ed3a679e86dad60fafa2a71572ec2dc3acf6f367. Schema-invalid input causes exceptions rather than structured fail-closed diagnostics; callers can lose the required failure envelope.
