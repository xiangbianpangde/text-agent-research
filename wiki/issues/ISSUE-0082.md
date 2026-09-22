---
id: "ISSUE-0082"
title: "attestation freshness test accepts artifact/corpus paths outside the package root"
status: "verified"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "attestation_path_containment_bypass,attestation_external_target_hash"
  - "attestation_corpus_path_containment_bypass"
  - "attestation_symlink_component_bypass"
  - "attestation_archive_symlink_dir_omission"
evidence: "commit 3eb82461f2f9fe0dd4eb68c889fd7f431d5fbace; research-retrieval-benchmark/tests/security/test_worker_isolation.py:4482-4507; /tmp/r58_attestation_path_escape.out SHA-256 5c4648862754b9c9f8ed2c41e2ce5748ac68867bd5566e78f92e56f239647bb8; /tmp/r58_attestation_corpus_path_escape.out SHA-256 391e49ef0ae4bcf9b21c92b95b5a36ebde94a412d7428d54e9dbf95a09fe8b09; /tmp/r58_attestation_symlink_probes.out SHA-256 6f69c6926183dfc290e3d404d2dcd1058503a7fdb6934ea9705de178e02c999c; v73 archive-mode /tmp/r59_v73_archive_symlink_dir_probe.out SHA-256 752e2631251cc2b65b4869b8155a6ce2eca45393598f7bc5a2de4097a365b51b"
related: []
fix_ref: "15dc0b9"
summary: "attestation freshness test accepts artifact/corpus paths outside the package root"
updated_at: "2026-09-22"
---

## 现象

A crafted attestation artifact key ../r58_attest_escape_outside pointing outside the package, with a matching external-file digest, makes test_attestation_hashes_are_current pass; the checker uses pkg / rel and is_file/read_bytes without rejecting absolute or .. paths. The same bypass applies to conformance_corpus keys: ../../../../r58_corpus_escape_outside resolved outside the package and the freshness test still passed. The checker also follows symlinked artifact leaves, symlinked parent components, and symlinked corpus leaves; all three copied-package probes passed the freshness test. In v73 archive mode, an undeclared symlink directory containing an external file is omitted by os.walk(..., followlinks=False) from the `present` set; verification still returned success.

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

## 处置记录 2026-09-22T17:38:36+0800

attestation keys could escape the package via ../ and symlinks; now validated + O_NOFOLLOW

## 处置记录 2026-09-22T18:18:31+0800

R59 re-reported this against v73 even though I had marked it fixed, so I re-reproduced it: os.walk(followlinks=False) does NOT descend into a symlinked directory, so an undeclared symlink dir pointing outside the package was neither listed nor flagged and archive-mode verification PASSED. Fixed: every directory is now lstat'd and an undeclared symlink dir raises UNDECLARED_SYMLINK_DIR. Verified against the reviewer's own probe: a symlink to /tmp/r59_external now yields 'ATTESTATION VERIFY FAILED: UNDECLARED_SYMLINK_DIR'. Tests: test_archive_mode_rejects_undeclared_symlink_directory plus a clean-tree control (test_archive_mode_still_accepts_a_clean_tree).
