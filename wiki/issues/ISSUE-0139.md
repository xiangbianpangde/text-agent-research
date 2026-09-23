---
id: "ISSUE-0139"
title: "§7.4『总成功率不下降』在 n=25 下不可判定：同代码同语料两次运行给出相反结论（PASS↔FAIL）"
status: "fixed"
severity: "high"
area: "bench"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "gate_verdict_reverses_between_runs,within_arm_variance_exceeds_between_arm_difference,insufficient_sample_for_gate,truncation_asymmetry_biases_scored_set"
evidence: "researchctl-product catalog 与 baseline 两 arm 各跑两轮同代码同语料（/tmp/m3-cat.log /tmp/m3-cat2.log /tmp/m3-base.log /tmp/m3-base2.log，逐例落盘 catalog/test/baseline-results.jsonl）。按截断排除后的同一规则：catalog run1 22/23=95.7%，run2 20/23=87.0%（臂内摆动 8.7pp）；baseline run1 20/22=90.9%，run2 19/19=100.0%（摆动 9.1pp）。§7.4 同条判定：run1 catalog 95.2% vs baseline 90.5% → PASS；run2 catalog 89.5% vs baseline 100.0% → FAIL，符号反转。25 例中 16 例的工具序列在两次运行间不同；2 例评分结果翻转（neg-transaction-keyword、neg-index-keyword 由 ok 变 MISS）。截断数 per arm：catalog 2/2、baseline 3/6，两臂被评分的集合不同，排除截断例并非中性。按 90% 基线、5pp 差异、80% power 估算需每臂约 685 例。"
related: []
fix_ref: "docs/specs/ResearchCTL-Product-v0.2-Pi-Retrieval-Journal-Spec.md#7.4.1"
summary: "§7.4『总成功率不下降』在 n=25 下不可判定：同代码同语料两次运行给出相反结论（PASS↔FAIL）"
updated_at: "2026-09-23"
---

## 现象

该门禁的判定在重复运行间翻转，且臂内摆动（8.7/9.1pp）不小于臂间差异（5.2/10.5pp）。原因有三：(1) 单例结果由模型自由发挥决定，25 例的抽样噪声远大于要检测的效应；(2) 截断例在两臂数量不同（2 vs 6），排除它们等于给截断少的一臂更多计分机会，本身带偏；(3) hard negative 的'保持干净'由'模型是否顺手问一下'决定，随机性最高。因此该条既不能判 PASS 也不能判 FAIL——正确结论是**测量精度不足**，需扩样或改判定口径。

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

## 处置记录 2026-09-23T02:16:55+0800

待裁决 + 需扩样，非代码修复项。已写入 G3 记录 §4/§9 并在 baseline.ts 输出中与判定同行打印。粗估需每臂约 685 例才能检测 5pp 差异；四轮交叉核对显示连 case 级稳定差异也不存在，故不支持退化为集合比较。

## 处置记录 2026-09-23T08:03:13+0800

2026-09 裁决：降为描述性指标，不作门禁。baseline.ts 标 obs 而非 PASS/FAIL 并同行打印两轮反转证据与单例分值。四轮交叉核对确认无稳定 case 级差异，此前优势主张已撤除。
