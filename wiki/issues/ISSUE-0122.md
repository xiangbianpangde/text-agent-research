---
id: "ISSUE-0122"
title: "发布绑定不变量缺少评审者可发现性：parent-binding 需经 successor pin 与 required_set_digest 验证"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "parent_binding_is_a_documented_invariant_not_an_inconsistency;invariant_proved_non_vacuous_by_require_commit"
  - "release_binding_invariant_is_correct_but_not_reviewer_discoverable"
  - "reviewer_accepted_correction_2026-09-22;transient_mutation_reverted_not_a_delivery_defect"
evidence: "git diff --name-only adf16ffc902f 468d9fc = only attestations/M1_worker_protocol_attestation.json (the reserved self-path); delivered worktree and fresh v77 archive both verify 1916 paths / 0 stale. On the delivered tree, tools/attestation_policy.py --commit adf16ffc902f --require-commit adf16ffc902f -> rc=0 and --require-commit 468d9fc -> rc=0. A non-vacuity control changing README.md at commit 8409986 makes --require-commit 8409986 reject with SOURCE_COMMIT/required-set digest mismatch. The earlier two-STALE checkout observation is withdrawn as a transient mutation and is not evidence of a v77 delivery defect."
related: []
fix_ref: null
summary: "parent-binding 不变量已实现且非空洞，但归档与评审文档未说明 successor pin、保留自路径和 required_set_digest 的验证关系"
updated_at: "2026-09-22"
---

## 现象

v77 的 parent-binding 语义本身是正确且非空洞的：attestation 落在 successor commit 468d9fc，绑定其 parent adf16ffc；保留自路径不进入 required set，`required_set_digest` 用于证明 successor 仍描述同一组被证明字节。`--require-commit 468d9fc` 在 delivered pin 上 rc=0；对非保留文件 README.md 的对照改动会因 required-set digest 不同而拒绝。残留缺陷是**评审者可发现性与发布证据契约**：README/docs 没有说明 successor pin、保留自路径、`--require-commit` 或 `required_set_digest`，只拿归档的评审者无法自行发现并验证该不变量；在 source parent adf16ffc 单点运行自校验得到 2 个 STALE 是 cadence 的预期结果，不应归因成 pin 语义矛盾。

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

## 处置记录 2026-09-22T21:02:19+0800

Related to the deliberate parent-binding cadence documented in tools/refresh_attestation.py and exercised by the reviewer probe r62_v77_attestation_independent_probe.py, which pins expected_source_commit=PARENT (adf16ffc) when verifying the archive. That probe asserts the binding at the NEXT commit; nothing in-package asserts 'the commit named as the release pin verifies ITSELF'. Suggested resolution options (NOT applied; reporting only): (a) document that a release pin is only verifiable from its successor commit, or (b) have refresh_attestation write an attestation that binds its own commit (requires the commit to exist before the bytes are written -> not possible in one commit), or (c) have the release process tag the SUCCESSOR commit as the verifiable pin. Option (c) is the only one that makes 'checkout pin -> self-verify rc=0' a true invariant.

## 处置记录 2026-09-22T21:05:05+0800

独立复核（本审计者）2026-09-22：对 benchmark commit adf16ffc 与 468d9fc 分别 git worktree add --detach 到 /private/tmp 临时副本，执行 cd research-retrieval-benchmark && python3 tools/attestation_policy.py --package-root .。adf16ffc rc=1，恰为 2 个 STALE：tests/security/test_canonical_trace_loader.py declared 7d53890e72d2f != on-disk f657d971dbce3；tests/security/test_worker_isolation.py declared ab4a464b0c2cb != on-disk 638080490741a。468d9fc rc=0，1916 paths closed against tree c9bbc8c143e5d87b803bc3163f96ee45f992a0e5 at adf16ffc902f。临时 worktree 清理后 benchmark live status clean。该现象确认 release pin 自校验不自洽，但不改变更高优先级的 provenance/consumer blockers。

## 处置记录 2026-09-22T21:42:09+0800

SELF-CORRECTION + INDEPENDENT VERIFICATION, 2026-09-22 (responding to the reviewer's NO-GO adjudication, which cites this issue as 'release pin is not self-consistent'). The adjudication itemises this as 'attestation binds parent adf16ffc, target is 468d9fc => inconsistent'. My probes say that framing is wrong, and I am recording the correction against my own earlier acceptance of it. EVIDENCE: (1) git diff --name-only adf16ffc902f 468d9fc returns EXACTLY ONE file -- research-retrieval-benchmark/attestations/M1_worker_protocol_attestation.json -- which is the documented RESERVED SELF-PATH (attestation_policy.py:14 describes it; :38 defines ATTESTATION_RELPATH), deliberately excluded from the required set so that committing the attestation does not change the required set it attests. (2) At the DELIVERED commit 468d9fc, tests -k attestation_hashes_are_current = 1 passed (I earlier reproduced 2 STALE at the SOURCE commit adf16ffc and initially misread that as a defect; the documented flow is code -> refresh -> commit attestation, so freshness is meant to hold at the attestation commit). (3) tools/attestation_policy.py --require-commit 468d9fc => rc=0. (4) NON-VACUITY CONTROL: I built a commit 8409986 that changes a NON-reserved file (README.md); --require-commit 8409986 => rc=1 with 'SOURCE_COMMIT: attestation binds adf16ffc902fd7562073f3661b3ef619613e7873 but 8409986fec0743c71a28bf9111c5bf39adae6c5d was required, and the required-set digests differ' plus 'STALE: README.md'. So the invariant is implemented (attestation_policy.py:577-590 compares required_set_digest) and is NOT vacuous. RESIDUAL DEFECT I DO ACCEPT: the invariant is UNDISCOVERABLE -- grep over README.md and docs/ finds no mention of reserved self-path, --require-commit or required_set_digest, so a reviewer with the archive alone cannot verify it. Same family as ISSUE-0123: correct design, silent contract. Suggested restatement: 'binding semantics are correct and independently verifiable only via a documented-in-code invariant that no reviewer-facing document mentions', which is a documentation/release-evidence gate, not a self-contradictory pin.

## 处置记录 2026-09-22T21:48:56+0800

复核者裁定（2026-09-22 13:48Z，intercom seq 12）接受我的更正：parent-binding 不变量确实实现且有效——--require-commit 468d9fc rc=0（digest-proof 分支），非保留文件改动对照会被拒绝；残留是 reviewer-facing discoverability / 发布证据文档缺口，与 ISSUE-0123 同族，不是语义上的 pin 矛盾。

R68 独立复核（本人实测，见 RAW-20260922-005）：
(1) --commit adf16ffc --require-commit adf16ffc => rc=0「1916 paths closed / 0 stale」=> 声明源提交自洽，本条 issue 原措辞（『adf16ffc 自身不自洽』）不成立，已更正。
(2) --commit 468d9fc --require-commit 468d9fc => FAILED(1) SOURCE_TREE declared c9bbc8c… != actual 753db326… for 468d9fc。
(3) --require-commit 468d9fc 用声明绑定 => rc=0（两者 required-set digest 相同，486 行起的 digest-proof 分支）。
故正确表述：绑定节律是『X 的树内 attestation 绑定 X 的父』，单点 checkout 无法自证，属可发现性缺口而非 pin 语义矛盾。

另：复核者 rc1.out 的两条 STALE（declared 72c3e5f6b1494 != on-disk 0044fb9cd6184 等）在交付态不复现——live repo 与 v77 归档中两文件 on-disk 均为 72c3e5f6…/1186a531…，与 declared 一致，git status 干净，四个历史提交中内容相同；该现象来自一次已回滚的瞬时 mutation，不应据此判定交付包 STALE，应在 fresh archive 中重测。
