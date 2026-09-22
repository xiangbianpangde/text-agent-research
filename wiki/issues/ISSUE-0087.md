---
id: "ISSUE-0087"
title: "researchctl 缺派生索引时抛裸 sqlite3 异常并以纯文本输出，违反 fail-closed envelope 契约"
status: "fixed"
severity: "high"
area: "researchctl-cli"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "missing_index_raises_raw_sqlite,non_json_error_output,cli_guard_only_for_bench"
evidence: "cwd=researchctl-product;command=python3 -m researchctl --root /tmp/fx query --entity CURRENT;stdout=stderr-only 'error: unable to open database file';exit=0 (无 JSON 文档);command=python3 -m researchctl --root /tmp/fx trace CURRENT;stdout 非 JSON → json.loads 抛 JSONDecodeError;path=researchctl/cli.py main() 的 isdir(root) 守卫仅对 bench --json 输出 envelope，queries.py _connect() 直接 sqlite3.connect；reference-case: main worktree fixture 存在故长期未暴露"
related: []
fix_ref: "researchctl-product@M0: queries.index_available + index_required_envelope; cli.py root-missing --json guard; cli.py cmd_bench compat shim"
summary: "researchctl 缺派生索引时抛裸 sqlite3 异常并以纯文本输出，违反 fail-closed envelope 契约"
updated_at: "2026-09-22"
---

## 现象

索引缺失/root 无效时 5 个只读命令（query/sources/trace/impact/history）输出纯文本错误而非可解析 fail_closed envelope，且缺索引时 QueryResult 状态码本应为 INDEX_STALE

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

## 处置记录 2026-09-22T16:50:32+0800

M0 第一刀已修并验证：新增 queries.index_available()/index_required_envelope()，5 个只读命令入口加守卫 → 缺索引统一返回 status=fail_closed / error_semantic=INDEX_STALE / authority=unresolved 的可解析 envelope；cli.py 在 root 不存在且 --json 时输出单个 JSON 文档（SOURCE_MISSING，exit 1）；cmd_bench 改为 compatibility-only 延迟导入，缺 bench/ 时返回 BENCH_NOT_AVAILABLE JSON fail-closed。证据：5/5 命令均为 fail_closed INDEX_STALE；product 套件 23 passed 含 test_missing_index_fails_closed_with_envelope(5 参数化) / test_drift_fails_closed_instead_of_returning_stale_results / test_bench_shim_json_fail_closed_without_bench_tree；443 checks 无回归。
