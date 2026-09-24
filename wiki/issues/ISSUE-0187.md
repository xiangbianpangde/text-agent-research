---
id: "ISSUE-0187"
title: "报告只对 tool-recoverable 检查 §3.2 逐码底线，source-integrity 在两个码各 4/5 时仍打印 “8/8 = 100.0%”"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "per_code_floor_checked_for_one_stratum_only source_integrity_rate_cannot_fail floor_computed_then_never_consulted test_mirrors_implementation stratum_exempt_from_floor"
evidence: "实测（59 行归档，`npm run m3:recovery -- --report`，commit 6193e2f 之前）：输出 `source-integrity: 8/8 = 100.0%`，无任何限定；而该 stratum 两个成员码均为 `SOURCE_MISSING` 4/5、`HASH_MISMATCH` 4/5。证据来源：`reportByStratum` 对两 stratum 均正确算出 `states_per_code[i].meets_minimum=false`，但 `recovery-run.ts` 的裁决块（旧 1008 行）只读 `toolRecoverable.under_sampled_codes`，`source-integrity` 的同一字段从未被任何消费者读取（`grep -n report.under_sampled_codes` 仅命中该单点）。契约依据：`docs/contracts/M3-Recovery-Measurement-Contract.md` §2.2 第 65 行「该 stratum 的每个码同样要求 ≥ 5 个独立状态（§3.2）。不因它更难造种子而豁免」，§3.2.4「不得被其他类别的成绩平均掉」。修复后同一命令输出 `INCONCLUSIVE — §3.2 floor applies to this stratum too: SOURCE_MISSING (4/5), HASH_MISMATCH (4/5)` 与 `INCONCLUSIVE — §3.2 floors unmet beyond tool-recoverable: source-integrity/SOURCE_MISSING: 4/5 ...`。变异验证：把 `gateBlockers` 恢复为只看 tool-recoverable → 新测试 FAIL（`a perfect rate must not exempt an under-sampled code in that stratum`）。"
related:
  - "ISSUE-0176"
  - "ISSUE-0174"
fix_ref: null
summary: "报告只对 tool-recoverable 检查 §3.2 逐码底线，source-integrity 在两个码各 4/5 时仍打印 “8/8 = 100.0%”"
---

## 现象

`reportByStratum` 一直正确计算每个 stratum 的逐码底线，缺陷在于**没有任何消费者读它**：裁决块只检查 `tool-recoverable` 的 `under_sampled_codes`，于是另一个 stratum 的底线被算了、打印了比率、然后被忽略。之所以在 source-integrity 上必然发生：该 stratum 没有数值阈值（判据是 disposition），所以「一个不可能失败的比率」永远不会自己引来质疑。另有一个更根本的放大器：本文件早已有一处注释记录过同类缺陷（“打印了讨喜的比率而契约底线未满足”），那次修复只把 tool-recoverable 的逐码底线接上，教训没有跨 stratum 复用。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

若按旧输出结项，会得出「source-integrity 100% 达标」的结论，而该 stratum 实际有两个码未达 §3.2 底线——属于**在有利方向上少报欠账**。同时它污染了预算申请：验收记录 §10.10 的逐码表因此过期（记 7 码缺额 / 需 9 回合），用今日判据重判实为 4 码缺额 / 需 5 回合，多申请的 4 个付费回合本不需要。

## 根因

规则被写在「打印层」而非「判定层」：底线判定散落为打印器里的一个内联过滤，于是新增/另一个 stratum 天然不被覆盖。同类根因在测试侧复现了一次：第一版回归测试把该过滤**在测试文件里重写**，只断言「测试文件里的过滤与测试文件里的过滤一致」，故把生产门禁改回缺陷行为时测试仍为绿。修法是把规则提取为 `gateBlockers(reports)`（生产代码，遍历全部 stratum），打印器与测试都调用它——使「新增 stratum 时静默漏检」在结构上不可能。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
