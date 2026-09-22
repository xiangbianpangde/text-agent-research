---
id: "ISSUE-0034"
title: "v62 telemetry sampler exceptions are swallowed on successful attempts"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "telemetry_fail_open,sampler_exception_swallow"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/worker_supervisor.py:380-385; /tmp/r49_v62_sampler_failure_probe.out"
related: []
fix_ref: null
summary: "v62 telemetry sampler exceptions are swallowed on successful attempts"
---

## 现象

on_poll wraps _sample_telemetry() in bare except and continues. Simulated unavailable sampler still yields response=true, schema_valid=true, exit=0, no invalidation; exact per-attempt resource proof is silently absent.

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
