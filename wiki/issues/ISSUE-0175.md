---
id: "ISSUE-0175"
title: "taint 检测器把「被沙箱拒绝的读取尝试」计为「已读取」：分类错误的代价是丢弃良好观测"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "attempt_counted_as_read"
  - "blocked_read_misclassified"
  - "taint_false_positive"
  - "discards_good_measurement"
  - "detector_reads_args_not_outcome"
evidence: "catalog/test/recovery.ts readGradingDesign() 原实现对 calls[].args 做正则匹配即返回 true，不看该调用是否真的拿到内容。实测证据：被测回合 rec-semantic-metadata-value-not-text 的 call#35 'cd .../docs/records && ls -la && head -c 300 M3-G3-acceptance-record.md 2>&1' 与 call#38 'cat .../M3-Recovery-Measurement-Contract.md'，在 sandbox-exec -f <profile> 下复算均返回 'Operation not permitted'（DENIED），但该回合被判 tainted。行内字段只有 tool/args/error_code 三项，无输出，故无法由观测本身区分。修复后：recovery-run.ts 写入 sandboxed 字段；readGradingDesign(calls, sandboxed) 在沙箱激活时对 enabled 判 false；缺省仍为保守（未隔离运行的尝试仍计为读取）。"
related:
  - "ISSUE-0171"
  - "ISSUE-0174"
fix_ref: null
summary: "taint 检测器把「被沙箱拒绝的读取尝试」计为「已读取」：分类错误的代价是丢弃良好观测"
---

## 现象

一个回合尝试读取判分文件但被沙箱拒绝时，仍被分类为 TAINTED/INCONCLUSIVE。由于裁决规定受污回合不得计入 PASS/FAIL 且不得凑底线，这个误判会静默丢弃本来有效的测量，方向是把结果压向 HOLD。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

若未发现，重跑后本可成为干净 PASS 的回合会被永久判为受污，缺口被高估。反之若反向误判（真读计为干净）则会虚高读数——两个方向都依赖能否区分 attempt 与 read。

## 根因

观测记录的是『调用了什么』而非『拿到了什么』；检测器只能从 args 推断意图，无法从行内数据推断结果。修法是让 runner 提供它已知的策略事实（沙箱是否激活），而不是让检测器猜。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
