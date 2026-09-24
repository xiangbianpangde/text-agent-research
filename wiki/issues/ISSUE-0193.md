---
id: "ISSUE-0193"
title: "请求上限的标定用了错单位：以 tool-call 数替代 provider dispatch 数，且原标定数字不可复现"
status: "open"
severity: "high"
area: "researchctl"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "calibration_uses_proxy_unit_not_enforced_unit"
  - "unreproducible_calibration_numbers"
  - "dispatch_count_not_recorded"
evidence: "catalog/test/recovery-run.ts 原注释称「Across the archived rows (112 turns that recorded calls): mean 23.5, p95 49, max 60」并据此取 100/回合。复核方（执行者-1，seq 8）指出该指标来自归档 Pi tool-call 数，不等价于独立测得的 broker upstream request 数，故不足以批准 cap=5/500。本侧独立重算 catalog/test/ 下全部含 calls 的 .jsonl（5 个文件：archive/trigger-results.allfix 25、archive/trigger-results.midfix-0146 25、baseline-results 50、trigger-results 25、recovery-results 59）：**184 回合，mean 14.8，p95 44，max 60**——与原称 112 回合/mean 23.5 均不符（112 回合不对应任何盘上语料；23.5 亦复现不出）。即原标定数字属不可复现claim。修（本 commit）：① 注释撤销原数字、改记实测的 184/14.8/44/60，并明写「这一条测的是 tool-call，而上限执行的是 dispatch，故 100/回合是以代用单位推出的界，不是在被执行单位上测出的数」；② Row 新增可选 dispatches{reserved,answered,failures}，由 recovery-run 在每回合前后读 childCredentialProxy() 取差值落盘（ISSUE-0194），使该系数今后可在正确单位上重推；③ 刻意用「缺字段」而非 0 表示未测量，避免旧行被读成「零消耗」——与 §5.6 撤回两个层指标所依据的同一「不可校验代理」失效模式。"
related: []
fix_ref: null
summary: "请求上限的标定用了错单位：以 tool-call 数替代 provider dispatch 数，且原标定数字不可复现"
---

## 现象

请求上限的标定用了错单位：以 tool-call 数替代 provider dispatch 数，且原标定数字不可复现

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
