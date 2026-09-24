---
id: "ISSUE-0164"
title: "实跑读数未记录被测模型：--model 缺省时继承父会话配置，结果文件与验收记录均无模型身份，读数不可复现"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "reading_without_model_identity,inherited_model_from_parent_session,run_not_reproducible"
evidence: "catalog/test/recovery-run.ts 的 --model/--provider 均为可选，缺省走 pi 自身解析（读继承环境）。46 行 recovery-results.jsonl 的字段只有 calls/distinct_state/expects_code/judged/scenario_id/stratum/text，无 provider/model；验收记录 §5.4.3 与合同也未声明被测模型。实测该次实跑的环境为 PI_MODEL=deepseek/deepseek-v4.1-flash、PI_PROVIDER=command-goat，即读数出自父会话碰巧配置的模型。修法：从 assistant message_start 事件取 provider/model（取『实际运行的』而非 --model 参数里『要求的』），写入 TurnResult.model 与结果行，报告头打印 measured model，并把该字段加入 StoredTurn 以免重判时丢失；dry-run 提示有多少行早于该修复（当前 37/37），明确声明不回溯补齐"
related: []
fix_ref: null
summary: "实跑读数未记录被测模型：--model 缺省时继承父会话配置，结果文件与验收记录均无模型身份，读数不可复现"
---

## 现象

一份门禁读数的价值取决于它能否被复现，而工具允许用『父会话恰好配置的任意模型』产生数字且不记录身份——同一命令两次运行可能测的是不同模型却打印同一个百分比

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
