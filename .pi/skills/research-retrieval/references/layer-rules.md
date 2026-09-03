# 检索分层体系与优先级规则（Layer Rules）

依据《超长程实验 Agent 检索系统设计方案.md》§5、§16 与 §25 规范。

---

## 一、 检索能力五层架构

| 层级 | 类型 | 核心工具 | 适用场景 | 权威度定位 |
|---|---|---|---|---|
| **Layer 1** | 物理路径检索 | `glob`, `find`, `ls` | 文件是否存在、文件列表、目录定位 | 物理事实（最廉价、最可靠） |
| **Layer 2** | 词面检索 | `grep`, `read` | 搜索精确术语、变量、标题、ID、报错日志 | 文本事实（主力日常工具） |
| **Layer 3** | 结构化检索 | `researchctl query` | 跨实体的文档类型、状态、属性关系过滤 | 派生元数据（可从文件系统重建） |
| **Layer 4** | 溯源关系检索 | `researchctl trace`, `sources`, `history`, `impact` | 溯源因果链（Report → Organized → Raw）与下游影响 | 因果依据链（科研审计核心） |
| **Layer 5** | 语义检索（RAG）| `researchctl query --text <T> --semantic` | 自由模糊回忆、词面拼写偏差、位置未知的线索检索 | **仅作为末级 Fallback（建议性）** |

---

## 二、 检索优先级铁律（Priority Invariants）

1. **显式结构优先于语义猜测**：
   - 寻找确定的 Entity、Run、Spec 时，直接查物理路径或调用 Layer 3 结构化查询；
   - 严禁通过语义向量去猜实体归属。
2. **当前结论优先看 CURRENT**：
   - 默认从 `reports/CURRENT.md` 开始获取项目全局现状，避免从零碎片段中自行拼凑。
3. **因果与事实严禁脑补**：
   - 数据来源必查 `sources`，数据根源必下钻 `trace` 到 Raw。
4. **历史演化必须锁定精确版本**：
   - 历史报告引用的 Organized 来源必须绑定精确 Git commit 与 content_hash，不可只记文件路径。
5. **Layer 5 降级原则**：
   - 只有在记不清文件名、出现拼写误差或自由回忆线索时才启用 `--semantic`；
   - 语义检索结果的 `ranking_authority` 始终为 `advisory`（建议性），不可替代真源验证。

---

## 三、 五大核心设计思想（§25）

1. **Report 是入口，不是唯一真源。**
2. **Index 是导航，不是证据。**
3. **Organized 是主要研究工作层。**
4. **Raw 是最终可审计底座。**
5. **历史来源必须引用文件的具体历史版本，而不能只引用当前路径。**
