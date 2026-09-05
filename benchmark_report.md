# ResearchCTL-Bench v0.5 P0.3B Accepted Shadow Report

> **Sol 审核：PASS_P0_3B_ACCEPTED。** P0.3B 修复已接受，可开始 P0.3C；本报告仍不是公开 Research Benchmark 认证。

## 当前结果

| 项目 | 结果 | 边界 |
| --- | --- | --- |
| Oracle coverage | 33 / 33 | 全部 canonical actions 独立编译并执行 |
| 严格 Oracle 结果 | 6 PASS / 27 FAIL | 当前 ResearchCTL prediction/observation |
| CIV | 0 | 八类 classifier，checkpoint state aware |
| Formal score / IQG | `null` / `null` | P0.3C 切换前不计算 |
| Tier | `N/A` | P0 总体仍 incomplete |
| Legacy diagnostic | 33 / 33，100.0 | 仅 diagnostic namespace |

严格通过场景：S10、S11、S14、S19、S26、S30。S29 继续因当前 SQLite schema 不满足冻结 §6.7 列合同而失败；S31 的外部 SIGKILL、无半提交与恢复固定点机制通过，但 participant 返回的额外 opaque reconcile result 被 exact evaluator 正确拒绝。

## 已接受的 P0.3B 信任边界

- manifest query registry 绑定 participant-visible query 与 Gold；action 不能隐藏 expected target。
- 严格 RFC3339/UTC 时间、显式对象 lifecycle、完整 as-of 状态与 cutoff/virtual-clock 绑定。
- 全部八类 CIV 基于 checkpoint 编译状态，支持动态版本和 temporal visibility。
- 全局完整 ResultRow contract；missing/extra/opaque/contradictory metadata 与非字符串 ref 均失败。
- fail-closed Gold 不含正向答案；附带 results/facts/evidence/graph 的拒答失败。
- S14 historical binding、S17 下游传播、S18 unrelated fresh、S28 新 session + CURRENT/INDEX 均独立表达。
- `source.tar` → deterministic builder → `fixture.tar` 的闭包可复现，AppleDouble/traversal/links fail-closed。
- CLE 使用显式 read transaction 和冻结 schema/order/normalization。
- timeout/exit 清理整个 POSIX process group。
- shadow formal 字段为 null，legacy 只在 diagnostic namespace。

## 机器验证

- Harness：50 / 50 PASS。
- ResearchCTL 原回归：443 / 443 PASS。
- Fresh extracted self-contained audit bundle：50 / 50 PASS，root fixture stored/fresh fingerprint 一致。
- Canonical source/fixture 双次重建摘要：`sha256:205483526cf17db0066b55c0f097a99043443a79ed0c5fa919805537b73eea01`。
- Trust-boundary `researchctl.*` imports：0。
- Action self-award fields：0。
- 第六次 Sol 审核：`PASS — P0.3B repair accepted; P0.3C may begin`。

## 下一步

P0.3C 将默认运行路径切换为 Oracle-only：不再调用 legacy `run_sXX()`，正式指标仅从 33 个 Oracle evaluation 聚合；legacy 仅保留显式诊断开关。P0.3C 完成后 P0 仍为 incomplete，必须继续 P0.4 六类负控制。
