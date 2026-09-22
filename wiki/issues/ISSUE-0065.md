---
id: "ISSUE-0065"
title: "v71 canonical trace is marked COMPLETE without a physical marker and is bound to v69 source"
status: "verified"
severity: "critical"
area: "bench"
discovered_at: "2026-09-18"
discovered_by: "agent"
tags: []
signals:
  - "v71_trace_missing_complete_marker,v71_trace_wrong_source_binding,v71_trace_attempt_invariant"
evidence: "reviewed commit 1ed201b636302ee095fb6713186f69a56e422ac9; results/traces/TRACE-20260917T155035Z-60f98c47/TRACE_MANIFEST.json; /tmp/r56_v71_canonical_loader_failopen.out SHA-256 30118836d80a5226982a3ad7863e55947afc8af67e4ed964b1ccd638af001118; canonical trace events.jsonl has 736 records, 336 attempt groups of exactly participant_response+evaluator_envelope, 32 campaign query_request records, and no physical COMPLETE/COMPLETE.json"
related: []
fix_ref: "74df6e4"
summary: "v71 canonical trace is marked COMPLETE without a physical marker and is bound to v69 source"
updated_at: "2026-09-22"
---

## 现象

Manifest says status=COMPLETE and publishes complete_marker_sha256, but neither marker file exists; source_commit=cc33db81cc180f871d2035a12d8badfc09a9591 is v69 rather than reviewed v71; every attempt group lacks its own query_request, all 736 wrapper session_id values are null, and 64 campaign-scope records lack run_uuid/attempt_id. The trace therefore is not failure-complete or replayable under the stated invariant.

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

## 处置记录 2026-09-22T14:39:55+0800

Independent v72 recheck against archive review_v72.zip: manifest status=COMPLETE but source_commit remains v69 cc33db81cc180f871d2035a12d8badfc09a9591 instead of reviewed 3eb82461f2f9fe0dd4eb68c889fd7f431d5fbace; 336 attempts have exactly participant_response+evaluator_envelope but 0/336 have an attempt-level query_request, 0 terminal record kinds, all 736 session_id values are null, and no physical COMPLETE/COMPLETE.json exists. Evidence: /tmp/r58_v72_canonical_trace_probe.out SHA-256 74c6a7fe5edb0e7e2e11664a3a9c09ae5f0fadcc94388eab13c639e68667c31c.

## 处置记录 2026-09-22T18:20:00+0800

Independent v73 archive recheck against reviewed archive commit `19dff4ffb65039f30f2d85664928fa62445442d8`: the shipped trace manifest is `COMPLETE` with a physical marker and 336 groups of request+response+envelope, but `source_commit=7bcecb782e482cbd54e11899c0624de17c03ed67` does not equal the reviewed archive commit; `source_subtree` is incorrectly the source repository root tree (`cbb40482...`) rather than the actual package subtree (`6d093da4...`); and terminal record kinds remain absent. All 64 campaign-scope records have null wrapper run/session/attempt identity as expected for campaign scope, while all 336 attempt groups have 3 records. The shipped loader nonetheless returns `valid=True, problems=[]`. Evidence: /tmp/r59_v73_trace_independent_probe.out SHA-256 e964744bf3395455b9ad4c9801c446d4fa9f07fd85c06ae171621fa1f5c97d74.

## 处置记录 2026-09-22T17:38:36+0800

complete_marker_sha256 was the manifest's own bytes; no physical COMPLETE marker

## 处置记录 2026-09-22T18:18:34+0800

source_subtree was confirmed to equal the repository ROOT tree (I verified it, not just read the report): the builder used {commit}^{tree}, which resolves to the repo-root tree, so for a package inside a larger repository it bound nothing about this package. Fixed to {commit}:{show-prefix}. Rebuilt trace TRACE-20260922T100808Z-5b03bd6e now records source_subtree=463dbba857a23824..., distinct from root tree e7cf7f24298fe2df.... Critically, the accompanying test does NOT merely assert the field is populated: test_builder_records_the_package_subtree_not_the_repo_root recomputes the expected value with 'git rev-parse <commit>:<prefix>' and asserts equality AND that it differs from source_tree -- it caught the stale shipped trace, which is why the trace was rebuilt in 74df6e4. source_commit is now the bound reviewed commit. Superseded trace removed; the loader treats >1 valid trace as ambiguous. Also hardened: symlinked store refused (see ISSUE-0064 note).

## 处置记录 2026-09-22T18:22:59+0800

v74 独立复核（archive c429cabecffabed6806aefb3844e73beb14fa78585b4f0057a010548a0b2e390，reviewed commit 8296dd5530600fd0554f6b4d68c5707b87851932）：trace `TRACE-20260922T100808Z-5b03bd6e` 有 1072 records/336 attempts、物理 marker、每 attempt request+response+envelope，loader baseline valid=True；但 manifest source_commit=15dc0b9...、source_tree=e7cf7f...、source_subtree=463db...，实际 reviewed target root tree=f5546d...、package subtree=744803...。attempt terminal record types 仍为空。证据 /tmp/r60_v74_trace_independent_probe.out SHA-256 4945798cf37ae65ab90f024ec78b08c051e83a295036266e71873a0bdbbad34f。

## 处置记录 2026-09-22T19:22:22+0800

v75 独立复核（archive 69af7f75096a08df5c3620987be822357a0635718cbc2a2e59e5313b805ae259，target 6adead09423679ee45e984b91b4480cb1bdf54f4）：trace 仍 source_commit=15dc0b9.../root=e7cf7f.../package=463db...，而 target root=4591807.../package=ce8d495...；1072 records/336 groups、loader 为 INTERNALLY_VALID_UNBOUND，attempt terminal kinds 仍为空。证据 /tmp/r61_v75_trace_independent_probe.out SHA-256 2cdb27143b0cc2d8e9adc95a25425d442e9f0c0513770f970d1cc20f64158308。
