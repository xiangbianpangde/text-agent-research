---
id: "ISSUE-0024"
title: "v61 runtime identity remains mutable and absent from evaluator envelopes"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "runtime_identity_missing,mutable_runtime_dependency"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; runner/sandbox_launcher.py:82-83, docker/Dockerfile.worker; docker/pyproject.worker.toml; runner/worker_supervisor.py:_build_envelope; /tmp/r48_v61_f06_static.out"
related: []
fix_ref: null
summary: "v61 runtime identity remains mutable and absent from evaluator envelopes"
updated_at: "2026-09-17"
---

## 现象

default container_image is researchctl-worker:latest; worker dependencies are ranged (jsonschema>=4.20.0,numpy>=1.24.0); evaluator envelope has no immutable OCI/image, lock, executable, mount, cgroup/resource-scope, or GPU identity.

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

## 处置记录 2026-09-17T16:27:10+0800

Round 51/v64 static/runtime identity audit: /tmp/r51_v64_runtime_static_probe.out (SHA-256 23057dd0bc0ba8d1ccd7c7868ef03d53aed9ff7b4fc63bdf0afb3fc466c6cb90) still reports mutable latest image, no BGE/FAISS imports, in-process SQLite ResearchCTL, deterministic Qwen extraction, ranged dependencies, and silent container fallback. The evaluator envelope still lacks immutable runtime/image/lock/mount/cgroup identity. F-06 remains open.
