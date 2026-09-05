# ResearchCTL-Bench v0.4 P0.3A Shadow Report

> **状态：P0.3A INCOMPLETE / Tier N/A。** 本报告不构成公开 Research Benchmark、排行榜成绩或科研/生产认证。

机器权威结果见 `benchmark_report.json`。当前评测器处于 `oracle_shadow`：33 个旧场景仍作为内部回归诊断展示，只有 7 个高风险锚点已接入独立 Oracle。

## 结果摘要

| 项目 | 结果 | 证据边界 |
| --- | --- | --- |
| Legacy conformance | 33 / 33 | 仅内部、自评分诊断 |
| 独立 Oracle coverage | 7 / 33 | P0.3A shadow |
| Oracle 锚点通过 | 1 / 7 | 仅 S31 通过严格 Gold 比较 |
| Certification eligibility | `false` | `P0_3_SHADOW_MODE`、`P0_3_ORACLE_COVERAGE_INCOMPLETE` |
| Tier | `N/A` | P0.3C 前不得授予 |
| P0 总状态 | `INCOMPLETE` | P0.3B/C 与 P0.4 尚未完成 |

## 七个 P0.3A 锚点

| 场景 | Oracle 结果 | 独立测量内容 |
| --- | --- | --- |
| S03 | FAIL | 外部内容更新后仍需返回被 pin 的历史结论及哈希证据 |
| S07 | FAIL | `R052 → EXP-017@v1` 精确版本绑定；当前 prediction 未提交绑定事实 |
| S12 | FAIL | `step=100, accuracy=0.723` 单元格、真实命令及完整证据图 exact match |
| S16 | FAIL | 由依赖图反向闭包计算真实 impact set 与 TP/FP/FN |
| S17 | FAIL | Raw 失效动作后由拓扑计算真实 stale set 与传播图 |
| S24 | FAIL | 必须精确 `DEF_NOT_FOUND` fail-closed，不能用泛化错误替代 |
| S31 | PASS | Harness 发出外部 `SIGKILL`；无半提交；两次 reconcile 达到同一固定点 |

这些失败是 P0.3A 的有效发现，不是回归噪声。旧 runner 的对应 PASS 不再能作为独立 benchmark 证据。

## 已冻结的信任边界

1. `oracle-manifest/v1` 只保存客观初始世界。
2. `scenario-actions/v1` 只能描述动作和查询，拒绝 `passed`、`score`、`expected_*`、`gold_*`、TP/FP/FN 与 CIV。
3. `prediction/v1` 只能承载 SUT 的状态、结果集、证据、图和路由声明。
4. `compiled-gold/v1` 在 SUT 启动前确定性生成并封存 digest。
5. `evaluate_scenario()` 仅比较 sealed Gold 与 execution captures；场景不能自行构造分数。

## 下一阶段

P0.3B 将其余 26 个场景迁移到相同 Oracle shadow 路径。只有 P0.3C 达到 33/33 Oracle coverage、切断全部 `run_sXX()` 活跃自评分路径后，才能声明 P0.3 完成；随后仍需执行 P0.4 六类负控制。
