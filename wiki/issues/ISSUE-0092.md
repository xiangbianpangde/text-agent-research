---
id: "ISSUE-0092"
title: "v73 attestation untracked-file scan drops package-subdirectory paths"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "attestation_untracked_subdir_rebase_bypass"
  - "git_pathspec_cwd_relative_silent_zero_recurred_in_manual_use"
evidence: "commit 19dff4ffb65039f30f2d85664928fa62445442d8; tools/attestation_policy.py:235-245; /tmp/r59_v73_untracked_prefix_probe.out SHA-256 c87a5c40feccd3d8010073878af107a3b79befee1690065a58f0d1ff4936e6c8"
related: []
fix_ref: "15dc0b9"
summary: "v73 attestation untracked-file scan drops package-subdirectory paths"
updated_at: "2026-09-22"
---

## 现象

git -C package ls-files --others returns a package-relative untracked file, but _rebase requires the repository prefix and returns an empty set; refresh/verify can accept an untracked file at package root.

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

## 处置记录 2026-09-22T18:18:27+0800

Reproduced locally and fixed: git ls-files --others prints CWD-relative paths, so the rebasing step matched nothing and returned an EMPTY set -- every untracked file under the package root was invisible to refresh AND verify. Fixed with --full-name on both the untracked and ignored scans. Verified: a probe file at .r59_untracked_prefix_probe.py is now reported and refresh exits 2. Regression tests: test_untracked_scan_is_not_pathspec_relative, test_nested_untracked_file_is_reported, test_gitignored_path_is_still_excluded_from_untracked (49 pass).

## 处置记录 2026-09-22T21:09:38+0800

RECURRENCE of the same root cause in manual use, 2026-09-22. Your fix (--full-name on the untracked and ignored scans) is correct and still in place for the package's own scans; I am recording that the SAME class silently bit me while auditing by hand, so it belongs here as a known trap rather than as a new issue. Command: cd /Users/xbpd/Projects/benchmark/research-retrieval-benchmark && git ls-tree -r adf16ffc902f --name-only -- ':(literal):sol' -> 0 files, exit 0, NO warning. Same command from the repo top level /Users/xbpd/Projects/benchmark -> 54 files, including the M1_P4A gate instrument :sol/3/P0P1_CLOSURE_AUDIT.py, and git cat-file -e 'adf16ffc902f::sol/3/P0P1_CLOSURE_AUDIT.py' succeeds. I briefly concluded ':sol is untracked / the gate instrument does not exist' from that silent 0 and had to retract it (recorded in ISSUE-0120). Reading rule to carry forward: a silent 0 from git means 'not found HERE', never 'does not exist' -- re-run from the repository top level (or with --full-name / :(top)) before drawing any absence conclusion. This matters for review work because a wrong absence conclusion is exactly how a reviewer wrongly clears or wrongly condemns a delivery.
