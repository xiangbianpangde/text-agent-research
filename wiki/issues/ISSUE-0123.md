---
id: "ISSUE-0123"
title: "load_canonical_trace 的返回契约未文档化 verdict/source_bound，而文档化的 {found,valid} 恰是 fail-open 谓词"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "canonical_trace_contract_omits_bound_axis_docpromises_failopen_predicate"
  - "contract_lock_test_added_and_mutation_verified;docstring_fix_validated_in_isolated_rehearsal"
  - "obligation_is_asserted_in_tests_but_absent_from_public_api_docs"
evidence: "tools/canonical_trace.py load_canonical_trace docstring: 'Returns {found, valid, records, problems, ...}. Verification failures are reported and never silently downgraded to the retired root alias.' — verdict/source_bound/unbound/unbound_note 全部未提及；grep -rn 'source_bound\|VERIFIED_BOUND' README.md docs/ => 0 hits（包内无任何散文文档要求消费者检查 bound 轴），仅 tools/canonical_trace.py:269,271 与 tests/security/test_canonical_trace_loader.py:312,322 提及。格式漂移同处：tools/attestation_policy.py:601 提示 'pass expected_required_set_digest=...'（下划线），而 argparse 实际注册的是 846 行 '--expected-required-set-digest'（连字符），照提示粘贴即 rc!=0 unrecognized arguments。全部在解压归档 /private/tmp/r62_v80_arch/iso/review_v77（SHA 7de9414fa01d，与 live 包 diff -rq 逐字节相同）上复现。"
related: []
fix_ref: null
summary: "load_canonical_trace 的返回契约未文档化 verdict/source_bound，而文档化的 {found,valid} 恰是 fail-open 谓词"
updated_at: "2026-09-22"
---

## 现象

load_canonical_trace 返回两种不同的『OK』：VERIFIED_BOUND（有效且源身份已绑定）与 INTERNALLY_VALID_UNBOUND（内部自洽但无仓库可锚定，valid=True/problems=[]）。docstring 只承诺 {found, valid, records, problems}，而 found && valid 对两者都为真 —— 即文档所写的谓词无法区分绑定与未绑定。ISSUE-0112 的 :sol 门禁 consumer 正是照此谓词写的，因此它的 fail-open 有文档依据，不只是 consumer 的疏忽。对照：同包的 tools/attestation_policy.py 在无仓库时 fail-closed（TREE_UNAVAILABLE, rc!=0），并给出 --expected-required-set-digest/--expected-source-commit/--expected-source-tree 逃生口（实测：zip-only + 独立摘要 => 0 stale 通过；喂错摘要 => REQUIRED_SET_DIGEST 拒绝；不喂 => NOTICE 明说 commit/tree 'is NOT verified'），两个工具对同一『无仓库』处境采取相反默认，而契约文档只覆盖了宽松的那个。

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

## 处置记录 2026-09-22T21:11:02+0800

SHARPNESS REFINEMENT after re-reading the suite, 2026-09-22. The obligation is NOT undocumented everywhere -- it is asserted in tests, which is exactly why the suite passes while a naive consumer still fails open. Evidence: tests/security/test_canonical_trace_loader.py:311-313 asserts result.get('source_bound') is False and result.get('verdict') == 'INTERNALLY_VALID_UNBOUND' while ALSO asserting result['valid'] is True ('integrity should hold without a repo'); :318-322 test_verdict_distinguishes_bound_from_unbound asserts bound['verdict'] == 'VERIFIED_BOUND'; :341 and :398 assert verdict == 'INVALID' on refusals. So the two-axis design is deliberate, tested, and correct. The defect is strictly one of DISCOVERABILITY: the public entry point's docstring documents only 'Returns {found, valid, records, problems, ...}' and neither README nor docs/ mention source_bound or VERIFIED_BOUND (grep over README.md and docs/ returns nothing), so a consumer who reads the documented contract but not the test file gets a predicate that accepts an UNBOUND trace. This also explains why the :sol/3/P0P1_CLOSURE_AUDIT.py gate at :301-305 failed open using found && valid without anyone noticing. REMEDY (unchanged, one doc change, no semantics change): state in the load_canonical_trace docstring that 'valid' means INTERNAL integrity only, that source binding is a SEPARATE axis, and that any consumer gating on provenance MUST require verdict == 'VERIFIED_BOUND' / source_bound is True. NOTE the same test lines are the natural place to lock the remedy in, e.g. asserting the docstring mentions the bound axis. NOT applied while v77 (SHA 7de9414f) is under review.

## 处置记录 2026-09-22T21:29:37+0800

FIX PREPARED AND VALIDATED IN ISOLATION (not shipped), 2026-09-22. Change is documentation-only -- no semantics touched. New docstring for load_canonical_trace now states the two axes explicitly: valid/found describe INTERNAL integrity only; source_bound/verdict describe PROVENANCE; an internally valid trace with unestablished provenance yields valid is True WITH source_bound is False and verdict == 'INTERNALLY_VALID_UNBOUND'; refusals yield 'INVALID'; and any provenance-gating consumer MUST require verdict == 'VERIFIED_BOUND' and MUST NOT accept on 'found and valid' alone (noting the shipped P0/P1 gate did exactly that and failed open). Added regression lock test_public_contract_documents_the_provenance_axis asserting the docstring names source_bound, verdict, VERIFIED_BOUND, INTERNALLY_VALID_UNBOUND and scopes 'valid' to internal integrity. MUTATION-VERIFIED: reverting the docstring to internal-only fails the lock (1 failed, 22 passed); restored state passes 23/23. Consistent with the earlier finding that the obligation was already asserted in tests (311-313/318-322) -- so the design was right and only the PUBLIC CONTRACT was silent. Full rehearsal: tests/security/ = 209 passed with the fix, freshness passes at the attestation commit. Cross-reference ISSUE-0112: the gate-side half lives outside the package root (:sol/3/) and is therefore reported, not patched.
