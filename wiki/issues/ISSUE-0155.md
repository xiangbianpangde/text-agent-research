---
id: "ISSUE-0155"
title: "wiki issue_add 并发调用会竞态到同一个 ID，后写覆盖先写且仍报 ok=true"
status: "open"
severity: "high"
area: "wiki"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "issue_id_race,concurrent_issue_add_overwrites,silent_data_loss_on_write,no_atomic_id_allocation"
evidence: "同批两次 issue_add（fixture 残留索引 / 空 turn 判分）均返回 created=ISSUE-0153 且 ok=true；事后 ls wiki/issues 只有 ISSUE-0153.md，其 title 为第二条（空 turn），第一条内容消失；重新提交第一条得到 ISSUE-0154"
related: []
fix_ref: null
summary: "wiki issue_add 并发调用会竞态到同一个 ID，后写覆盖先写且仍报 ok=true"
---

## 现象

同一条消息里并发发出两个 wiki issue_add 调用时，两者都分配到同一个 ISSUE-NNNN，第二个覆盖第一个文件，但两个调用都返回 ok=true 且各自打印 created=ISSUE-NNNN。结果是一条登记的内容被静默丢弃，只靠人工比对标题才发现。ID 分配（读取最大编号 → +1 → 写文件）不是原子的，缺少文件锁或 O_EXCL 语义。

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
