---
id: "ISSUE-0154"
title: "四个 catalog 测试依赖 fixture 里残留的 .index/：fresh clone 下必败，且掩盖了一个真实的调用顺序前置条件"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "test_depends_on_gitignored_state,index_semantic_requires_prior_base_index,leftover_state_masks_failure,fresh_clone_tests_fail,latent_precondition_bug"
evidence: "清空 researchctl/tests/fixtures/product-v1/tree/.index 后 npm run test:catalog：not ok 3 (backend.test.ts:65)、not ok 7 (drift.test.ts:100)、not ok 5 (layer.test.ts)；修复后 128/128 pass 且再次清空索引仍全绿；CLI 实测：无 .index 时 `index --semantic` → status 1 / 'unable to open database file'，先 `index` 再 `index --semantic` → status success / document_count 6"
related: []
fix_ref: null
summary: "四个 catalog 测试依赖 fixture 里残留的 .index/：fresh clone 下必败，且掩盖了一个真实的调用顺序前置条件"
---

## 现象

backend.test.ts / drift.test.ts / layer.test.ts 均在共享 fixture 树上直接查询或调用 `index --semantic`，但 .index/ 被 .gitignore 覆盖、不入库。此前它们通过，只因为更早的实验步骤在 fixture 里留下了 .index/。清空后 3 个文件立即失败。其中一个不是测试瑕疵而是真实前置条件：`researchctl index --semantic` 在完全没有 .index/ 的树上直接退出非零（stderr: 'unable to open database file'），必须先跑一次普通 `index`。该顺序无人记录，layer.test.ts 原先漏了这一步而未被发现。注意：trigger.ts 的 ensureSemanticIndex 初版把索引写进了共享模板树，反而破坏了 layer.test.ts 中断言『无语义索引必须 fail-closed』的用例——fixture 必须保持无索引，语义索引应建在私有副本上。

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
