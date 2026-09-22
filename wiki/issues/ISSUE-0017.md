---
id: "ISSUE-0017"
title: "v61 run_benchmark_campaign --help executes campaign then crashes because summaries directory is absent"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-16"
discovered_by: "agent"
tags: []
signals:
  - "campaign_cli_contract,output_dir_parent"
evidence: "commit e6994d705c04dfa70d19db7024974b34f60e8fdf; run_benchmark_campaign.py:main; /tmp/r48_v61_bench_help.out"
related: []
fix_ref: "0c62c0d5b7f12890590049fc686fb674fbf630a8"
summary: "v61 run_benchmark_campaign --help executes campaign then crashes because summaries directory is absent"
updated_at: "2026-09-16"
---

## 现象

--help 未被解析，命令实际运行 20-query campaign；随后在 results/summaries/scorecard.md write_text 处因父目录不存在抛 FileNotFoundError，声明 campaign completed 但 CLI 返回失败

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

## 处置记录 2026-09-16T15:46:44+0800

v62 independent check: researchctl-bench --help exits rc=0 and prints argparse help without running campaign (/tmp/r49_v62_bench_help.out).
