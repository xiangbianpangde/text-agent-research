---
id: "ISSUE-0068"
title: "v71 declared Python >=3.10 but oracle/compile_gold.py is syntactically invalid on Python 3.10"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "declared_python_version_incompatibility,python310_compile_failure"
evidence: "commit 1ed201b636302ee095fb6713186f69a56e422ac9; research-retrieval-benchmark/pyproject.toml:requires-python >=3.10; oracle/compile_gold.py:610; ruff --select F821 /tmp/r56_v71_python310_compile.out"
related: []
fix_ref: null
summary: "v71 declared Python >=3.10 but oracle/compile_gold.py is syntactically invalid on Python 3.10"
updated_at: "2026-09-18"
---

## 现象

Python 3.10 rejects the backslash escape inside an f-string expression at oracle/compile_gold.py:610, while Python 3.12.7 compileall succeeds. The package advertises >=3.10 but cannot parse on that supported interpreter.

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

## 处置记录 2026-09-18T08:45:17+0800

Evidence artifact created: ruff --target-version py310 oracle/compile_gold.py output at /tmp/r56_v71_python310_compile.out, SHA-256 8fd43e2cc589ce53524e19a11b49389fb666a54db95cd297c30afde4e6fcef05. Ruff reports invalid-syntax at line 610 in addition to lint findings.
