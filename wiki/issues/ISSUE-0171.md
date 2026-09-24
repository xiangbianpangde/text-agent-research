---
id: "ISSUE-0171"
title: "种子树临时目录名含场景 id：被测子进程 pwd 即得场景名，并据此 grep 到判分源码"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "temp_dir_name_leaks_scenario_id"
  - "pwd_discloses_grading_target"
  - "answer_key_readable_by_subject"
  - "tainted_turn_passed_silently"
  - "containment_breach_second_channel"
  - "timeout_while_hunting_answer_key"
evidence: "catalog/test/recovery.ts seedAll() 原为 mkdtempSync(join(tmpdir(), 'm3-recovery-'+scenario.id+'-'))；实测 seeded root=/var/folders/.../m3-recovery-rec-semantic-rebuilt-before-p0-rDMYxl/tree，父目录名即场景 id。结果文件 catalog/test/recovery-results.jsonl 39 行中 8 行的调用 args 含判分设计路径（recovery.ts / recovery.test.ts / recovery-run.ts / recovery-results.jsonl / M3-G3-acceptance-record.md / M3-Recovery-Measurement-Contract.md）：rec-semantic-document-added 11 次、rec-semantic-db-file-deleted 11 次、src-manifests-both-deleted 6 次，命令形如 'cd /Users/xbpd/Projects/researchctl-product && sed -n 1140,1330p catalog/test/recovery.ts'。rec-semantic-rebuilt-before-p0 在 240s 内跑 'grep -ril 'rebuilt.before.p0' /Users/xbpd --include=*.py'（call #13/#14）后 timeout after 240000ms。修复后 basename(dirname(root))=m3-recovery-tree-DQPmuV，discloses id=false。"
related:
  - "ISSUE-0163"
fix_ref: null
summary: "种子树临时目录名含场景 id：被测子进程 pwd 即得场景名，并据此 grep 到判分源码"
---

## 现象

被测回合可从自己的工作目录读出正在被评分的场景名；据该名 grep 文件系统即命中 catalog/test/recovery.ts（含期望错误码、恢复步骤、判据本体）。8/39 回合读取了判分设计且全部 PASS，读数里无任何痕迹；2 个回合把全部 240s 预算耗在找答案上并被记为 timeout（读起来像『装置太慢』而非『回合去找答案』）。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

该 8 个 PASS 不可与未受污染的回合等同；tool-recoverable 的 96.2% 中含 6 个受污回合，去掉后为 19/20=95.0%（恰好压线）。§7.4 门禁与 G3 裁决均不能建立在可能已读答案的回合上。

## 根因

mkdtempSync 的 prefix 直接拼接 scenario.id；子进程 cwd 在 <dir>/tree，向上取父目录即得场景 id。此前只按『环境变量与 argv 是否含仓库路径』设计隔离（ISSUE-0163），漏掉文件系统路径名这条通道。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
