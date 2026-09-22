---
id: "ISSUE-0116"
title: "bench 归档在无 git 环境下 pytest 报 3 failed/12 errors：git 依赖测试用 check=True 直接抛错而非 skip"
status: "fixed"
severity: "medium"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "archive_pytest_git_dependent_errors,test_prerequisite_as_failure,false_suite_verdict"
evidence: "reviewer R61: /tmp/r61_v75_archive_pytest.out SHA f94fd835 (210 passed/3 failed/12 errors in the extracted archive) vs /tmp/r61_v75_target_pytest.out SHA 52cd49bb (225 passed in the clean worktree); failure trace: subprocess.CalledProcessError ['git','-C','/private/tmp/rev/review_v76','rev-parse','--show-prefix'] rc=128 from tests/security/test_canonical_trace_loader.py:29-34 check=True"
related: []
fix_ref: "468d9fc0"
summary: "bench 归档在无 git 环境下 pytest 报 3 failed/12 errors：git 依赖测试用 check=True 直接抛错而非 skip"
updated_at: "2026-09-22"
---

## 现象

提取归档没有 .git，所以从 git tree 推导 required set 的测试无法运行。这些测试用 check=True 的 subprocess 调用，于是抛 CalledProcessError，归档套件被读成 broken 而不是 prerequisites unmet，从而任何 225 passed 的说法对归档都是假的。修复为显式检测仓库缺失并 skip 并给出原因：归档现为 221 passed / 23 skipped / 0 failed / 0 errors，worktree 内 0 skip 且覆盖不变。

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

## 处置记录 2026-09-22T19:47:41+0800

Fixed: git-dependent tests now detect the missing repository and SKIP with a reason instead of raising CalledProcessError. Verified by running the shipped archive: 221 passed / 23 skipped / 0 failed / 0 errors (was 210 passed / 3 failed / 12 errors). The closure audit's submitted_pytest_suite_passes check went from FAIL to PASS in-archive for the first time, with zero newly-failing checks vs the v74 baseline. In the worktree, zero tests skip, so the binding coverage is unchanged where it is actually observable. Implemented via a GitUnavailable exception + _require_git() helper in test_canonical_trace_loader.py and an AttestationError guard in the two worker_isolation attestation tests.
