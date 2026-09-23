---
id: "ISSUE-0142"
title: "researchctl/tests 在 fresh checkout 上整体无法收集：4 个测试模块硬依赖被 .gitignore 忽略的顶层 fixture/ 目录"
status: "fixed"
severity: "high"
area: "env"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "fixed_by_canonical_bundle_materialization,443_checks_reproducible_on_fresh_checkout"
  - "test_suite_uncollectable_on_fresh_checkout,gitignored_fixture_required_by_tests,verification_entrypoint_not_self_sufficient"
evidence: "cd <repo> && python3 -m pytest researchctl/tests -q → 'Interrupted: 4 errors during collection'，ERROR test_p0b.py / test_p0c.py / test_p1a.py / test_p1b.py；根因 'FileNotFoundError: /Users/xbpd/Projects/researchctl-product/fixture' 与 'git -C .../fixture status --short' exit 128。.gitignore:25 为 'fixture/'。在 pristine HEAD 的独立检出（git archive HEAD | tar -x -C /tmp/headchk）中复现完全相同的 4 个 collection error，证明与工作树未提交改动无关。"
related: []
fix_ref: "researchctl-product@fa7ea21"
summary: "researchctl/tests 在 fresh checkout 上整体无法收集：4 个测试模块硬依赖被 .gitignore 忽略的顶层 fixture/ 目录"
updated_at: "2026-09-23"
---

## 现象

任何按 HEAD 全新检出该仓库的人（或 CI）都无法运行 Python 测试套件——不是测试失败，而是根本无法收集。目录纪律里被忽略的 fixture/ 却是 4 个测试模块的硬依赖，说明该 fixture 存在于开发机上但从未进入版本控制。后果：Spec §8 G0『现有 443 checks 无回归』与 §12 发布证据包『现有 443 checks 回归结果』在干净环境不可复核；且由于 fixture/ 被忽略，其内容无版本历史、无灾难恢复（与 ISSUE-0127 同形：关键证据只有磁盘副本）。需决定该 fixture 的生成方式（脚本化重建 / fixture 生成器 / 改指向 in-repo 的 researchctl/tests/fixtures/）并纳入版本控制。

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

## 处置记录 2026-09-23T08:50:34+0800

已修复并端到端验证：(1) fixture 以 canonical bundle（14KB、11 commits、27 files、生成确定性）纳入版本控制 researchctl/tests/fixtures/legacy-fixture-v1.bundle；(2) 新增物化器 legacy_fixture_materialize.py 与 test-product --legacy --materialize 一站式路径；(3) 在干净 git archive HEAD 检出上实测 443/443 PASS（此前该环境为 4 个 collection error、0 checks）。选 bundle 而非重建：test_p0b.py 的 G 段硬编码三个 commit SHA（f0d7ffc/a8cb33c/1bf12e0）作为历史不变性契约，bundle 携带原对象故 SHA 原样复现，重建则需逐字节复刻 11 棵树。新增 6 条回归测试并做变异验证（回退退出码语义/移除 user 配置/允许覆盖非空目标 → 分别变红）；移除 user 配置可独立复现 217/443。README 已同步。
