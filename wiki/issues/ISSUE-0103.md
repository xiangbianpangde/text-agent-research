---
id: "ISSUE-0103"
title: "canonical trace source triple (commit/tree/subtree) is shape-checked only and is not bound to any repository, so a fabricated or unrelated source triple verifies valid"
status: "fixed"
severity: "critical"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "trace_source_binding_unverified,fabricated_commit_accepted,manifest_marker_consistent_tamper"
evidence: "/tmp/rs2 probe: rewrote manifest+COMPLETE source_subtree to an UNRELATED tree id (git rev-parse HEAD^{tree}), recomputed complete_marker_sha256 so manifest and marker agree; tools/canonical_trace.py:254-257 only regex-checks shape -> load_canonical_trace returned valid=True"
related: []
fix_ref: "4d422f0"
summary: "canonical trace source triple (commit/tree/subtree) is shape-checked only and is not bound to any repository, so a fabr…"
updated_at: "2026-09-22"
---

## 现象

load_canonical_trace validates source_commit/source_tree/source_subtree only by 40-hex shape plus manifest<->marker equality. The triple is never compared to the actual repository, so any internally consistent forged triple (including an unrelated tree, or a well-formed commit id that exists nowhere) verifies valid. This is the same class as ISSUE-0065 (source_subtree equalled the repo ROOT tree, i.e. bound nothing about this package) but survives the format fix: the corrected builder value is not itself re-derived at load time.

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

## 处置记录 2026-09-22T18:37:08+0800

v74 独立复现：基线 trace loader valid=True；把 manifest+COMPLETE 的 source_commit/source_tree/source_subtree 改成互相一致但虚构的 a{40}/b{40}/c{40}，重算 marker hash 后仍 valid=True。同期 role↔payload 与 wrapper↔payload identity 变异已被拒绝，root/entry symlink 也被拒绝。证据 /tmp/r60_v74_trace_mutation_probe.out SHA-256 be6dc487b10e1823346ad7eeb0598a10fb10050c11a6066e691508f6d174feeb。

## 处置记录 2026-09-22T19:01:53+0800

Two-stage fix, both verified. (1) a7cf04f re-derives source_commit/source_tree/source_subtree from the repository (existence via cat-file -e, self-resolution, {commit}^{tree}, and {commit}:{show-prefix}) instead of shape-checking them, so a fully self-consistent forged triple is refused. (2) 4d422f0 repairs the regression that first attempt introduced: reporting 'no repository reachable' as a trace PROBLEM made the shipped P3 audit fail in a git-less archive (closure PASS -> NOT_CLOSED). The axes are now explicit: valid = internal integrity, source_bound = identity re-derived, verdict = INVALID | INTERNALLY_VALID_UNBOUND | VERIFIED_BOUND. An unbound trace keeps valid=True with problems==[] and explains itself in unbound_note. A reachable repo that contradicts the triple remains a hard failure. Tests: tests/security/test_canonical_trace_loader.py 14 passed, fixture builds a REAL repo so binding is exercised, test_binding_check_is_not_vacuous guards the control; mutation (revert to shape-only) fails exactly the binding tests while the control stays green. Self-caught: a first version also rejected source_subtree == source_tree, which would wrongly fail a package that IS the repo root.

## 处置记录 2026-09-22T19:24:21+0800

v75 role/identity/root/entry mutation controls remain closed; archive forged triple is internally valid and unbound as intended, while clean Git-bound forged triple is invalid. Combined v75 mutation evidence: /tmp/r61_v75_trace_mutation_probe.out SHA-256 42f3f7acfc92802784ef4f62f4fee6e83f8d0ef2b211da5b2b9904eb04e7d1bd; binding evidence /tmp/r61_v75_source_binding_probe.out SHA-256 c0a498d06f45b427a72587e035c10c7df9efbb64e4e8fa31e3b8845bf3e9c77d.

## 处置记录 2026-09-22T21:02:15+0800

POST-COMPACTION INDEPENDENT RE-VERIFICATION of the fix (3 probes, all against temp copies/worktrees; live package never mutated, verified clean after each). (1) FAITHFUL ISSUE-0103 TAMPER re-run: rewrote manifest source_subtree + COMPLETE marker to an UNRELATED real tree (git rev-parse HEAD^{tree}=51cbc1db88047ee9 of the owning repo) AND recomputed complete_marker_sha256 so manifest and marker AGREE. MODE 1 (repo reachable, detached git worktree at pin adf16ffc): valid=False, verdict=INVALID, problem='source_subtree 51cbc1db88047ee9... != 463dbba857a2382497af1d40a39f561dd3f0da23 for 15dc0b9cbcfd80fe772d3ba35b64...'. MODE 2 (no repo, plain copy): valid=True but source_bound=False, verdict=INTERNALLY_VALID_UNBOUND, unbound=True with the explanatory unbound_note — i.e. the two axes are correctly separated per the ISSUE-0108 repair, NOT conflated. (2) NEGATIVE CONTROL (fix non-vacuous): neutralised the guard call site in a throwaway copy (bound,problem=(False,None)); the SAME tamper then returned valid=True, problems=[] (accepted). So the guard is what refuses it; the PASS is not vacuous. (3) BOUND-CASE 6/6 REFUSALS: in a repo-reachable worktree, forging nonexistent commit / real-commit-wrong-tree / garbage commit / wrong subtree / retarget-to-pin / retarget-other all returned valid=False INVALID (caught first by the manifest<->COMPLETE marker cross-check, then by git re-derivation). (4) HISTORICAL TRIPLE IS GENUINELY VERIFIABLE: trace 5b03bd6e declares commit 15dc0b9c / tree e7cf7f24298f / subtree 463dbba857a2; all three re-derive exactly from the repo, and 15dc0b9c is a true ancestor of the release pin adf16ffc (12 commits between). Historical accuracy is thus CONFIRMED, not assumed. (5) PROVENANCE COHERENCE: runner/ and workers/ are BYTE-IDENTICAL between the trace-producing commit and the release pin; only verification tooling (canonical_trace.py +164, attestation_policy.py +212) and tests changed, so the trace was produced by the same worker code that ships. (6) ARCHIVE-vs-PIN: extracted review_v77 verifies 0 problems / 0 notices against an INDEPENDENT pin (expected_source_commit=adf16ffc, expected_source_tree from repo, expected_required_set_digest re-derived): 1916/1916 match. Regression: tests/security 208 passed.
