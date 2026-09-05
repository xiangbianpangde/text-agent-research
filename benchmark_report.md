# ResearchCTL-Bench v0.5 P0.3B Shadow Report

> **状态：P0.3B INCOMPLETE / Tier N/A。** 本报告不构成公开 Research Benchmark、排行榜成绩或科研/生产认证。

机器权威结果见 `benchmark_report.json`。当前全部 33 个 canonical 场景已进入独立 Oracle shadow，但默认路径仍同时运行 legacy `run_sXX()`；因此 formal score 尚未切换到 Oracle-only。

## 结果摘要

| 项目 | 结果 | 证据边界 |
| --- | --- | --- |
| Legacy conformance | 33 / 33 | 仅内部、自评分诊断 |
| 独立 Oracle coverage | 33 / 33 | P0.3B shadow，完整覆盖 |
| 严格 Oracle 结果 | 5 PASS / 28 FAIL | Gold + prediction/observation 独立比较 |
| Certification eligibility | `false` | `P0_3_SHADOW_MODE` |
| Tier | `N/A` | P0.3C 前不得授予 |
| P0 总状态 | `INCOMPLETE` | P0.3C 与 P0.4 尚未完成 |

## 已通过的严格场景

| 场景 | 独立证据 |
| --- | --- |
| S10 | CURRENT 的直接来源结果集与 manifest 关系一致 |
| S19 | 删除 Organized 中间文件后查询严格 fail-closed |
| S26 | 精确实体查询走结构化 current 路由，未越界使用 semantic |
| S30 | Harness 持有真实 freeze lock 时，第二写入者返回 `TX_LOCKED` |
| S31 | Harness 外部 `SIGKILL`；canonical state 无半提交；两次 reconcile 固定点一致 |

## 28 个严格失败的意义

失败不是 coverage 缺失，也不应被 legacy 33/33 掩盖。它们主要揭示：

- `prediction/v1` 未返回定义事实、版本绑定、历史事实或运行偏差；
- 未返回 S12 的精确 `0.723` 单元格、真实命令和完整证据图；
- S16/S17 的结果集与独立依赖闭包不一致；
- 多个负向场景只返回泛化 `error`/`NOT_FOUND`，不满足精确 condition；
- semantic 查询未提供 Oracle 所需的结果身份和路由声明；
- S29 被测 SQLite schema 缺少规范 §6.7 冻结的 CLE 列，评测器明确拒绝动态删列比较；
- 完整性输出未精确匹配独立推导的 hash/orphan/drift 条件。

## P0.3B 信任边界

1. 33 个 `scenario-actions/v1` 文件只描述动作和查询。
2. Action pack 中手写 `passed`、`score`、`expected_*`、`gold_*`、TP/FP/FN 或 CIV 的字段数为 0。
3. 全部场景的 `compiled-gold/v1` 在 SUT 启动前确定性生成。
4. Runner、Oracle、DSL 和 evaluator 对 `researchctl.*` import 数为 0。
5. S29 使用固定 CLE 表/列/排序/规范化合同；schema 不兼容即失败。
6. Legacy 分数明确标记为 `legacy_diagnostic_only`，不授予 Tier。

## 验证

- P0 Harness：29 / 29 PASS；包含四 Schema、33 Gold determinism、no-self-award、真实集合差、图 exact match、S29/S30/S31 状态测试。
- ResearchCTL 原回归：443 / 443 PASS。
- 完整 shadow 运行：33 / 33 Oracle coverage，无 runner crash。
- `certification_eligible=false`、`iqg_passed=false`、Tier `N/A`。

## 下一阶段

P0.3C 将删除默认运行路径对 legacy `run_sXX()` 的依赖，并仅从 33 个 Oracle evaluation 聚合正式指标。只有 Oracle-only 路径、指标与报告验收通过后，才可声明 P0.3 完成；P0 仍需随后通过 P0.4 六类负控制。
