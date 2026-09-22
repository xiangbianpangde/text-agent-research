---
id: "ISSUE-0012"
title: "v60 direct declaration verification and prebuilt launcher accept paths outside constructor checks"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "declaration_authority_bypass"
evidence: "commit c928f356764c5b9b4483aafa339dd2bc24531755; runner/sandbox_launcher.py:299-340; runner/worker_supervisor.py:548-583; /tmp/r47_v60_decl_probe.out; /tmp/r47_v60_prebuilt_bypass.out"
related: []
fix_ref: null
summary: "v60 direct declaration verification and prebuilt launcher accept paths outside constructor checks"
updated_at: "2026-09-17"
---

## 现象

SandboxLauncher.verify_declaration() and load_produced_declaration() accept HMAC-sealed declarations with policy/task_id/workspace_tree_digest/provenance_only extras; missing manifest_version is accepted. WorkerSupervisor accepts a prebuilt undeclared launcher (declaration_enforced=False, undeclared_snapshot=True).

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

## 处置记录 2026-09-16T13:46:09+0800

v61复现补充：verify_declaration() 仍未自足，合法 WorkspaceRenderer 签名的 unknown top-level、missing manifest_version、unknown nested entry 均 ACCEPT；participant_manifest={} 跳过 __init__ 验证，却 prepare_sandbox() 设置 declaration_enforced=True，prebuilt supervisor 随后 ACCEPT。证据 /tmp/r48_v61_f01_verify.out、/tmp/r48_v61_empty_manifest_bypass.out。

## 处置记录 2026-09-16T15:18:19+0800

v62追加形状探针：合法 origin/track + self-attested declarations with entries=['x'], entries='x', {'raw/a':'bad'}, {'raw/a':[]} all pass direct verify_declaration(); verifier 不检查 entries/map/meta shape。证据 /tmp/r49_v62_f01_shape_probe.out。

## 处置记录 2026-09-16T15:34:49+0800

v62 cross-process durability probe: declaration signed in producer Python process is rejected by a fresh consumer because _DECLARATION_KEY is regenerated at import (producer digest d80e...; consumer SnapshotIntegrityError). Evidence /tmp/r49_v62_cross_process_hmac.out. Persisted declaration is not verifiable/durable authorization.

## 处置记录 2026-09-17T16:37:52+0800

Round 51/v64 static verifier repro: /tmp/r51_v64_static_probe_v2.out (SHA-256 d770ada4bd0abbc0f7d545b37f2464fef4ffbd0370ccfe34bd10183a6c307079) reports verify_accepts_missing_manifest_version=true, verify_accepts_malformed_entries_list=true, and verify_accepts_malformed_entry_scalar=true for direct attest_declaration()/verify_declaration(). Constructor loading adds some schema checks, but the direct verifier remains self-sufficient only syntactically and does not enforce the full declaration contract; authorization bypasses are separately recorded in ISSUE-0054.
