# ResearchCTL-Bench P1 Contract — Reproducible B1 Research Benchmark

> 状态：Frozen（已闭合 FZ-01–FZ-08 全部机械附录，第十二轮 Sol 独立冻结审查 Job aad0919c-e9c2-4368-9959-845745e162bc 裁决 PASS，2026-09-06 正式冻结）。
>
> 适用范围：P1A–P1C。P2、B2/B3 Agent 评测、远程 OCI 与排行榜治理不在本合同实施范围。
>
> 前置条件：P0 Harness `complete_harness`；用户批准最小 P1 及 D1–D8；Sol 独立冻结审查通过 `aad0919c-e9c2-4368-9959-845745e162bc`。

## 1. 目标与成功定义

P1 将已完成的固定 33 场景 P0 Harness 升级为可复现、多实例、held-out、多 SUT 的 **B1 Kernel Research Benchmark**，并保留 P0 已冻结的 Oracle 独立性、进程协议、CIV、完整性门禁与负控制约束。

P1 成功必须同时满足：

1. 所有实例由冻结的任务族与确定性 Universe Generator 生成；
2. ResearchCTL 与至少一个完全独立的真实 baseline 通过同一个 benchmark-owned B1 API 接入；
3. public、private、local-hidden 三类 split 的语义、承诺与泄漏边界明确；
4. participant artifact 在 held-out material 可见前完成内容绑定；
5. 每个 participant/instance 重复运行，显式报告方差与 prediction 稳定性；
6. aggregate performance 与 paired baseline difference 报告冻结的 95% CI；
7. clean-room rerun 能重建实例、Gold、运行结果和统计 digest；
8. P0.4 六类负控制在 P1 路径下继续无法获得资格或合格结论。

P1 成功不要求 ResearchCTL 获得高分、通过 IQG 或胜过 baseline。

## 2. 非目标

P1 明确排除：

- B2 自然语言 Agent 路由和工具选择能力；
- B3 多会话、多模型或长程 Agent 连续性；
- LLM backbone 比较；
- 远程 OCI submission/evaluation service；
- persistent secret challenge server；
- 私有测试轮换服务、提交配额、反滥用或污染披露服务；
- 公共排行榜治理；
- S/A/B/S-Tier；
- 对 ResearchCTL 的科研、商业或生产认证。

这些能力只能由后续独立合同授权。

## 3. 公开声明边界

P1C 前只允许：

- `ResearchCTL-Bench P1 B1 benchmark candidate`；
- `dynamic B1 benchmark under construction`；
- `internal/local held-out evaluation`。

P1C 验收后首次允许：

> ResearchCTL-Bench P1 is a reproducible B1 kernel research benchmark with deterministic dynamic task generation, local held-out evaluation, independent baselines, and repeated-run statistical reporting.

涉及 hidden 时必须紧邻声明：

> The hidden split is evaluator-held during a local evaluation campaign; it is not a remote secret challenge and does not provide adversarial submission secrecy.

禁止声称：`secret challenge benchmark`、`anti-cheat leaderboard`、`unseen to all developers`、B2/B3 Agent benchmark、Tier 或 certification。

## 4. 冻结决策 D1–D8

| ID | 冻结值 |
| --- | --- |
| D1 | 8 task families / 144 instances |
| D2 | 48 public / 48 private / 48 local-hidden |
| D3 | hidden = campaign-scoped `local_evaluator_held`；不声称远程保密 |
| D4 | hidden formal validity 需要文件系统隔离和禁网；否则仅 diagnostic |
| D5 | 保留 `sut-adapter/v1`；冻结 benchmark-owned `b1-kernel/v1` virtual CLI；增加 `run_seed` |
| D6 | participant 精确 tar SHA-256 必需；本地 OCI digest 可选 |
| D7 | independent deterministic FileGraph/Lexical baseline；P0 stub/controls 不算 baseline |
| D8 | R=5；held-out 8-family macro 主指标；paired 10,000 次 cluster bootstrap 95% CI；保留 IQG 点阈值；Tier N/A |

## 5. 单一 Benchmark 与代码边界

P1 在现有 `bench/` 内扩展，不创建第二个 runner、Oracle、evaluator 或 canonical benchmark：

```text
bench/
├── adapters/                 # 现有 transport + participant artifact binding
├── oracle/                   # 现有 state/compiler + generator/seed/canonical encoding
├── dsl/                      # 现有 action/prediction contracts
├── evaluators/               # 现有 exact evaluators + repeated-run statistics
├── baselines/                # independent-filegraph-v1
├── packs/
│   ├── p0_seed_v1/           # 冻结 conformance seed，不改写
│   └── p1_b1_v1/             # release/families/commitments/public material
└── tests/
```

公开入口继续为 `bench/runner.py`、`bench/evaluator.py`、`bench/cli.py`。

P1 新增合同至少包括：

- `universe-generator/v1`；
- `task-family/v1`；
- `benchmark-release/v1`；
- `participant-artifact/v1`；
- `evaluation-series/v1`；
- `bench-cjson/v1`。

生成实例继续编译为 P0 冻结的 `oracle-manifest/v1` 与 `compiled-gold/v1`，动作流与预测协议采用严格确定性兼容增量的 `scenario-actions/v2` 与 `prediction/v2`，不得另建平行 Gold 模型。

## 6. 确定性 Universe Generator

### 6.1 Seed hierarchy

每个 split 使用独立的 256-bit cryptographically random root：`S_public`、`S_private`、`S_hidden`。三者相互独立；不得从 public root 推导 held-out root。

对 release `R`、generator version `G`、family `F@V`、ordinal `i`、rejection attempt `a`：

```text
K_instance = HMAC-SHA256(
  key = S_split,
  msg = "ResearchCTL-Bench/P1-B1/v1\0" ||
        release_id || generator_version || family_id ||
        family_version || ordinal || attempt
)
```

必须使用 domain-separated substream：`objects`、`relations`、`content`、`timestamps`、`mutation`、`actions`、`query`。

随机抽样使用 HMAC counter stream 与 unbiased integer rejection；weighted choice 只使用整数权重。禁止依赖 Python/NumPy RNG 版本、wall time、PID、filesystem order、UUID4、locale 或 platform hash order。

### 6.2 Versioning

每个实例绑定 `generator_version`、`family_id`、`family_version`、完整 family digest、split、ordinal、attempt。任何可能改变生成字节或分布的行为变更必须提升 `generator_version`；family 可执行语义变化必须提升 `family_version`。

### 6.3 Canonical encoding

`bench-cjson/v1` 冻结为：UTF-8；Unicode NFC；object key lexical sort；array order significant；禁止 NaN/Infinity；generator identity 数据禁止 JSON float；整数规范编码；compact separators；hashed bytes 无 final newline。

该合同不追溯改变 P0 digest。

### 6.4 Instance identity

`instance_descriptor` 至少包含：

- release/generator/family identity 与 digest；
- split、ordinal、attempt；
- Oracle manifest、scenario actions、source archive 与 fixture digest。

`instance_digest = SHA256(bench-cjson(instance_descriptor))` 为唯一 authority。显示 ID 使用 `RCTL1-<family>-<split>-<ordinal>-<24 hex>`，不得替代完整 digest。

### 6.5 Generation pipeline

固定顺序：derive candidate seed → construct base Universe → entities/artifacts/facts/relations → physical fixture → preassigned subvariant → mutations → action/query registry → schema validation → Gold compilation → static acceptance → accept/reject。

Gold 必须在任何 SUT 启动前编译。

### 6.6 Rejection sampling

只允许因 generator validity reject：ID collision、目标缺失、非预期 ambiguity、图约束失败、mutation 前置条件不成立、集合基数不足、metric 不适用等。

每 ordinal 最多 64 attempts；耗尽返回 `GENERATOR_REJECTION_EXHAUSTED` 并使 release 失败。禁止静默跳过 ordinal。

reject predicate 禁止读取任何 participant/ResearchCTL/baseline 输出、分数、通过状态或经验难度。

## 7. Task Families 与 144 实例

| Family | B1 capability | P0 anchors | Total | Public | Private | Hidden |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| F01 | Definition identity, authority, evolution | S01–S06 | 18 | 6 | 6 | 6 |
| F02 | Run/spec binding, runtime deviation | S07–S09 | 18 | 6 | 6 | 6 |
| F03 | Provenance graph, evidence penetration | S10–S12 | 18 | 6 | 6 | 6 |
| F04 | Historical snapshot, as-of | S13–S15 | 18 | 6 | 6 | 6 |
| F05 | Stale propagation, reverse impact | S16–S18 | 18 | 6 | 6 | 6 |
| F06 | Integrity, corruption, ambiguity, fail-closed | S19–S24, S32-B | 24 | 8 | 8 | 8 |
| F07 | Explicit kernel retrieval modes | S25–S27 | 12 | 4 | 4 | 4 |
| F08 | Rebuild, transaction, crash/restart | S28–S31, S32-A | 18 | 6 | 6 | 6 |

总计 144 = 48 public + 48 private + 48 local-hidden。

F07 只测显式指定的 kernel mode，不测 LLM 是否聪明地选择路由。F08 不得描述为完整 B3 Agent continuity。

`task-family/v1` 必须绑定 family/version/digest、B1 capability、P0 anchors、对象/操作/mutation 白名单、subvariant schedule、cardinality/temporal/topology constraints、positive/negative requirements、checkpoint types、applicable metrics、forbidden conditions 与 generation acceptance predicates。

Family spec 禁止包含手写 Gold、expected result/graph、TP/FP/FN、score 或 participant-specific logic。

144 实例只支持 aggregate B1 inference；family-level 初版结果为 descriptive，不允许 family superiority 声明。

## 8. Split 与泄漏边界

### 8.1 Public

公开 root、生成实例及 Gold-free task definitions 可入仓。用于开发/调试，不得声称 unseen。

### 8.2 Private

稳定 maintainer/evaluator holdout，不公开，不得在 artifact freeze 后用于调参。它不对 benchmark maintainer 保密。

### 8.3 Local-hidden

- `secrecy_model = local_evaluator_held`；
- root 在 campaign participants artifact 全部冻结后生成并绑定；
- 同一 campaign 对所有 participants 使用相同 hidden material；
- 非 persistent challenge；
- seed/material 为 clean-room 复现披露后，campaign 标记 `retired`，不得继续称 hidden。

### 8.4 Repository 与 commitments

仓库允许 generator、schemas、family specs、public seeds/instances、private/hidden digest commitments、release manifest 与统计代码。

仓库禁止 private/hidden plaintext root 和完整 hidden pack。若 plaintext hidden material 与 participant source 同仓可见，该 split 自动分类为 `public/contaminated`。

### 8.5 Hidden validity

Formal local-hidden 必须：participant 只见 materialized workspace；Oracle/Gold/seed/evaluator-held pack 不在 workspace/env/args；participant 文件系统读取被隔离；network disabled；报告记录 isolation backend。

主机无法提供隔离或禁网能力时，hidden result 必须 `evaluation_valid=false` 或降为 diagnostic，不得 fail-open。

## 9. B1 Semantic API 与多 SUT

### 9.1 Benchmark-owned virtual CLI

P1 将现有 command vocabulary 正式冻结为 benchmark-owned `b1-kernel/v1` virtual CLI，而非 ResearchCTL 私有 native API。每个 participant-owned adapter 将其翻译到自身实现。

保留 `sut-adapter/v1` transport，并增加：

- participant artifact identity；
- `b1-kernel/v1` capability declaration；
- 每次 invoke 的 `run_seed`；
- formal mode 禁网与 isolation evidence。

### 9.2 Neutrality

Generic runner/codec/Oracle/DSL/evaluator 禁止按 participant identity 分支或 import participant implementation。Benchmark 仓库不得提供 ResearchCTL 比 baseline 更丰富的兼容适配。

### 9.3 B1 限制

Formal B1 禁止外部 LLM API。固定 embedding/vector dependency 可作为 kernel artifact 一部分，但必须 artifact-bound 且披露。

## 10. Participant Artifact Binding

`participant-artifact/v1` 至少包含：participant ID/version、artifact type、exact artifact SHA-256、entrypoint command、adapter protocol、B1 API version、adapter digest/containment、seed mode、declared kernel dependencies、可选 source commit。

Portable mandatory binding 是 participant tar exact-byte SHA-256；本地 OCI image digest 可附加。

Evaluator 在 campaign 前哈希 exact tar，解包到 fresh read-only participant root；public/private/hidden campaign 全程不得换 artifact，结束后重新校验 digest。Participant tar 只允许 normalized relative regular files/directories，拒绝 absolute/`..`、symlink、hardlink、device/FIFO/socket、AppleDouble/PAX/xattr；entrypoint 必须在解包 root 内且 artifact root formal execution 时只读。

held-out root/material 可见后 participant code 任一字节变化都使 campaign invalid。

## 11. Independent Baseline

必须实现 `independent-filegraph-v1`：

- 与 ResearchCTL 完全独立；
- 不 import `researchctl.*`、`bench.oracle`、`bench.dsl`、`bench.evaluators` 或 benchmark packs；
- 从 materialized workspace 构建自己的状态；
- deterministic exact/lexical lookup、基础 file/source graph traversal；
- 无证据时明确 fail-closed；
- 实现完整 B1 surface，不得对多数任务返回 unsupported。

P0 stub 和六类负控制均不算 baseline。

同一 campaign 中 ResearchCTL 与 baseline 必须接收相同 instance、actions、virtual time、workspace visibility、network policy、timeout、run_seed 与硬件/环境。

## 12. 重复运行与统计协议

### 12.1 Repetitions

每个 formal instance、每个 participant 恰好 `R=5`。`run_seed(instance,repetition)` 由 benchmark 确定性派生，同一 instance/repetition 对所有 participants 相同。

Participant 声明 `seed_mode=deterministic` 或 `explicit_run_seed`。随机 participant 若不能接受并复现显式 seed，只能 diagnostic。

### 12.2 Scores

- `instance_score = mean(pass_r), r=1..5`；
- `family_score = mean(instance_score in family)`；
- primary `heldout_macro_score = unweighted mean(8 family scores)`，只使用 private + hidden；
- 另报 public macro、private macro、hidden macro、held-out micro 与现有 PGEM/VLP/SF1/IF1/FCAA/ZHR/CIV。

### 12.3 Variance

报告 5 个 round-level macro scores、mean、SD、min/max、发生 pass/fail 波动的实例比例、normalized prediction digest 波动比例。

`seed_mode=deterministic` participant 发生语义输出变化即 `DETERMINISM_CLAIM_VIOLATION`，不得靠平均隐藏。

### 12.4 Confidence intervals

使用 deterministic stratified cluster bootstrap：instance 为 resampling unit；5 repetitions 随 instance 保持成簇；每 family 内独立 resample；再计算 family 与 macro score；10,000 replicates；bootstrap seed 从 release/statistics digest 派生；双侧 95% percentile CI。

不得把 5 次 repetition 当作 5 倍独立 task samples。

### 12.5 Paired baseline comparison

ResearchCTL 与 baseline 必须对相同 instance identities paired resample。

`Δ = ResearchCTL heldout_macro_score - baseline heldout_macro_score`。只有 `lower_bound(CI95(Δ)) > 0` 才允许 superiority 声明；P1 验收不要求 superiority。

### 12.6 Missingness

Participant timeout、crash、protocol violation、malformed/no prediction 均记 failed repetition，不得删除或 retry-until-success。

Harness/environment fault 使 paired experimental unit invalid；所有 compared participants 对该 unit 一起重新运行，同时保留原 fault evidence。

### 12.7 IQG 与 multiplicity

保留点阈值：CIV=0、ZHR=0、VLP≥0.98、SF1≥0.98、IF1≥0.98、FCAA≥0.98。任何 formal repetition 的 CIV 使 integrity qualification 失败。

最小 P1 不要求 IQG 下 95% CI 超过 0.98。

唯一 primary inference 为 ResearchCTL vs baseline held-out macro；无需 multiplicity adjustment。Family 与 secondary metrics 默认 descriptive。未来新增多个 inferential hypotheses 时用 Holm-Bonferroni、family-wise α=0.05。

## 13. 评测有效性与性能分离

P1 报告必须分离：

- `harness.p0_status`；
- `harness.p1_status`；
- `evaluation_valid`；
- artifact/protocol/coverage/integrity 状态；
- held-out performance、CI、variance、baseline delta；
- `tier = N/A`。

`evaluation_valid=true` 要求 release/family/generator identity 精确、全部实例/repetition accounted、artifact bound、Gold pre-SUT、hidden isolation valid、无未解决 harness fault、统计可复现。

`evaluation_valid` 不要求高分。低分或 IQG 失败 participant 仍可得到有效的 research benchmark result。

Harness 完成不等于 participant 通过。

## 14. Evidence Bundle 与 Clean-room

Formal campaign evidence bundle 必须包含：release/generator/family identity；split commitments 与 auditor-access roots；instance lockfile/IDs/digests/attempts；manifest/action/source/fixture/Gold digests；harness 与 P0.4 attestation digest；participant artifact manifests/digests；environment/isolation；run-seed schedule；raw adapter transcript；normalized predictions；Oracle evaluations；repetition outcomes；bootstrap seed；statistics digest。

Clean-room auditor 必须能在 fresh environment：验证 digest；从 roots 重建实例；重建 manifest/action/fixture/Gold；在 pre-SUT 条件下运行同一 artifact 与 seeds；重现 seeded predictions 和统计 report digest。

禁止复用 warm cache、旧 `.index`、participant 输出、预生成 Gold 或 workspace residue。

披露 hidden root 后 campaign 必须 retired。

## 15. P1A / P1B / P1C

### P1A — Generator & Family Contract

交付：bench-cjson、HMAC counter stream、generator、8 versioned families、ID/digest、144 quota contract、public generation、rejection constraints。

退出条件：G01–G08 全部通过；48 public instances 可从 public root 跨 clean environment byte-identical 重建。

允许声明：`Dynamic B1 benchmark candidate`。

### P1B — Held-out & Multi-SUT

交付：private/local-hidden commitments、campaign lifecycle、artifact binding、benchmark-owned B1 API、真实 independent baseline、同 runner evaluation、文件隔离与禁网 capability gates。

退出条件：S01–S07、B01–B06 全部通过；ResearchCTL 和 baseline 使用相同 frozen artifacts/campaign material 被测。

允许声明：`Local held-out B1 benchmark candidate`。

### P1C — Statistics & Reproducibility

交付：R=5、variance、macro/micro、paired comparison、10k CI、missingness、完整 evidence bundle、independent clean-room rerun。

退出条件：T01–T08、R01–R08 全部通过；统计 report/digest 与 clean-room 结果一致；P0.4 controls 在 P1 路径继续拒绝。

允许声明：`Reproducible B1 kernel Research Benchmark`，必须注明 local-held-out/B1-only。

## 16. 机械验收门

### Generator / Family

- G01 同 seed/version、两个 clean environments → descriptors 与 authority digests byte-identical；
- G02 三 split roots 独立；public root 不可推导 held-out；
- G03 每实例通过现有 Oracle/DSL schemas；
- G04 rejection attempt 与 accepted bytes 可复现；
- G05 64 attempts 耗尽使 release fail；
- G06 family/generated DSL 无 Gold/self-score；
- G07 每实例 Gold pre-SUT；
- G08 精确配额 144 与 per-family/per-split allocation。

### Split / Leakage

- S01 public root 重建全部 public instances；
- S02 仓库无 private/hidden plaintext root；
- S03 split commitment 在 participant execution 前；
- S04 hidden root 在 artifacts freeze 后 campaign-bound；
- S05 participant 不可读 Oracle/Gold/held-out seed/pack；
- S06 隔离不可用使 hidden invalid/diagnostic；
- S07 hidden seed 披露后 campaign retired。

### Multi-SUT / Artifact

- B01 ResearchCTL 与 baseline 使用未修改 generic runner；
- B02 generic components 对 participant imports 为 0；
- B03 无 participant identity branch；
- B04 artifact freeze 后改一字节使 evaluation invalid；
- B05 baseline 不依赖 ResearchCTL 或 Oracle/evaluator；
- B06 baseline 实现完整 B1 surface；P0 unsupported stub 不合格。

### Statistics

- T01 每 formal unit 恰好 5 repetitions；
- T02 paired participants 使用相同 run_seed；
- T03 timeout/protocol failure 记失败不丢失；
- T04 frozen synthetic matrix 产生精确 macro/SD/CI；
- T05 paired bootstrap resample 相同 instances；
- T06 bootstrap byte/digest deterministic；
- T07 deterministic declaration variation 被检出；
- T08 secondary inference 需要 Holm correction。

### Reporting / Reproducibility

- R01 Harness 与 participant performance 字段分离；
- R02 低分 participant 可 `evaluation_valid=true`；
- R03 partial/single-family 无 formal aggregate；
- R04 Tier 始终 N/A；
- R05 hidden 标为 local evaluator-held；
- R06 clean-room 重建全部 task/Gold digest；
- R07 clean-room 重现 seeded results/statistics；
- R08 六类 P0.4 controls 在 P1 路径继续拒绝。

## 17. 禁止捷径

禁止：participant-specific benchmark code；generated task 手写 Gold；SUT 后编译 Gold；按 SUT 结果选 seed/reject；retry until pass；删除 crash/timeout 分母；从 public root 派生 held-out；提交 plaintext hidden 后仍称 hidden；把 repetition 当独立 task；以 stub/controls 冒充 baseline；held-out 可见后改 participant；不升 version 改 family semantics；恢复 legacy `run_sXX()` P1 评分；用 Harness 通过授予 participant Tier。

## 18. P1 总退出条件

只有 P1A、P1B、P1C 全部验收，且独立 clean-room evidence 通过，P1 才可标为 complete。此前状态分别为 `candidate_p1a`、`candidate_p1b`、`candidate_p1c`，不得使用完成态 Research Benchmark 声明。

P1 complete 后仍不自动启动 P2；B2/B3、远程 OCI、secret challenge 与排行榜治理需要用户另行批准和独立合同。

## 19. 规范性机械附录：冻结编码与算法

本附录是本合同唯一的机器规范与算法真值来源，具有最高权威；凡此前正文中的文字叙述若与本附录在字段、类型、顺序、算法或字节上存在出入，一律以本附录为准。本附录内所有对象均定义为 `additionalProperties: false` 闭集，禁止引入任何未声明字段。

### 19.1 规范编码与基础数据类型

#### 19.1.1 规范 JSON 编码 (bench-cjson/v1)
所有哈希预影像（preimage）与规范传输对象必须经由 `bench-cjson/v1` 序列化：
1. **允许值域**：仅允许 `null`、`boolean`、有符号 64 位整数（Int64）、Unicode NFC 字符串、数组（Array）、对象（Object）。严禁浮点数（Float）、`NaN`、`Infinity`、未编码二进制（Binary）及 UTF-16 孤立代理区（Surrogate）。
2. **规范化与键排序**：所有对象键与字符串值在解析和校验前必须完成 Unicode NFC 规范化；规范化后若产生键冲突（Key Collision），必须拒绝并判定序列化失败。对象的键按其 UTF-8 字节字典序升序（Byte Lexical Ascending Order）排序。数组元素的相对顺序必须严格保留，不得自动重排。
3. **字符串转义**：仅对双引号 `"`（U+0022）、反斜杠 `\`（U+005C）以及 C0 控制字符（U+0000 至 U+001F）进行转义。控制字符必须转义为 6 字符小写十六进制 `\u00xx`。正斜杠 `/` 严禁转义（不得输出 `\/`）。其余合法 Unicode 标量值直接以原生 UTF-8 字节编码输出。
4. **整数编码**：整数必须采用最短十进制 ASCII 字符串表示，严禁前导符号 `+`、严禁无效前导零（例如 `01`），且严禁负零 `-0`。
5. **格式紧凑**：分隔符使用最紧凑形式（键值间 `:`，元素间 `,`），严禁包含任何多余空格、制表符或末尾换行符（No Final Newline）。

#### 19.1.2 基础类型与字面量模式
- **Digest**：精确匹配正则 `^sha256:[0-9a-f]{64}$` 的小写 ASCII 字符串，表示 32 字节哈希值。在 KDF 内部运算时使用其去除 `sha256:` 前缀后的原始 32 字节二进制（Raw 32 Bytes）。
- **Hex32**：精确匹配正则 `^[0-9a-f]{64}$` 的 64 位小写十六进制字符串（即未带 `sha256:` 前缀的 32 字节十六进制表达）。
- **UInt32**：范围在 `0` 至 `2^32 - 1`（即 `0..4294967295`）内的无符号整数。在帧协议中采用 4 字节大端序二进制（`>I`）编码。
- **UInt64**：范围在 `0` 至 `2^64 - 1` 内的无符号整数。在计数器流中采用 8 字节大端序二进制（`>Q`）编码。
- **Int64**：范围在 `-2^63` 至 `2^63 - 1` 内的有符号整数。
- **Decimal**：评测报告中所有浮点、比率、分数与统计量必须采用精确 12 位小数的 ASCII 字符串编码（匹配正则 `^-?(0|[1-9][0-9]*)\.[0-9]{12}$`），在不可用、分母为 0 或未完成评测时显式取 `null`。计算过程必须以有理数（Exact Rational）分数累加并保持分子分母精度；开方运算采用正确舍入的十进制高精度算术；最终输出采用向偶数舍入（Round-Half-Even）严格保留 12 位小数（例如 `0.7` 编码为 `"0.700000000000"`，`0` 编码为 `"0.000000000000"`）。严禁 IEEE-754 二进制浮点数直接进入规范输出。

---

### 19.2 配额与指标规范

#### 19.2.1 配额规范 (quota-profile/v1) 与 144 实例分布
全量 144 个实例在 8 个任务族（F01–F08）和 3 个划分（Public、Private、Local-Hidden）中的实例配额完全由 `quota-profile/v1` 冻结。

| 任务族 | B1 核心能力 | Public | Private | Local-Hidden | 总计 (Total) | Held-Out (Private+Hidden) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| **F01** | 定义身份、权威性与演化 | 6 | 6 | 6 | 18 | 12 |
| **F02** | Run/Spec 绑定与运行时偏差 | 6 | 6 | 6 | 18 | 12 |
| **F03** | 溯源图与证据穿透 | 6 | 6 | 6 | 18 | 12 |
| **F04** | 历史快照与 As-Of 状态 | 6 | 6 | 6 | 18 | 12 |
| **F05** | 陈旧传播与逆向影响分析 | 6 | 6 | 6 | 18 | 12 |
| **F06** | 完整性、损坏、歧义与 Fail-Closed | 8 | 8 | 8 | 24 | 16 |
| **F07** | 显式内核检索路由模式 | 4 | 4 | 4 | 12 | 8 |
| **F08** | 重建、事务与崩溃恢复 | 6 | 6 | 6 | 18 | 12 |
| **总计** | **全评测规模** | **48** | **48** | **48** | **144** | **96** |

`quota-profile/v1` 的精确规范 JSON 字节为：
```json
{"families":["F01","F02","F03","F04","F05","F06","F07","F08"],"family_quotas":{"F01":{"local_hidden":6,"private":6,"public":6,"total":18},"F02":{"local_hidden":6,"private":6,"public":6,"total":18},"F03":{"local_hidden":6,"private":6,"public":6,"total":18},"F04":{"local_hidden":6,"private":6,"public":6,"total":18},"F05":{"local_hidden":6,"private":6,"public":6,"total":18},"F06":{"local_hidden":8,"private":8,"public":8,"total":24},"F07":{"local_hidden":4,"private":4,"public":4,"total":12},"F08":{"local_hidden":6,"private":6,"public":6,"total":18}},"schema_version":"quota-profile/v1","split_totals":{"local_hidden":48,"private":48,"public":48},"total_instances":144}
```
其 SHA-256 摘要冻结为：
`quota_profile_digest = sha256:6c26fb4ce20da8030fdef949292925115441c73471562b93275c4a83fe65dbb6`。

#### 19.2.2 序号 (Ordinal) 作用域规则
实例在生成和锁定时分配 `ordinal`（UInt32）。`ordinal` 的作用域严格为每个 `(family_id, split)` 对，从 `0` 开始连续递增，严禁跳号：
- 对于 F01、F02、F03、F04、F05、F08：其 `public`、`private`、`local-hidden` 的 `ordinal` 取值范围各为 `0..5`（各 6 个实例）。
- 对于 F06：其 `public`、`private`、`local-hidden` 的 `ordinal` 取值范围各为 `0..7`（各 8 个实例）。
- 对于 F07：其 `public`、`private`、`local-hidden` 的 `ordinal` 取值范围各为 `0..3`（各 4 个实例）。

#### 19.2.3 指标闭集规范 (metric-profile/v1)
评测报告支持的二级诊断与完整性指标闭集由 `metric-profile/v1` 冻结，共包含 $M=7$ 项指标：
```json
{"metric_ids_ordered":["CIV","FCAA","IF1","PGEM","SF1","VLP","ZHR"],"schema_version":"metric-profile/v1"}
```
其 SHA-256 摘要冻结为：
`metric_profile_digest = sha256:2e998c351aa12f82595feb1c935b359bbd1e677a44a2c159c878455ef0fb69be`。

---

### 19.3 任务族、生成器与发布身份预影像

#### 19.3.1 任务族规范 (task-family/v1) 与身份
每个任务族定义必须完全符合 `task-family/v1` 规范模式，所有 18 个顶层字段均为必填项，`additionalProperties: false`：
- `schema_version` (String): 固定为常量 `"task-family/v1"`；
- `family_id` (String): 必须为 `"F01"` 至 `"F08"` 之一；
- `family_version` (String): 匹配语义版本正则 `^[0-9]+\.[0-9]+\.[0-9]+$`（例如 `"1.0.0"`）；
- `capability` (String): 任务族对应的 B1 内核能力描述；
- `p0_anchors` (String 数组): 该族继承的 P0 场景锚点标识数组（非空）；
- `object_kinds` (String 数组): 允许的对象类型，元素限定为 `"entity" | "artifact"`；
- `operation_allowlist` (String 数组): 允许的操作列表，元素限定为 21 项 B1 操作之一；
- `mutation_allowlist` (String 数组): 允许的状态变异操作列表；
- `subvariant_schedule` (Object 数组): 变体调度计划，每项包含：
  - `subvariant_id` (String): 变体唯一标识；
  - `weight` (Int64): 调度权重（整数 $\ge 1$）；
  - `parameters` (Object): 闭集参数字典（`additionalProperties: false`），允许且仅允许包含以下非负 Int64 标量字段（可选）：`"branching_factor"`, `"max_depth"`, `"min_depth"`, `"noise_rate_ppm"`, `"redundancy_factor"`；严禁任何未声明参数键；
- `cardinality_constraints` (Object): 基数约束字典，必须包含 `min_entities` (Int64), `max_entities` (Int64), `min_artifacts` (Int64), `max_artifacts` (Int64)；
- `temporal_constraints` (Object): 时间约束字典，必须包含 `start_time` (RFC3339 UTC 字符串), `tick_interval_seconds` (Int64)；
- `topology_constraints` (Object): 图拓扑约束字典，必须包含 `allow_cycles` (Boolean), `max_depth` (Int64)；
- `positive_requirements` (String 数组): 正向判定条件谓词标识；
- `negative_requirements` (String 数组): 负向判定条件谓词标识；
- `checkpoint_types` (String 数组): 检查点类型列表，元素限定为 `"results" | "provenance_graph" | "asserted_facts" | "evidence"`；
- `applicable_metrics` (String 数组): 适用指标列表，元素必须属于 `metric_ids_ordered`；
- `forbidden_conditions` (String 数组): 生成期禁止出现的条件标识；
- `generation_acceptance_predicates` (String 数组): 生成验收谓词列表。
`family_body_digest = sha256:SHA256(bench-cjson(task-family/v1))`。
任务族身份对象 `FamilyIdentity` 包含：
```json
{
  "family_body_digest": Digest,
  "family_id": "F01",
  "family_schema_version": "task-family/v1",
  "family_version": "1.0.0"
}
```
`FamilyIdentity` 中的 `family_id` 与 `family_version` 必须与被哈希的 `task-family/v1` 保持严格字符相等。
`family_digest = sha256:SHA256(bench-cjson(FamilyIdentity))`。

#### 19.3.2 生成器配置与配置文件身份
- `generator-config/v1`：
  ```json
  {
    "attempt_limit": 64,
    "domain_order": ["objects", "relations", "content", "timestamps", "mutation", "actions", "query"],
    "generator_version": "universe-generator/v1",
    "metric_profile_digest": Digest,
    "quota_profile_digest": Digest,
    "schema_version": "generator-config/v1",
    "split_order": ["public", "private", "local-hidden"]
  }
  ```
  `generator_config_digest = sha256:SHA256(bench-cjson(generator-config/v1))`。
- `generator-profile/v1`：
  ```json
  {
    "domain_order": ["objects", "relations", "content", "timestamps", "mutation", "actions", "query"],
    "generator_config_digest": Digest,
    "generator_version": "universe-generator/v1",
    "schema_version": "generator-profile/v1",
    "source_tree_digest": Digest
  }
  ```
  `generator_profile_digest = sha256:SHA256(bench-cjson(generator-profile/v1))`。
- `generator_digest = sha256:SHA256(bench-cjson({"generator_profile_digest": generator_profile_digest, "generator_version": "universe-generator/v1", "schema_version": "generator/v1", "source_tree_digest": source_tree_digest}))`。

#### 19.3.3 实例描述符 (InstanceDescriptor) 与实例摘要
每个评测实例的唯一权威身份由 `InstanceDescriptor` 冻结：
```json
{
  "attempt": UInt32,
  "family_digest": Digest,
  "family_id": "F01",
  "family_version": "1.0.0",
  "fixture_tree_digest": Digest,
  "generator_version": "universe-generator/v1",
  "oracle_manifest_digest": Digest,
  "ordinal": UInt32,
  "query_registry_digest": Digest,
  "release_id": "RCTL-P1-B1-2026-01",
  "scenario_action_digest": Digest,
  "schema_version": "instance-descriptor/v1",
  "source_tree_digest": Digest,
  "split": "public" | "private" | "local-hidden"
}
```
其中：
- `oracle_manifest_digest = sha256:SHA256(bench-cjson(oracle-manifest/v1))`
- `scenario_action_digest = sha256:SHA256(bench-cjson(scenario-actions/v2))`。P1 评测动作流规范定义为 `scenario-actions/v2`，其由 P0 `scenario-actions/v1`（`bench/dsl/schemas/scenario-actions-v1.schema.json`）经以下确定性增量修改得到，其余所有属性、定义与约束保持逐字节完全相同：
  1. `$id`: 由 `"scenario-actions/v1"` 变更固定为常量 `"scenario-actions/v2"`；
  2. `properties.schema_version.const`: 由 `"scenario-actions/v1"` 变更固定为常量 `"scenario-actions/v2"`；
  3. `$defs.invokeParams`: 扩展为联合模式 `{"oneOf": [{"$ref": "#/$defs/queryParams"}, {"$ref": "#/$defs/emptyParams"}, {"$ref": "#/$defs/writeParamsWithQuery"}]}`。
  此项变更允许普通 `invoke` 步骤直接合法承载包含 `idempotency_key, actor, authorization_ref` 的写入参数，使 `freeze_report` 等带参内核操作在评测动作流中获得闭集模式约束。
- `query_registry_digest = sha256:SHA256(bench-cjson(query-registry/v1))`
- `source_tree_digest` 与 `fixture_tree_digest` 由 §19.4 `bench-tree/v1` 物理树规则计算。
- `instance_digest = sha256:SHA256(bench-cjson(InstanceDescriptor))`。
- **Display ID**：采用格式 `RCTL1-<family_id>-<split>-<ordinal>-<first24hex>`，其中 `first24hex` 为去除 `sha256:` 前缀后 `instance_digest` 的前 24 个小写十六进制字符。Display ID 仅作为人类可读标签，严禁作为机器权威身份。

#### 19.3.4 发布锁定文件 (release-lockfile/v1) 与发布摘要 (ReleaseIdentity)
- `release-lockfile/v1` 由生成器在 Release 阶段一次性生成，内部包含全部 144 个实例条目：
  ```json
  {
    "entries": [
      {
        "family_id": "F01",
        "instance_digest": Digest,
        "ordinal": 0,
        "split": "public"
      }
    ],
    "generator_version": "universe-generator/v1",
    "release_id": "RCTL-P1-B1-2026-01",
    "schema_version": "release-lockfile/v1"
  }
  ```
  `entries` 的 144 个条目必须严格按照以下顺序排序：
  1. `family_id` 字典序升序（`F01` 至 `F08`）；
  2. `split` 按照 `"public"`, `"private"`, `"local-hidden"` 的固定顺序；
  3. `ordinal` 整数升序。
  锁定文件严禁包含自身所处的发布哈希，以消除自引用循环。
  `lockfile_digest = sha256:SHA256(bench-cjson(release-lockfile/v1))`。
- `ReleaseIdentity` 汇总整个基准发布的顶层不可变身份：
  ```json
  {
    "b1_api_digest": Digest,
    "family_identities": [8 个 FamilyIdentity 对象，严格按 F01..F08 顺序排列],
    "generator_version": "universe-generator/v1",
    "lockfile_digest": Digest,
    "metric_profile_digest": Digest,
    "quota_profile_digest": Digest,
    "release_id": "RCTL-P1-B1-2026-01",
    "release_schema_version": "release-identity/v1",
    "schema_version": "release-identity/v1",
    "statistics_profile_digest": Digest
  }
  ```
  `release_digest = sha256:SHA256(bench-cjson(ReleaseIdentity))`。

#### 19.3.5 统计配置身份规范 (statistics-profile/v1)
`statistics-profile/v1` 是纯输入配置对象，冻结统计协议参数，严禁包含任何统计输出、报告哈希或自引用哈希：
```json
{
  "bootstrap_profile": "p1-bootstrap/v1",
  "estimand_id": "heldout-macro-v1",
  "generator_digest": Digest,
  "known_answer_input_digest": Digest,
  "release_lockfile_digest": Digest,
  "repetition_count": 5,
  "report_projection_version": "statistics-report/v1",
  "schema_version": "statistics-profile/v1"
}
```
其哈希公式为：
`statistics_profile_digest = sha256:SHA256(bench-cjson(statistics-profile/v1))`。
在正式发布中，`generator_digest` 取自发布的生成器摘要，`release_lockfile_digest` 取自发布锁定文件摘要，`known_answer_input_digest` 绑定 §19.11 的测试夹具摘要。

---

### 19.4 物理树规范与归档规范 (bench-tree/v1)

所有文件系统物理树（`source_tree`、`fixture_tree`、`root_tree`、`workspace_tree`）的哈希统一由 `bench-tree/v1` 算法确定性计算：
1. **仅限常规文件**：树内仅允许常规文件（Regular Files）。严禁符号链接（Symlink）、硬链接（Hardlink）、目录项实体（Directory Records）、设备文件、FIFO、套接字（Socket）、扩展属性（Extended Attributes）及 macOS AppleDouble 文件（`._*`）。
2. **路径规范**：文件相对路径必须采用 POSIX 风格，以 `/` 分隔；严禁前导斜杠 `/`；路径各组件必须为非空 Unicode NFC 字符串；严禁包含 `.`、`..` 组件或 NUL 字节。
3. **保留命名空间约束 (Reserved Namespace)**：
   为确保事务暂存与崩溃恢复的命名空间绝对隔离，工作区及归档树内所有合法文件路径严禁包含子串 `.tmp.` 或以 `.tmp` 结尾（此类路径为基准事务临时文件的全局保留命名空间）。生成器与归档校验时，若发现任何匹配 `*.tmp.*` 或 `*.tmp` 的路径，必须直接拒绝。
4. **碰撞与前缀冲突拒绝**：
   - 树中严禁出现任何重复的规范路径（包括经 Unicode NFC 规范化后冲突的路径），一旦发现重复路径必须立即拒绝并终止；
   - 严禁出现常规文件路径作为另一文件路径组件前缀的冲突（例如同时存在文件 `a` 与文件 `a/b`），一旦检测到前缀冲突必须直接拒绝。
   - 此两条拒绝校验规则对所有物理树及 USTAR 归档强制适用，校验不通过的归档一律视为非法。
5. **隐式目录**：所有目录均为隐式目录，严禁输出独立目录记录；空目录在树中被严格禁止并拒绝。
6. **路径排序与记录格式**：每个文件生成唯一的规范记录：
   `Record = Frame("path", utf8(normalized_path)) || Frame("mode", u16be(mode)) || Frame("content", file_bytes)`
   其中 `mode` 仅允许取 `0o644`（不可执行）或 `0o755`（可执行）。
   记录列表按 `utf8(normalized_path)` 字节序严格升序排序。
7. **树摘要计算**：
   `bench_tree_digest = sha256:SHA256(Record_0 || Record_1 || ... || Record_{K-1})`。
8. **传输归档 (USTAR Profile)**：分发归档必须采用严格标准化的 P0 USTAR Profile：`uid=0`, `gid=0`, `uname=""`, `gname=""`, `mtime=0`, 仅包含按上述排序的文件，无独立目录头，无 PAX/xattr 扩展头。

---

### 19.5 评估活动状态机、承诺与 Canary 隔离规范

#### 19.5.1 活动清单 (campaign-manifest/v1) 与 9 状态字段空性矩阵
评测活动由 `campaign-manifest/v1` 记录，其包含 17 个严格字段：
1. `campaign_schema_version` (`"campaign-manifest/v1"`)
2. `campaign_id` (Digest | null)
3. `release_digest` (Digest)
4. `state` (String)
5. `isolation_profile_digest` (Digest)
6. `network_policy_digest` (Digest)
7. `created_at_attestation` (RFC3339 UTC String)
8. `participant_artifact_digests_sorted` (Digest 数组 | null)
9. `artifact_set_digest` (Digest | null)
10. `campaign_digest` (Digest | null)
11. `private_root_commitment` (Digest | null)
12. `hidden_root_commitment` (Digest | null)
13. `commitment_digest` (Digest | null)
14. `materialization_evidence_digest` (Digest | null)
15. `evidence_digest` (Digest | null)
16. `disclosure_digest` (Digest | null)
17. `retired_reason` (String | null)

字段在 9 状态下的强制非空（REQ）与强制为空（NULL）矩阵如下：
| 状态 (State) | 字段 1,3..7 | 字段 2,8..10 | 字段 11..12 | 字段 13 | 字段 14 | 字段 15 | 字段 16..17 | 说明 |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| **DRAFT** | REQ | NULL | NULL | NULL | NULL | NULL | NULL | 初始草案，字段 2(campaign_id)与字段 8..17 均为 NULL |
| **ARTIFACTS_FROZEN** | REQ | REQ | NULL | NULL | NULL | NULL | NULL | 参与方制品哈希集冻结并计算 campaign_id 与 campaign_digest |
| **ROOTS_CREATED** | REQ | REQ | REQ | NULL | NULL | NULL | NULL | 私有及隐藏根物理树生成并写入承诺 |
| **COMMITTED** | REQ | REQ | REQ | REQ | NULL | NULL | NULL | 根承诺摘要汇总并写入承诺清单 |
| **MATERIALIZED** | REQ | REQ | REQ | REQ | REQ | NULL | NULL | 物化并检验物理根树，写入物化证据 |
| **EXECUTING** | REQ | REQ | REQ | REQ | REQ | NULL | NULL | 执行中，保持物化状态不可变 |
| **EVIDENCE_FROZEN** | REQ | REQ | REQ | REQ | REQ | REQ | NULL | 评测执行结束，运行系列与证据冻结 |
| **COMPLETED_UNDISCLOSED** | REQ | REQ | REQ | REQ | REQ | REQ | NULL | 评测合格完成，隐藏集保持本地隔离保留 |
| **DISCLOSED_RETIRED** | REQ | REQ | REQ | REQ | REQ | REQ | REQ | 隐藏集已披露用于复现，活动永久退役 |

#### 19.5.2 状态转换图、不可变性与转换事件 (campaign-event/v1)
唯一允许的 9 项状态转换图（Transition Graph）及其事件名称（`event_type`）为：
- `T0: DRAFT->ARTIFACTS_FROZEN`
- `T1: ARTIFACTS_FROZEN->ROOTS_CREATED`
- `T2: ROOTS_CREATED->COMMITTED`
- `T3: COMMITTED->MATERIALIZED`
- `T4: MATERIALIZED->EXECUTING`
- `T5: EXECUTING->EVIDENCE_FROZEN`
- `T6: EVIDENCE_FROZEN->COMPLETED_UNDISCLOSED`
- `T7: EVIDENCE_FROZEN->DISCLOSED_RETIRED`
- `T8: COMPLETED_UNDISCLOSED->DISCLOSED_RETIRED`

**不可变性规则与单调转换**：
1. **不可变性豁免与约束**：除字段 4（`state`）严格依照转换边从 `from_state` 更新为 `to_state` 之外，活动清单中任何字段一旦在某一状态被赋予非 null 值，在后续所有状态转换中必须保持**逐字节严格不可变**。任何对已有非空字段（非 `state`）的修改均属致命违规，导致评测活动立即失效。
2. 每次状态转换仅允许将该转换对应载荷的一组字段由 `null` 置为非空合法值，并由当前 `from_state` 原子迁入 `to_state`。
3. `campaign-event/v1` 中的 `campaign_id` 必须与清单中的 `campaign_id`（非 null 时）保持字符相等。

每个事件由闭集对象 `campaign-event/v1` 记录：
```json
{
  "campaign_id": Digest | null,
  "event_digest": Digest,
  "event_payload": {},
  "event_type": "DRAFT->ARTIFACTS_FROZEN",
  "from_state": "DRAFT",
  "previous_event_digest": Digest | null,
  "schema_version": "campaign-event/v1",
  "seq": UInt32,
  "to_state": "ARTIFACTS_FROZEN"
}
```
- `seq` 从 `0` 开始严格单调递增，严禁跳号；
- 首个事件（`seq = 0`）对应 `T0: DRAFT->ARTIFACTS_FROZEN`，其 `campaign_id=null`（在载荷中输出新生成的 `campaign_id`）, `from_state="DRAFT"`, `to_state="ARTIFACTS_FROZEN"`, `event_type="DRAFT->ARTIFACTS_FROZEN"`, `previous_event_digest=null`；
- 后续所有事件的 `campaign_id` 必须与清单中的 `campaign_id` 严格字符相等；
- 后续事件 `previous_event_digest` 必须严格等于上一事件的 `event_digest`；
- `event_digest = sha256:SHA256(bench-cjson(campaign-event/v1 excluding event_digest))`；
- 各转换事件的 `event_payload` 仅携带该转换新绑定的非空字段对象：
  - `T0`: `{"artifact_set_digest": Digest, "campaign_digest": Digest, "campaign_id": Digest, "participant_artifact_digests_sorted": [Digest, "..."]}`
  - `T1`: `{"hidden_root_commitment": Digest, "private_root_commitment": Digest}`
  - `T2`: `{"commitment_digest": Digest}`
  - `T3`: `{"materialization_evidence_digest": Digest}`
  - `T4`: `{}`
  - `T5`: `{"evidence_digest": Digest}`
  - `T6`: `{}`
  - `T7`: `{"disclosure_digest": Digest, "retired_reason": string}`
  - `T8`: `{"disclosure_digest": Digest, "retired_reason": string}`

#### 19.5.3 承诺公式、物化与证据对象规范
- `artifact_set_digest = sha256:SHA256(bench-cjson(participant_artifact_digests_sorted))`（数组由参与方完整 Digest 字符串按其解出的 32 字节原始二进制升序排序，无重复）。
- `campaign-identity/v1`:
  ```json
  {
    "artifact_set_digest": Digest,
    "created_at_attestation": string,
    "isolation_profile_digest": Digest,
    "network_policy_digest": Digest,
    "release_digest": Digest,
    "schema_version": "campaign-identity/v1"
  }
  ```
  `campaign_digest = sha256:SHA256(bench-cjson(campaign-identity/v1))`。
- `campaign_id = sha256:SHA256(bench-cjson({"artifact_set_digest": artifact_set_digest, "created_at_attestation": created_at_attestation, "release_digest": release_digest}))`。
- `root-commitment/v1`：
  ```json
  {
    "campaign_id": Digest,
    "root_kind": "private" | "hidden",
    "root_tree_digest": Digest,
    "schema_version": "root-commitment/v1"
  }
  ```
  `private_root_commitment = sha256:SHA256(bench-cjson(root-commitment/v1 with root_kind="private"))`。
  `hidden_root_commitment = sha256:SHA256(bench-cjson(root-commitment/v1 with root_kind="hidden"))`。
- `commitment/v1`：
  ```json
  {
    "artifact_set_digest": Digest,
    "campaign_id": Digest,
    "hidden_root_commitment": Digest,
    "private_root_commitment": Digest,
    "schema_version": "commitment/v1"
  }
  ```
  `commitment_digest = sha256:SHA256(bench-cjson(commitment/v1))`。
- `materialization-evidence/v1`：
  ```json
  {
    "campaign_id": Digest,
    "hidden_root_digest": Digest,
    "materialized_at_attestation": string,
    "participant_artifact_digests_sorted": [Digest, "..."],
    "private_root_digest": Digest,
    "schema_version": "materialization-evidence/v1",
    "workspace_tree_digest": Digest
  }
  ```
  `materialization_evidence_digest = sha256:SHA256(bench-cjson(materialization-evidence/v1))`。
- **物化开箱验证（Opening Verification）**：在 `T3: COMMITTED->MATERIALIZED` 时，评测机物化解包 `private_root` 与 `hidden_root`，必须验证其哈希值能完全重构承诺：
  `sha256:SHA256(bench-cjson({"campaign_id": campaign_id, "root_kind": "private", "root_tree_digest": private_root_digest, "schema_version": "root-commitment/v1"})) == private_root_commitment`；
  `sha256:SHA256(bench-cjson({"campaign_id": campaign_id, "root_kind": "hidden", "root_tree_digest": hidden_root_digest, "schema_version": "root-commitment/v1"})) == hidden_root_commitment`。
  若任一项校验不符，禁止进入物化，评测活动自动置为无效。
- `evidence-bundle/v1`：
  ```json
  {
    "campaign_id": Digest,
    "canary_transcript_digest": Digest,
    "frozen_at_attestation": string,
    "materialization_evidence_digest": Digest,
    "schema_version": "evidence-bundle/v1",
    "series_digest": Digest,
    "statistics_digest": Digest
  }
  ```
  `evidence_digest = sha256:SHA256(bench-cjson(evidence-bundle/v1))`。
- `disclosure-manifest/v1`：
  ```json
  {
    "campaign_id": Digest,
    "disclosed_at_attestation": string,
    "evidence_digest": Digest,
    "hidden_root_tree_digest": Digest,
    "retired_reason": string,
    "schema_version": "disclosure-manifest/v1"
  }
  ```
  `disclosure_digest = sha256:SHA256(bench-cjson(disclosure-manifest/v1))`。

#### 19.5.4 隐藏集隔离规范与 16 项 Canary 验证 (hidden-validity/v1)
评测机运行 local-hidden split 前必须运行 16 项确定性 Canary 探测并生成 `hidden-validity/v1` 证明：
```json
{
  "backend": "sandbox-exec" | "docker" | "containerd",
  "backend_version": string,
  "canary_targets": [
    "read:evaluator_root",
    "read:oracle_root",
    "read:gold",
    "read:private_seed",
    "read:hidden_seed",
    "read:private_pack",
    "read:hidden_pack",
    "write:evaluator_root",
    "write:oracle_root",
    "write:gold",
    "write:private_seed",
    "write:hidden_seed",
    "write:private_pack",
    "write:hidden_pack",
    "network:loopback",
    "network:external"
  ],
  "canary_transcript_digest": Digest,
  "network_policy": "deny_all",
  "policy_digest": Digest,
  "read_allowlist": ["materialized_workspace", "participant_artifact", "runtime_library"],
  "read_denylist": ["evaluator_root", "gold", "hidden_pack", "hidden_seed", "oracle_root", "private_pack", "private_seed"],
  "schema_version": "hidden-validity/v1",
  "write_allowlist": ["bounded_temp", "materialized_workspace"]
}
```
- `isolation-profile/v1`:
  ```json
  {
    "canary_targets": ["read:evaluator_root", "read:oracle_root", "read:gold", "read:private_seed", "read:hidden_seed", "read:private_pack", "read:hidden_pack", "write:evaluator_root", "write:oracle_root", "write:gold", "write:private_seed", "write:hidden_seed", "write:private_pack", "write:hidden_pack", "network:loopback", "network:external"],
    "network_policy": "deny_all",
    "read_allowlist": ["materialized_workspace", "participant_artifact", "runtime_library"],
    "read_denylist": ["evaluator_root", "gold", "hidden_pack", "hidden_seed", "oracle_root", "private_pack", "private_seed"],
    "schema_version": "isolation-profile/v1",
    "write_allowlist": ["bounded_temp", "materialized_workspace"]
  }
  ```
  `isolation_profile_digest = sha256:SHA256(bench-cjson(isolation-profile/v1))`。
  `hidden-validity/v1.policy_digest` 必须完全等同于 `isolation_profile_digest`。
- `network-policy/v1`:
  ```json
  {
    "denied_egress": ["external", "loopback"],
    "policy": "deny_all",
    "schema_version": "network-policy/v1"
  }
  ```
  `network_policy_digest = sha256:SHA256(bench-cjson(network-policy/v1))`。
- Canary 探测要求：
  - 16 项探测必须逐一执行，所有 16 项探测的返回结果必须均为失败（Denial / Blocked）；
  - 探测过程记录为有序数组 `transcript: [{"error": string, "result": "blocked", "target": string}, ...]`, 其规范哈希为 `canary_transcript_digest = sha256:SHA256(bench-cjson(transcript))`；
  - 任何一项探测成功越权访问或网络成功连通，或隔离后端不可用，必须立即将评测标记为 `evaluation_valid = false`。

---

### 19.6 B1 Virtual CLI、查询注册表与传输协议 (b1-api/v1)

#### 19.6.1 查询注册表 (query-registry/v1) 与参数非空绑定矩阵
查询操作参数由 `query-registry/v1` 解耦，保证参与方仅能通过 `query_id` 请求，无法获知 Gold 目标引用：
```json
{
  "records": [
    {
      "as_of": string | null,
      "change_type": string | null,
      "participant_locator": string | null,
      "query_id": "Q001",
      "text": string | null
    }
  ],
  "schema_version": "query-registry/v1"
}
```
- `query_id` 必须为非空非 null 字符串，全局唯一，按 UTF-8 字节升序排序；
- `query_registry_digest = sha256:SHA256(bench-cjson(query-registry/v1))` 进入实例描述符 `InstanceDescriptor`。
- **操作至必填非空注册表字段映射**：
  | B1 操作 | 必须非空（Not Null）的注册表字段 |
  | --- | --- |
  | `query_entity`, `query_exact_routing`, `query_external_basis`, `query_facts`, `query_lineage`, `query_project_current`, `query_sources`, `query_state`, `trace_evidence`, `trace_graph` | `participant_locator` |
  | `query_text_lexical`, `query_text_semantic`, `query_project_index` | `text` |
  | `query_as_of_state` | `as_of`（必须为合法 RFC3339 UTC 字符串） |
  | `impact`, `stale_status` | `participant_locator` 与 `change_type` |
  | `index`, `query_history`, `reconcile_integrity`, `tx_reconcile`, `freeze_report` | 不需要查询注册表负载字段（仅需在 query_id 存在时保证 query_id 唯一匹配） |
  若被调用的查询操作在注册表中对应的必填字段为 null 或未定义，替换程序必须在启动进程前直接判定评测失败（`status="fail_closed", error_semantic="INVALID_QUERY_REGISTRY"`）。

#### 19.6.2 B1 虚拟 CLI 闭集操作表与哈希预影像
`b1-api/v1` 严格定义全部 21 项可执行操作，按 `name` 的 Unicode 字典序严格升序排列：
```json
{
  "kernel_version": "b1-kernel/v1",
  "operations": [
    {
      "argv": ["freeze-report", "--idempotency-key", {"param": "idempotency_key"}, "--actor", {"param": "actor"}, "--authorization-ref", {"param": "authorization_ref"}],
      "conditions": ["civ", "authority", "refusal"],
      "name": "freeze_report",
      "params": ["query_id", "idempotency_key", "actor", "authorization_ref"],
      "projection": ["status", "error_semantic", "results", "evidence", "wire.run_seed_ack"]
    },
    {
      "argv": ["impact", {"registry": "participant_locator"}, "--change-type", {"registry": "change_type"}],
      "conditions": ["civ", "version", "graph", "authority"],
      "name": "impact",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "provenance_graph", "route_sequence", "as_of"]
    },
    {
      "argv": ["index"],
      "conditions": ["civ", "version", "graph", "refusal"],
      "name": "index",
      "params": [],
      "projection": ["status", "error_semantic", "results", "provenance_graph", "asserted_facts", "evidence", "retrieval_mode", "ranking_authority", "route_sequence", "as_of"]
    },
    {
      "argv": ["history", "--as-of", {"registry": "as_of"}],
      "conditions": ["civ", "version", "authority", "as_of"],
      "name": "query_as_of_state",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "asserted_facts", "evidence", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--entity", {"registry": "participant_locator"}],
      "conditions": ["civ", "version", "authority", "as_of"],
      "name": "query_entity",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "provenance_graph", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--entity", {"registry": "participant_locator"}],
      "conditions": ["civ", "routing", "refusal"],
      "name": "query_exact_routing",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "retrieval_mode", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--entity", {"registry": "participant_locator"}],
      "conditions": ["civ", "authority", "as_of"],
      "name": "query_external_basis",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "asserted_facts", "evidence", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--entity", {"registry": "participant_locator"}],
      "conditions": ["civ", "authority", "as_of"],
      "name": "query_facts",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "asserted_facts", "evidence", "route_sequence", "as_of"]
    },
    {
      "argv": ["history"],
      "conditions": ["civ", "version", "as_of"],
      "name": "query_history",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "provenance_graph", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--entity", {"registry": "participant_locator"}],
      "conditions": ["civ", "version", "authority", "as_of"],
      "name": "query_lineage",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--entity", {"registry": "participant_locator"}],
      "conditions": ["civ", "version", "authority"],
      "name": "query_project_current",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "provenance_graph", "asserted_facts", "evidence", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--text", {"registry": "text"}],
      "conditions": ["civ", "version", "routing"],
      "name": "query_project_index",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "retrieval_mode", "ranking_authority", "route_sequence", "as_of"]
    },
    {
      "argv": ["sources", {"registry": "participant_locator"}],
      "conditions": ["civ", "version", "authority", "as_of"],
      "name": "query_sources",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "evidence", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--entity", {"registry": "participant_locator"}],
      "conditions": ["civ", "version", "authority", "as_of"],
      "name": "query_state",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "asserted_facts", "evidence", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--text", {"registry": "text"}],
      "conditions": ["civ", "version", "routing"],
      "name": "query_text_lexical",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "retrieval_mode", "ranking_authority", "route_sequence", "as_of"]
    },
    {
      "argv": ["query", "--text", {"registry": "text"}, "--semantic"],
      "conditions": ["civ", "version", "routing", "authority"],
      "name": "query_text_semantic",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "retrieval_mode", "ranking_authority", "route_sequence", "as_of"]
    },
    {
      "argv": ["reconcile"],
      "conditions": ["civ", "refusal"],
      "name": "reconcile_integrity",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "evidence"]
    },
    {
      "argv": ["impact", {"registry": "participant_locator"}, "--change-type", {"registry": "change_type"}],
      "conditions": ["civ", "version", "graph", "authority"],
      "name": "stale_status",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "provenance_graph", "route_sequence", "as_of"]
    },
    {
      "argv": ["trace", {"registry": "participant_locator"}],
      "conditions": ["civ", "version", "graph", "authority"],
      "name": "trace_evidence",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "provenance_graph", "evidence", "route_sequence", "as_of"]
    },
    {
      "argv": ["trace", {"registry": "participant_locator"}],
      "conditions": ["civ", "version", "graph", "authority"],
      "name": "trace_graph",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "provenance_graph", "evidence", "route_sequence", "as_of"]
    },
    {
      "argv": ["tx-reconcile"],
      "conditions": ["civ", "refusal"],
      "name": "tx_reconcile",
      "params": ["query_id"],
      "projection": ["status", "error_semantic", "results", "evidence"]
    }
  ],
  "schema_version": "b1-api/v1"
}
```
其 SHA-256 摘要冻结为：
`b1_api_digest = sha256:e8cf1488cc32be80a53d8c8e803d9182c59623abd488c564ce504655741f8e1e`。

#### 19.6.3 检查条件与投影语法语义
- **条件语义 (conditions)**：
  - `civ`：断言完整性校验。评测机检查预测中是否存在任何虚假凭证（包括声称不存在的提交、篡改哈希、将非权威事实标记为权威等）；CIV 违规数 $> 0$ 则条件判定失败。
  - `version`：版本精确校验。评测机比对预测版本引用与 Gold 版本引用完全一致。
  - `graph`：溯源图完全匹配。评测机调用 `graph_exact_match` 比对 Gold 图的节点集合与有向边集合完全一致。
  - `authority`：权威断言校验。比对 `ranking_authority` 及事实来源权威级别。
  - `as_of`：快照截止时间校验。验证返回事实及结果均发生于 `as_of` 时间戳之前，严禁包含未来事实。
  - `routing`：检索模式与路由序列校验。验证 `retrieval_mode` 与 `route_sequence` 符合白名单。
  - `refusal`：正确拒绝校验。在输入损坏或无证据时，验证预测状态为 `fail_closed` 或 `error` 并回显预期的 `error_semantic`。
- **投影字段语法 (projection)**：
  投影列表指明从参与方返回的 `prediction/v2` 对象中提取哪些键参与评分与归一化。
  `"wire.run_seed_ack"` 为唯一特殊字段路径，指示从传输响应外层（Response Envelope）读取 `run_seed_ack` 并嵌入归一化对象的 `wire` 键下。其余所有项均严格对应 `prediction/v2` 顶层键名。

#### 19.6.4 传输层与线路协议绑定 (sut-adapter/v1)
- **请求信封（invoke）**：
  ```json
  {
    "arguments": ["query", "--entity", "EXP-017"],
    "b1_api_version": "b1-kernel/v1",
    "operation": "invoke",
    "request_id": "req-000001",
    "run_seed": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "schema_version": "sut-adapter/v1",
    "timeout_ms": 30000
  }
  ```
- **响应信封（invoke success）**：
  ```json
  {
    "exit_code": 0,
    "operation": "invoke",
    "payload": { "/* 必须为严格合法的 prediction/v2 对象 */": null },
    "request_id": "req-000001",
    "run_seed_ack": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "schema_version": "sut-adapter/v1",
    "status": "ok",
    "stderr": "",
    "stdout": ""
  }
  ```
  `run_seed_ack` 必须精确回显请求中的 `run_seed`；不一致或缺失视为协议违规，本次运行判定为失败（`pass = 0`）。
- **响应载荷规范与确定性增量 (prediction/v2)**：
  在 P1 运行中，响应载荷（`payload`）必须为严格合法的 `prediction/v2` 对象。`prediction/v2` 由 P0 `prediction/v1`（`bench/dsl/schemas/prediction-v1.schema.json`）经以下确定性增量修改定义，其余所有属性、定义、必填字段与校验约束保持逐字节完全相同：
  1. `$id`: 由 `"prediction/v1"` 变更固定为常量 `"prediction/v2"`；
  2. `properties.schema_version.const`: 由 `"prediction/v1"` 变更固定为常量 `"prediction/v2"`；
  3. `$defs.result.properties.ref`: 由 `{"type": "string"}` 放宽为 `{"type": ["string", "null"]}`。
  此项增量与下述 §19.8 的归一化规则严格一致，明确允许参与方输出省略 `ref` 或显式输出 `ref: null`。
- **健康检查信封（health success）**：
  ```json
  {
    "details": {
      "adapter": "independent-filegraph",
      "b1_api_version": "b1-kernel/v1",
      "capabilities": ["prepare", "invoke", "reset_context", "restart", "health", "shutdown"],
      "seed_mode": "deterministic" | "explicit_run_seed"
    },
    "operation": "health",
    "request_id": "req-health",
    "schema_version": "sut-adapter/v1",
    "status": "ok"
  }
  ```

---

### 19.7 独立 FileGraph Baseline 与日志规范

#### 19.7.1 独立基线语义配置 (independent-filegraph-profile/v1)
独立基线 `independent-filegraph-v1` 必须严格遵守以下规范对象：
```json
{"casefold":"default-full-casefold","current_selection":"one-current-or-fail","decode":"utf8-strict","failure_codes":["AMBIGUOUS","INVALID_FRONTMATTER","INVALID_UTF8","NOT_FOUND","UNSUPPORTED_PROOF","UNVERIFIED_REF"],"frontmatter_schema":"filegraph-frontmatter/v1","graph":"declared-frontmatter-relations-bfs","limit":"after-sort","lookup":"exact-id-version-path","normalization":"NFC","ranking":["score_desc","path_utf8","entity_id_utf8"],"schema_version":"independent-filegraph-profile/v1","score":"integer-token-multiset-intersection","token_boundaries":"UCD-General_Category-L-or-N","transaction":"journal-v1","unicode_data_version":"15.0.0","zero_score":"omit"}
```
其 SHA-256 摘要冻结为：
`filegraph_profile_digest = sha256:9df1b1509829995c465d5f50717cf31ace9448cd4a36f6b30a46abb71e27ffa6`。

#### 19.7.2 文件头部格式 (filegraph-frontmatter/v1) 与精准提取
- **帧定界字节**：
  包含 frontmatter 的文件首部字节必须精确为：
  ASCII 字节串 `@@BENCH-FRONTMATTER-BEGIN\n`（共 26 字节，末尾为十六进制 `0x0A` 单字节）；
  紧随一行紧凑的、无内部换行的 UTF-8 `bench-cjson(filegraph-frontmatter/v1)` 对象字节；
  紧随定界字节串 `\n@@BENCH-FRONTMATTER-END\n`（共 25 字节，首尾均为 `0x0A`）；
  后续为文件正文原始字节（Body Bytes）。
- **对象规范**：
  ```json
  {
    "content_hash": Digest,
    "current": boolean,
    "entity_id": string,
    "git_commit": string,
    "path": string,
    "relations": {
      "depends_on": [string, "..."],
      "derived_from": [string, "..."],
      "evidence": [string, "..."],
      "sources": [string, "..."]
    },
    "schema_version": "filegraph-frontmatter/v1",
    "status": "valid" | "invalid" | "stale" | "deprecated",
    "version": string
  }
  ```
  - `path` 必须完全等同于该文件在工作区内的 POSIX 规范相对路径；
  - `content_hash` 必须精确等于 `sha256:SHA256(Body Bytes)`；
  - `relations` 内部 4 个关系数组的元素必须为合法形式的目标引用：精确的 `entity_id@version` 字符串或工作区内 POSIX 规范相对路径；
  - 缺失定界符、非法 UTF-8、JSON 解析失败、键重复、存在未定义关系字段或类型错误，基线必须一律返回 `status="fail_closed", error_semantic="INVALID_FRONTMATTER"`。

#### 19.7.3 事务操作日志规范 (journal-v1) 与恢复状态机
- **暂存意图模型 (Staged Intents) 与路径唯一性不变式 (Unique Path Invariant)**：
  1. `journal-v1` 采用严格的暂存意图事务模型。在事务执行期间，所有变动仅记录于日志中并保存暂存内容，**物理工作区严禁被提前修改**。
  2. **路径唯一性不变式**：在单个 `journal-v1` 事务内，每个物理文件 `path` 最多只能出现一条暂存意图记录（`prepare`、`write` 或 `delete`）。同一事务内对同一路径提交多条变异意图属于非法序列，在追加至日志前必须被校验拒绝。
- **记录结构**：
  ```json
  {
    "new_digest": Digest | null,
    "old_digest": Digest | null,
    "op": "prepare" | "write" | "delete" | "commit" | "abort",
    "path": string | null,
    "seq": UInt32,
    "staged_bytes_b64": string | null
  }
  ```
- **各操作字段空性约束**：
  - `prepare`: `path` 非空字符串，`old_digest=null`，`new_digest` 为 Digest，`staged_bytes_b64` 为 Base64 编码的暂存内容。
  - `write`: `path` 非空字符串，`old_digest` 为当前物理文件 Digest，`new_digest` 为写入后目标文件 Digest，`staged_bytes_b64` 为 Base64 编码的写入内容。
  - `delete`: `path` 非空字符串，`old_digest` 为被删除文件 Digest，`new_digest=null`，`staged_bytes_b64=null`。
  - `commit`: `path=null`, `old_digest=null`, `new_digest=null`, `staged_bytes_b64=null`。
  - `abort`: `path=null`, `old_digest=null`, `new_digest=null`, `staged_bytes_b64=null`。
- **崩溃模型与崩溃原子性物化原语 (Crash-Atomic Replacement Primitive)**：
  1. **崩溃模型 (Crash Model)**：评测基准崩溃安全性涵盖进程突然终止（如 SIGKILL、OOM）及主机掉电/内核崩溃等任意指令边界的中断。持久化操作在提交与重放阶段强制执行持久顺序（`fsync` 日志文件、`fsync` 临时文件与父目录）。
  2. **单一确定性临时相对路径构造与预提交相交拒绝**：
     - **临时相对路径构造函数 $T(path, seq)$**：
       对任一条 `prepare` 或 `write` 变异记录，其目标文件 `path` 必须为规范 POSIX 相对路径。临时文件路径 $T(path, seq)$ 必须且仅能依照下列单一确定性规则在目标文件同级目录下构造相对路径，严禁使用任何替代缩写或别名语法：
       令 `parent` 为 `path` 中最后一个字符 `/` 之前的部分（若 `path` 不含 `/`，则 `parent = ""`）；
       令 `base` 为 `path` 中最后一个字符 `/` 之后的部分（若 `path` 不含 `/`，则 `base = path`）；
       临时相对路径精确定义为：
       $$T(path, seq) = (\text{parent} == "" \text{ ? "" : } \text{parent} + "/") + "." + \text{base} + ".tmp." + \text{str}(seq)$$
       例如：对于目标 `path = "a/b"`, `seq = 7`，其值为唯一的同级隐藏相对路径 `"a/.b.tmp.7"`；对于目标 `path = "foo"`, `seq = 0`，其值为唯一的同级隐藏相对路径 `".foo.tmp.0"`。结果在任何情况下均为保留在工作区内部的合法相对路径，绝不生成绝对路径或越界路径。
     - **预提交相交拒绝（Pre-Commit Disjointness Check）**：事务在提交写入 `commit` 记录前必须执行相交校验；若某条变异记录派生的 $T(path, seq)$ 命中工作区已有合法文件路径、与本事务中其他记录的临时路径重合或与另一变异记录的目标 `path` 重合，该事务直接判定非法并在提交前拒绝。
  3. **崩溃原子性替换原语**：对于 `prepare` 与 `write`，物理文件的安装必须经由临时文件的原子替换（Atomic Rename）：
     - 将 `staged_bytes_b64` 解码写入同目录临时路径 $T(path, seq)$；
     - 校验临时文件哈希精确等于 `new_digest`；
     - 执行 `fsync` 确保临时文件数据持久落盘；
     - 调用文件系统原子重命名原语（POSIX `rename` / Python `os.replace`）将临时文件覆盖至目标 `path`；
     - 执行父目录 `fsync` 确保目录项持久更新。
     对于 `delete` 操作，执行 `unlink` 并 `fsync` 父目录。
  4. **二态可观测性保证**：得益于保留命名空间隔离、预提交相交校验与原子重命名原语，物理文件 `path` 在任何时刻（包括任何阶段发生崩溃）在文件系统中**仅可能处于两种二值可观测状态之一**：要么处于操作前的原始状态（对于 `prepare` 为文件尚不存在，对于 `write` 为当前哈希精确等于 `old_digest`），要么处于操作完成后的精确目标状态（哈希精确等于 `new_digest`），绝不存在中间截断态或损坏内容。
- **物理变动点与幂等崩溃恢复状态机**：
  1. **未提交事务截断与回滚优先规则（Uncommitted Abort Priority）**：
     - 若日志中**未包含**完整合法的 `commit` 记录（包括末条为 `abort`、末尾记录在写入 `commit` 前发生截断、末行缺失 `0x0A` 换行符等一切非提交终止状态）：由于物理工作区在提交前从未被实质修改，恢复程序直接丢弃全部未提交暂存意图，仅需定向删除该日志中 `prepare` 与 `write` 记录所派生的临时路径集 $\{T(path, seq)\}$ 中可能残留的文件；工作区维持事务前初始状态，此过程视为正常回滚而非恢复损坏。
  2. **已提交事务的幂等重放规则（Committed Idempotent Replay）**：
     若日志成功以合法 `commit` 记录结尾，且各记录格式完好，恢复程序首先定向清理本日志中 `prepare` 与 `write` 记录所派生的确定性临时路径集 $\{T(path, seq)\}$ 中残留的任何临时文件（绝不进行全盘盲目通配扫描，不波及任何合法文件），随后自 `seq = 0` 依序重放暂存意图，保证中途任意次崩溃均可完全幂等恢复：
     - 对于 `prepare`（创建文件）：若目标 `path` 文件尚不存在，执行上述崩溃原子性替换原语写入目标文件；若目标 `path` 文件已存在且其当前哈希精确等于 `new_digest`，视作前次已完成原子安装，直接进入下一条；其余状态直接判定失败；
     - 对于 `write`（修改文件）：若当前文件哈希等于 `old_digest`，执行上述崩溃原子性替换原语原子覆盖目标文件；若当前文件哈希已精确等于 `new_digest`，视作前次已完成原子安装，直接进入下一条；其余状态直接判定失败；
     - 对于 `delete`（删除文件）：若当前文件存在且哈希等于 `old_digest`，删除该文件并 `fsync` 父目录；若文件已不存在，视作前次已完成删除，直接进入下一条；其余状态直接判定失败；
     - 解码后的 `staged_bytes_b64` 原始二进制哈希必须精确等于对应记录的 `new_digest`。
  3. **已提交日志的结构损坏拒绝**：若日志已包含 `commit` 记录，但内部存在 `seq` 跳号、重复、记录 JSON 语法错误或重放校验不匹配，恢复程序必须返回 `status="fail_closed", error_semantic="UNSUPPORTED_PROOF"`。

#### 19.7.4 基线一致性向量 (baseline-vector/v1)
评测机根据 `release-lockfile/v1` 的 144 个实例与其动作流中实际执行的 invoke 步骤生成向量集合：
- 每个实际调用的 invoke 步骤产生一条记录：
  ```json
  {
    "action_id": "step-1",
    "action_step": 1,
    "argv_digest": Digest,
    "expected_projection_digest": Digest,
    "instance_digest": Digest,
    "operation": "query_entity",
    "repetition": 0
  }
  ```
  - `action_step` 为 `scenario-actions/v2` 中该步骤的 1-based UInt32 整数；
  - `action_id` 固定为 `f"step-{action_step}"`；
  - `repetition` 为该向量评测对应的轮次下标（UInt32，静态一致性向量集取固定值 `0`）；
  - `argv_digest = sha256:SHA256(bench-cjson(concrete_argv_array))`；
  - `expected_projection_digest`: 取 Oracle 编译生成的 Gold 检查点中与该步骤 `capture_id` 匹配的记录，按 `b1-api/v1` 中该操作声明的 `projection` 提取对应属性；若该操作声明了 `"wire.run_seed_ack"` 投影，则额外合成属性 `wire: {"run_seed_ack": run_seed(i, repetition)}`（使用该实例在该轮次的确定性运行种子）；预期投影对象记为 `expected_projection_object`；
  - `expected_projection_digest = sha256:SHA256(bench-cjson(expected_projection_object))`；
- 记录严格按照四元组 `(instance_lockfile_index, action_step, repetition, operation)` 升序排序；
- `baseline-vector/v1` 对象：
  ```json
  {
    "profile_digest": Digest,
    "release_digest": Digest,
    "schema_version": "baseline-vector/v1",
    "vector_records": [...]
  }
  ```
  其中 `profile_digest` 必须完全等同于 `filegraph_profile_digest`。
  `conformance_vector_digest = sha256:SHA256(bench-cjson(baseline-vector/v1))`。
  发布基准必须确保 21 项 B1 操作在全量向量中至少各出现一次，且基线在此向量集上的通过率必须达到 100%。

---

### 19.8 归一化预测与全序规则 (normalized-prediction/v1)

#### 19.8.1 归一化闭集对象与子模式
评测机从 SUT 的响应中提取并构建 `normalized-prediction/v1`：
```json
{
  "as_of": string | null,
  "asserted_facts": [
    {
      "fact_id": string,
      "occurred_at": string,
      "predicate": string,
      "subject": string,
      "value": string | Int64 | boolean | null
    }
  ],
  "error_semantic": string | null,
  "evidence": [
    {
      "artifact_ref": string,
      "argv": [string, "..."] | null,
      "atom_id": string,
      "column": string | null,
      "kind": string,
      "row_key": [string, "..."] | null,
      "value": string | Int64 | boolean | null,
      "value_type": string | null
    }
  ],
  "provenance_graph": {
    "edges": [
      {
        "relation": string,
        "source_ref": string,
        "target_ref": string
      }
    ],
    "nodes": [
      {
        "node_id": string
      }
    ]
  } | null,
  "ranking_authority": string | null,
  "results": [
    {
      "content_hash": string | null,
      "entity_id": string | null,
      "git_commit": string | null,
      "is_available": boolean,
      "is_stale": boolean,
      "path": string | null,
      "ref": string | null,
      "relation_type": string | null,
      "section": string | null,
      "status": string | null,
      "version_ref": string | null
    }
  ] | null,
  "retrieval_mode": string | null,
  "route_sequence": [string, "..."],
  "schema_version": "normalized-prediction/v1",
  "status": "success" | "warning" | "error" | "fail_closed" | "review_required",
  "wire": {
    "run_seed_ack": Hex32 | null
  }
}
```

#### 19.8.2 数组全序比较与 Tie-Breaker 规则
为消除不同语言运行时字典遍历顺序差异，所有集合型数组必须按确定性全序升序排序：
1. **类型序与标量值比较**：在任何值比较中，类型优先级标签固定为：`null` 为 0；`false` 为 1；`true` 为 2；`Int64` 为 3；`string` 为 4。同类型下，`Int64` 按有符号整数数值比较；`string` 按 UTF-8 字节序字典升序比较。
2. **results 规范化与排序元组**：
   - **P1 传输层与归一化映射**：在 P1 运行中，参与方响应中的 `results[].ref` 字段遵循 `prediction/v2`，允许缺省（Omitted）或显式为 `null`；归一化程序在构造 `normalized-prediction/v1` 时，若输入结果项中 `ref` 缺失或为 `null`，一律映射为 `normalized_ref = null` 并存储在归一化结果项的 `ref` 字段中；若为有效非空字符串则保留原字符串。
   - **排序比较**：依序按 `entity_id ?? ""`、`version_ref ?? ""`、`path ?? ""`、`content_hash ?? ""`、`git_commit ?? ""`、`ref`（按类型序，null 排在最前）、`status ?? ""`、`is_stale`、`relation_type ?? ""`、`section ?? ""`、`is_available` 比较；若完全相等，以该元素自身的 `bench-cjson(result_item)` UTF-8 字节串作为终极 Tie-Breaker。
3. **asserted_facts 排序元组**：依序按 `subject`、`predicate`、`value`（按上述类型序规则）、`occurred_at`、`fact_id` 比较；相等以 `bench-cjson(fact_item)` UTF-8 字节串 Tie-Break。
4. **evidence 排序元组**：依序按 `atom_id`、`artifact_ref`、`kind`、`value`（按上述类型序规则）比较；相等以 `bench-cjson(evidence_item)` UTF-8 字节串 Tie-Break。
5. **graph.nodes 排序**：严格按 `node_id` 的 UTF-8 字节升序排序。
6. **graph.edges 排序元组**：依序按 `source_ref`、`relation`、`target_ref` 比较；相等以 `bench-cjson(edge_item)` UTF-8 字节串 Tie-Break。
7. **route_sequence**：作为调用路径流，严格保留原始数组次序，严禁排序。

#### 19.8.3 排除字段与归一化哈希
以下瞬态或非语义字段严禁进入归一化对象：
`request_id`, `capture_id`, `warnings`, `errors`, `exit_code`, `stdout`, `stderr`, 执行耗时（duration）、系统时间戳、本地绝对路径、进程 ID（PID）及任何宿主机环境特征。
若 SUT 发生协议违规、超时崩溃或未产出预测，其归一化哈希记为 `null`。在产出合法预测时：
`normalized_prediction_digest = sha256:SHA256(bench-cjson(normalized-prediction/v1))`。

---

### 19.9 种子派生、Run Seeds 与 Bootstrap 协议 (p1-bootstrap/v1)

#### 19.9.1 帧编码与分域种子派生
字段帧编码定义为：
`Frame(name, bytes) = u16be(len(ASCII(name))) || ASCII(name) || u32be(len(bytes)) || bytes`。
其中整数值采用指定宽度的无符号大端序二进制输出；字符串必须先做 Unicode NFC 规范化再转 UTF-8。

实例消息 `InstanceMessage` 由 8 个严格帧依序串联而成：
`InstanceMessage = Frame("context", utf8("ResearchCTL-Bench/P1-B1/v1")) || Frame("release_id", utf8(release_id)) || Frame("generator_version", utf8(generator_version)) || Frame("family_id", utf8(family_id)) || Frame("family_version", utf8(family_version)) || Frame("split", utf8(split)) || Frame("ordinal", u32be(ordinal)) || Frame("attempt", u32be(attempt))`。

种子与子流派生链为：
- `K_instance = HMAC-SHA256(S_split, InstanceMessage)`。
  其中 `S_split` 为 32 字节二进制密钥：对于 `public` 划分，`S_split` 固定为 32 字节已知常量 `0x00, 0x01, ..., 0x1f`；对于 `private` 和 `local-hidden`，为评测机保管的 32 字节独立保密密钥。
- `K_domain(D) = HMAC-SHA256(K_instance, Frame("domain", ASCII(D)))`。
  域标识 `D` 严格限定于闭集：`objects`, `relations`, `content`, `timestamps`, `mutation`, `actions`, `query`, `run-seed`, `bootstrap`。
- `Block(D, c) = HMAC-SHA256(K_domain(D), Frame("counter", u64be(c)))`。计数器 $c$ 从 0 开始单调递增。

#### 19.9.2 实例特异性 Run Seed 派生
对于任意实例 $i$ 与重复轮次 $r \in \{0, 1, 2, 3, 4\}$，其运行种子为 64 位小写十六进制字符串：
`run_seed(i, r) = lowercase_hex(HMAC-SHA256(K_domain("run-seed"), Frame("repetition", u32be(r))))`。
全评测 144 个实例共计产生 $144 \times 5 = 720$ 个特异性的运行种子，必须依实例严格隔离。

#### 19.9.3 无偏整数生成与加权抽取原语
- **Uniform(n)**（要求 $1 \le n \le 2^{32}$）：
  生成器各域维护独立的持久游标状态 `(c, word_index)`，初值为 `c = 0, word_index = 0`。
  每个 32 字节的 `Block(D, c)` 包含 8 个 4 字节大端序无符号整数字 $W_0, W_1, \dots, W_7$。
  令拒绝阈值 `limit = floor(2^32 / n) * n`。
  抽取循环：
  1. 读取字 $x = W_{\text{word\_index}}$；
  2. `word_index += 1`；若 `word_index == 8`，则令 `c += 1, word_index = 0`；
  3. 若 $x < limit$，返回 $x \pmod n$；
  4. 若 $x \ge limit$（落入拒绝区），丢弃该字，继续循环。
- **加权抽取（Weighted Choice）**：
  给定 $K$ 个正整数权重 $w_0, w_1, \dots, w_{K-1}$，权重总和必须满足 $1 \le W = \sum_{m=0}^{K-1} w_m \le 2^{32}$。计算前缀和 $C_j = \sum_{m=0}^j w_m$。
  调用一次 $v = \text{Uniform}(W)$（满足 $0 \le v < W$）。
  选取满足 $v < C_j$ 的最小下标 $j$，返回该项。

#### 19.9.4 分层整群 Bootstrap 算法 (p1-bootstrap/v1)
评测机采用确定性分层整群 Bootstrap 计算置信区间：
1. **分层与抽样单元**：固定为 8 个任务族（Strata = 8 families）。重抽样单元为 Held-Out 实例群（Instance Cluster），即每个抽取的实例携带其全部 5 次重复运行及参与方对照数据同时进入样本。
2. **种子派生**：
   ```json
   {
     "ordered_instance_digests": [144 个实例摘要，严格按 release-lockfile 顺序排列],
     "ordered_participant_artifact_digests": [所有参与方 Digest 字符串，按解出的 32 字节原始值升序排序],
     "release_digest": Digest,
     "statistics_profile_digest": Digest
   }
   ```
   `K_boot_bytes = SHA256(bench-cjson(bootstrap_preimage))`（32 字节原始二进制）。
   `bootstrap_seed = lowercase_hex(K_boot_bytes)`（在报告中以 64 位 Hex32 呈现）。
3. **确定性独立抽样**：
   总复制次数固定为 10,000 次（`replicate = 0..9999`）。
   对于每个任务族 $f$，其 held-out 实例候选集 $H_f$ 按 `release-lockfile/v1` 的原始顺序筛选（`private` 0..count-1，紧随 `local-hidden` 0..count-1），大小为 $N_{\text{heldout}, f}$。
   在每次复制中，对 $d = 0 .. N_{\text{heldout}, f} - 1$ 进行独立抽取：
   每个抽样步骤从初始游标 `(c=0, word_index=0)` 开始使用其独立派生密钥：
   `K_draw = HMAC-SHA256(K_boot_bytes, Frame("replicate", u32be(rep)) || Frame("family_id", ASCII(family_id)) || Frame("draw_index", u32be(d)))`。
   字流由 `HMAC-SHA256(K_draw, Frame("counter", u64be(c)))` 生成，并调用 `Uniform(N_{\text{heldout}, f})` 获得所抽取的实例下标。
4. **置信区间端点**：
   将 10,000 次复制估计值按升序严格排序得到数组 $b[0..9999]$。
   双侧 95% 置信区间端点固定取精确下标值：
   `CI95 = [b[249], b[9749]]`，严禁任何形式的线性插值（No Interpolation）。
5. **配对估计（Paired Comparison）**：
   对照差值 $\Delta = \text{heldout\_macro}[\text{focal}] - \text{heldout\_macro}[\text{baseline}]$ 在同一次重抽样复制样本中联合计算，形成 10,000 个配对差值后依同法排序取分位数。

---

### 19.10 统计估计量、方差与完整性准入检查 (IQG)

#### 19.10.1 核心估计量计算公式
对于参与方 $p$、划分 $s \in \{\text{public}, \text{private}, \text{local-hidden}\}$、任务族 $f \in \{\text{F01}..\text{F08}\}$：
1. **实例得分**：
   $$\text{instance\_score}[p, i] = \frac{1}{5} \sum_{r=0}^4 pass[p, i, r]$$
2. **划分任务族得分**：
   $$\text{split\_family\_score}[p, s, f] = \frac{1}{N_{s, f}} \sum_{i \in \text{instances}(s, f)} \text{instance\_score}[p, i]$$
3. **Held-Out 任务族得分**（仅使用 private 与 hidden）：
   $$\text{heldout\_family\_score}[p, f] = \frac{1}{N_{\text{heldout}, f}} \sum_{i \in \text{instances}(\text{private} \cup \text{hidden}, f)} \text{instance\_score}[p, i]$$
4. **Primary Held-Out 宏平均得分**（基准主指标）：
   $$\text{heldout\_macro}[p] = \frac{1}{8} \sum_{f=1}^8 \text{heldout\_family\_score}[p, f]$$
5. **各划分宏平均得分**：
   $$\text{public\_macro}[p] = \frac{1}{8} \sum_{f=1}^8 \text{split\_family\_score}[p, \text{"public"}, f]$$
   $$\text{private\_macro}[p] = \frac{1}{8} \sum_{f=1}^8 \text{split\_family\_score}[p, \text{"private"}, f]$$
   $$\text{hidden\_macro}[p] = \frac{1}{8} \sum_{f=1}^8 \text{split\_family\_score}[p, \text{"local-hidden"}, f]$$
6. **Held-Out 微平均得分**：
   $$\text{heldout\_micro}[p] = \frac{1}{96} \sum_{i \in \text{instances}(\text{private} \cup \text{hidden})} \text{instance\_score}[p, i]$$
7. **轮次宏平均与样本标准差**：
   对于轮次 $r \in \{0, 1, 2, 3, 4\}$：
   $$\text{round\_macros}[p, r] = \frac{1}{8} \sum_{f=1}^8 \left( \frac{1}{N_{\text{heldout}, f}} \sum_{i \in \text{instances}(\text{private} \cup \text{hidden}, f)} pass[p, i, r] \right)$$
   令 $\bar{R}_p = \frac{1}{5} \sum_{r=0}^4 \text{round\_macros}[p, r]$。样本标准差采用无偏估计（自由度分母为 $R - 1 = 4$）：
   $$\text{sample\_sd}[p] = \sqrt{ \frac{1}{4} \sum_{r=0}^4 (\text{round\_macros}[p, r] - \bar{R}_p)^2 }$$
   $$\min[p] = \min_{r=0..4} \text{round\_macros}[p, r], \quad \max[p] = \max_{r=0..4} \text{round\_macros}[p, r]$$

#### 19.10.2 波动率计算公式
分母固定为全量 144 个正式实例：
- **通过状态波动率**：
  $$\text{pass\_variation\_rate}[p] = \frac{1}{144} \sum_{i=1}^{144} \mathbf{1}\left[ \exists r_1, r_2 \in \{0..4\}: pass[p, i, r_1] \ne pass[p, i, r_2] \right]$$
- **预测哈希波动率**：
  $$\text{prediction\_variation\_rate}[p] = \frac{1}{144} \sum_{i=1}^{144} \mathbf{1}\left[ \exists r_1, r_2 \in \{0..4\}: \text{digest}[p, i, r_1] \ne \text{digest}[p, i, r_2] \text{ 且两者均非 null} \right]$$

#### 19.10.3 完整性准入检查 (IQG) 判定公式
IQG 在全部 96 个 held-out 实例 $\times 5$ 次重复（共 480 次评测运行）上进行微观累加（Micro-Aggregation）。
对 7 项指标，分别累加各指标在全部 480 次运行中的 $TP_m, FP_m, FN_m, Applicable_m$：
1. **覆盖率指标**：若 $Applicable_{\text{CIV}} > 0$，则 $coverage = \frac{TP_{\text{CIV}} + FP_{\text{CIV}}}{Applicable_{\text{CIV}}}$；若 $Applicable_{\text{CIV}} == 0$，则 $coverage = \text{null}$。
2. **查准率与 F1 指标精确公式**：
   - 查准率：$P_m = \frac{TP_m}{TP_m + FP_m}$（若 $TP_m + FP_m == 0$ 则为 0.0）；
   - 查全率：$R_m = \frac{TP_m}{TP_m + FN_m}$（若 $TP_m + FN_m == 0$ 则为 0.0）；
   - F1 值：$F1_m = \frac{2 \cdot P_m \cdot R_m}{P_m + R_m}$（若 $P_m + R_m == 0$ 则为 0.0）；
   - 准确率：$Acc_m = \frac{TP_m}{Applicable_m}$（若 $Applicable_m == 0$ 则为 0.0）。
3. **各具体指标标量值对应关系**：
   - `VLP`（版本沿革查准率）：取 $P_{\text{VLP}}$；
   - `SF1`（状态判定 F1）：取 $F1_{\text{SF1}}$；
   - `IF1`（影响分析 F1）：取 $F1_{\text{IF1}}$；
   - `FCAA`（事实权威准确率）：取 $Acc_{\text{FCAA}}$；
   - `PGEM`（溯源图完全匹配率）：取 $\frac{TP_{\text{PGEM}}}{Applicable_{\text{PGEM}}}$（若 $Applicable_{\text{PGEM}} == 0$ 则为 0.0），作为二级描述性诊断指标报告，不设 IQG 硬性门禁；
   - `ZHR`（幻觉违规计数）：取 $FP_{\text{ZHR}} + FN_{\text{ZHR}}$；
   - `CIV`（凭据完整性违规计数）：取 $CIV\_count$。
4. **合格判定（qualified）**：当且仅当满足以下全部硬性点阈值且无空分母时，`qualified = true`，否则一律为 `false`：
   1. $CIV\_count == 0$（零容忍）；
   2. $coverage \ne \text{null} \land coverage \ge 0.98$；
   3. $VLP \ge 0.98$；
   4. $SF1 \ge 0.98$；
   5. $IF1 \ge 0.98$；
   6. $FCAA \ge 0.98$；
   7. $ZHR == 0$。
- Public 划分的指标仅作为调试输出，严禁计入正式 IQG 判定。

#### 19.10.4 故障重跑与缺失处置规则
- **Harness Fault（评测机故障）**：因宿主机死锁、沙箱基础设施中断等评测机原因导致的失败。以 `(instance, repetition)` 为最小原子重跑单元：在该单元内将所有参与方使用原始相同 `run_seed` 共同重跑一次。若重跑成功，重跑结果覆盖原记录；若重跑仍发生 Harness Fault，最终状态记为 `"fault"`，`pass_matrix` 记为 `null`，评测活动标记为 `evaluation_valid = false`。
- **Participant Fault（参与方故障）**：参与方自身进程崩溃、超时或协议违规。严禁重跑，该轮次最终状态记为 `"fail"`，`pass_matrix` 记为整数 `0`（Int64 `0`），预测哈希记为 `null`，并在处置清单中记录为 `"participant_fault"`。

---

### 19.11 合成 Known-Answer 测试夹具与向量

为验证评测机统计与 Bootstrap 算法实现的跨平台绝对一致性，定义规范合成测试夹具 `statistics-known-answer/v1`：

#### 19.11.1 规范输入对象与哈希
该夹具包含 8 个任务族，每个族分配 2 个 held-out 实例（$I_0, I_1$），共 16 个实例条目。参与方 A 在各族 $I_0$ 的 5 次重复运行均通过（`"11111"`），$I_1$ 隔次通过（`"01010"`）；参与方 B 在各族 $I_0$ 均未通过（`"00000"`），$I_1$ 隔次通过（`"01010"`）。
其完全紧凑的规范 JSON 字节为：
```json
{"families":["F01","F02","F03","F04","F05","F06","F07","F08"],"instances":[{"bits_A":"11111","bits_B":"00000","family_id":"F01","instance_id":"I0"},{"bits_A":"01010","bits_B":"01010","family_id":"F01","instance_id":"I1"},{"bits_A":"11111","bits_B":"00000","family_id":"F02","instance_id":"I0"},{"bits_A":"01010","bits_B":"01010","family_id":"F02","instance_id":"I1"},{"bits_A":"11111","bits_B":"00000","family_id":"F03","instance_id":"I0"},{"bits_A":"01010","bits_B":"01010","family_id":"F03","instance_id":"I1"},{"bits_A":"11111","bits_B":"00000","family_id":"F04","instance_id":"I0"},{"bits_A":"01010","bits_B":"01010","family_id":"F04","instance_id":"I1"},{"bits_A":"11111","bits_B":"00000","family_id":"F05","instance_id":"I0"},{"bits_A":"01010","bits_B":"01010","family_id":"F05","instance_id":"I1"},{"bits_A":"11111","bits_B":"00000","family_id":"F06","instance_id":"I0"},{"bits_A":"01010","bits_B":"01010","family_id":"F06","instance_id":"I1"},{"bits_A":"11111","bits_B":"00000","family_id":"F07","instance_id":"I0"},{"bits_A":"01010","bits_B":"01010","family_id":"F07","instance_id":"I1"},{"bits_A":"11111","bits_B":"00000","family_id":"F08","instance_id":"I0"},{"bits_A":"01010","bits_B":"01010","family_id":"F08","instance_id":"I1"}],"release_digest":"sha256:0000000000000000000000000000000000000000000000000000000000000000","schema_version":"statistics-known-answer/v1","statistics_profile_version":"p1-statistics/v1"}
```
其 SHA-256 哈希冻结为：
`known_answer_input_digest = sha256:a8bc8261ea3eb542241a145bc2ebf2e363ebd5d526c5977088f24b742298503a`。

#### 19.11.2 合成统计配置与 Bootstrap 预影像
- 合成统计配置文件 `statistics-profile/v1` 的规范紧凑字节为：
```json
{"bootstrap_profile":"p1-bootstrap/v1","estimand_id":"heldout-macro-v1","generator_digest":"sha256:5555555555555555555555555555555555555555555555555555555555555555","known_answer_input_digest":"sha256:a8bc8261ea3eb542241a145bc2ebf2e363ebd5d526c5977088f24b742298503a","release_lockfile_digest":"sha256:4444444444444444444444444444444444444444444444444444444444444444","repetition_count":5,"report_projection_version":"statistics-report/v1","schema_version":"statistics-profile/v1"}
```
其 SHA-256 哈希冻结为：
`statistics_profile_digest = sha256:bd08e958ec639020396e8446c076bccd047989765ea7969bdae97a9ef9761eab`。
- 合成 Bootstrap 预影像包含 16 个合成实例摘要与 2 个合成参与方摘要，其规范紧凑字节为：
```json
{"ordered_instance_digests":["sha256:274c797a52a9a3545d284dbcfca8c40591f2abb65ed18c2f0c3fde4d1abd3208","sha256:59e100af12684a25695696be6c53217b4bd859e0a57eebe4986bbb981f9b37c8","sha256:27f3701b1a42df05ec1cb6e370307674aaf357bef85eed45e5e975e2abd90fa3","sha256:828f5e62b4ea6d92f2e9e83d41901fe30fa2ced1c8a5ea7aee4920546263e532","sha256:e35a53e30d5d43ce3077b44af3cc71a1f320d5ed99f5818a4701a877f23456b9","sha256:644a18d1599c63abdcaf3747567c5abf03c6fb241dad61a8a37d317db0536e6b","sha256:d064952c58409f4d4822e27bbd09f789b1146776a40e6c1b604335975251ee8b","sha256:fddf000ddc53f34ca28837b1690292b26f341ee7cb1d764d119f2a85e2cd356f","sha256:46b0a76998085a8637a6000302fcc30669825c2520575a7413ff011c2260118d","sha256:d42af5a535a96e705aca240736273ca0aa5285ffb72d46c767ec7ea7f3994847","sha256:5edcf35cc449ada4e3e4cfdd1154a6fe999a331f77dda37cb8a6b10f67623ed2","sha256:993a527a02eed9cdfb8448fe523228e2a0696627fb0a32f5d8f4e98f9ac2e152","sha256:34a25d20f3b611d23046e04a8fcb4f320160323967ba4473edeb1bedc97f2870","sha256:7c0f6699f21e52ea2a325f99b6f286891ebaafaf137ddad86c41873d9cb246c0","sha256:847902d36344a48cbdc104c98f9674a08a844eb982199ad77b80288360088a67","sha256:98bf8f517da10c999464f65abe207edb4b958f62a242631f07796f23cf65bf9c"],"ordered_participant_artifact_digests":["sha256:2222222222222222222222222222222222222222222222222222222222222222","sha256:3333333333333333333333333333333333333333333333333333333333333333"],"release_digest":"sha256:0000000000000000000000000000000000000000000000000000000000000000","statistics_profile_digest":"sha256:bd08e958ec639020396e8446c076bccd047989765ea7969bdae97a9ef9761eab"}
```
其对应的 Bootstrap 根密钥二进制为 `K_boot_bytes`，其 64 位小写十六进制字符串（即报告中的 `bootstrap_seed`）必须精确为：
`bootstrap_seed = f25bf832810e022df4c1a9ff893497c3e4fc83f844efeb0bee3221f7c03a96cf`。

#### 19.11.3 冻结的预期输出向量
在上述规范输入下，评测机经由 §19.9 与 §19.10 算法计算，必须精确输出以下 12 位小数数值：
```text
A_point     = "0.700000000000"
B_point     = "0.200000000000"
Delta       = "0.500000000000"
A_rounds    = ["0.500000000000", "1.000000000000", "0.500000000000", "1.000000000000", "0.500000000000"]
B_rounds    = ["0.000000000000", "0.500000000000", "0.000000000000", "0.500000000000", "0.000000000000"]
A_sample_sd = "0.273861278753"
B_sample_sd = "0.273861278753"
A_CI95      = ["0.550000000000", "0.850000000000"]
B_CI95      = ["0.100000000000", "0.300000000000"]
Delta_CI95  = ["0.250000000000", "0.750000000000"]
```

---

### 19.12 评测报告规范投影与类型约束

#### 19.12.1 运行系列报告 (evaluation-series/v1)
记录单次评测活动中全量 144 个实例 $\times 5$ 次重复的原始结果：
```json
{
  "campaign_digest": Digest,
  "coverage_complete": boolean,
  "harness_faults": [
    {
      "code": string,
      "instance_digest": Digest,
      "phase": string,
      "repetition": UInt32
    }
  ],
  "instance_digests_ordered": [144 个 Digest，严格匹配 release-lockfile 顺序],
  "normalized_prediction_digests": [720 个对象，按 lockfile 顺序再 repetition 升序],
  "outcomes": [720 个对象，按 lockfile 顺序再 repetition 升序],
  "participant_artifact_digest": Digest,
  "participant_faults": [
    {
      "code": string,
      "instance_digest": Digest,
      "phase": string,
      "repetition": UInt32
    }
  ],
  "release_digest": Digest,
  "repetitions": 5,
  "run_seed_schedule": [720 个对象，按 lockfile 顺序再 repetition 升序],
  "schema_version": "evaluation-series/v1",
  "seed_mode": "deterministic" | "explicit_run_seed",
  "series_digest": Digest
}
```
- `run_seed_schedule` 包含 720 条记录：`{"instance_digest": Digest, "repetition": UInt32, "run_seed": Hex32}`；
- `outcomes` 包含 720 条记录：`{"digest_or_null": Digest | null, "instance_digest": Digest, "repetition": UInt32, "score_or_null": Decimal | null, "status": "pass" | "fail" | "fault"}`；
- `normalized_prediction_digests` 包含 720 条记录：`{"digest": Digest | null, "instance_digest": Digest, "repetition": UInt32}`；
- `participant_faults` 与 `harness_faults` 按四元组 `(instance_digest, repetition, phase, code)` 严格升序排序；
- `series_digest = sha256:SHA256(bench-cjson(evaluation-series/v1 excluding series_digest))`。

#### 19.12.2 统计报告 (statistics-report/v1)
包含基准正式估计量与对比结果。正式评测要求参与方数量 $N \ge 2$（至少包含焦点被测模型与基线参与方）：
```json
{
  "bootstrap_profile": "p1-bootstrap/v1",
  "bootstrap_seed": Hex32,
  "campaign_digest": Digest,
  "ci_endpoint_indices": {
    "lower": 249,
    "upper": 9749
  },
  "coverage_disposition": [
    [
      {
        "instance_digest": Digest,
        "reason": string,
        "status": "complete" | "participant_fault" | "harness_fault" | "invalid"
      }
    ]
  ],
  "evaluation_valid": boolean,
  "family_digests_ordered": [8 个 Digest，按 F01..F08 顺序排列],
  "heldout_ci95": [
    [Decimal, Decimal]
  ],
  "heldout_family_scores": [
    [Decimal | null]
  ],
  "heldout_macro": [Decimal | null],
  "heldout_micro": [Decimal | null],
  "hidden_family_scores": [
    [Decimal | null]
  ],
  "hidden_macro": [Decimal | null],
  "instance_digests_ordered": [144 个 Digest，严格按 lockfile 顺序排列],
  "iqg": [
    {
      "civ_count": Int64,
      "coverage": Decimal | null,
      "participant_digest": Digest,
      "qualified": boolean
    }
  ],
  "max": [Decimal | null],
  "metric_count_matrix": [
    [
      [Int64, Int64, Int64, Int64]
    ]
  ],
  "metric_ids_ordered": ["CIV", "FCAA", "IF1", "PGEM", "SF1", "VLP", "ZHR"],
  "min": [Decimal | null],
  "missingness_disposition": [
    [
      {
        "instance_digest": Digest,
        "reason": string,
        "status": "complete" | "participant_fault" | "harness_fault" | "invalid"
      }
    ]
  ],
  "paired_baseline_delta": {
    "baseline_digest": Digest,
    "delta": Decimal | null,
    "focal_digest": Digest
  },
  "paired_delta_ci95": {
    "baseline_digest": Digest,
    "ci95": [Decimal, Decimal] | null,
    "focal_digest": Digest
  },
  "participant_digests_ordered": [N 个 Digest，严格按其 32 字节原始值升序排列],
  "participant_roles": {
    "baseline_digest": Digest,
    "focal_digest": Digest
  },
  "pass_matrix": [
    [
      [Int64 | null]
    ]
  ],
  "pass_variation_rate": [Decimal | null],
  "prediction_digest_matrix": [
    [
      [Digest | null]
    ]
  ],
  "prediction_variation_rate": [Decimal | null],
  "private_family_scores": [
    [Decimal | null]
  ],
  "private_macro": [Decimal | null],
  "public_family_scores": [
    [Decimal | null]
  ],
  "public_macro": [Decimal | null],
  "release_digest": Digest,
  "round_macros": [
    [Decimal | null, Decimal | null, Decimal | null, Decimal | null, Decimal | null]
  ],
  "run_seed_schedule_digest": Digest,
  "sample_sd": [Decimal | null],
  "schema_version": "statistics-report/v1",
  "split_commitments": [
    {
      "family_id": "F01",
      "hidden_digest": Digest,
      "private_digest": Digest,
      "public_digest": Digest
    }
  ],
  "statistics_digest": Digest,
  "statistics_profile_digest": Digest
}
```
- `participant_digests_ordered` 包含 $N \ge 2$ 个唯一 Digest 字符串；
- `participant_roles` 中 `focal_digest != baseline_digest` 且两者均必须出现在 `participant_digests_ordered` 中；
- 所有参与方专属数组的外层维度均为 $N$（依次对应 `participant_digests_ordered` 中的第 $0..N-1$ 个参与方）；
- `public_family_scores`, `private_family_scores`, `hidden_family_scores`, `heldout_family_scores` 的内层维度均为 8（严格对应 `F01` 至 `F08`）；
- `metric_count_matrix` 维度为 $[N][7][4]$：第 2 维对应 7 个指标（`"CIV"`, `"FCAA"`, `"IF1"`, `"PGEM"`, `"SF1"`, `"VLP"`, `"ZHR"`），第 3 维固定为 `[TP, FP, FN, Applicable]`；
- `pass_matrix` 维度为 $[N][144][5]$，元素为 `1`（pass）、`0`（fail）或 `null`（harness fault）；
- `prediction_digest_matrix` 维度为 $[N][144][5]$，元素为 `Digest` 或 `null`；
- `coverage_disposition` 与 `missingness_disposition` 维度为 $[N][144]$，第 2 维严格匹配 144 个实例在 lockfile 中的顺序；
- `heldout_ci95` 数组长度为 $N$，每个元素为 `[Decimal, Decimal] | null`（若该参与方评测无效或 heldout_macro 为 null 则取 `null`）；
- `paired_delta_ci95` 的 `ci95` 字段为 `[Decimal, Decimal] | null`；
- `split_commitments` 严格包含 8 条记录（`F01` 至 `F08`）。对每个任务族与划分，其实例摘要列表是将 `release-lockfile/v1.entries` 中匹配 `(family_id, split)` 的条目保留其锁定文件原始顺序（严格为 ordinal 升序）提取的 `instance_digest` 字符串数组：
  `public_digest = sha256:SHA256(bench-cjson({"family_id": family_id, "instance_digests": [... 该族 public 实例 digests 按 ordinal 升序 ...], "split": "public"}))`；
  `private_digest = sha256:SHA256(bench-cjson({"family_id": family_id, "instance_digests": [... 该族 private 实例 digests 按 ordinal 升序 ...], "split": "private"}))`；
  `hidden_digest = sha256:SHA256(bench-cjson({"family_id": family_id, "instance_digests": [... 该族 local-hidden 实例 digests 按 ordinal 升序 ...], "split": "local-hidden"}))`；
- `run_seed_schedule_digest = sha256:SHA256(bench-cjson(run_seed_schedule))`；
- `statistics_digest = sha256:SHA256(bench-cjson(statistics-report/v1 excluding statistics_digest))`；
- 评测环境瞬态数据、硬件信息、操作系统内核、启动时间均进入独立的 `environment-attestation/v1`，严禁渗入 `statistics-report/v1` 或参与 `statistics_digest` 计算。

## 20. Freeze Gate

P1 合同已完成 FZ-01–FZ-08 的闭集算法、schemas、状态机、B1 API 投影、确定性临时路径规范与 known-answer fixture 全部直接写入本合同 §19 规范性机械附录，并通过第十二轮 Sol 独立冻结审查（Job ID: `aad0919c-e9c2-4368-9959-845745e162bc`，裁决：`PASS — freeze P1 contract; P1A implementation may begin`）。

本合同正式转为 `Frozen`。P1A 实施准予开始。P2 保持延期并不在本合同内实施。

<!-- approved-by-user: D1-D8; approved-at: 2026-09-05; design-review: fcfb6ae8-fb21-4f6e-949c-f559fbd8d573; freeze-review: aad0919c-e9c2-4368-9959-845745e162bc (PASS, 2026-09-06) -->
