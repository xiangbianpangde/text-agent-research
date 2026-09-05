# ResearchCTL-Bench v0.6 P0.3C Oracle-Only Report

> **P0.3 Independent Oracle & Gold Compiler：COMPLETE。** P0 总体仍为 INCOMPLETE；P0.4 六类负控制尚未验收，因此 Tier N/A，本报告不构成公开 Benchmark 认证。

## 正式 Oracle 结果

| 项目 | 结果 |
| --- | --- |
| Evaluation engine | `oracle_only` |
| P0.3 status | `complete_p0_3c` |
| Oracle coverage | 33 / 33 |
| Formal passed / failed | 6 / 27 |
| Formal composite | 20.8 / 100 |
| CIV | 0 |
| Integrity gate | FAIL（指标不足） |
| Certification eligibility | `false` |
| Tier | `N/A` |
| Ineligible reason | `P0_4_NEGATIVE_CONTROLS_PENDING` |

严格通过场景：S10、S11、S14、S19、S26、S30。

S29 继续因当前 SQLite schema 不满足冻结 §6.7 列合同而失败。S31 的外部 SIGKILL、canonical no-half-commit 与两次恢复固定点检查通过，但 participant 返回的额外 opaque reconcile result 被完整 ResultRow exact evaluator 拒绝。

## P0.3C 切换证明

- 默认 CLI 的 scenario registry 来自 `bench/packs/p0_seed_v1/pack.json` 和 action DSL。
- 默认路径不访问或调用 legacy `run_sXX()`。
- 正式 `passed_scenarios`、composite、TP/FP/FN、CIV、VLP、PGEM、FCAA 与 IQG 全部由 `OracleScenarioEvaluation` 聚合。
- 默认 `legacy_diagnostic` 为空。
- `--legacy-diagnostic` 才运行旧场景；其输出只进入独立 namespace，不能改变 formal fields。
- 部分运行继续为 `diagnostic_partial` 且 Tier N/A。
- P0.4 未完成始终阻断认证资格。

## 信任边界

P0.3B 已经第六次 Sol 审核明确签字：`PASS — P0.3B repair accepted; P0.3C may begin`。其机械证据继续适用：

- 查询/Gold 单源 registry；无隐藏 target 或场景自评分。
- 严格 RFC3339/UTC、显式 lifecycle 和完整 as-of state。
- checkpoint-state 八类 CIV。
- 完整 typed ResultRow、fail-closed 附加答案拒绝、code+ref exactness。
- `source.tar` 双摘要与确定性 fixture builder。
- 固定 CLE 事务快照与进程组清理。
- root fixture fingerprint 在 fresh extraction 后 stored=fresh。

## 机器验证

- P0 Harness：53 项（P0.3C 新增 pack/default/legacy 隔离测试后，以最终测试输出为准）。
- ResearchCTL 原回归：443 / 443 PASS。
- Trust-boundary `researchctl.*` imports：0。
- Action self-award fields：0。
- 默认完整运行：Oracle-only 33/33，无 runner crash。

## 下一步

进入 P0.4 Benchmark-of-the-Benchmark，实施并验收 Always-Pass、Always-Abstain、Universal-Stale、Universal-Impact、Random、Gold-Reader 六类负控制。任何负控制均不得获得 certification eligibility 或合格结论；Gold-Reader 必须被隔离边界阻断。
