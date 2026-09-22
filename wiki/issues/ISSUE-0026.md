---
id: "ISSUE-0026"
title: "v61 raw retention manifest collapses identical CAS blobs across systems"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "retention_provenance_collision,raw_manifest_noninjective"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/campaign.py:60-103; /tmp/r48_v61_retention_collision.out"
related: []
fix_ref: null
summary: "v61 raw retention manifest collapses identical CAS blobs across systems"
updated_at: "2026-09-17"
---

## 现象

when A and B CAS contain the same digest, manifest.blobs has one entry and records only system='B'; the A source attribution is overwritten, so digest references are not injectively bound to all producer/system contexts.

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

## 处置记录 2026-09-17T16:28:05+0800

Round 51/v64 retention collision repro: /tmp/r51_v64_retention_collision_probe.out (SHA-256 325aafe23398cc0ce7019113f445566f3ec6046ad54c605f7912755ad5b3af0f) created identical CAS content for systems A/B; raw_manifest.json contained one blob record with system=B, overwriting A attribution. Digest-only blob keys are not injective provenance.
