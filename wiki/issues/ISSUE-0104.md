---
id: "ISSUE-0104"
title: "v74 attestation verifier follows symlinked reserved self file"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "attestation_reserved_self_path_symlink_follow"
evidence: "commit 8296dd5530600fd0554f6b4d68c5707b87851932; /tmp/r60_v74_attestation_self_symlink_probe.out SHA-256 8135ed9c68eeea1a457c003f44fa37ef98fdc741cf9d16fe28b178de9d0e209d; tools/attestation_policy.py:112 strict_json_load(root / ATTESTATION_RELPATH), verify() self path is excluded from artifact closure"
related: []
fix_ref: "120ac20"
summary: "v74 attestation verifier follows symlinked reserved self file"
updated_at: "2026-09-22"
---

## 现象

把 attestations/M1_worker_protocol_attestation.json 替换为指向 package 外部副本的 symlink 后，archive-mode `--expected-required-set-digest sha256:a855...` 仍返回 rc=0；reserved self path 未经 O_NOFOLLOW/read_verified 校验，外部 JSON 可作为 attestation 真源。

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

## 处置记录 2026-09-22T19:14:41+0800

v75 复核仍通过：archive attestation self file 替换为外部 symlink 后，--expected-required-set-digest sha256:82da... 返回 rc=0；证据 /tmp/r61_v75_attestation_self_symlink_probe.out SHA-256 f9eb6bcbb803e35726c0239bacb306a1c7e080d0ca6ab89f402e0ae8e9675773。

## 处置记录 2026-09-22T19:47:29+0800

Refused against the shipped archive (review_v77). strict_json_load() -- which loads the TRUST ANCHOR -- used plain Path.read_text(), which follows symlinks, even though attestation_policy's own module header forbids exactly that. The anchor is now read through the same O_NOFOLLOW/read_verified path as every other file, and a symlinked self-path is refused by name. No digest could ever have caught this: the anchor's own bytes are excluded from artifacts as the reserved self-path, so only refusing the link helps. The refusal message says REFUSED, not missing, since a reviewer reads it first.
