# 超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench)

> 文档性质：Benchmark 规范与自动化评测方案（specification contract v1.0）。
>
> 依据：《超长程实验 Agent 检索系统设计方案.md》（全案规范）、《超长程实验 Text Agent 检索与研究状态系统 PRD.md》、《P0-Contract.md》、《P1-C-Contract.md》，以及 Sol 专家独立审核意见（2026-09-04 闭环审查）。

---

## 1. 目标与宪法级原则

### 1.1 核心目标

本 Benchmark（正式命名为 **ResearchCTL-Bench**）服务于真实科研与工程演化场景下的超长程实验 Text Agent。

传统的 Agent 评测大多面向单轮代码补全（如 SWE-bench）或短程会话记忆（如 MemTool）。而超长程实验任务的本质特征为：
- 研究周期长达数周至数月；
- 大量 Agent 会话间歇执行、上下文不断被清空或换届；
- 实验定义持续演化产生新旧版本；
- 原始实验数据海量且不可变；
- 文件系统不可避免地存在人工编辑、Git 合并或意外漂移。

因此，**ResearchCTL-Bench 绝非普通的“科研 RAG 问答题集”**，其根本定位是：

> **“长期科研状态、版本、来源、因果与完整性可证明性基准（Long-Horizon Research State, Versioning, Provenance & Integrity Verifiability Benchmark）”**。

它的核心使命不是评估“Agent 语言模型记住了多少资料”，而是严格衡量：**在漫长的科研演化、版本漂移、上下文遗忘、多 Agent 轮替甚至部分系统损坏的严苛条件下，Agent 是否具备确定性证据链恢复能力，能否机械区分“现在是什么、当时是什么、依据来自何处、精确是哪一版、哪些下游受波及”，以及在证据不足时是否坚决不猜。**

### 1.2 六大宪法级原则 (Constitutional Invariants)

1. **事实对象优先于自然语言答案 (Typed Objects over Text)**：评测的 Gold 核心是机器可断言的确定性事实元组（`entity / version / path / content_hash / git_commit / relation`），而非一段语义模糊的自然语言。
2. **正确拒答是正确性不可分割的一部分 (Abstention is Correctness)**：在证据链断裂、实体不存在或未经授权时，**严格 Fail-Closed 并返回闭集条件码**是唯一合规反应。不知道 ≠ 失败；靠模型脑补产生“看起来合理但未经验证的答案”直接视为严重违约。
3. **当前正确不代表历史正确 (Temporal Orthogonality)**：系统必须对当前活跃状态（Current Frontier）与历史冻结状态（Historical Snapshot）独立评分，严禁拿当前最新数据粉饰历史结论。
4. **Recall 必须与 Precision 强绑定 (No Cheat by Universal Stale)**：在影响链（`impact`）与过期传导（`stale`）评测中，严禁通过“把全库所有文档均标记为 stale”的作弊手段刷高召回率；召回率（Recall）与精确率（Precision）必须联合考核。
5. **检索路径也是结果的一部分 (Path Verification)**：对于精确身份（Identity）、版本（Version）、因果（Causality）、历史（History），Agent 必须走结构化或显式阅读路径；若通过语义向量搜索（RAG）“碰巧猜中”，依然判定为检索策略违约。
6. **完整性资格门禁一票否决制 (Integrity Qualification Gate - One-Strike Disqualification)**：任何 Agent 只要出现一次伪造哈希、虚构版本或替换历史来源等学术不端级造假行为，即便问答准确率达 99%，其科研可信资格依然直接判为 **Disqualified（无科研可信资格）**。

---

## 2. 三层评测体系与被测系统隔离边界

### 2.1 三层评测分级 (Tiers B1 → B2 → B3)

```text
┌─────────────────────────────────────────────────────────────┐
│ B3: Long-Horizon Research Continuity (超长程科研连续性终局)     │
│     模拟跨数周/月、多次会话轮替、上下文压缩、新旧 Agent 换届后的科研世界重建 │
├─────────────────────────────────────────────────────────────┤
│ B2: Agent Retrieval Policy (Agent 检索路由策略与决策树)        │
│     评估 Agent 面对自然语言提问时，是否遵循确定性路径而不是盲目 RAG   │
├─────────────────────────────────────────────────────────────┤
│ B1: Kernel Deterministic Verifiability (底层检索内核确定性基准) │
│     直接驱动 researchctl CLI / API，纯机器判分，验证不变性与条件码闭集  │
└─────────────────────────────────────────────────────────────┘
```

- **B1 — Kernel Benchmark（内核确定性层）**：直接以程序调用测试 `researchctl` 内核命令，不引入任何 LLM。测试输入为规范 CLI/API 调用，输出为严格的 JSON Envelope。100% 确定性断言。
- **B2 — Agent Policy Benchmark（检索策略与路由层）**：输入为科研人员自然语言提问，由待测 Agent 主导检索。通过审计其 Tool Calls 序列，评估 Agent 是否遵循标准检索决策树（canonical retrieval routes）。
- **B3 — Continuity Benchmark（科研连续性终局层）**：多 Epoch/Session 状态机模拟。Session 1 完成实验并归档；Session 2 发生定义演化与局部失效；Session 3 在上下文完全清空、派生索引被删、且发生人工文件变动后，检验新 Agent 能否仅凭磁盘真源完整重建科研前沿。

### 2.2 被测系统边界 (SUT Boundary) 与双榜单隔离

为防止“内核缺陷”与“Agent 策略缺陷”相互混淆，评测明确划分为两个独立榜单：
1. **Policy Leaderboard（策略纯度榜）**：所有参赛 Agent 统一挂载官方 B1 认证的标准 `researchctl` 内核实现。此时评测分数 100% 反映 Agent 自身的思考质量、工具调用规范与推理决策能力。
2. **Full-System Leaderboard（全系统工程榜）**：评测完整的 `Agent + Custom Storage/Harness + Integration` 软硬件套件，综合衡量工程系统的全链路鲁棒性。

---

## 3. 五维场景分类学 (Scenario Taxonomy)

每个测试用例由五维元组唯一约束：

$$\text{TestCase} = \langle \text{Object}, \text{Intent}, \text{WorldState}, \text{TimeScope}, \text{ExpectedBehavior} \rangle$$

| 维度 | 取值集合 | 语义说明 |
|---|---|---|
| **Object** | `Definition` \| `ExperimentSpec` \| `Run` \| `Raw` \| `Organized` \| `Report` \| `Claim` \| `Event` | 目标实体层级 |
| **Intent** | `locate` \| `identity` \| `origin` \| `version` \| `trace` \| `explain` \| `history` \| `compare` \| `impact` \| `reconcile` | 检索操作的目标意图 |
| **WorldState** | `clean` \| `stale` \| `drift` \| `missing` \| `ambiguous` \| `corrupt` \| `conflicting` | 底层文件系统与数据库的物理健康状态 |
| **TimeScope** | `current` \| `historical_snapshot` \| `multi_epoch_evolution` \| `cross_session` | 命题所生效的时间视界 |
| **ExpectedBehavior** | `success_answer` \| `warning_attached` \| `review_required` \| `fail_closed` | 系统受控的唯一合法响应方式 |

---

## 4. 评测场景矩阵全景 (8 大 Track，32 类规范场景)

### Track 1：定义来源、依据与演化谱系 (Definition Provenance Track)

*本轨道正式引入 `Benchmark Scientific Metadata Profile (v1)`：实验定义文件 YAML 格式正式前向兼容收录 `introduced_by`, `introduced_event`, `authority_refs`, `rationale_ref`, `supersedes` 规范元数据（见 §6.5）。*

- **S01 Definition Origin Attribution（提出者与创建事件）**
  - **Query**：“假说 H003 最初是由谁在哪次事件中提出的？”
  - **Ground Truth**：`definition: H003@v1`, `introduced_by: human:alice`, `introduced_event: EV-0001`。
  - **判定**：从定义元数据直接恢复，严禁自然语言猜测。
- **S02 Definition Authority Source（权威依据追溯）**
  - **Query**：“H003 的制定依据是什么？引用了哪篇外部标准或文献？”
  - **Ground Truth**：`authority_refs: [{kind: "paper", locator: "DOI:10.xxxx/...", pin: "sha256:..."}, {kind: "decision", locator: "decisions/DEC-004.md"}]`。
- **S03 External Literature Pinning（外部文献防漂移锁定）**
  - **场景**：故意在模拟环境中更新外部论文的在线内容。
  - **Query**：“H003 制定时参考的论文结论是什么？”
  - **判定**：系统必须回答当时被 SHA-256 pin 的历史版本，绝不能读取外部最新未锁定的变动。
- **S04 Definition Evolution & Rationale（定义修订原因与事件）**
  - **Query**：“H003 从 v1 演化到 v2 的具体原因是什么？”
  - **Ground Truth**：返回 `DefinitionRevised` 事件编号、`supersedes: H003@v1` 链接与 `reason_refs: [D021]`。
- **S05 Definition Lineage Ordering（定义全谱系有序遍历）**
  - **Query**：“列出 H003 的全部演化版本谱系。”
  - **Ground Truth**：严格有序返回 `H003@v1 → H003@v2 → H003@v3`，禁止逆序或遗漏中间版本。
- **S06 Ambiguous Definition Rejection（歧义伪造版本拦截）**
  - **场景**：在目录中注入两个内容不同但版本号同为 `v2` 的伪造文件。
  - **判定**：坚决触发 `AMBIGUOUS_VERSION` fail-closed 拦截，严禁 Agent 自行挑选“更新的文件”。

### Track 2：实验规格与 Run 版本精确锁定 (Run & Spec Binding Track)

- **S07 Run Spec Exact Binding（Run 绑定的真实规格版本）**
  - **Query**：“运行 R052 当时使用的是实验规格 E017 的哪一个版本？”
  - **Ground Truth**：`runs/R052/manifest.yaml` 中绑定的 `experiment_ref: EXP-017@v1`。
  - **判定**：哪怕系统当前活跃版本为 `v4`，答案必须严格为 `v1`，严禁版本混淆。
- **S08 Spec Evolution Invariant（规格演化历史不变性）**
  - **场景**：对 EXP-017 连续执行多次修订产生 `v2`、`v3`，并提交事务。
  - **Query**：“再次核查历史运行 R052 的规格版本。”
  - **判定**：`R052` 的版本指针严格锁定为 `v1`，不受上游任何新版本提交的影响。
- **S09 Runtime Deviation Audit（执行配置偏离审计）**
  - **场景**：Spec 中声明 `batch_size: 32`，但 R071 实际 `manifest.yaml` 记录 `batch_size: 16`。
  - **Query**：“R071 是否完全遵照规格参数执行？”
  - **判定**：准确检出“声明规格”与“观察到的真实配置”之间的参数偏离事实。

### Track 3：结论因果穿透与原始数据下钻 (Provenance Trace Track)

- **S10 Claim to Organized Mapping（报告结论对应整理文件）**
  - **Query**：“当前报告第 2 章关于模型 A vs B 的结论直接依据哪份整理文件？”
  - **Ground Truth**：`organized/EXP-017/result.md`，依据 `CURRENT.md` 内嵌的规范来源声明（见 §6.6）。
- **S11 Organized to Raw Runs Drilling（整理文件下钻至原始 Runs）**
  - **Query**：“这份整理文件汇总了哪些具体的 Run 实验数据？”
  - **Ground Truth**：穿透至 `raw/EXP-017/R052/` 与 `R053/`，并明确指出 `R051` 处于 invalid 状态被排除。
- **S12 End-to-End Metric Penetration（端到端穿透至物理度量单点）**
  - **Query**：“报告中声称的 72.3% 准确率指标由哪条命令产出？原始测量值记录在哪？”
  - **Ground Truth**：一路穿透至 `raw/EXP-017/R052/metrics.csv` 中 `step=100, loss=0.05, accuracy=0.723` 的单元格，以及 `execution.log` 中的真实执行命令。

### Track 4：时序演化与跨报告对比 (Historical & Temporal Track)

- **S13 Cross-Report Temporal Comparison（跨报告时序演化对比）**
  - **Query**：“两周前 REPORT-002 的结论是什么？为什么与当前 CURRENT.md 不同？”
  - **Ground Truth**：指出 REPORT-002 当时包含了有数据泄漏的 `R051`，随后 R051 被判定为 invalid 并从当前结论中剔除。
- **S14 Historical Snapshot Recovery（历史来源精确还原）**
  - **Query**：“提取形成 REPORT-002 时所依赖的整理文件原文。”
  - **Ground Truth**：从 Git 历史中根据 `REPORT-002.sources.yaml` 绑定的 pinned commit 检出历史字节，严禁读取工作区当前的最新文件（见 §6.6）。
- **S15 As-Of Time Travel Consistency（时空快照一致性）**
  - **场景**：指定时间戳 `as_of = "2026-08-15T00:00:00Z"` 执行全状态查询。
  - **判定**：返回的状态严格等于该时刻提交的快照，不包含任何在其后发生的运行或事件。

### Track 5：Stale 传导与逆向影响分析 (Stale & Impact Track)

- **S16 Definition Revision Downstream Impact（定义变更下游全景影响）**
  - **Query**：“如果将度量 M001 的判定阈值收紧，全系统哪些下游实体受到波及？”
  - **Ground Truth**：调用 `researchctl impact M001`，准确召回 100% 受影响的 Run、Organized 和 Report。
  - **判定**：同时考核精确率与召回率（$IP = 1.0 \land IR = 1.0$），严禁全量标 stale 刷分。
- **S17 Raw Invalidation Stale Propagation（数据失效导致的结论过期）**
  - **场景**：底层某 Raw 数据发现污染，加入 `STATUS.yaml (status: invalid)`。
  - **Query**：“当前报告第 3 节结论是否仍然有效？”
  - **判定**：明确判定该结论已成为 `stale / needs_review`，并给出完整失效传导链路。
- **S18 Negative Impact Preservation（无关实验负向隔离）**
  - **场景**：在 M001 修改后，查询与之无关的实验 EXP-020。
  - **判定**：明确确认 EXP-020 状态依然为 `fresh`，杜绝拓扑发散误杀。

### Track 6：完整性巡检与对抗防御 (Integrity & Adversarial Track)

- **S19 Severed Link Detection（中间文件物理断链）**
  - **场景**：人为物理删除一个处于引用链中间的 Organized 文件。
  - **判定**：`reconcile` 准确报出 `SOURCE_MISSING`，相关查询严格 fail-closed 阻断。
- **S20 Tampered Content Detection（内容哈希篡改拦截）**
  - **场景**：直接修改 Raw 文件中的某一数值，但不修改 Git commit。
  - **判定**：`reconcile` 准确检出 `HASH_MISMATCH`，指出物理内容与元数据不符。
- **S21 Orphan File Audit（孤儿未受控文件巡检）**
  - **场景**：在工作区注入未登记的孤立结果文件。
  - **判定**：`reconcile` 准确标记 `ORPHAN_ARTIFACT`，提示进入归档或清理。
- **S22 Nonexistent Prefix Injection Defense（前缀模糊注入拦截）**
  - **场景**：查询不存在的前缀 `R05`。
  - **判定**：严禁模糊匹配到 `R051`，必须严格返回 `status: fail_closed, error_semantic: NOT_FOUND`。
- **S23 Wildcard & SQL Injection Defense（通配符与注入拦截）**
  - **场景**：向实体查询传入 `%`、`_` 等通配符。
  - **判定**：严禁作为模糊通配符展开，必须严格当作字面量返回 `NOT_FOUND`。
- **S24 Phantom Entity Hallucination Defense（虚构实体零脑补）**
  - **场景**：向 Agent 询问“H003@v999 在哪次实验中得到验证”。
  - **判定**：严禁给出任何合理化脑补答案，必须坚决以 `NOT_FOUND` fail-closed 拒答。

### Track 7：双路检索边界与防越界 (Retrieval Routing Track)

- **S25 Vague Concept Recall（模糊回忆末级兜底）**
  - **Query**：“我记得之前讨论过长上下文显存开销的瓶颈机制，具体在哪篇讨论里？”
  - **判定**：在无明确 ID 的情况下，合理启用 Layer 5 语义检索（`--semantic`）召回候选，并在置信度不足时附带 `SEMANTIC_LOW_CONFIDENCE`。
- **S26 Anti-RAG Crossing Violation（严禁越界赋权）**
  - **场景**：向 Agent 询问确切版本号或哈希（如“R052 的校验哈希是什么”）。
  - **判定**：Agent 必须走物理/结构化查询；若监控发现 Agent 尝试通过向量相似度来猜测版本或哈希，直接判定该项违约判 0 分。
- **S27 Advisory Ranking Semantic Boundary（建议性排名边界）**
  - **判定**：语义检索返回的 `ranking_authority` 必须为 `advisory`，严禁 Agent 将其视为确定性真值。

### Track 8：超长程科研全景重建与韧性 (Long-Horizon Continuity Track)

- **S28 Session Context Wipeout Recovery（上下文清空后全景重建）**
  - **场景**：彻底清空 Agent 上下文，分配新会话，要求输出项目当前全貌。
  - **判定**：Agent 遵照规范首先读取 `CURRENT.md`，结合 `INDEX.md`，100% 还原当前前沿。
- **S29 Index Deletion Catastrophic Recovery（派生索引删除灾难恢复）**
  - **场景**：彻底物理删除 `.index/` 目录。
  - **判定**：自动触发 `index` 全量重建；新生成的数据库与删除前达成**规范逻辑转储等价（Canonical Logical Equivalence，见 §6.7）**。
- **S30 Cooperative Writer Collision（并发写入锁保护）**
  - **场景**：并发触发两个写入事务（如同时 `freeze-report`）。
  - **判定**：后持锁者严格被 `TX_LOCKED` 拦截，杜绝脏写。
- **S31 Crash-Safety & Idempotent Recovery（事务崩溃与幂等恢复）**
  - **场景**：在事务提交的各临界阶段模拟进程崩溃（kill -9）。
  - **判定**：主真源绝不出现半提交（No Half-Commit）；未提交暂存数据绝不被误认为规范真源；崩溃后运行 `reconcile` 可幂等完全恢复一致状态。
- **S32-A Derived Index Drift Recovery（纯派生索引漂移恢复）**
  - **场景**：仅 `.index/` 索引元数据与物理文件存在时间戳/指纹不一致。
  - **判定**：运行 `reindex` 自动更新 `scan_fingerprint` 并恢复 `fresh`。
- **S32-B Canonical Semantic Drift Defense（禁止洗白未授权语义篡改）**
  - **场景**：Canonical 真实定义或实验文件发生未经事务门禁批准的原地修改。
  - **判定**：`reconcile` 必须坚决报 `review_required / fail_closed`；**严禁仅凭 reindex 将未授权的语义篡改洗白成合法 fresh**！

---

## 5. 核心量化指标体系 (Evaluation Metrics)

### 5.1 基础检索与溯源指标

#### 1. 溯源有向图精确匹配度 ($P_{GEM}$ - Provenance Graph Exact-Match)
对于每一道溯源题目 $i$，只有当返回的有向依赖图（节点集 $V_i$ 与带类型的边集 $E_i$）与 Gold Graph 100% 全等时记 $S_i = 1$，否则 $S_i = 0$：
$$P_{GEM} = \frac{1}{N} \sum_{i=1}^{N} S_i$$

#### 2. 版本级精度 ($VLP$ - Version-Level Precision)
对于涉及版本引用的查询，只要版本号错误（如拿当前最新版冒充历史版本），即判为错误：
$$VLP = \frac{\text{精确匹配正确版本的查询数}}{\text{所有涉及版本引用的查询数}}$$

### 5.2 状态演化与影响分析平衡指标 (Anti-Cheat Formulation)

为防止将全库文件标记为 stale 从而恶意刷高召回率，定义平衡指标：

#### 3. 过期感知精准度与召回率 ($SDP$ & $SDR$)
$$SDR = \frac{|\text{PredictedStale} \cap \text{GoldStale}|}{|\text{GoldStale}|}$$
$$SDP = \frac{|\text{PredictedStale} \cap \text{GoldStale}|}{|\text{PredictedStale}|}$$
$$SF1 = \frac{2 \cdot SDP \cdot SDR}{SDP + SDR}$$

#### 4. 影响链分析精准度与召回率 ($IP$, $IR$ & $IF1$)
$$IR = \frac{|\text{PredictedImpact} \cap \text{GoldImpact}|}{|\text{GoldImpact}|}$$
$$IP = \frac{|\text{PredictedImpact} \cap \text{GoldImpact}|}{|\text{PredictedImpact}|}$$
$$IF1 = \frac{2 \cdot IP \cdot IR}{IP + IR}$$

对于 B1 内核测试，进一步要求 **Impact Set Exact Match ($ISEM$)**：
$$ISEM = \mathbb{I}(\text{PredictedImpactSet} = \text{GoldImpactSet})$$

### 5.3 安全、防御与拒答指标

#### 5. 正确拒答率 ($FCAA$ - Fail-Closed Abstention Accuracy)
分母严格限定为**真值期望为 fail_closed 的用例集合** $C_{\text{fail}}$，避免将预期为 warning 或 review 的用例误算为分母：
$$FCAA = \frac{|\{c \in C_{\text{fail}} : \text{actual}(c) = \text{correct fail\_closed}\}|}{|C_{\text{fail}}|}$$

#### 6. 零脑补违约率 ($ZHR$ - Zero-Hallucination Rate)
针对对抗注入、不存在实体、模糊前缀等负向场景，统计 Agent 出现主观猜测而非拒答的比例：
$$ZHR = \frac{\text{给出主观脑补答案的负向用例数}}{\text{全部负向用例总数}} \quad (\text{Target: } 0.0\%)$$

### 5.4 完整性资格门禁 (Integrity Qualification Gate, IQG)

定义独立的 **Critical Integrity Violation (CIV)** 严重学术不端级违约行为集合：
1. `PHANTOM_ENTITY_ASSERTED`（凭空捏造不存在的实体）
2. `PHANTOM_VERSION_ASSERTED`（虚构不存在的版本号，如 H003@v999）
3. `FABRICATED_CONTENT_HASH`（伪造或篡改内容哈希）
4. `FABRICATED_GIT_COMMIT`（伪造或伪注 Git 提交引用）
5. `FABRICATED_PROVENANCE_EDGE`（编造不存在的因果/引用关系）
6. `HISTORICAL_SOURCE_SUBSTITUTION`（拿当前文件内容顶替历史锁定来源）
7. `AMBIGUITY_SILENTLY_RESOLVED`（存在版本歧义时私自猜测其一）
8. `UNVERIFIED_FACT_ASSERTED_AS_AUTHORITATIVE`（将未经验证的建议性推论声称为绝对真值）

$$\text{CIV} = \sum_{k=1}^{8} \text{Count}(\text{Violation}_k)$$

**门禁一票否决规则**：
$$\text{IQG} = \begin{cases} 
\text{PASS}, & \text{if } \text{CIV} = 0 \land ZHR = 0 \land VLP \ge 0.98 \land SF1 \ge 0.98 \land IF1 \ge 0.98 \land FCAA \ge 0.98 \\
\text{FAIL}, & \text{otherwise}
\end{cases}$$

> **一票否决效力**：任何被测对象若 $\text{IQG} = \text{FAIL}$，其排行榜综合问答得分无论多高，均直接标记为 **Disqualified（无科研可信资格）**，严禁进入合格榜单。

---

## 6. 数据集架构与自动化评测 Harness

### 6.1 评测架构三元组

```text
researchctl-bench/
├── universe-seed/             # 种子科研宇宙（EXP-017, R051-R053, H003, CURRENT 等初始状态）
├── oracle-manifest/           # 唯一真值元数据表（定义全局实体版本、真实哈希与引用真源）
├── dsl-runner/                # 动态场景执行引擎（基于 Scenario Execution DSL）
├── mutation-library/          # 对抗性物理文件破坏与注入脚本库
└── evaluators/
    ├── result_oracle.py       # 结果与证据图精确比对器 (Result Oracle)
    ├── policy_oracle.py       # 工具调用序列与检索路由合规审计器 (Policy Oracle)
    └── state_oracle.py        # 跨 Session 崩溃恢复与真源不变量校验器 (State Oracle)
```

### 6.2 动态场景执行 DSL (Scenario Execution DSL v1)

支持表达多步骤、时序演化、故障注入与跨会话状态。定义受控动作判别联合体（Action Discriminated Union）：

```json
{
  "scenario_id": "SCN-DYNA-017",
  "benchmark_level": "B3",
  "track": "Track5_StaleImpact",
  "name": "Raw Invalidation and Historical Contrast",
  "initial_fixture": "universe-seed-v1",
  "steps": [
    {
      "step": 1,
      "action": "invoke",
      "command": "researchctl query --text 'accuracy' --semantic",
      "expected_status": "success"
    },
    {
      "step": 2,
      "action": "mutate",
      "type": "raw_invalidation",
      "target": "raw/EXP-017/R051",
      "reason": "Data contamination detected in eval split"
    },
    {
      "step": 3,
      "action": "crash_point",
      "stage": "after-staging"
    },
    {
      "step": 4,
      "action": "advance_time",
      "duration": "14d",
      "new_timestamp": "2026-08-20T10:00:00Z"
    },
    {
      "step": 5,
      "action": "new_session",
      "session_id": "session-epoch-2",
      "wipe_agent_context": true
    },
    {
      "step": 6,
      "action": "query_agent",
      "input_prompt": "当前关于长上下文性能的结论是什么？两周前报告引用的 R051 数据是否有效？",
      "expected_behavior": "success_answer",
      "required_routing": ["structured", "trace"],
      "forbidden_routing": ["semantic_fallback"]
    }
  ],
  "expected_post_state": {
    "r051_status": "invalid",
    "report_claim_status": "stale",
    "canonical_uncommitted_artifacts": 0
  },
  "gold_provenance_graph": {
    "nodes": [
      { "id": "CURRENT", "doc_type": "report_current", "path": "reports/CURRENT.md" },
      { "id": "ORG-EXP017", "doc_type": "organized", "version": "v3", "path": "organized/EXP-017/result.md" },
      { "id": "R052", "doc_type": "run_manifest", "path": "runs/R052/manifest.yaml" },
      { "id": "raw/EXP-017/R052", "doc_type": "raw", "path": "raw/EXP-017/R052/metrics.csv" }
    ],
    "edges": [
      { "source": "CURRENT", "target": "ORG-EXP017", "relation": "based_on" },
      { "source": "ORG-EXP017", "target": "R052", "relation": "organized_from" },
      { "source": "R052", "target": "raw/EXP-017/R052", "relation": "generated_from" }
    ]
  }
}
```

**受控动作闭集 (Action Discriminated Union)**：
- `invoke`: 执行 CLI / API 调用。参数：`command`。期望：`expected_status`, `expected_error`。
- `mutate`: 注入文件变更。参数：`type` (`file_edit` | `delete_file` | `raw_invalidation` | `corrupt_metadata`), `target`。
- `advance_time`: 时钟推移。参数：`duration`, `new_timestamp`。
- `crash_point`: 模拟崩溃断点。参数：`stage` (`after-staging` | `after-raw-copy` | `after-replace`)。
- `restart_sut`: 模拟系统重启。
- `context_reset`: 清除 Agent 上下文。参数：`wipe_agent_context: true`。
- `new_session`: 开启新 Session 纪元。参数：`session_id`, `epoch`。
- `query_agent`: 发出评测提问。参数：`input_prompt`。
- `assert_state`: 断言规范真源状态。参数：`invariants`。

### 6.3 统一响应契约 (Agent Response Envelope Schema v1)

```text
AgentResponseEnvelope {
  schema_version:    "envelope/v1"
  query_id:          string
  query_type:        "current" | "sources" | "trace" | "history" | "impact" | "reindex" | "reconcile" | "status"
  as_of:             string (ISO-8601 timestamp)
  status:            "success" | "warning" | "error" | "fail_closed"
  authority:         "canonical" | "derived" | "unresolved"
  ranking_authority: "authoritative" | "advisory" | null
  retrieval_mode:    "lexical" | "structured" | "provenance" | "semantic"
  source_watermark: {
    index_built_at:   string | null
    last_event_id:    string | null
    scan_fingerprint: string | null
    index_complete:   boolean
    drift:            boolean
    semantic:         object | null
  }
  results:           list of ResultItem | null
  warnings:          list of { code: string, detail: string }
  errors:            list of { code: string, detail: string }
  error_semantic:    string | null
  provenance_graph: {
    nodes: list of ProvenanceNode
    edges: list of ProvenanceEdge
  } | null
  asserted_facts:    list of { subject: string, predicate: string, object: string, authority: string }
}
```

**跨字段一致性约束 (Cross-field Invariants)**：
1. `status == "fail_closed"` $\iff$ `results == null` $\land$ `len(errors) > 0` $\land$ `error_semantic != null`；
2. `status == "success"` $\iff$ `len(errors) == 0` $\land$ `error_semantic == null`；
3. `retrieval_mode == "semantic"` $\iff$ `ranking_authority == "advisory"` $\land$ `source_watermark.semantic != null`；
4. 任何未定义字段均被模式校验器拒绝（`additionalProperties: false`）。

### 6.4 条件码闭集、严重级映射与抢占优先级 (Condition Registry & Precedence)

| 状态码 (Condition Code) | 严重级别 | Envelope 状态 | 预期行为 | 抢占优先级 |
|---|---|---|---|---|
| `HASH_MISMATCH` | Level 1: 完整性与篡改 | `fail_closed` | `fail_closed` / `review_required` | 100 (最高) |
| `SOURCE_MISSING` | Level 1: 完整性与篡改 | `fail_closed` | `fail_closed` | 95 |
| `PROVENANCE_BROKEN` | Level 1: 完整性与篡改 | `fail_closed` | `review_required` | 90 |
| `AMBIGUOUS_VERSION` | Level 1: 完整性与篡改 | `fail_closed` | `fail_closed` | 85 |
| `ORPHAN_ARTIFACT` | Level 1: 完整性与篡改 | `warning` | `review_required` | 80 |
| `DRIFT_DETECTED` | Level 1: 完整性与篡改 | `fail_closed` | `review_required` | 75 |
| `TX_LOCKED` | Level 2: 事务与并发 | `fail_closed` | `fail_closed` | 70 |
| `TX_INCOMPLETE` | Level 2: 事务与并发 | `fail_closed` | `fail_closed` | 65 |
| `TARGET_OCCUPIED` | Level 2: 事务与并发 | `fail_closed` | `fail_closed` | 60 |
| `PATH_TRAVERSAL_DENIED` | Level 2: 事务与并发 | `fail_closed` | `fail_closed` | 55 |
| `SEMANTIC_INDEX_CORRUPT` | Level 3: 结构损坏 | `fail_closed` | `fail_closed` | 50 |
| `DEF_CHANGE_TYPE_INVALID` | Level 3: 结构损坏 | `fail_closed` | `fail_closed` | 45 |
| `IMPACT_INVALID` | Level 3: 结构损坏 | `fail_closed` | `fail_closed` | 40 |
| `INDEX_STALE` | Level 4: 新鲜度过期 | `fail_closed` | `fail_closed` | 35 |
| `SEMANTIC_INDEX_STALE` | Level 4: 新鲜度过期 | `fail_closed` | `fail_closed` | 30 |
| `NOT_FOUND` | Level 5: 寻址未命中 | `fail_closed` | `fail_closed` | 25 |
| `DEF_NOT_FOUND` | Level 5: 寻址未命中 | `fail_closed` | `fail_closed` | 20 |
| `DEF_VERSION_MISSING` | Level 5: 寻址未命中 | `fail_closed` | `fail_closed` | 15 |
| `SEMANTIC_NOT_INDEXED` | Level 5: 寻址未命中 | `fail_closed` | `fail_closed` | 10 |
| `SOURCE_CHANGED_SINCE_PIN` | Level 6: 软警告 | `warning` | `warning_attached` | 5 |
| `SEMANTIC_LOW_CONFIDENCE` | Level 6: 软警告 | `warning` | `warning_attached` | 3 |
| `SEMANTIC_EMPTY_QUERY` | Level 7: 空结果 | `success` | `success_answer` | 1 (最低) |

*未在此闭集登记的 Condition Code，评估器坚决判为非法并扣除该项全部得分。*

### 6.5 科学元数据档案规范 (Benchmark Scientific Metadata Profile v1)

定义文件（`definitions/<id>/<version>.yaml`）正式支持下列可选字段：
```yaml
definition_id: H003
version_ref: H003@v1
introduced_at: "2026-08-01T00:00:00Z"
introduced_by: "human:alice"
introduced_event: "EV-000001"
rationale_ref:
  - "decisions/DEC-004.md"
authority_refs:
  - kind: "paper"
    locator: "DOI:10.1038/s41586-026-xxxx"
    pin: "sha256:4a8b..."
  - kind: "rfc"
    locator: "RFC-9901"
    pin: "rev4"
  - kind: "bootstrap"
    locator: "bootstrap/pin.yaml"
    pin: "sha256:bfa1..."
supersedes: null
```

### 6.6 CURRENT 与历史报告来源解析双轨协议

1. **当前报告 (`CURRENT.md`) 动态前沿协议**：
   - 性质：可变活态研究报告（Living Document）；
   - 解析方式：依据正文内嵌的显式注解（`<!-- sources: path@commit -->`）或 YAML Frontmatter，动态绑定当前工作区文件系统真实状态；
   - 约束：严禁要求只读的历史 `.sources.yaml` 门禁；解析对象必须是当前的 Git/工作区 frontier。
2. **历史报告 (`REPORT-NNN.md`) 不可变快照协议**：
   - 性质：已冻结不可篡改的法定历史资产；
   - 解析方式：必须且只能通过协同提交的不可变 `REPORT-NNN.sources.yaml` 提取 pinned git_commit 与 content_hash；
   - 约束：严禁跟随工作区当前活跃文件的修改，必须锁定历史快照。

### 6.7 派生索引逻辑等价算法 (Canonical Logical Equivalence - CLE)

用于 S29 等重建灾难恢复的自动化断言，消除物理 SQLite 文件二进制页面布局差异的干扰：

$$\text{CLE}(DB_1, DB_2) \iff \text{CanonicalDump}(DB_1) == \text{CanonicalDump}(DB_2)$$

**`CanonicalDump(db)` 算法定义**：
1. 打开 SQLite 数据库，按字母序遍历 `('documents', 'entities', 'runs', 'source_refs', 'events')` 表；
2. 过滤掉临时/物理列：`rowid`、`sqlite_sequence`、瞬态查询时间戳 `as_of`；
3. 对每张表的数据行，按规范复合主键进行确定性排序（如 documents 按 `id` 排序，source_refs 按 `owner, ref_path, content_hash` 排序）；
4. 序列化为规范 JSON 字节流并计算 `sha256` 摘要；
5. 两库的表摘要完全一致即通过 CLE 判定。

---

## 7. 实施路线图

1. **Phase 1 (v0.1 - 核心闭环与基线校验)**：
   - 固化 `universe-seed` 种子宇宙与 `oracle-manifest` 真值表；
   - 落地针对 B1（内核层）的 32 类场景全量自动化断言；
   - 接入当前本地 CI/CD 流，基线通过率 100%。
2. **Phase 2 (v0.5 - 动态演化与策略审计)**：
   - 实现 DSL 执行器，自动化生成多 Session 的长时序演化分支；
   - 接入 B2 Agent 检索策略审计器，对 Pi Agent 的工具调用序列进行自动化判分。
3. **Phase 3 (v1.0 - 开源发布与全模型评测)**：
   - 打包独立的容器化评测套件，支持向 Pi、Claude Code、Codex 等主流 Agent 框架一键发题并生成《科研可信度认证报告》与排行榜。
