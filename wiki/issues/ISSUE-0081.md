---
id: "ISSUE-0081"
title: "v71 sandbox sensitive-pattern purge chmods external symlink targets before unlinking the link"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "symlink_nofollow_purge,external_target_mutation,cleanup_toc_tou"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9 (unchanged at HEAD 3eb82461f2f9fe0dd4eb68c889fd7f431d5fbace); research-retrieval-benchmark/runner/sandbox_launcher.py:474-488 and 509-518; /tmp/r56_v71_sandbox_symlink_chmod_probe.out SHA-256 edb560d2ee41be0f1ce6238252cc8e81651644d8f1e586cd0de3dfdefa99244b"
related: []
fix_ref: null
summary: "v71 sandbox sensitive-pattern purge chmods external symlink targets before unlinking the link"
---

## 现象

_force_remove() calls os.chmod(target, 0o600) even when target is a symlink. On macOS the chmod follows the link: an external target changed from mode 0o700 to 0o600, then the symlink was removed. Cleanup must use no-follow descriptor operations and never mutate external targets.

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
