---
id: "ISSUE-0182"
title: "测试自身能写入付费观测归档（recovery-results.jsonl），且 --run 无 preflight 门禁时会把零调用回合落盘"
status: "open"
severity: "high"
area: "researchctl"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "test_writes_paid_archive append_only_record_mutated_by_test stub_pi_reached_real_archive no_quota_but_record_altered"
evidence: "复现：按裁决方要求为 --run 加 inline preflight 门禁后做变异测试（把门禁改为 false &&）。变异体 `M3_RESULTS_PATH` 未设时，子进程 `recovery-run.ts --run --only rec-stale-nested-subdir-doc` 走到 appendFileSync，向恒真的 `catalog/test/recovery-results.jsonl` 追加第 56 行（scenario=rec-stale-nested-subdir-doc, calls=0, sha=b053fb943ed23d33）。文件 536782 → 538361 字节。**无模型回合、无额度消耗**（pi 被替换为退出码 9 的桩，且最早一次变异因 `timeout` 命令在 macOS 不存在而根本没执行）。影响实测：`--report` 读数由 22/23 变为 21/22（零调用行成为该场景的最新可用观测，把一条真观测挤掉）。修复：`RESULTS_PATH = process.env.M3_RESULTS_PATH ?? <默认>`；测试指向临时文件，并额外断言真实归档**逐字节不变**。变异验证：移除门禁 → 测试失败且归档 md5 前后一致（45e1574b23ed687d437d917f5de3e0ea）。已删除污染行并复原为 55 行。"
related:
  - "ISSUE-0180"
  - "ISSUE-0179"
fix_ref: null
summary: "测试自身能写入付费观测归档（recovery-results.jsonl），且 --run 无 preflight 门禁时会把零调用回合落盘"
---

## 现象

`catalog/test/recovery-results.jsonl` 是**追加写**的付费回合记录，其唯一价值就是可信；但它对任何调用 `--run` 的进程都可写，包括测试。本次由测试写入了一行没有任何授权回合付费的观测，而删除该行又必须人工介入——记录的可信性既依赖『没人误写』，也依赖『有人手工擦除』。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

付费观测归档被非授权写入污染，且零调用行会作为『最新观测』参与判分，直接改变 stratum 读数（22/23→21/22）。若未发现，归档将同时包含授权观测与测试产物，而二者外观完全相同——这正是本项目反复出现的失效形状：判据无法区分『我该看到的』与『我不该看到的』。

## 根因

两个独立缺口。(1) `--run` 路径未强制 preflight，故装置状态未知时仍会走到落盘（ISSUE-0180）。(2) 归档路径是硬编码常量，没有测试接缝，故任何驱动 `--run` 的测试都在对生产记录写入；追加写语义使污染不可自然消除。二者叠加才造成实际污染：缺 (1) 则测试仍只读，缺 (2) 则门禁失效也不落盘。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
