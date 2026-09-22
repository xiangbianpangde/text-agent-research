---
id: "ISSUE-0088"
title: "根 .gitignore 的 fixture/ 模式同时吞掉 bench 公共根的实例 fixture，导致新 worktree 中 G01/负向控制/adapter 用例必然失败"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "gitignore_fixture_swallow,public_root_absent_in_worktree,env_dependent_test_failure"
evidence: "cwd=researchctl-product;command=git check-ignore -v bench/packs/p1_public_v1/instances/public/RCTL1-F01-public-0-e89f2df02194a718cc37cf7a/fixture/.auth/registry.yaml;stdout=.gitignore:25:fixture/ → 命中;command=PYTHONPATH=. python3 -m pytest bench/tests -q;stdout=6 failed, 146 passed (test_p0_1_scoring::test_researchctl_wrapper_emits_one_json_document, test_p0_2_adapter 2, test_p0_4_controls::test_attestation_is_bound_and_all_controls_are_rejected, test_p1_release::test_committed_public_root_rebuilds_byte_identically, test_p1a_gates::test_committed_public_root_byte_identical);command=same 10 tests in main worktree (文字Agent检索系统);stdout=10 passed → 证明是 worktree 环境性而非回归;verify_public_root → failures=1400 byte mismatch;committed public root tracked files=296 but instances/*/fixture/ untracked(.gitignore)"
related: []
fix_ref: null
summary: "根 .gitignore 的 fixture/ 模式同时吞掉 bench 公共根的实例 fixture，导致新 worktree 中 G01/负向控制/adapter 用例必然失败"
---

## 现象

main 工作区因磁盘上存在未跟踪的 bench/packs/p1_public_v1/instances/public/*/fixture/ 与根 fixture/ 而侥幸全绿；新建 git worktree 只检出已跟踪文件，这些目录不存在，于是公共根字节比对 1400 处失败、负向控制 attestation 失配、adapter/wrapper 用例取不到 fixture。产品分支不修 bench/，仅记录。

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
