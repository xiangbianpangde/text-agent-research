---
id: "ISSUE-0105"
title: "v74 attestation source binding remains on parent commit instead of reviewed archive commit"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "attestation_source_binding_parent_commit"
evidence: "archive c429cabecffabed6806aefb3844e73beb14fa78585b4f0057a010548a0b2e390; attestation source_commit=74df6e495d073f5c9f01e3fbffc02d65928ca508/source_tree=a3a4e8c6...; reviewed target=8296dd5530600fd0554f6b4d68c5707b87851932/root tree=f5546d9b...; clean target worktree command output /tmp/r60_v74_attestation_require_target_clean.out SHA-256 947da65142c89c61a25e1a77c10c7cd01f5cb7f296c8c728753e1a4b929eee13"
related: []
fix_ref: "120ac20"
summary: "v74 attestation source binding remains on parent commit instead of reviewed archive commit"
updated_at: "2026-09-22"
---

## 现象

archive attestation's required-set digest is correct, but strict verification with --commit/--require-commit reviewed target fails SOURCE_TREE because the map binds parent 74df rather than target 8296; offline expected-digest mode does not enforce exact source commit/tree.

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

## 处置记录 2026-09-22T19:28:11+0800

v75 复核：attestation source_commit=4d422f0ed524.../source_tree=aa3977...，target=6adead094236.../root tree=4591807...；clean target worktree 用 `--commit 6ade... --require-commit 6ade...` 返回 SOURCE_TREE mismatch。证据 /tmp/r61_v75_attestation_require_target_clean.out SHA-256 3fafcd355c1ab4873309b2f509d2a76aa2eba7c553d1ea0f1eaf09e82cd67c2f。仅使用 `--require-commit`（不强制 `--commit`）时现有 self-path exception 可通过，故该发现取决于审计是否要求 exact reviewed commit/tree。

## 处置记录 2026-09-22T19:47:29+0800

With independent pins supplied (--expected-source-commit/--expected-source-tree) the forged binding is now REFUSED: 'SOURCE_COMMIT: declared 74df6e49... != independently expected ...'. Without pins, archive mode emits SOURCE_COMMIT_UNVERIFIED / SOURCE_TREE_UNVERIFIED as NOTICES on stderr while problems stay empty, so a git-less consumer cannot read 'verified' as covering the commit attribution, and is not broken by a missing repository either (the ISSUE-0108 failure mode). verify() keeps its problems-only signature so existing callers are unaffected; the new two-axis API is verify_detailed().

## 处置记录 2026-09-22T20:51:35+0800

v77 exact-target recheck: archive 7de9414fa01dfac284c029bc37aad9f004bbc04f8b02578bd8c500294de20e04 targets 468d9fc0fd00c96063596e03969695a80a3c709f (root tree 753db32618061720a4f350dfb72828812eb8a538), but the attestation declares parent adf16ffc902fd7562073f3661b3ef619613e7873/tree c9bbc8c143e5d87b803bc3163f96ee45f992a0e5. Independent expected_source_commit/tree verification refuses both SOURCE_COMMIT and SOURCE_TREE. Evidence /tmp/r62_v77_attestation_target_pin.out SHA-256 889185c98974bb19d635501935101e02cb688211b342411852a15b93bb8016a8.
