# 超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench)

> 文档性质：Benchmark 规范与自动化评测方案（Specification Contract v1.0 规范终审稿）。
>
> 依据：《超长程实验 Agent 检索系统设计方案.md》（全案规范）、《超长程实验 Text Agent 检索与研究状态系统 PRD.md》、《P0-Contract.md》、《P1-C-Contract.md》，以及 Sol 专家独立审核意见（2026-09-04 终审复核）。

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

**被测系统 (SUT) 交互契约**：
- **Standard Input / Output Contract**：SUT 必须通过标准进程调用的 `stdout` 输出符合 §6.3 冻结的 `AgentResponseEnvelope` JSON 字节流，`stderr` 用于调试日志。
- **Capability Isolation**：评测 Runner 为每个用例分配独立的临时沙箱工作区（Workspace），SUT 严禁逃逸至沙箱外读取预置答案。

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
  - **Ground Truth**：`definition: H003@v1`, `introduced_by: human:alice`, `introduced_event: EV-000001`。
  - **判定**：从定义元数据直接恢复，严禁自然语言猜测。
- **S02 Definition Authority Source（权威依据追溯）**
  - **Query**：“H003 的制定依据是什么？引用了哪篇外部标准或文献？”
  - **Ground Truth**：`authority_refs: [{kind: "paper", locator: "DOI:10.1038/s41586-026-xxxx", pin: "sha256:4a8b..."}, {kind: "decision", locator: "decisions/DEC-004.md"}]`。
- **S03 External Literature Pinning（外部文献防漂移锁定）**
  - **场景**：故意在模拟环境中更新外部论文的在线内容。
  - **Query**：“H003 制定时参考的论文结论是什么？”
  - **判定**：系统必须回答当时被 SHA-256 pin 的历史版本，绝不能读取外部最新未锁定的变动。
- **S04 Definition Evolution & Rationale（定义修订原因与事件）**
  - **Query**：“H003 从 v1 演化到 v2 的具体原因是什么？”
  - **Ground Truth**：返回 `DefinitionRevised` 事件编号、`supersedes: H003@v1` 链接与 `rationale_ref: [decisions/DEC-004.md]`。
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
  - **判定**：严禁给出任何合理化脑补答案，必须坚决以 `DEF_NOT_FOUND` fail-closed 拒答。

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

### 6.1 评测架构与 Oracle 真值单一权威契约

```text
researchctl-bench/
├── universe-seed/             # 种子科研宇宙（EXP-017, R051-R053, H003, CURRENT 等初始物理文件）
├── oracle-manifest/           # 唯一根真值元数据（manifest.yaml，定义全局实体初始版本、哈希与关系）
├── dsl-runner/                # 动态场景执行引擎（基于 Scenario Execution DSL v1）
├── mutation-library/          # 对抗性物理文件破坏与注入脚本库
└── evaluators/
    ├── compile_scenario_gold.py # 唯一 Gold 编译工具（由 Oracle 状态机编译场景 Gold 视图）
    ├── result_oracle.py       # 结果与证据图精确比对器 (Result Oracle)
    ├── policy_oracle.py       # 工具调用序列与检索路由合规审计器 (Policy Oracle)
    └── state_oracle.py        # 跨 Session 崩溃恢复与真源不变量校验器 (State Oracle)
```

#### 6.1.1 唯一根真值 (`oracle-manifest/manifest.yaml`)
`oracle-manifest/manifest.yaml` 是整个 Benchmark 宇宙初始状态的**唯一绝对权威 (Single Source of Truth)**。用例场景文件严禁手写定义初始事实。
在 `universe-seed-v1` 中，`runs/R052/manifest.yaml` 与 `oracle-manifest.yaml` 均严格且唯一绑定到 `experiment_ref: EXP-017@v1`。

#### 6.1.2 确定性 Oracle 状态转换函数与 Gold 编译
Benchmark 采用状态机形式化定义 Oracle 演化：
$$\text{OracleState}_{t+1} = \operatorname{Apply}(\text{OracleState}_t, \text{Action}_t)$$

各受控动作对 Oracle 状态的确定性作用规则：
1. `invoke`: 若为只读查询，Oracle 状态不变；若为事务提交命令，仅当 SUT 成功写入且通过签名验证时更新对应实体的状态；
2. `mutate(type="raw_invalidation", target=T, reason=R)`: 将实体 $T$ 的状态置为 `invalid`，并根据引用拓扑有向图，将所有直接和间接依赖 $T$ 的下游 Organized 和 Report 标记为 `is_stale = true`；
3. `mutate(type="delete_file", target=T)`: 从物理状态中删除 $T$，将所有终点为 $T$ 的关系标记为 `PROVENANCE_BROKEN`；
4. `advance_time(duration=D, new_timestamp=TS)`: 更新 Oracle 的虚拟时钟 `now = TS`；
5. `crash_point(stage=S)`: 任何处于未提交状态（uncommitted）的暂存数据均被丢弃，Oracle 状态保持为最后一次合法提交的状态；
6. `new_session` / `context_reset`: 清除 Agent 记忆，对底层 Oracle 真值无任何副作用。

**禁止手写 Gold 规则 (Prohibition of Hand-Authored Gold)**：
- 场景定义 DSL 文件中**严禁包含手写的 `expected_post_state`、`gold_provenance_graph` 或 `gold_results`**。
- 所有 Gold 期望必须由官方工具 `compile_scenario_gold.py` 读取 `oracle-manifest.yaml` 并执行 $\prod \operatorname{Apply}$ 编译生成到 `build/gold/<scenario_id>.gold.json`。
- CI 静态检查器一旦检测到 DSL 文件中存在手写 Gold 字段，直接以 `TESTCASE_DUAL_ORACLE_FORBIDDEN` 拒绝该测试用例。

---

### 6.2 动态场景执行 DSL (Scenario Execution DSL v1)

#### 6.2.1 形式化机器 Schema (`scenario-dsl-v1.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ScenarioExecutionDSLV1",
  "type": "object",
  "required": [
    "scenario_id",
    "benchmark_level",
    "track",
    "name",
    "initial_fixture",
    "steps"
  ],
  "additionalProperties": false,
  "properties": {
    "scenario_id": {
      "type": "string",
      "pattern": "^SCN-[A-Z0-9_-]+$"
    },
    "benchmark_level": {
      "type": "string",
      "enum": ["B1", "B2", "B3"]
    },
    "track": {
      "type": "string",
      "enum": [
        "Track1_DefinitionProvenance",
        "Track2_RunSpecBinding",
        "Track3_ProvenanceTrace",
        "Track4_HistoricalTemporal",
        "Track5_StaleImpact",
        "Track6_IntegrityAdversarial",
        "Track7_RetrievalRouting",
        "Track8_LongHorizonContinuity"
      ]
    },
    "name": {
      "type": "string",
      "minLength": 1
    },
    "initial_fixture": {
      "type": "string",
      "pattern": "^[a-z0-9_-]+$"
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["step", "action"],
        "additionalProperties": false,
        "properties": {
          "step": { "type": "integer", "minimum": 1 },
          "action": {
            "type": "string",
            "enum": [
              "invoke",
              "mutate",
              "advance_time",
              "crash_point",
              "restart_sut",
              "context_reset",
              "new_session",
              "query_agent",
              "assert_state"
            ]
          },
          "command": { "type": "string" },
          "expected_status": {
            "type": "string",
            "enum": ["success", "fail_closed", "warning", "error"]
          },
          "expected_error": { "type": ["string", "null"] },
          "timeout_ms": { "type": "integer", "minimum": 1000, "maximum": 60000 },
          "type": {
            "type": "string",
            "enum": [
              "file_edit",
              "delete_file",
              "raw_invalidation",
              "corrupt_metadata",
              "link_severing"
            ]
          },
          "target": { "type": "string" },
          "content": { "type": "string" },
          "reason": { "type": "string" },
          "duration": {
            "type": "string",
            "pattern": "^[0-9]+[smhdw]$"
          },
          "new_timestamp": {
            "type": "string",
            "format": "date-time"
          },
          "stage": {
            "type": "string",
            "enum": [
              "after-staging",
              "after-raw-copy",
              "after-replace",
              "during-build"
            ]
          },
          "action_after": {
            "type": "string",
            "enum": ["terminate_sut", "restart_sut"]
          },
          "clean_ipc": { "type": "boolean" },
          "wipe_agent_context": { "type": "boolean" },
          "session_id": { "type": "string" },
          "epoch": { "type": "integer", "minimum": 1 },
          "input_prompt": { "type": "string" },
          "expected_behavior": {
            "type": "string",
            "enum": [
              "success_answer",
              "warning_attached",
              "review_required",
              "fail_closed"
            ]
          },
          "required_routing": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": [
                "lexical",
                "structured",
                "provenance",
                "history",
                "impact",
                "trace"
              ]
            }
          },
          "forbidden_routing": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": [
                "semantic_fallback",
                "raw_scan",
                "unindexed_search"
              ]
            }
          },
          "invariants": {
            "type": "array",
            "items": { "type": "string" }
          },
          "cle_check": {
            "type": "object",
            "required": ["baseline_path", "candidate_path"],
            "additionalProperties": false,
            "properties": {
              "baseline_path": { "type": "string" },
              "candidate_path": { "type": "string" }
            }
          }
        }
      }
    }
  }
}
```

#### 6.2.2 动作执行语义与故障注入生命周期
1. **`invoke`**: 在隔离沙箱中执行 CLI 命令。默认 `timeout_ms=10000`。超时直接以 `RUNNER_TIMEOUT` fail-closed 终止测试。
2. **`mutate`**: 物理变更注入。对沙箱文件系统进行受控修改，记录变更指纹。
3. **`advance_time`**: 虚拟时钟推移。通过环境变量 `FAKETIME` 或虚拟时钟垫片将系统时间锁定至 `new_timestamp`。
4. **`crash_point`**: 崩溃注入点生命周期绑定。在 SUT 执行事务时，注册针对指定 `stage`（如 `after-staging`）的拦截钩子。当 SUT 执行到达该阶段时，Runner 向 SUT 进程组发送 `SIGKILL` 强制终止，模拟断电级异常。
5. **`restart_sut`**: 重启被测系统，清理未释放的命名管道与临时锁。
6. **`context_reset` / `new_session`**: 清空 Agent 会话上下文，开启新纪元。
7. **`query_agent`**: 向 Agent 发出自然语言科研提问，捕获输出的 Envelope 与 Tool Calls 路由序列。
8. **`assert_state`**: 验证物理文件与派生索引的不变量。若配置 `cle_check`，调用 §6.7 的 `CanonicalDump()` 验证两个数据库的逻辑等价性。

#### 6.2.3 规范 DSL 用例示例 (`SCN-DYNA-017.json`)

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
      "stage": "after-staging",
      "action_after": "terminate_sut"
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
      "epoch": 2,
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
  ]
}
```

---

### 6.3 统一响应契约 (Agent Response Envelope Schema v1)

#### 6.3.1 形式化机器 Schema (`agent-response-envelope-v1.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentResponseEnvelopeV1",
  "type": "object",
  "required": [
    "schema_version",
    "query_id",
    "query_type",
    "as_of",
    "status",
    "authority",
    "ranking_authority",
    "retrieval_mode",
    "source_watermark",
    "results",
    "warnings",
    "errors",
    "error_semantic",
    "provenance_graph",
    "asserted_facts"
  ],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "string", "const": "envelope/v1" },
    "query_id": { "type": "string", "minLength": 1 },
    "query_type": {
      "type": "string",
      "enum": ["current", "sources", "trace", "history", "impact", "reindex", "reconcile", "status", "query"]
    },
    "as_of": { "type": "string", "format": "date-time" },
    "status": {
      "type": "string",
      "enum": ["success", "warning", "fail_closed", "error"]
    },
    "authority": {
      "type": "string",
      "enum": ["canonical", "derived", "unresolved"]
    },
    "ranking_authority": {
      "type": ["string", "null"],
      "enum": ["authoritative", "advisory", null]
    },
    "retrieval_mode": {
      "type": "string",
      "enum": ["lexical", "structured", "provenance", "history", "impact", "semantic"]
    },
    "source_watermark": {
      "type": "object",
      "required": ["index_built_at", "last_event_id", "scan_fingerprint", "index_complete", "drift", "semantic"],
      "additionalProperties": false,
      "properties": {
        "index_built_at": { "type": ["string", "null"], "format": "date-time" },
        "last_event_id": { "type": ["string", "null"], "pattern": "^EV-[0-9]{6}$" },
        "scan_fingerprint": { "type": ["string", "null"], "pattern": "^sha256:[0-9a-f]{64}$" },
        "index_complete": { "type": "boolean" },
        "drift": { "type": "boolean" },
        "semantic": {
          "type": ["object", "null"],
          "required": ["model", "dim", "index_hash", "built_at"],
          "additionalProperties": false,
          "properties": {
            "model": { "type": "string" },
            "dim": { "type": "integer", "minimum": 1 },
            "index_hash": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
            "built_at": { "type": "string", "format": "date-time" }
          }
        }
      }
    },
    "results": {
      "type": ["array", "null"],
      "items": {
        "type": "object",
        "required": ["entity_id", "versioned_ref", "path", "content_hash", "git_commit", "section", "status", "relation_type", "is_stale", "is_available", "score"],
        "additionalProperties": false,
        "properties": {
          "entity_id": { "type": "string" },
          "versioned_ref": { "type": ["string", "null"] },
          "path": { "type": "string" },
          "content_hash": { "type": ["string", "null"], "pattern": "^sha256:[0-9a-f]{64}$" },
          "git_commit": { "type": ["string", "null"], "pattern": "^[0-9a-f]{7,40}$" },
          "section": { "type": ["string", "null"] },
          "status": { "type": "string", "enum": ["valid", "invalid", "fresh", "stale", "frozen", "unknown"] },
          "relation_type": {
            "type": ["string", "null"],
            "enum": ["based_on", "organized_from", "generated_from", "uses", "derived_from", "supersedes", "impacts", null]
          },
          "is_stale": { "type": "boolean" },
          "is_available": { "type": "boolean" },
          "score": { "type": ["number", "null"], "minimum": 0.0, "maximum": 1.0 }
        }
      }
    },
    "warnings": {
      "type": "array",
      "items": { "$ref": "#/$defs/ConditionItem" }
    },
    "errors": {
      "type": "array",
      "items": { "$ref": "#/$defs/ConditionItem" }
    },
    "error_semantic": { "type": ["string", "null"] },
    "provenance_graph": {
      "type": ["object", "null"],
      "required": ["nodes", "edges"],
      "additionalProperties": false,
      "properties": {
        "nodes": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "doc_type", "version", "path", "content_hash", "git_commit", "leaf_metric"],
            "additionalProperties": false,
            "properties": {
              "id": { "type": "string" },
              "doc_type": {
                "type": "string",
                "enum": ["definition", "experiment_spec", "run_manifest", "raw", "organized", "report_current", "report_historical", "event"]
              },
              "version": { "type": ["string", "null"] },
              "path": { "type": "string" },
              "content_hash": { "type": ["string", "null"], "pattern": "^sha256:[0-9a-f]{64}$" },
              "git_commit": { "type": ["string", "null"], "pattern": "^[0-9a-f]{7,40}$" },
              "leaf_metric": { "type": ["string", "null"] }
            }
          }
        },
        "edges": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["source", "target", "relation"],
            "additionalProperties": false,
            "properties": {
              "source": { "type": "string" },
              "target": { "type": "string" },
              "relation": {
                "type": "string",
                "enum": ["based_on", "organized_from", "generated_from", "uses", "derived_from", "supersedes", "impacts"]
              }
            }
          }
        }
      }
    },
    "asserted_facts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["subject", "predicate", "object", "authority"],
        "additionalProperties": false,
        "properties": {
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "authority": { "type": "string", "enum": ["canonical", "derived", "advisory"] }
        }
      }
    }
  },
  "$defs": {
    "ConditionItem": {
      "type": "object",
      "required": ["code", "detail"],
      "additionalProperties": false,
      "properties": {
        "code": {
          "type": "string",
          "enum": [
            "HASH_MISMATCH",
            "SOURCE_MISSING",
            "PROVENANCE_BROKEN",
            "AMBIGUOUS_VERSION",
            "DRIFT_DETECTED",
            "ORPHAN_ARTIFACT",
            "TX_LOCKED",
            "TX_INCOMPLETE",
            "TARGET_OCCUPIED",
            "PATH_TRAVERSAL_DENIED",
            "SEMANTIC_INDEX_CORRUPT",
            "DEF_CHANGE_TYPE_INVALID",
            "IMPACT_INVALID",
            "INDEX_STALE",
            "SEMANTIC_INDEX_STALE",
            "NOT_FOUND",
            "DEF_NOT_FOUND",
            "DEF_VERSION_MISSING",
            "SEMANTIC_NOT_INDEXED",
            "SOURCE_CHANGED_SINCE_PIN",
            "SEMANTIC_LOW_CONFIDENCE",
            "SEMANTIC_EMPTY_QUERY"
          ]
        },
        "detail": { "type": "string" }
      }
    }
  }
}
```

#### 6.3.2 全状态机跨字段一致性严格不变量 (Exhaustive State Invariants)

对于任何生成的 `AgentResponseEnvelope`，必须严格满足以下互斥状态约束：

1. **`fail_closed` 状态**：
   $$\text{status} = \text{"fail\_closed"} \iff (\text{results} = \text{null}) \land (\operatorname{len}(\text{errors}) > 0) \land (\text{error\_semantic} \ne \text{null}) \land (\text{authority} = \text{"unresolved"})$$
2. **`success` 状态**：
   $$\text{status} = \text{"success"} \iff (\text{results} \ne \text{null}) \land (\operatorname{len}(\text{errors}) = 0) \land (\text{error\_semantic} = \text{null}) \land (\operatorname{len}(\text{warnings}) = 0) \land (\text{authority} \ne \text{"unresolved"})$$
3. **`warning` 状态**：
   $$\text{status} = \text{"warning"} \iff (\text{results} \ne \text{null}) \land (\operatorname{len}(\text{errors}) = 0) \land (\text{error\_semantic} = \text{null}) \land (\operatorname{len}(\text{warnings}) > 0) \land (\text{authority} \ne \text{"unresolved"})$$
4. **`error` 状态（引擎底层严重故障，如物理磁盘/SQLite 损坏）**：
   $$\text{status} = \text{"error"} \iff (\text{results} = \text{null}) \land (\operatorname{len}(\text{errors}) > 0) \land (\text{error\_semantic} \ne \text{null}) \land (\text{authority} = \text{"unresolved"})$$
5. **语义检索建议性赋权约束**：
   $$\text{ranking\_authority} = \text{"advisory"} \iff \text{retrieval\_mode} = \text{"semantic"}$$
   若 $\text{retrieval\_mode} \ne \text{"semantic"}$，则 $\text{ranking\_authority} \in \{\text{"authoritative"}, \text{null}\}$；若 $\text{retrieval\_mode} = \text{"semantic"}$，则 $\text{source\_watermark.semantic} \ne \text{null}$。

---

### 6.4 条件码闭集、抢占优先级算法与预期映射 (Condition Registry & Precedence Contract)

注册表规范标识：`condition_registry_version: "condition-registry/v1"`。

#### 6.4.1 完整条件码表格 (22 个闭集码严格全序权重)

| 状态码 (Condition Code) | 严重级别 | Envelope 默认状态 | 预期行为基础值 | 唯一权重 $W$ |
|---|---|---|---|---|
| `HASH_MISMATCH` | Level 1: 完整性与篡改 | `fail_closed` | 上下文决定 (见 6.4.3) | **100** (最高) |
| `SOURCE_MISSING` | Level 1: 完整性与篡改 | `fail_closed` | 上下文决定 (见 6.4.3) | **95** |
| `PROVENANCE_BROKEN` | Level 1: 完整性与篡改 | `fail_closed` | 上下文决定 (见 6.4.3) | **90** |
| `AMBIGUOUS_VERSION` | Level 1: 完整性与篡改 | `fail_closed` | 上下文决定 (见 6.4.3) | **85** |
| `DRIFT_DETECTED` | Level 1: 完整性与篡改 | `fail_closed` | `review_required` | **80** |
| `ORPHAN_ARTIFACT` | Level 1: 完整性与篡改 | `warning` | `review_required` | **75** |
| `TX_LOCKED` | Level 2: 事务与并发 | `fail_closed` | `fail_closed` | **70** |
| `TX_INCOMPLETE` | Level 2: 事务与并发 | `fail_closed` | `fail_closed` | **65** |
| `TARGET_OCCUPIED` | Level 2: 事务与并发 | `fail_closed` | `fail_closed` | **60** |
| `PATH_TRAVERSAL_DENIED` | Level 2: 事务与并发 | `fail_closed` | `fail_closed` | **55** |
| `SEMANTIC_INDEX_CORRUPT` | Level 3: 结构损坏 | `fail_closed` | `fail_closed` | **50** |
| `DEF_CHANGE_TYPE_INVALID` | Level 3: 结构损坏 | `fail_closed` | `fail_closed` | **45** |
| `IMPACT_INVALID` | Level 3: 结构损坏 | `fail_closed` | `fail_closed` | **40** |
| `INDEX_STALE` | Level 4: 新鲜度过期 | `fail_closed` | `fail_closed` | **35** |
| `SEMANTIC_INDEX_STALE` | Level 4: 新鲜度过期 | `fail_closed` | `fail_closed` | **30** |
| `NOT_FOUND` | Level 5: 寻址未命中 | `fail_closed` | `fail_closed` | **25** |
| `DEF_NOT_FOUND` | Level 5: 寻址未命中 | `fail_closed` | `fail_closed` | **20** |
| `DEF_VERSION_MISSING` | Level 5: 寻址未命中 | `fail_closed` | `fail_closed` | **15** |
| `SEMANTIC_NOT_INDEXED` | Level 5: 寻址未命中 | `fail_closed` | `fail_closed` | **10** |
| `SOURCE_CHANGED_SINCE_PIN` | Level 6: 软警告 | `warning` | `warning_attached` | **5** |
| `SEMANTIC_LOW_CONFIDENCE` | Level 6: 软警告 | `warning` | `warning_attached` | **3** |
| `SEMANTIC_EMPTY_QUERY` | Level 7: 空结果 | `success` | `success_answer` | **1** (最低) |

#### 6.4.2 确定性抢占裁决算法 (Precedence Arbiter Algorithm)
1. 收集系统检测到的全部激活条件集合 $C = \{c_1, c_2, \dots\} \subset \text{Registry}$；
2. 由于所有 22 个码赋予了严格互异的整数权重 $W(c) \in [1, 100]$，权重不存在平局（Strict Total Order, Tie-Free）；
3. 计算主条件（Primary Condition）：
   $$c^* = \operatorname{argmax}_{c \in C} W(c)$$
4. 若 $W(c^*) \ge 10$（即处于 Level 1 至 Level 5）：
   - Envelope 的主错误码必须设为 $c^*$：`error_semantic = c^*.code`；
   - 将 $c^*$ 填入 `errors[0]`，其余激活的阻断性条件（$W \ge 10$）按权重降序填入 `errors[1..]`；
   - 若同时存在 Level 6 条件（$W < 10$），将其填入 `warnings`；
   - `status = "fail_closed"`（若为 Level 3 严重底层故障则设为 `"error"`）；
   - `results = null`。
5. 若 $W(c^*) < 10$（即仅有 Level 6 或 Level 7 警告/空结果）：
   - `error_semantic = null`，`errors = []`；
   - 将检测到的警告按权重降序填入 `warnings`；
   - 若 $\operatorname{len}(\text{warnings}) > 0$ 则 `status = "warning"`，否则 `status = "success"`。

#### 6.4.3 ExpectedBehavior 映射契约
针对 `HASH_MISMATCH`、`SOURCE_MISSING`、`PROVENANCE_BROKEN`、`AMBIGUOUS_VERSION` 等严重条件，评测 Oracle 根据查询请求类型 `query_type` 确定唯一的预期行为：
- **审计巡检类意图 (`query_type` 为 `reconcile` 或 `status`)**：
  $$\text{ExpectedBehavior} = \text{"review\_required"}$$
  系统应准确报告出受损文件与原因，供人工或巡检流程核查。
- **获取使用类意图 (`query_type` 为 `query`、`sources`、`trace`、`history`、`impact`)**：
  $$\text{ExpectedBehavior} = \text{"fail\_closed"}$$
  系统必须坚决中断返回，严禁使用已损坏或断链的数据进行计算或应答。
- **孤儿文件 (`ORPHAN_ARTIFACT`)**：`ExpectedBehavior = "review_required"`，Envelope 状态设为 `warning`。
- **软警告 (`SOURCE_CHANGED_SINCE_PIN` / `SEMANTIC_LOW_CONFIDENCE`)**：`ExpectedBehavior = "warning_attached"`，Envelope 状态设为 `warning`。

#### 6.4.4 注册表一致性测试向量 (Conformance Test Vectors)
- **Vector 1**: 输入 $C = \{\text{HASH\_MISMATCH}, \text{INDEX\_STALE}\}$
  - 判定：$W(\text{HASH\_MISMATCH}) = 100 > W(\text{INDEX\_STALE}) = 35$。
  - 输出：`status="fail_closed"`, `error_semantic="HASH_MISMATCH"`, `errors=[HASH_MISMATCH, INDEX_STALE]`, `warnings=[]`。
- **Vector 2**: 输入 $C = \{\text{ORPHAN\_ARTIFACT}, \text{SOURCE\_CHANGED\_SINCE\_PIN}\}$
  - 判定：$W(\text{ORPHAN\_ARTIFACT}) = 75$ (Level 1 警告级), $W(\text{SOURCE\_CHANGED\_SINCE\_PIN}) = 5$。
  - 输出：`status="warning"`, `error_semantic=null`, `errors=[]`, `warnings=[ORPHAN_ARTIFACT, SOURCE_CHANGED_SINCE_PIN]`, `expected_behavior="review_required"`。
- **Vector 3**: 输入 $C = \{\text{PROVENANCE\_BROKEN}, \text{NOT\_FOUND}\}$
  - 判定：$W(\text{PROVENANCE\_BROKEN}) = 90 > W(\text{NOT\_FOUND}) = 25$。
  - 输出：`status="fail_closed"`, `error_semantic="PROVENANCE_BROKEN"`, `errors=[PROVENANCE_BROKEN, NOT_FOUND]`。

---

### 6.5 科学元数据档案规范 (Benchmark Scientific Metadata Profile v1)

文件规范标识：`profile_version: "scientific-metadata/v1"`。

#### 6.5.1 形式化定义模式 (`definitions/<id>/<version>.yaml`)

```yaml
profile_version: "scientific-metadata/v1"   # REQUIRED
definition_id: "H003"                      # REQUIRED: pattern ^[A-Za-z0-9_-]+$
version_ref: "H003@v1"                     # REQUIRED: pattern ^[A-Za-z0-9_-]+@v[0-9]+$
title: "Long-context Attention Sparsity Hypothesis" # REQUIRED
statement: "Transformer KV cache scaling achieves sub-quadratic complexity..." # REQUIRED
introduced_at: "2026-08-01T00:00:00Z"      # REQUIRED: RFC 3339 date-time
introduced_by: "human:alice"               # REQUIRED: pattern ^(human|agent):[a-zA-Z0-9_.-]+$
introduced_event: "EV-000001"              # REQUIRED: pattern ^EV-[0-9]{6}$
authority_refs:                            # REQUIRED: minItems >= 1
  - kind: "paper"                          # REQUIRED: enum [paper, rfc, bootstrap, standard, decision]
    locator: "DOI:10.1038/s41586-026-xxxx" # REQUIRED: URI or path
    pin: "sha256:4a8b7921..."              # REQUIRED: sha256:hash (paper/bootstrap/standard) or rev (rfc)
  - kind: "decision"
    locator: "decisions/DEC-004.md"
    pin: "sha256:bfa144..."
rationale_ref:                             # OPTIONAL: default []
  - "decisions/DEC-004.md"
supersedes: null                           # REQUIRED: pattern ^[A-Za-z0-9_-]+@v[0-9]+$ or null
```

#### 6.5.2 元数据校验与缺失处理规则
1. **模式严格封闭性**：定义文件必须遵守 `additionalProperties: false`。若出现未在此 Profile 登记的属性，Runner 在加载测试数据集时即触发 `DEF_SCHEMA_INVALID` 终止；
2. **基线数据集完整性保证**：在 `universe-seed-v1` 中，所有 S01–S06 相关的定义文件均完整具备上述 REQUIRED 字段。若评测环境物理文件缺失 `introduced_by`，Runner 将用例标记为 `FIXTURE_SCHEMA_INVALID` 阻断执行；
3. **不存在实体的查询防护**：在 S24（虚构实体查询）中，若查询 `H003@v999`，由于物理文件不存在，系统必须严格返回 `status: fail_closed, error_semantic: "DEF_NOT_FOUND"`，严禁 Agent 凭空编造作者或哈希。

---

### 6.6 CURRENT 与历史报告来源解析双轨协议

#### 6.6.1 当前报告 (`CURRENT.md`) 动态前沿协议
- **法律地位**：动态演进的可变活态报告（Living Document）；
- **来源声明语法**：必须通过文档头部的 YAML Frontmatter 或 HTML 注解进行显式声明：
  ```yaml
  ---
  sources:
    - path: organized/EXP-017/result.md
      relation: based_on
  ---
  ```
- **冲突处理规则**：若同时存在 Frontmatter 与行内注解（`<!-- source: ... -->`），**Frontmatter 具有最高绝对优先级**。若两者针对同一路径声明了相互矛盾的 `relation`，解析器直接触发 `DOC_SOURCE_DECLARATION_CONFLICT` 并进入 `fail_closed`；
- **解析目标**：始终动态绑定工作区文件系统的当前物理文件。正文或注解中的 Git 提交信息仅作为辅助追溯标记，不作为排他性历史快照锁；
- **排他性规则**：解析 `CURRENT.md` 时，解析器**严禁读取或寻找 `CURRENT.sources.yaml` 侧车文件**。

#### 6.6.2 历史报告 (`REPORT-NNN.md`) 不可变快照协议
- **法律地位**：已完成学术/工程归档的冻结历史资产（Frozen Historical Asset）；
- **唯一解析依据**：必须且仅能通过物理侧车文件 `reports/history/REPORT-NNN.sources.yaml` 提取来源；
- **快照强锁定解析规则**：解析器**严禁直接读取当前工作区中的活动文件**，必须根据 sidecar 中记录的 `git_commit`，通过 Git 树对象读取历史提交快照中的文件内容，并核验物理字节是否匹配 `content_hash`。

#### 6.6.3 来源解析失败与异常映射表

| 场景条件 | 检测到的故障现象 | 触发的 Condition Code | 抢占权重 | Envelope 状态 | 预期行为 |
|---|---|---|---|---|---|
| 历史报告 | 找不到 `REPORT-NNN.sources.yaml` 侧车文件 | `SOURCE_MISSING` | 95 | `fail_closed` | `fail_closed` |
| 历史报告 | 侧车文件内声明的 `report_id` 与报告文件名不匹配 | `DEF_CHANGE_TYPE_INVALID` | 45 | `fail_closed` | `fail_closed` |
| 历史报告 | 侧车文件中引用的 Git Commit 在版本库中不存在 | `PROVENANCE_BROKEN` | 90 | `fail_closed` | `fail_closed` |
| 历史报告 | Git 提交中的历史内容与记录的 `content_hash` 不匹配 | `HASH_MISMATCH` | 100 | `fail_closed` | `fail_closed` |
| 历史报告 | 侧车文件中存在重复的来源路径声明 | `AMBIGUOUS_VERSION` | 85 | `fail_closed` | `fail_closed` |
| 历史报告 | 历史快照核验无误，但工作区当前文件已被改动 | `SOURCE_CHANGED_SINCE_PIN` | 5 | `warning` | `warning_attached` |
| 当前报告 | 声明依赖的整理文件在工作区物理丢失 | `SOURCE_MISSING` | 95 | `fail_closed` | `fail_closed` |
| 当前报告 | 声明语法错误或 Frontmatter 与行内注解冲突 | `DEF_CHANGE_TYPE_INVALID` | 45 | `fail_closed` | `fail_closed` |

---

### 6.7 派生索引规范逻辑等价算法 (Canonical Logical Equivalence - CLE)

用于 S29（派生索引删除灾难恢复）等场景的确定性判据。**本规范彻底废除对 SQLite 物理文件的二进制字节一致性要求**，全面采用 `CanonicalDump()` 规范逻辑转储算法：

$$\text{CLE}(DB_1, DB_2) \iff \operatorname{SHA256}(\text{CanonicalDump}(DB_1)) == \operatorname{SHA256}(\text{CanonicalDump}(DB_2))$$

#### 6.7.1 算法执行步骤与表遍历次序
算法在只读事务（`PRAGMA query_only = ON;`）下执行，严格按以下固定次序遍历六张核心业务表：
1. `documents`
2. `entities`
3. `relations`  *(必须包含关系拓扑表，防止断链漏洞)*
4. `runs`
5. `source_refs`
6. `events`

*SQLite 内部系统表（如 `sqlite_master`、`sqlite_sequence`、`sqlite_stat%`）一律忽略。*

#### 6.7.2 表列投影与复合主键排序契约

每张表提取固定列，并按规范主键进行无歧义升序排序（Strict Total Ordering）：

```text
Table: documents
  Columns: [id, doc_type, path, content_hash, git_commit, section, parent_id, status, meta_json]
  Sort Key: ORDER BY id ASC

Table: entities
  Columns: [id, entity_type, version, path, content_hash, spec_ref, status]
  Sort Key: ORDER BY id ASC, version ASC

Table: relations
  Columns: [source_id, target_id, relation_type, authority]
  Sort Key: ORDER BY source_id ASC, target_id ASC, relation_type ASC

Table: runs
  Columns: [run_id, experiment_id, experiment_ref, model, context_length, seed, status, reason]
  Sort Key: ORDER BY run_id ASC

Table: source_refs
  Columns: [owner_id, ref_path, ref_commit, content_hash, relation_type]
  Sort Key: ORDER BY owner_id ASC, ref_path ASC, content_hash ASC

Table: events
  Columns: [event_id, event_type, timestamp, actor, payload_json]
  Sort Key: ORDER BY event_id ASC
```
*(注：瞬态构建时间戳 `indexed_at`、查询瞬时字段 `as_of` 以及物理存储 `rowid` 显式排除在外。)*

#### 6.7.3 规范 JSON 字节序列化与哈希
1. **字段规范化**：
   - `NULL` 映射为 JSON `null`；
   - `INTEGER` 保持为 JSON 整数；
   - `REAL` 统一格式化为标准 6 位浮点数字符串（`%.6f`），`-0.0` 统一归一化为 `0.000000`；出现 `NaN` 或 `Infinity` 直接抛出异常拒绝；
   - `TEXT` 统一执行 Unicode NFC 归一化，按照 RFC 8259 规范进行字符转义；
   - `BLOB` 统一转为小写十六进制字符串并附带 `hex:` 前缀。
2. **字节流生成**：
   - 使用紧凑格式编码（`separators=(',', ':')`），消除任何冗余空格；
   - 字典键严格按字母升序排列（`sort_keys=True`）；
   - 行与行之间以单个换行符 `\n` 分隔；
3. **哈希计算**：将生成的整库规范字节流送入 `SHA-256` 算法，输出 64 位十六进制摘要作为该数据库的逻辑指纹。

---

## 7. 实施路线图

1. **Phase 1 (v0.1 - 核心闭环与基线校验)**：
   - 固化 `universe-seed-v1` 种子宇宙与 `oracle-manifest.yaml` 真值表；
   - 实现 `compile_scenario_gold.py` 与 `CanonicalDump()` 基准比对器；
   - 落地针对 B1（内核层）的 32 类场景全量自动化断言，CI 通过率达 100%。
2. **Phase 2 (v0.5 - 动态演化与策略审计)**：
   - 接入 DSL 执行器，自动化注入崩溃、断链、时间推移与跨 Session 切换；
   - 接入 B2 Agent 检索策略审计器，严格检验 Tool Calls 路由决策树。
3. **Phase 3 (v1.0 - 开源发布与全模型评测)**：
   - 发布容器化评测套件，面向主流开源与商业 Agent 发布 Benchmark 排行榜。
