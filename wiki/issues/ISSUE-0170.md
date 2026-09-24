---
id: "ISSUE-0170"
title: "结果文件里的 judged 是判据的旧快照：--report 只在内存中重判不写回，直接读 JSONL 的审计者会得到与 harness 相反的数字"
status: "open"
severity: "medium"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "persisted_verdict_stale_snapshot,report_does_not_write_back,on_disk_contradicts_harness"
evidence: "catalog/test/recovery-run.ts:424-444 —— report 路径把每行喂给 judgeRecovery({scenario, calls, text, observable_codes, ...}) 求 verdict，再用 reportByStratum 汇总；全程不写文件（写盘只在 --run 的 appendFileSync，第 396 行）。于是 catalog/test/recovery-results.jsonl 中每行的 judged 字段是**该行写入时**的判据输出。判据一旦修改（本轮三次：ISSUE-0166/0167/0169），盘上 judged 立即与 harness 的读数不一致。实测：修完 ISSUE-0169 后 npm run m3:recovery -- --report 报 source-integrity 10/10 = 100.0%，而直接读该文件统计 judged.recovered 得 9/10 —— src-current-target-deleted 盘上仍为 false。我自己在按执行者-1 裁决逐条核对时先读到 9/10，险些把「与 harness 不符」记成 harness 的问题。风险方向：审计者按合同『读数必须可从落盘数据复算』的要求直接读 JSONL，会看到与记录相反的数字，且无法判断哪个是当前口径。"
related: []
fix_ref: null
summary: "结果文件里的 judged 是判据的旧快照：--report 只在内存中重判不写回，直接读 JSONL 的审计者会得到与 harness 相反的数字"
---

## 现象

同一份落盘数据，harness 重判得 10/10、直接读文件得 9/10；判据是被测量装置的一部分，但它的输出被冻结在写盘那一刻，且没有任何字段说明这是快照

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
