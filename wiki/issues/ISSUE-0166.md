---
id: "ISSUE-0166"
title: "可达成性守卫断言的是「声明码消失」，而判据要求「条件消失」：1 个 tool-recoverable 场景按合同判据不可能通过"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "guard_weaker_than_jurisdiction,achievability_proxy_not_property,unachievable_scenario_ships"
evidence: "assertScenarioAchievable 断言 recovery_steps 后『声明码不再出现』（codeOf(retry)===expects_code || issuesOf 含 expects_code 即判失败）。但判据要看的是整条链路与最终重试成功。逐场景实测（29 个 tool-recoverable，执行声明的 recovery_steps 后按 §4.3 三个入口分别取样）：rec-drift-integrity-organized-edit（声明 DRIFT_DETECTED，steps=index，retry=reconcile）恢复后 reconcile 仍为 fail_closed/HASH_MISMATCH，issues=[HASH_MISMATCH,SOURCE_CHANGED_SINCE_PIN]。原因已定位：该种子 edit 的是 organized/EXP-101/result.md，而它正是 reports/CURRENT.sources.yaml 里 content_hash: sha256:95665d2c... 的 pinned current source；改动 pinned 源文件后 reindex 只会把新字节记入新 hash，HASH_MISMATCH 由此永久成立（属 §2.2 的 source-integrity 范畴，工具无权限修）。即该场景声明的恢复动作根本不是它自己的类别的恢复动作。判分侧已实测确认：模型走声明路径（reconcile → index → reconcile）得到 HASH_MISMATCH，被判 FAIL——失败判得对，是场景错。守卫之所以漏掉：它只问『声明码是否消失』，而这里声明码 DRIFT_DETECTED 确实消失了（被 HASH_MISMATCH 顶替），于是守卫放行。修法：守卫改为断言『恢复后不再有任何 CONDITION 码（tool-recoverable ∪ source-integrity 闭集），或残留者恰为另一个类别的条件』，后者说明场景归类错而非可恢复。另注意 query 路径看不到 HASH_MISMATCH（reindex 后 query 报 success）——只按 failing_call 入口断言必然漏判，故守卫须按 §4.3 多入口取样。"
related: []
fix_ref: null
summary: "可达成性守卫断言的是「声明码消失」，而判据要求「条件消失」：1 个 tool-recoverable 场景按合同判据不可能通过"
---

## 现象

装置自证『可达成』的标准弱于它实际判分用的标准：守卫只证明声明码不再出现，判据却要求条件被清除。于是有一个场景无论模型怎么做都拿不到 PASS，而它的失败会被记成模型没修好

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
