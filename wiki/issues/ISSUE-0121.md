---
id: "ISSUE-0121"
title: "以 Node spawn 启动 pi --print 时，继承 stdin 会导致子进程永久挂起"
status: "open"
severity: "high"
area: "env"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "spawn_inherited_stdin_hang,pi_print_mode_blocking,harness_no_output"
evidence: "catalog/test/trigger.ts runTurn；对照实验：同一命令行在 bash 中 40s 内正常退出，Node spawn 继承 stdin 时 45s 后 child.exitCode === null；改为 stdio:['ignore','pipe','pipe'] 后 close code 0、3293 bytes"
related: []
fix_ref: null
summary: "以 Node spawn 启动 pi --print 时，继承 stdin 会导致子进程永久挂起"
---

## 现象

用 node:child_process spawn 启动 'pi --print --mode json ...' 时，若 stdio 为默认（继承父进程 stdin），pi 会等待 stdin 输入而永不退出；harness 因此对所有 25 个用例都拿不到任何输出，且无报错——表现为整体静默超时而非失败。shell 直接执行同一命令则正常，因为 shell 下 stdin 是终端或被立即关闭。

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

规避：spawn 时显式 stdio:['ignore','pipe','pipe']。诊断要点：'shell 能跑、spawn 挂起' 的组合优先怀疑 stdin 继承，而不是命令本身或权限。
