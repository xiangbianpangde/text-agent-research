

# ResearchCTL-Bench P0 Contract — Benchmark Harness Construction

> 状态：Frozen。
>
> 适用范围：P0.1–P0.4。P1 Research Benchmark 与 P2 Leaderboard 不在本合同实施范围。
>
> 决策来源：PM-DEC-0001；延期边界：PM-DEF-0001。

## 1. 目标

将现有 ResearchCTL-Bench 从绑定本仓库实现的内部 conformance test，升级为能够独立、可复现地测量多个 SUT 的 benchmark harness。

P0 成功不以“再次获得 100 分”为标准，而以错误、退化或作弊 SUT 无法获得资格，并且第二个独立实现能通过同一协议被测量为标准。

## 2. 当前证据的合法定位

1. `researchctl/tests/` 的功能测试继续作为实现回归证据。
2. 当前 33 个场景继续作为 public toy/conformance seed，不作为公开 Research Benchmark 成绩。
3. 当前 `benchmark_report.*` 不具有公开认证效力。
4. P0 完成前禁止使用 S-Tier、A-Tier、B-Tier、Enterprise Proven、Scientific Certified 等认证措辞。

## 3. P0 实施顺序

### P0.1 — Scoring & Certification Safety

必须实现：

- 无适用样本的指标输出 `null` / `N/A`，不得默认为满分；
- 增加 `evaluation_mode`、`certification_eligible`、coverage summary 与不具备资格的原因；
- `--scenario`、`--track` 等部分运行只能输出 diagnostic/partial 结果，Tier 必须为 `N/A`；
- 修复 `--track` 实际过滤；
- composite 只在固定 coverage 合同下用于完整结果，不能只平均本次出现的 Track 后授予资格；
- 移除当前 formatter 中夸大的公开认证文案。

### P0.2 — Generic SUT Adapter

必须冻结进程级 NDJSON/JSON 协议，至少覆盖：`prepare`、`invoke`、`reset_context`、`restart`、`health`、`shutdown`。

Generic runner 与 Oracle 禁止 import `researchctl.*`。官方 ResearchCTL 必须通过和第三方相同的 adapter 接入，禁止依赖 `PYTHONPATH=os.getcwd()`。

### P0.3 — Independent Oracle & Gold Compiler

必须从独立 `oracle-manifest` 与动作序列确定性编译 pre-state、post-state、Gold result set、Gold provenance graph 与 expected condition。

Scenario 只能提交 prediction。TP、FP、FN、CIV、版本精度、图 exact match 与拒答正确性必须由独立 evaluator 计算，禁止 scenario runner 手填。

Oracle 实现禁止复用 SUT resolver、reconciler、schema 或 query 实现，以避免共因缺陷。

P0.3 按用户确认的审计路线分阶段交付：

- **P0.3A**：冻结 `oracle-manifest/v1`、`scenario-actions/v1`、`prediction/v1`、`compiled-gold/v1`，建立独立状态机、Gold compiler 与通用 evaluator，并迁移 S03/S07/S12/S16/S17/S24/S31 七个高风险锚点；状态必须保持 `INCOMPLETE`、Tier `N/A`。
- **P0.3B**：33 个场景全部进入 Oracle shadow；legacy 结果只能调试，不能进入正式指标；状态仍为 `INCOMPLETE`。
- **P0.3C**：默认路径切断全部 `run_sXX()` 自评分，33/33 由独立 Gold 计算；只有此阶段退出条件通过后，才可声明 P0.3 完成。

### P0.4 — Benchmark-of-the-Benchmark

至少提供六类负控制：Always-Pass、Always-Abstain、Universal-Stale、Universal-Impact、Random、Gold-Reader。

这些负控制均不得获得 certification eligibility 或合格结论；Gold-Reader 必须被隔离边界阻断。

## 4. 代码边界

新增职责进入现有 `bench/` 边界：

- `bench/adapters/`
- `bench/oracle/`
- `bench/dsl/`
- `bench/evaluators/`
- `bench/controls/`
- `bench/packs/`
- `bench/tests/`

保留 `bench/runner.py`、`bench/evaluator.py`、`bench/cli.py` 的公开入口并原位迁移；本阶段不创建第二套 canonical benchmark，不移动现有公开路径。

## 5. P0 退出条件

必须同时满足：

1. Generic runner 与 Oracle 对 `researchctl.*` 零 import；
2. 同一 runner 能无修改测量 ResearchCTL 与至少一个独立 baseline；
3. 所有正式实例均由独立 manifest 编译 Gold；
4. 正式指标不存在手写 TP/FP/FN 或硬编码 `passed=True`；
5. partial、缺 Track、缺 family、空分母均不能产生 Tier；
6. S12 验证精确 metric cell 与完整证据图；S16/S17 使用真实集合差；S31 验证外部终止、no-half-commit 与幂等恢复；
7. 六类负控制均无法钻过资格门；
8. 自包含干净环境中，同 task pack 与 SUT image 的 B1 双次运行产生相同字节结果与 digest。

任一条件未满足，P0 状态保持 incomplete，不得进入 P1。

## 6. P1/P2 门禁

只有 P0 退出条件全部满足且用户再次批准后，才允许启动：动态 Universe Generator、public/private/challenge split、真实 B2/B3、多模型统计评测、远程 OCI 排行榜与治理机制。

<!-- note-skills-derived-from: PM-DEC-0001; promotion_id: PROM-RCTL-BENCH-P0-CONTRACT-V1; promoted_at: 2026-09-04T04:21:34.446Z -->
