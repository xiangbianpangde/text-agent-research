---
id: "ISSUE-0124"
title: "attestation_policy.py 打印的唯一补救指引用了下划线参数名（expected_required_set_digest=），照抄即 rc=2 unrecognized arguments"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "attestation_policy_hint_flag_spelling_underscore_vs_hyphen_unusable_remediation"
  - "independently_reproduced_by_reviewer_byte_for_byte"
  - "root_cause_assertion_checked_token_not_actionable_flag;fix_validated_209_of_209_security_tests_pass_in_isolated_rehearsal"
evidence: "tools/attestation_policy.py:601 在 TREE_UNAVAILABLE 分支打印 'pass expected_required_set_digest=<digest from an independent source> to verify an archive without git; without it this cannot be checked and must not be assumed'；而 argparse 在 846 行注册 '--expected-required-set-digest'（连字符）。照抄打印文本复现：python3 tools/attestation_policy.py --package-root . --expected_required_set_digest sha256:3ff5a8f7 -> rc=2，stderr 'attestation_policy.py: error: unrecognized arguments: --expected_required_set_digest sha256:3ff5a8f7'（/tmp/hint_bad.out）；改用连字符：同命令 --expected-required-set-digest sha256:3ff5a8f7 -> rc=0，'attestation verified: 1916 paths closed against tree c9bbc8c143e5d87b803bc3163f96ee45f992a0e5 at adf16ffc902f, 0 stale'（/tmp/hint_good.out）。argparse 不下划线↔连字符互转，故该拼写 100% 失败；同段三条提示里另两条同名参数（486/496/507/869 行的 Python 形参与 846-860 行的 CLI）也只有这一条被打印。"
related: []
fix_ref: null
summary: "attestation_policy.py 打印的唯一补救指引用了下划线参数名（expected_required_set_digest=），照抄即 rc=2 unrecognized arguments"
updated_at: "2026-09-22"
---

## 现象

无 git 归档场景下 attestation_policy.py 会 fail-closed（TREE_UNAVAILABLE, rc!=0），并在 problems 里给出唯一一条、以祈使句写的补救指令。但该指令给出的是内部 Python 形参名（下划线），不是 CLI 标志名（连字符），所以照做的人得到的不是验证结果而是一个 argparse 用法错误 rc=2。危害不只是打错字：这是 fail-closed 拒绝时用户能拿到的唯一指引，指引不可用会诱导用户得出『没有这个开关』的结论并就此放过验证（即从 fail-closed 退回 fail-open），恰与该工具设计意图相反。修法只需在提示里改成 --expected-required-set-digest（或同时给出 Python 形参名与 CLI 标志名），成本极低。

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

INDEPENDENT REPRODUCTION by reviewer 01a08b88, 2026-09-22 21:10, in files /private/tmp/r62_v78_hint_bad_independent.out and r62_v78_hint_good_independent.out. Their bad-case output is byte-for-byte identical to mine (/private/tmp/hint_bad.out, 21:07) in the usage block and error text: 'attestation_policy.py: error: unrecognized arguments: --expected_required_set_digest sha256:3ff5a8f7537f3204ee63f906bf4824f9c46283ad30c71ca41e09f369f3882897' (the digest is the real required-set digest, so this is the actual printed hint being pasted back). Their good-case output is likewise identical: 'attestation verified: 1916 paths closed against tree c9bbc8c143e5d87b803bc3163f96ee45f992a0e5 at adf16ffc902f, 0 stale' (119 bytes, same as mine). Two independent parties, same bytes, same rc semantics => the finding is confirmed, not single-source. Severity stays medium: the patch is one line, but the cost is asymmetric because this hint is the ONLY remediation the tool prints when it fail-closes, so the documented recovery path is unusable exactly when a user needs it.

## 处置记录 2026-09-22T21:11:07+0800

独立复核（本审计者）2026-09-22：tools/attestation_policy.py:601 打印 expected_required_set_digest=，而 argparse:846 仅注册 --expected-required-set-digest；在 live benchmark package 上下划线拼写 rc=2 unrecognized arguments，连字符拼写 rc=0 且输出 1916 paths/0 stale。该 medium issue 确认成立。

## 处置记录 2026-09-22T21:29:37+0800

ROOT CAUSE FOUND + FIX VALIDATED IN ISOLATION, 2026-09-22. My earlier note said 'no test locks the hint' -- that was WRONG, caused by grepping the full hint string ('expected_required_set_digest=<digest') instead of the token. The token IS asserted at tests/security/test_attestation_policy.py:504: 'assert any("expected_required_set_digest" in p for p in problems)'. That assertion checks only that the TOKEN appears, never that it is an ACTIONABLE FLAG -- which is precisely why the Python-kwarg spelling could ship while the suite stayed green. This is the mechanism behind the defect, and it means the defect was locked in by a too-weak assertion rather than merely overlooked. FIX (3 parts, one line each): (1) tools/attestation_policy.py:601 hint now reads 'pass --expected-required-set-digest <digest from an independent source>...'; (2) the assertion now requires '--expected-required-set-digest' AND forbids 'expected_required_set_digest='; (3) a contract-lock test test_public_contract_documents_the_provenance_axis. MUTATION-VERIFIED: reverting the hint to the buggy spelling FAILS the new assertion (1 failed, 59 passed) and restoring it passes 60/60; reverting the docstring FAILS the contract lock (1 failed, 22 passed) and restoring passes 23/23. PAYOFF MEASURED in git-free archive mode against the tool's own declared required-set digest: the OLD flag spelling yields 'error: unrecognized arguments: --expected_required_set_digest ...' while the CORRECTED spelling yields rc=0 'attestation verified: 1916 paths closed against tree c9bbc8c143e5d87b803bc3163f96ee45f992a0e5 at adf16ffc902f, 0 stale'. Full shipping rehearsal (isolated worktree from delivered 468d9fc, NOT the frozen artifact): refresh_attestation -> 1916 paths / 12 corpus frames / 0 stale bound to c2ac71113f28; after committing the attestation (649a83c) freshness passes and tests/security/ = 209 passed. Patch saved outside the repo at /private/tmp/R64_validated_fix.patch (sha256 b89d9d538e91d6f7...). Frozen review artifact SHA 7de9414f unchanged; all rehearsal worktrees removed. NOT SHIPPED -- v77 stays frozen pending the reviewer's verdict.
