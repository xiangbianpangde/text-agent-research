---
id: "ISSUE-0177"
title: "intercom 的 agentName 由频道内 joinOrdinal 派生，同一 session 在不同频道会互换身份（执行者-1/执行者-2），故按该名引用的『裁决/授权』事后无法解析到人"
status: "open"
severity: "high"
area: "env"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "agent_name_derived_from_join_order"
  - "identity_label_swaps_between_channels"
  - "authority_attribution_unresolvable"
  - "mutable_identity_used_as_evidence"
  - "join_ordinal_not_identity"
evidence: "~/.pi/agent/intercom/channels.json：对全部 250 个 channel 的 500 条 membership 校验，agentName 恒等于 '执行者-' + joinOrdinal（mismatches=0），即该名是**每频道加入顺序**的函数，不是稳定身份。实测同一 peer session 01a0ccd1-6dcf-77a0-b769-70d152380549 在不同频道的名字互换：channel 605fa709(13:56)/8577c1ee(20:46) 中它叫『执行者-1』而本 session 01a0c805 叫『执行者-2』；channel f6ce34a9(22:01)/abedddaf(22:40)/82209aae(23:48)/186b5a21(00:28) 中它叫『执行者-2』而本 session 叫『执行者-1』。唯一稳定的标识是 sessionId。本条消息头 identity=执行者-2 / target=执行者-1 / channel=82209aae，按该频道 membership 解析得 sender=01a0ccd1、receiver=01a0c805，与 sessionId 一致。"
related:
  - "ISSUE-0175"
  - "ISSUE-0176"
fix_ref: null
summary: "intercom 的 agentName 由频道内 joinOrdinal 派生，同一 session 在不同频道会互换身份（执行者-1/执行者-2），故按该名引用的『裁决/授权』事后无法解析到人"
---

## 现象

查证『谁做的裁决/授权』时，按 intercom 显示的名字（执行者-1/执行者-2）检索会得到互相矛盾的结果：同一个 session 既是 seq 10 的『执行者-1』又是 seq 11 的『执行者-2』，而记录里把它们写成两个不同权威。名字在频道过期后无法回溯，故按名字写进验收记录的授权链在事后不可验证。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

验收记录（M3-G3-acceptance-record）以『执行者-1 裁决 seq 10』『执行者-2 授权 seq 11』区分权威，据 channels.json 实为**同一 session** 01a0ccd1 在两个频道的两个名字。后果不是读错一个人，而是读错『有几个独立复核者』——而独立复核正是本仓库 G3 门禁的构成要件（层 attribution 两项要求独立证据）。若按名字判独立性，会把同一人的两次发言计为两次独立复核。

## 根因

频道显示名按加入顺序分配，属于展示层便利，却被当成身份用于证据链。本仓库纪律本身要求『物理路径 > 词面精确 > 结构化元数据』且『语义/词面不得用于身份判定』，而 sessionId 是这里唯一的结构化身份；记录引用名字即违反该纪律。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
