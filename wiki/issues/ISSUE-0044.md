---
id: "ISSUE-0044"
title: "v62 missing workspace is represented by schema-valid zero tree digest"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "v71_workspace_tree_digest_omits_symlink_directories"
  - "workspace_identity_zero_sentinel,missing_workspace_fail_open"
evidence: "commit 0c62c0d5b7f12890590049fc686fb674fbf630a8; runner/worker_supervisor.py:720-727; /tmp/r49_v62_workspace_identity_probe.out"
related: []
fix_ref: null
summary: "v62 missing workspace is represented by schema-valid zero tree digest"
updated_at: "2026-09-18"
---

## 现象

After deleting the workspace after supervisor construction, a valid worker response is accepted with schema_valid=true and workspace_tree_digest=sha256:000...000. Missing snapshot identity is encoded as a valid sentinel instead of invalidating the attempt.

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

## 处置记录 2026-09-17T16:36:54+0800

Round 51/v64 static probe remains open: deleting/missing the workspace yields an envelope with workspace_tree_digest=sha256:6675043dce125cddd7fd383e56081294bb59fd2e413abd56e635d4ffd565687d, schema_valid=true, and no violations in the tested internal path; the broader _safe_workspace_digest() fallback still has a zero-digest identity sentinel. Missing workspace identity must fail closed, not be represented by a successful-looking digest.

## 处置记录 2026-09-18T08:52:25+0800

v71 independent digest probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: compute_workspace_tree_digest() returns the identical digest for a workspace with no link and a workspace containing linkdir -> external/secret.txt. os.walk does not descend symlink dirs and the digest code records no symlink-dir entry, so the boundary digest is blind to an entire directory redirect. Evidence /tmp/r56_v71_workspace_digest_symlink_dir_probe.out SHA-256 332d2cd8f427ba76fb96878712b943e28878a7381d6004f208b1fd043e0871d5. Runtime workspace digesting must either reject all symlinks or encode them unambiguously.
