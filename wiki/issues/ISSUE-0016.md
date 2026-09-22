---
id: "ISSUE-0016"
title: "v61 module-level origin reader remains rebindable and shutdown round-trip omits lineage sampling"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "trust_anchor_module_rebind,lineage_sampling_window"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/sandbox_launcher.py:_ORIGINS_READER; runner/worker_supervisor.py:shutdown() _read_frame_with_deadline; /tmp/r48_v61_f01_rebind.out; /tmp/r48_v61_shutdown_roundtrip_probe.out"
related: []
fix_ref: null
summary: "v61 module-level origin reader remains rebindable and shutdown round-trip omits lineage sampling"
updated_at: "2026-09-16"
---

## 现象

import runner.sandbox_launcher as m; m._ORIGINS_READER=lambda: frozenset(('attacker',)) 后 attacker declaration verify_declaration=ACCEPT；worker 在收到 shutdown 请求后才创建 detached child、返回合法 shutdown_ack 并退出时 child 在 5/5 trials 存活

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

## 处置记录 2026-09-16T15:27:53+0800

v62 further authority probe: SandboxLauncher._declaration_core is ordinary mutable class attribute; rebound to lambda d:{} then attacker-mutated entries verify_declaration() as ACCEPT_AFTER_UNSIGNED_ENTRY_MUTATION (/tmp/r49_v62_key_core_rebind_probe.out). _DECLARATION_KEY is also ordinary class attribute, so same-process code can replace the HMAC key and self-attest. Metaclass protects only two anchor names, not signer/key/core/policy.
