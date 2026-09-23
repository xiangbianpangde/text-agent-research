---
id: "ISSUE-0141"
title: "researchctl-product 工作树存在无归属的未提交索引优化改动，使验收记录的提交统计与工作树状态不一致"
status: "open"
severity: "medium"
area: "env"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "pre_existing_pytest_collection_errors_missing_gitignored_fixture_dir,index_change_result_neutral_verified_readonly"
  - "unattributed_uncommitted_work_in_verified_worktree,worktree_not_clean_during_acceptance_record,in_flight_concurrent_edit_unclaimed"
evidence: "cd /Users/xbpd/Projects/researchctl-product && git status --short → ' M researchctl/indexer.py'、' M researchctl/semantic.py'，git diff --stat = 56 insertions(+)，两文件 mtime 均为 2026-09-23 00:21:19。内容为派生查询索引（indexer.py 的 QUERY_INDEX_SQL：idx_source_refs_owner/idx_source_refs_ref_path/idx_documents_doc_type 等 6 个；semantic.py 的 SEMANTIC_QUERY_INDEX_SQL：idx_terms_doc_id_term_tf/idx_ngrams_doc_id_ngram），注释明确声明不改冻结 schema 契约。核查：git log 486477b..b84c1ae -- researchctl/ 为空，证明 M3 全程未触碰 researchctl/；wiki 中无任何 issue 认领该工作（grep idx_source_refs/idx_terms_doc_id/查询索引 均无命中）。由执行者-2 于 intercom a8669331(seq 10) 抽查发现。"
related: []
fix_ref: null
summary: "researchctl-product 工作树存在无归属的未提交索引优化改动，使验收记录的提交统计与工作树状态不一致"
updated_at: "2026-09-23"
---

## 现象

我被交接的 M3 验收记录按提交统计描述交付物，而工作树中同时存在属于别的任务、尚未提交且无人认领的代码改动。后果有二：(1) 记录的『git 工作树干净，命令可复现』类前提（Spec §8 G0 明列）当前不成立，而报告未提及；(2) 这些改动触及 indexer/semantic 查询路径，与 M3 测试所用的 fixture/索引行为存在潜在耦合，却未纳入 M3 的验证范围。处置纪律：不得覆盖或回滚他人未提交工作；M3 结项须与该改动分开处理；报告须如实声明工作树状态。需认领方补充提交归属与验证证据。

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

## 处置记录 2026-09-23T08:30:56+0800

补充只读验证结果（未触碰他人文件，未提交）：(1) 结果中性——indexer 侧带索引与显式 DROP INDEX 后同一查询结果集完全一致（source_refs 5 行），documents/entities/runs 计数一致，两次 build_index 确定性一致；(2) semantic 侧在 product-v1 fixture 上返回 INDEX_STALE fail_closed 且不建表，但该行为系「base index is not fresh」的既有 Fail-Closed 语义，非该 diff 引入；(3) M3 的 Node 套件不经过 Python 索引路径（trigger.ts 只用 researchctl/tests/fixtures/product-v1/tree 作为语料根），故 M3 证据未受该改动影响——但这只说明耦合不存在，不改变归属不明的结论；(4) 另发现 researchctl/tests 的 4 个 collection error（缺顶层 fixture/，该目录被 .gitignore:25 忽略），在 pristine HEAD 的 /tmp 检出中完全相同，属既有问题而非本次引入。该 diff 的注释声称索引不被 validate_schema_only 检查（仅用 PRAGMA table_info），已核实成立。

## 处置记录 2026-09-23T08:50:34+0800

仍未闭合：indexer.py/semantic.py 的未提交索引优化保持原样，未纳入 G0 切片提交 fa7ea21。作者/认领人仍待确认。已补充只读验证：索引改动结果中性、M3 证据不受影响（详见前次更新）。
