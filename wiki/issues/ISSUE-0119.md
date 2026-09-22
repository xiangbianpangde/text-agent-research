---
id: "ISSUE-0119"
title: "attestation atomic writer follows a symlinked parent directory and writes outside the package"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "attestation_atomic_write_parent_symlink_escape,dirfd_anchor_follows_symlink"
  - "independently_reproduced_by_me_atomic_write_escaped_package_via_symlinked_parent"
evidence: "v77 archive 7de9414fa01dfac284c029bc37aad9f004bbc04f8b02578bd8c500294de20e04; /tmp/r62_v77_atomic_writer_symlink_probe.out; tools/refresh_attestation.py:atomic_write lines 36-64"
related:
  - "ISSUE-0104"
fix_ref: null
summary: "atomic_write opens path.parent by string with O_DIRECTORY but without componentwise O_NOFOLLOW, so an attestations symlink redirects the replacement outside the package"
updated_at: "2026-09-22"
---

## 现象

With review_v77/attestations replaced by a symlink to an external directory, atomic_write(review_v77/attestations/M1_worker_protocol_attestation.json, payload) returns successfully and modifies the external target.

## 复现

Move attestations/ aside, symlink review_v77/attestations to the outside directory, then call tools.refresh_attestation.atomic_write on the apparent package self-path; inspect the outside file bytes.

## 影响

The claimed atomic writer is not package-anchored: a redirected parent lets refresh mutate an external trust-anchor file while reporting success. Verification later refuses the symlink, but the write itself violates containment and can damage an external file.

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-22T21:42:15+0800

INDEPENDENT REPRODUCTION (mine, 2026-09-22), confirming the reviewer's HIGH finding. Setup: isolated copy of the package; renamed attestations/ to attestations_real/ and replaced it with a SYMLINK to an outside directory /private/tmp/v0119/OUTSIDE. Then called refresh_attestation.atomic_write on the reserved self-path. Result: 'wrote through symlink WITHOUT refusal: True' and the outside target file was actually created -- the write ESCAPED the package root with no refusal. Then removed the redirected artifact and restored the directory. This is a trust-boundary escape, not a style issue: the attestation is the artifact a reviewer trusts, and it can be redirected to an attacker-chosen path outside the package by a symlinked parent component. Note the contrast with the READ path, which is already hardened: attestation_policy.read_verified walks keys componentwise from a root fd with O_NOFOLLOW (ISSUE-0082) -- the WRITE path never received the equivalent treatment. Remedy confirmed as stated: dirfd + componentwise NOFOLLOW on the write path, plus an escape test.
