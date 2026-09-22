---
id: "ISSUE-0113"
title: "v75 archive-mode attestation completely skips conformance_corpus validation"
status: "fixed"
severity: "critical"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "attestation_archive_corpus_validation_bypass_v75"
evidence: "archive review_v75.zip SHA-256 69af7f75096a08df5c3620987be822357a0635718cbc2a2e59e5313b805ae259; commit 6adead09423679ee45e984b91b4480cb1bdf54f4; tools/attestation_policy.py:529-563 returns before corpus checks at 656-679; /tmp/r61_v75_archive_corpus_empty_probe.out SHA f9eb6bcbb803e35726c0239bacb306a1c7e080d0ca6ab89f402e0ae8e9675773; /tmp/r61_v75_archive_corpus_malformed_probe.out SHA f9eb6bcbb803e35726c0239bacb306a1c7e080d0ca6ab89f402e0ae8e9675773; /tmp/r61_v75_archive_corpus_extra_probe.out SHA f9eb6bcbb803e35726c0239bacb306a1c7e080d0ca6ab89f402e0ae8e9675773"
related: []
fix_ref: "41fe134"
summary: "v75 archive-mode attestation completely skips conformance_corpus validation"
updated_at: "2026-09-22"
---

## 现象

在 archive-mode expected required-set digest 校验中，将 conformance_corpus 分别改为空对象、数组或加入额外伪造 frame，命令均 rc=0、输出 1916 paths closed；archive 分支在 corpus set/digest 检查之前直接 return，corpus provenance 完全未验证。

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

## 处置记录 2026-09-22T19:47:24+0800

All three reviewer probes (corpus={}, corpus=[], forged extra frame) are now REFUSED against the shipped archive. Root cause: the archive branch ended in an early 'return problems, notices', so the entire conformance_corpus section at the end of verify() was unreachable in archive mode -- a mode-specific early return silently disabled a whole policy section. The corpus check is now a shared helper (_check_conformance_corpus) reached by BOTH modes: git blobs in-repo, the (already independently pinned) declared map in archive mode. Extracted rather than duplicated so the two modes cannot drift apart again. Regression tests: 3 parametrized archive cases + control (unmutated archive must still verify) + an in-repo forged-corpus guard to prove the extraction did not weaken the original path. Mutation (restoring the early return) fails all 3 archive cases while the control stays green.
