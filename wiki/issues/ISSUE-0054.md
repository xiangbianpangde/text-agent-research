---
id: "ISSUE-0054"
title: "v64 declaration authorization can be widened by rebinding the HMAC key or mutating public declared entries"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-17"
discovered_by: "agent"
tags: []
signals:
  - "authorization_boundary_bypass"
  - "declaration_key_rebinding"
  - "mutable_declaration_entries"
  - "v71_declaration_key_closure_introspection"
  - "v71_module_key_reader_rebind,v71_sealed_snapshot_sync_bypass"
  - "v71_process_local_declaration_not_replayable"
  - "v71_sealed_nested_entry_mutation"
evidence: "commit 5227b03dbf2af80d9abd5d47161483dd2864d519; research-retrieval-benchmark/runner/sandbox_launcher.py:81,147,266-334,967-1006; /tmp/r51_v64_key_probe.out SHA-256 72e4969c1e97cc71a9ef43f7bfb19adca5e7c34fdf08faa689a9c8fb9b684ee7; /tmp/r51_v64_manifest_mutation_probe.out SHA-256 521ba351df5af2a2c9603d0a4e0c25f139513dfb204a847ae4b803ac556182dd"
related: []
fix_ref: null
summary: "The process-local HMAC seal protects content integrity only, not producer authorization: _DECLARATION_KEY is a mutable class attribute and declared_entries is a mutable public map consumed during snapshot admission."
updated_at: "2026-09-18"
---

## 现象

After rebinding SandboxLauncher._DECLARATION_KEY, an attacker-created declaration is accepted and verified. After normal verification, adding data/evil.txt to launcher.declared_entries causes that undeclared file to remain in the participant snapshot.

## 复现

In the extracted v64 package run the key and manifest-mutation probes. The first reports class_key_rebind=true and forged_verified=true; the second reports data/evil.txt in remaining after post-verification mutation.

## 影响

A same-process participant or caller able to reach the launcher can authorize arbitrary content or forge a producer declaration; this violates F-01 authorization and invalidates snapshot-bound provenance.

## 根因

Signing and verification dereference SandboxLauncher._DECLARATION_KEY at call time, while enforcement dereferences self.declared_entries at materialization time. Neither is an immutable, producer-bound capability or kernel-enforced boundary.

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

Round 51 independent clean-room finding. The attestation's declaration_hmac_signed and trust-anchor claims must not be read as authorization evidence; HMAC integrity, trusted origin checks, and a mutable process-local object do not prove who is authorized to define the participant boundary.

## 处置记录 2026-09-17T18:57:09+0800

Round 52/v65 does not close F-01. `/tmp/r52_v65_key_rebind_probe.out` SHA-256 ecbda3837ce6d23f49c4c2c6ad2e0c151232549e0aab6da5eb13148469e21820 rebinds the module-global `_DECLARATION_KEY_READER` and obtains forged_verified=true even though the class key attribute is absent. The new shallow seal can also be bypassed by setting public/private state `_declaration_sealed=False` before adding an entry, or by replacing `_sealed_entry_snapshot`; `/tmp/r52_v65_declaration_flag_probe.out` SHA-256 f74988b789d302b90a051d9207cbde62aa75a8addbcda208990fbc03a06a7d reports accepted with data/evil.txt in the effective snapshot. The v65 regression only catches ordinary key insertion while leaving same-process state mutation possible.

## 处置记录 2026-09-17T18:57:28+0800

Correction to the preceding evidence note: the exact SHA-256 for `/tmp/r52_v65_declaration_flag_probe.out` is `f74988d789d302b90a051d9207cbde62aa75a8addbcda208990fbc03a06a7d` (not the mistyped value in the previous note).

## 处置记录 2026-09-17T19:53:26+0800

v66 leaves the seal state mutable. Clean-room probe /tmp/r53_v66_decl_seal_bypass.out mutates both public declared_entries and _sealed_entry_snapshot to add data/evil.txt; _enforce_participant_declaration accepts and leaves evil present. Rebinding module _DECLARATION_KEY_READER also forges a declaration (evidence /tmp/r53_v66_decl_key_probe.out). HMAC integrity remains process-local, not producer-bound authorization.

## 处置记录 2026-09-18T08:15:47+0800

v71 clean-room probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: rebinding runner.sandbox_launcher._DECLARATION_KEY_READER lets SandboxLauncher.attest_declaration() mint a declaration accepted by verify_declaration (module_key_rebind_verify=accepted); after adding raw/evil.txt to public declared_entries, synchronizing mutable _sealed_entry_snapshot lets prepare_sandbox() accept and retain evil. Evidence /tmp/r56_v71_declaration_trust_bypass.out SHA-256 a36acfd72c564b1f0e3777af980f4cf0c609e5c29d229774958e1c5be4ed2b1b. Metaclass protection of class origin names does not make the process-local key or entry snapshot an authorization capability.

## 处置记录 2026-09-18T08:34:01+0800

v71 restart probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: a declaration attested in one Python process is written to disk, then a fresh process importing sandbox_launcher rejects the same bytes because _DECLARATION_KEY_READER generated a new key. Evidence /tmp/r56_v71_declaration_restart_probe.out SHA-256 68427d1f79a67f3f736d1ad0476f5fb67d3f7f64bc8f1e1a0ef1dcb887327a52. The process-local HMAC is neither a durable independently verifiable provenance seal nor a cross-process authorization mechanism.

## 处置记录 2026-09-18T08:36:36+0800

v71 closure probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: the supposedly hidden process-local HMAC key is recoverable from _DECLARATION_KEY_READER.__closure__[0].cell_contents (32 bytes), and the recovered value equals reader(). Evidence /tmp/r56_v71_declaration_closure_introspection.out SHA-256 28e923e78a961d649356381c9c49975983d289b013780253d203e71334d905ee. Moving a key from a class attribute into a Python closure is not an authorization boundary against same-process code.

## 处置记录 2026-09-18T09:02:07+0800

v71 clean-room declaration probe against commit 1ed201b636302ee095fb6713186f69a56e422ac9: _sealed_entry_snapshot = dict(declared_entries) is shallow. Mutating declared_entries['raw/x.txt']['sha256']/size after sealing changes the sealed snapshot too; _enforce_participant_declaration accepts attacker bytes (enforce=accepted, sealed_entry_snapshot_matches=true) even though producer_sha differs. Evidence /tmp/r56_v71_declaration_nested_mutation_probe.out SHA-256 d5f727aeda414352a9590e35f220daee1ab0172c8457044d29f72d367e0cb0cf. Seal must deep-copy immutable metadata and keep authoritative declaration inaccessible to mutable caller state.
