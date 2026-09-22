---
id: "ISSUE-0112"
title: "v75 P0/P1 closure consumer treats INTERNALLY_VALID_UNBOUND trace as accepted"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "canonical_trace_unbound_consumer_valid_only"
  - "gate_consumer_valid_only_confirmed_out_of_package_scope"
  - "gate_predicate_confirmed_from_bound_commit_never_touches_bound_axis;independently_reproduced_by_reviewer_unbound_consumer_probe"
  - "verdict_field_is_computed_not_spoofable_forgery_defeated"
evidence: "commit 6adead09423679ee45e984b91b4480cb1bdf54f4; :sol/3/P0P1_CLOSURE_AUDIT.py:301-305 checks only found && valid; /tmp/r61_v75_unbound_consumer_probe.out SHA-256 d7b30216a5fa60449fd57be53143d849f861f918f34c75c5d04186dd56a6170f"
related: []
fix_ref: null
summary: "v75 P0/P1 closure consumer treats INTERNALLY_VALID_UNBOUND trace as accepted"
updated_at: "2026-09-22"
---

## 现象

v75 loader deliberately returns valid=True/source_bound=False/verdict=INTERNALLY_VALID_UNBOUND for a git-less archive. On a forged-but-internally-consistent triple, the P0/P1 closure condition `found && valid` is still true and does not require VERIFIED_BOUND or an independent attestation; source identity absence is therefore accepted by the shipped gate.

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

## 处置记录 2026-09-22T20:51:43+0800

v77 archive recheck: load_canonical_trace() returns found=true, valid=true, source_bound=false, verdict=INTERNALLY_VALID_UNBOUND, problems=[] for 7de9414fa01dfac284c029bc37aad9f004bbc04f8b02578bd8c500294de20e04. A shipped-style consumer using only found && valid therefore accepts it; requiring verdict == VERIFIED_BOUND rejects it. Evidence /tmp/r62_v77_unbound_consumer_probe.out SHA-256 d649be400651321cc5c9182dda7893ee1aa18da66c988d79bbfa4a684f2fff05.

## 处置记录 2026-09-22T20:54:54+0800

SCOPE VERIFIED (3 axes), and a correction to my earlier phrasing. I previously said 0112 is 'outside the reviewed package' — that is TRUE but was asserted, not proven; it is now proven: (1) review_v77.zip has 1946 entries ALL prefixed review_v77/, ':sol' count 0; (2) attestations/M1_worker_protocol_attestation.json declares 1916 package-relative paths with NO ':sol' key, self_path=attestations/M1_worker_protocol_attestation.json; (3) the consumer file :sol/3/P0P1_CLOSURE_AUDIT.py:298-303 branches only on found && valid. NOTE the repo relation: pkg dir research-retrieval-benchmark is a SUBDIR of repo /Users/xbpd/Projects/benchmark, and :sol/ sits beside it in the SAME repo and IS tracked at the bound commit adf16ffc (54 files). So the auditor is not excluded by being untracked — it is excluded because the artifact map is package-root-scoped. Correction to my message: I said 'this is a :sol gate-instrument defect'. That holds, but only because of package-root scoping; the reviewer's package cannot fix a file that is not shipped inside it. I am NOT editing my own auditor. ALSO: in-package consumers of load_canonical_trace are TESTS ONLY (tests/security/test_canonical_trace_loader.py), so the fix cannot be shipped as a package-level consumer edit either. Registered companion issue ISSUE-0120: the auditor itself is unbound/unverifiable (:sol edits do not break the package attestation, verified by appending to it and observing rc=0; its SHA256SUMS references unreachable /mnt/data paths).

## 处置记录 2026-09-22T21:04:13+0800

MATERIAL NARROWING of this issue, established by physical probes (not reasoning). (A) SPOOFING IS IMPOSSIBLE. I injected every plausible claim into BOTH the trace manifest AND the COMPLETE marker (verdict=VERIFIED_BOUND, source_bound=true, valid=true, unbound=false, binding_verified, source_verified), recomputed complete_marker_sha256 so the two files agree, and re-ran the loader on the extracted archive: it still returned verdict=INTERNALLY_VALID_UNBOUND, source_bound=False, valid=True. grep confirms verdict is never read from the manifest (0 hits for payload.get('verdict')/manifest['verdict']) — it is COMPUTED by verify_source_binding (tools/canonical_trace.py:147-152, whose docstring is explicit that bound=False means 'could NOT be independently confirmed -- never that it was confirmed wrong'). So an attacker cannot defeat a verdict-checking consumer by editing files; the failure mode is the CONSUMER's predicate choice, not trace forgeability. (B) THE CONSUMER'S PREDICATE HAD DOCUMENTARY SUPPORT. The loader docstring promises only '{found, valid, records, problems, ...}' and grep shows the shipped package contains NO prose anywhere (README.md, docs/) requiring a consumer to check source_bound/VERIFIED_BOUND — the obligation exists only in code (lines 269/271) and in tests (test_canonical_trace_loader.py:312/322). found && valid is exactly the predicate the docstring's contract enumerates, and it is true for both bound and unbound traces. So the :sol gate was written to the documented contract; the contract under-specifies. Registered as companion ISSUE-0123 (medium). (C) CONTRAST CONFIRMED: the SAME package's tools/attestation_policy.py fail-closes in the identical git-less situation (TREE_UNAVAILABLE, rc!=0) and its documented escape hatch WORKS as advertised — zip-only + independently-supplied digest => '0 stale' rc=0 (1916 paths); wrong digest => REQUIRED_SET_DIGEST refusal; omitted => explicit NOTICE that commit/tree 'is NOT verified'. Two tools in one package take OPPOSITE defaults on the same condition, and only the lax one's contract is documented. NOTE a real (minor) bug in that same hint text: attestation_policy.py:601 tells the user to pass 'expected_required_set_digest=' with underscores while argparse registers '--expected-required-set-digest' (line 846); pasting the hint verbatim yields rc!=0 'unrecognized arguments'. My scope conclusion is UNCHANGED and now stronger: the package cannot fix :sol/3/P0P1_CLOSURE_AUDIT.py (not in the package-root-scoped artifact map), but the package CAN and should tighten its own contract/docs/tests so found&&valid is documented as insufficient. Reproduced on the extracted archive SHA 7de9414fa01d (byte-identical to live package per diff -rq).

## 处置记录 2026-09-22T21:11:21+0800

BOUND-COMMIT CONFIRMATION (authoritative source, not the working tree), 2026-09-22. git show 'adf16ffc902f::sol/3/P0P1_CLOSURE_AUDIT.py' lines ~301-305 read exactly: trace = load_canonical_trace(root) if load_canonical_trace else {'found': False}; if trace.get('found') and trace.get('valid'): ev = trace['records'] else: ev = {'missing': True, 'trace_problems': trace.get('problems', [])}. So the gate selects its evidence bundle on found AND valid ONLY. A grep of the whole bound-commit script for verdict|source_bound|VERIFIED_BOUND returns no trace-loader usage -- the only two 'verdict' hits (lines 336, 347) are the gate's OWN output verdict dict, not the trace's verdict. The failure is therefore real and located: an INTERNALLY_VALID_UNBOUND trace is routed into ev = trace['records'] as if it were a bound evidence bundle. INDEPENDENT REPRODUCTION by reviewer 01a08b88 (/private/tmp/r62_v77_unbound_consumer_probe.out, run against their clean extraction /private/tmp/r62_v77_clean/review_v77) reproduces the same conclusion with richer detail: found=true, valid=true, source_bound=false, verdict='INTERNALLY_VALID_UNBOUND', problems=[], attempt_count=336, accepted_by_shipped_gate_found_and_valid=true, required_gate='verdict == VERIFIED_BOUND', gate_would_pass=false. Two independent parties now agree on both halves -- the loader returns valid=true for an unbound trace, and the found&&valid predicate accepts it. CROSS-REFINES ISSUE-0123: the remedy should be applied on BOTH sides where each is fixable -- a docstring/contract fix inside the package (ISSUE-0123) plus, in the delivery flow, requiring verdict == VERIFIED_BOUND at the gate (outside the package root, so reported not patched). Neither changes any package semantics beyond documentation, so neither invalidates the reviewed SHA by itself; both are held for the post-verdict version.
