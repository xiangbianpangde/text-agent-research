---
id: "ISSUE-0015"
title: "v60 full pytest run intermittently fails while copying disallowed .git objects"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "snapshot_copy_race"
evidence: "commit c928f356764c5b9b4483aafa339dd2bc24531755; runner/sandbox_launcher.py:734-758; /tmp/r47_v60_full_1.txt; /tmp/r47_v60_full_2.txt; /tmp/r47_v60_full_3.txt; /tmp/r47_v60_p0.json"
related: []
fix_ref: null
summary: "v60 full pytest run intermittently fails while copying disallowed .git objects"
updated_at: "2026-09-16"
---

## 现象

Three sequential clean full pytest runs produced 124/124, 124/124, then 122/124; the failing renderer tests raised source workspace does not exist for transient .git/objects/<prefix> while _safe_tree_copy recursively copied .git that purge later removes.

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

## 处置记录 2026-09-16T14:05:05+0800

v61继续复现：clean extracted archive / private/tmp/r48_v61_clean.lAqtCe, no PYTHONPATH, run4 collected 130，129 passed/1 failed；失败仍为 tests/security/test_worker_isolation.py::test_f01_renderer_emits_role_based_declaration，_safe_tree_copy() 把 .git 递归复制时遇到 /sealed/.git/objects/23 消失，报 SnapshotIntegrityError: source workspace does not exist。随后 run5/run6 各 130/130 passed，确认 nondeterministic race。证据 /tmp/r48_v61_pytest_4.out,/tmp/r48_v61_pytest_5.out,/tmp/r48_v61_pytest_6.out。

## 处置记录 2026-09-16T15:16:44+0800

v62补充：修复仅捕获 file copy 的 FileNotFoundError；存在 check 与递归调用之间若目录消失，_safe_tree_copy 仍抛 SnapshotIntegrityError。确定性 check-to-call race（删除 src/raw/vanish 或 root/src 后返回 exists=True）分别报 source workspace does not exist / source workspace is not a directory（/tmp/r49_v62_snapshot_race_probe.out）。这覆盖 live .git/<prefix> 目录消失形态。

## 处置记录 2026-09-16T15:46:52+0800

v62 partial repair verified: missing file between scandir/copy is tolerated, but directory/root disappearance still hard-fails (directory source workspace does not exist; root source workspace is not a directory). /tmp/r49_v62_snapshot_race_probe.out. This only narrows the .git file race; whole-tree snapshot remains race-sensitive.
