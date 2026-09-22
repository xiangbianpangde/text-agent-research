---
id: "ISSUE-0098"
title: "M1-3 header handle 校验后仍按路径二次打开导致 resolve TOCTOU"
status: "open"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "m13_verified_handle_path_reopen_tocou"
evidence: "commit 6f7d4cc53eba60e2e3f854d8a213bb34503f6be7; /tmp/r60_m13_resolve_toctou_probe.out SHA-256 9cec831f0a1c66a1cb3db7d7a63651ea8c52df8b59dc99ad7468cb07509ab773; session-retrieval/query.ts:338-410, scanner.ts:484-555"
related: []
fix_ref: null
summary: "M1-3 header handle 校验后仍按路径二次打开导致 resolve TOCTOU"
updated_at: "2026-09-22"
---

## 现象

resolveExactRef 先由 indexSessionHeaders 读取并校验 header，随后 readLinesBounded(target.path) 按路径重新打开；通过 now() 在两阶段之间替换文件后，返回 status=ok、text=evil replacement，未绑定已校验 inode/handle。声明的 F8 '通过已校验 handle 读取' 未实现。

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

## 处置记录 2026-09-22T18:17:35+0800

追加确定性故障注入证据：/tmp/r60_m13_resolve_external_symlink_tocou_probe.out SHA-256 c8c5943581311222ccf0de73d77202051e6cf3d686803d55b9d2691138de0a23。now() 在 header index 完成后将已验证 regular file 替换为 root 外部 symlink；readLinesBounded(target.path) 跟随外链并返回 external replacement，证明 F8 不是仅理论竞态。
