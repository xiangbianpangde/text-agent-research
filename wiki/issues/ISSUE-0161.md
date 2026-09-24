---
id: "ISSUE-0161"
title: "recovery harness 把 PYTHONPATH=<harness 仓库> 传给被测子进程，模型据此找到并读取判分源码与自己的结果文件，39/39 全部 unjudged"
status: "fixed"
severity: "critical"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "harness_leaks_grader_source_via_pythonpath,eval_measures_its_own_apparatus,model_reads_its_own_results_file"
evidence: "npm run m3:recovery -- --run 实跑 39 场景：39/39 unjudged（36 例 timeout after 240000ms、4 例 2 empty turn(s)，1 例 met SOURCE_MISSING 与声明 INDEX_STALE 不符），两分层分母均为 0，rate=n/a。结果文件 catalog/test/recovery-results.jsonl。bash 调用共 1189 次（占全部调用 79%），其中 697 次（59%）的 command 里明确出现 harness 仓库路径 /Users/xbpd/Projects/researchctl-product。模型实际读取：catalog/test/recovery.ts（含全部 39 个场景定义与判分标准）、catalog/test/recovery-run.ts、catalog/test/recovery-results.jsonl（它自己的结果文件）、docs/records/M3-G3-acceptance-record.md、bench/runner.py。成因：catalog/test/trigger.ts:497 env:{...process.env, PYTHONPATH: REPO}，REPO 定义于 trigger.ts:52 且指向 harness 仓库根，该环境变量随子进程继承，等于给模型一条回到判分源码的路径。对照：同 harness 已发表的 corpus 跑 trigger-results.allfix（25 例）为 23%，更早的 corpus pre-0146（29 例）为 0%（当时 bash 调用为 0）。另：19/39 例超时且调用数 25–75，与目标不符——rec-stale-untracked-probe-organized 场景中 research_integrity(action=reconcile) 与后续 research_query 全部返回 success，而场景声明应得 INDEX_STALE"
related: []
fix_ref: "42cfc6e"
summary: "recovery harness 把 PYTHONPATH=<harness 仓库> 传给被测子进程，模型据此找到并读取判分源码与自己的结果文件，39/39 全部 unjudged"
updated_at: "2026-09-23"
---

## 现象

recovery 测量装置给被测模型泄漏了判分源码路径：模型读到场景定义（含期望错误码）与自己的结果文件，测得的是装置而非工具的可恢复性；同时 39/39 无有效读数却写成一次『已跑』，若无 unjudged 分离，空的分子会被误读为 0% 恢复率

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

## 处置记录 2026-09-23T19:27:26+0800

已修：assertScenarioAchievable 改为在一次性副本上验证（回归断言钉住『断言前后条件不变』）；子进程不再继承 PYTHONPATH=<harness 仓库>（实测移除后 backend 仍正常）。实跑读数由此从 39/39 unjudged 变为 tool 21/22、src 9/10。残留：扩展自身 import researchctl 仍会暴露包路径，9 个场景据此探到仓库根（泄漏率 59%→35%，未归零），已作为未闭合项写入验收记录 §5.4.3
