# 超长程实验 Agent 检索系统设计方案

## 1. 目标

本系统服务于一种不同于传统 Coding Agent 的“现实时间超长程实验任务”。

传统长程任务通常表现为：

- 单次 Agent 会话持续较长；
- 上下文不断增长；
- 任务在较连续的模型时间内完成。

本项目中的超长程实验则表现为：

- 一个研究项目持续数天、数周甚至数月；
- 大量 Agent 会话彼此间断；
- 每次任务只处理整个研究项目中的一个 Task Slice；
- 实验运行、人工操作、会议、数据生成等发生在现实时间中；
- Text Agent 必须跨这些间断任务持续理解“整个研究目前在哪里”。

因此检索系统的目标不是单纯回答：

> “哪些文本和当前问题语义相似？”

而是可靠回答：

1. 当前项目的结论是什么？
2. 某个结论为什么成立？
3. 这个结论来自哪些整理文件？
4. 整理文件对应哪些原始实验？
5. 某个实验使用的是哪个版本的定义？
6. 某项定义后来是否变化？
7. 两周前为什么得到和现在不同的结论？
8. 某个 Task Slice 对整个研究状态产生了什么影响？
9. 哪些内容是当前有效状态，哪些只是历史状态？
10. 当模型遗忘、上下文压缩或换 Agent 后，是否仍然能够机械恢复上述信息？

核心设计原则：

> **显式结构优先于语义猜测，确定性检索优先于 RAG，当前状态与历史来源必须同时可恢复。**

---

# 2. 总体信息结构

系统以用户现有工作流为基础，不强行改造成细粒度知识图谱。

核心信息层级保持：

```text
L0 Raw
原始实验材料
        ↓ 整理

L1 Organized
整理后的实验文件
        ↓ 编目

L2 Index
目录 / 索引 / 导航层
        ↓ 综合

L3 Report
阶段性汇报 / 当前结论
```

用户和 Text Agent 的正常阅读顺序：

```text
Report
  ↓ 信息不足
Index
  ↓ 找到相关实验
Organized
  ↓ 需要验证细节
Raw
```

这是一套 Progressive Disclosure 检索体系。

系统默认不从 Raw 开始理解项目，也不要求模型每次重新扫描整个研究目录。

---

# 3. 四层的职责

## 3.1 L0 — Raw

Raw 表示：

> 原始世界发生了什么。

例如：

- 原始实验日志；
- CSV；
- JSONL；
- 模型原始输出；
- benchmark 输出；
- stdout / stderr；
- 图片；
- checkpoint；
- 人工实验记录；
- 原始会议材料；
- 仪器数据。

Raw 原则：

- immutable；
- 不润色；
- 不覆盖；
- 可增加 metadata；
- 可标记 invalid/corrupted；
- 重要文件保存 hash；
- 必须有稳定身份或稳定路径。

Raw 不承担“解释”。

---

## 3.2 L1 — Organized

Organized 表示：

> 人或 Agent 已经如何整理这些 Raw。

例如：

```text
organized/
  EXP-017/
    result.md
    analysis.md
```

内容可以包括：

- 实验目的；
- 设置；
- 结果表；
- 图；
- 异常；
- 初步观察；
- Raw 路径；
- 运行编号；
- 数据处理说明。

Organized 是最重要的“研究工作层”。

它：

- 对人类可读；
- 对 Agent 易于 grep/read；
- 可以持续维护；
- 使用 Git 保留历史版本；
- 必须能够向下定位 Raw。

---

## 3.3 L2 — Index

Index 表示：

> 整个研究空间里有什么，以及去哪里找。

它不是证据层，而是导航层。

例如：

```text
INDEX.md

## 长上下文实验

EXP-017
目的：比较模型 A/B 在 128K 场景下的性能
状态：完成
主要发现：A 当前表现更好

整理文件：
organized/EXP-017/result.md

Raw：
raw/EXP-017/

关联汇报：
REPORT-003 §3.2
```

Index 主要回答：

- 有哪些实验？
- 哪个实验和某个问题相关？
- 当前有哪些 active / completed / failed Task？
- 某个 Hypothesis 对应哪些 Experiment？
- 文件在哪里？

Index 可以：

- 自动维护；
- 自动生成；
- 从 canonical files 重建。

它不应该成为唯一真源。

---

## 3.4 L3 — Report

Report 表示：

> 当前或者某个阶段，我们如何理解整个研究。

例如：

```text
reports/
  CURRENT.md
  history/
    REPORT-001.md
    REPORT-002.md
    REPORT-003.md
```

正常情况下 Text Agent 首先阅读 `CURRENT.md`。

Report 应该：

- 高度压缩；
- 面向人阅读；
- 记录关键结论；
- 记录重要不确定性；
- 记录当前研究状态；
- 对重要结论保留来源引用。

历史 Report 一旦冻结，禁止自动重写。

---

# 4. 两条核心检索链

系统实际上同时存在两种完全不同的检索。

## 4.1 阅读检索链

用于快速理解项目：

```text
CURRENT Report
      ↓
    Index
      ↓
 Organized
      ↓
     Raw
```

强调：

> 从高信息密度向低层逐步下钻。

---

## 4.2 Provenance 检索链

用于回答：

> “这个结论到底从哪里来的？”

路径：

```text
Report Conclusion
      ↓
Exact Organized Version
      ↓
Experiment / Run
      ↓
Raw
```

注意：

> Index 不一定属于 provenance。

Index 是导航。

来源追踪应该可以绕过 Index，直接从 Report 指向真正的 Organized source。

---

# 5. 检索系统分层

我建议把 Text Agent 的检索能力正式划分为五层。

---

## Layer 1：物理路径检索

工具：

```text
glob
find
ls
```

负责回答：

- 哪些文件存在？
- 某个 Experiment 在哪里？
- 有哪些 Run？
- 某个目录下有哪些内容？

适合：

> identity 已经比较明确的问题。

例如：

```text
找到 EXP-017
列出 REPORT 历史
查看所有 R052 相关文件
```

这是最便宜、最可靠的检索。

---

## Layer 2：Lexical Retrieval

工具：

```text
grep
read
```

负责：

- 搜索术语；
- 找标题；
- 搜索 ID；
- 搜索变量；
- 查找错误信息；
- 搜索某个实验描述。

例如：

```text
grep "long context"
grep "R052"
grep "H003"
```

这仍然应该是主力工具。

因为科研文件通常本身已经具有较强结构。

---

## Layer 3：结构化检索

通过轻量索引，例如 SQLite：

```text
research.sqlite
```

保存的是文件系统派生出来的 metadata。

例如：

```text
entities
--------
id
type
path
version
status
updated_at

relations
---------
source
relation
target

documents
---------
path
type
experiment
stage
status
```

查询例如：

```text
所有与 H003 有关的 completed experiment

所有引用 Metric M03@v1 的 active Task

所有在 REPORT-003 中被引用的 Organized 文件

所有引用 R052 的结论
```

这一层主要解决：

> grep 很难稳定回答的结构问题。

SQLite 不是 source of truth。

必须支持：

```text
reindex
```

完全从文件重建。

---

# 6. Layer 4：Provenance / Relation Retrieval

这是实验 Agent 和普通 Coding Agent 最大的区别之一。

Coding Agent 的重要关系通常是：

```text
symbol
definition
reference
call graph
```

Experiment Agent 的重要关系是：

```text
Question
   ↓
Hypothesis
   ↓
Experiment
   ↓
Run
   ↓
Raw
   ↓
Organized
   ↓
Report
   ↓
Decision
```

系统需要支持 typed relation，例如：

```text
generated_from
organized_from
summarized_by
referenced_by
supports
contradicts
uses
derived_from
supersedes
invalidates
motivated_by
```

例如：

```text
R052
  --uses--> E017@v4

organized/EXP-017/result.md
  --organized_from--> R052

REPORT-003 §3.2
  --based_on--> organized/EXP-017/result.md@commit-a73bf

REPORT-004
  --supersedes--> REPORT-003
```

推荐提供：

```text
trace <entity>

parents <entity>

children <entity>

why <entity>
```

例如：

```text
trace REPORT-003:C2
```

得到：

```text
REPORT-003:C2
  ↓
EXP-017/result.md @ a73bf
  ↓
R052
  ↓
raw/EXP-017/R052/
```

---

# 7. Layer 5：Semantic Retrieval / RAG

RAG 不作为主检索层。

只用于：

- 长篇会议记录；
- 文献；
- 大量历史笔记；
- 自由文本；
- 不知道具体文件位置时的语义搜索。

例如：

> 我记得之前讨论过“长上下文性能下降可能主要来自检索而不是推理”，在哪里？

这种问题适合 RAG。

但是以下问题禁止优先使用 RAG：

```text
R052 使用的是哪个 ExperimentSpec？
REPORT-003 当时引用的是哪个版本的 result.md？
E017@v4 的前一个版本是什么？
某个 Run 是否 invalid？
```

这些必须通过：

```text
metadata / manifest / provenance
```

回答。

原则：

> **Identity、Version、Causality、History 不交给向量相似度猜。**

---

# 8. Report Source 设计

为了保持用户现有 Report 工作方式，不需要把每句话变成独立 Evidence Entity。

采用轻量方案。

每个 Report：

```text
REPORT-003.md
REPORT-003.sources.yaml
```

例如：

```yaml
report: REPORT-003

created_at: 2026-08-28

sources:
  - path: organized/EXP-017/result.md
    git_commit: a73bf21
    sections:
      - long-context

  - path: organized/EXP-021/analysis.md
    git_commit: b12ac77
    sections:
      - model-comparison
```

Report 文件本身保持适合阅读。

对于特别重要的关键结论，可以增加 claim-level reference：

```markdown
## 3.2 长上下文表现

模型 A 在当前 Protocol 下整体优于 B。

<!-- sources:
EXP-017/result.md@a73bf §4.2
EXP-021/analysis.md@b12ac §3.1
-->
```

不要求所有句子都如此。

只有：

> 会影响后续研究决策的重要结论

需要 claim-level provenance。

---

# 9. 为什么必须保存 exact source version

如果 Report 只引用：

```text
organized/EXP-017/result.md
```

那么 Organized 后来修改后：

> 历史结论的来源就被改变了。

因此 Report 冻结时必须保存：

```text
path
+
git commit / content hash
+
section
```

历史链成为：

```text
REPORT-003
      ↓
result.md @ commit A
```

而不是：

```text
REPORT-003
      ↓
result.md latest
```

这是整个历史来源系统最关键的一条规则。

---

# 10. Current 与 Historical 需要物理分离

推荐：

```text
reports/
├── CURRENT.md
└── history/
    ├── REPORT-001.md
    ├── REPORT-001.sources.yaml
    ├── REPORT-002.md
    ├── REPORT-002.sources.yaml
    └── ...
```

`CURRENT.md`：

- 当前最新认知；
- 可以持续维护。

阶段结束：

```text
CURRENT
   ↓ freeze
REPORT-004
```

随后继续生成新的 CURRENT。

旧 REPORT：

> 永远不自动刷新。

即使 Organized 文件后来发生改变。

这样可以回答：

> 为什么 8 月 15 日和 8 月 28 日的判断不同？

---

# 11. Raw → Organized 的来源链

每个 Organized 文件至少需要能说明：

```text
我整理的是哪些 Raw？
```

可以直接使用 Markdown 元信息：

```yaml
---
id: ORG-EXP017
experiment: EXP-017

sources:
  - raw/EXP-017/R051/
  - raw/EXP-017/R052/
  - raw/EXP-017/R053/
---
```

或者：

```markdown
## Raw Sources

- R051: raw/EXP-017/R051/
- R052: raw/EXP-017/R052/
- R053: raw/EXP-017/R053/
```

不需要把每个数字都拆成 Evidence Entity。

只要：

> Organized 能稳定向下定位 Raw。

---

# 12. Research Index 的职责

Index 推荐至少维护四种导航。

## 实验索引

```text
Hypothesis → Experiment
```

## 时间索引

```text
日期 → Experiment / Run / Report
```

## 主题索引

```text
Topic → Organized Files
```

## 状态索引

```text
active
completed
failed
invalid
superseded
```

例如：

```text
INDEX.md

## H003

Experiments:
- EXP-017 completed
- EXP-021 completed
- EXP-028 active

Current report:
REPORT-004 §2

Organized:
- EXP-017/result.md
- EXP-021/analysis.md
```

Index 可以自动生成。

---

# 13. 日志与检索的结合

系统应区分三种日志。

## Agent Execution Log

记录：

```text
tool call
tool result
stdout
stderr
reasoning trajectory
```

用于：

> debugging / audit。

---

## Task Handoff Log

记录每个 Task Slice：

```text
做了什么
产生了什么
有哪些异常
有哪些 unresolved
```

用于：

> Text Agent 快速 ingest。

---

## Research Event Log

记录：

```text
ExperimentCreated
RunCompleted
ReportFrozen
DefinitionRevised
TaskCompleted
EvidenceInvalidated
DecisionCommitted
```

用于：

> 项目时间轴和历史状态恢复。

检索时：

```text
当前是什么？
→ Report / State

文件在哪里？
→ Index

为什么？
→ Provenance

当时发生了什么？
→ Research Event Log

Agent 具体做了什么？
→ Execution Log
```

各层职责明确。

---

# 14. Hook / Gate 与检索系统的关系

检索系统的正确性不能依赖 Text Agent 自己记得维护文件。

因此必须由 Harness 自动维护。

## Report Finalize Hook

冻结 Report 时：

1. 扫描 source refs；
2. 校验文件存在；
3. 保存 exact Git commit/hash；
4. 生成 `.sources.yaml`；
5. 更新 Index；
6. 写入 `ReportFrozen` event。

---

## Organized Update Hook

Organized 更新时：

1. 更新 index；
2. 检查 Raw refs；
3. 标记哪些 CURRENT 内容可能 stale；
4. 不修改 Historical Report。

---

## Raw Ingest Hook

Raw 进入系统：

1. 分配 identity；
2. 计算 hash；
3. 写 metadata；
4. 更新 Raw index。

---

## Definition Revision Gate

实验定义发生语义变化：

禁止直接覆盖。

必须：

```text
E017@v3
↓
E017@v4
```

并执行 impact analysis。

---

# 15. Reconciler

因为超长程任务中必然存在：

- Agent 崩溃；
- 人工编辑；
- Git merge；
- Hook Bug；
- 文件移动；
- 外部脚本产生文件。

因此系统需要定期 Reconcile：

```text
Physical Files
      ↓
scan
      ↓
Expected Metadata
      ↓
compare Index
```

检测：

```text
Report 引用了不存在文件

Organized 引用了不存在 Raw

Index 中存在已经删除文件

Report source manifest 缺失

historical source hash 不匹配

orphan raw

orphan organized file
```

可确定性修复的自动修复。

涉及语义的：

```text
review_required
```

交给 Text Agent / Human。

---

# 16. 检索优先级规则

Text Agent 不应该自己随意选择搜索方式。

推荐默认策略：

```text
Step 1
Report

Step 2
显式引用 / Index

Step 3
Structured query / provenance

Step 4
grep

Step 5
Raw

Step 6
Semantic retrieval
```

根据问题类别稍作调整。

---

# 17. 典型问题的检索路线

## “目前关于 X 的结论是什么？”

```text
CURRENT.md
```

---

## “为什么得到这个结论？”

```text
CURRENT
↓
source refs
↓
Organized
```

---

## “这个数据具体怎么来的？”

```text
Organized
↓
Raw reference
↓
Raw
```

---

## “两周前不是这么说的吗？”

```text
Historical Report
↓
Report Source Manifest
↓
Historical Organized Version
```

---

## “有哪些实验和这个问题相关？”

```text
INDEX
+
structured query
```

---

## “我记得我们之前某次讨论过这个概念，但不知道在哪里”

```text
semantic retrieval
```

---

## “R052 到底使用的是 E017 v3 还是 v4？”

```text
Run Manifest / structured metadata
```

禁止 RAG。

---

# 18. 文件系统建议

MVP 可以保持非常简单：

```text
project/
│
├── reports/
│   ├── CURRENT.md
│   └── history/
│       ├── REPORT-001.md
│       ├── REPORT-001.sources.yaml
│       └── ...
│
├── index/
│   └── INDEX.md
│
├── organized/
│   ├── EXP-001/
│   ├── EXP-002/
│   └── ...
│
├── raw/
│   ├── EXP-001/
│   ├── EXP-002/
│   └── ...
│
├── experiments/
│
├── runs/
│
├── tasks/
│
├── events/
│
├── logs/
│
├── .index/
│   └── research.sqlite
│
└── .work/
```

其中：

```text
reports/
organized/
experiments/
tasks/
```

由 Git 管理。

Raw 大文件可以外置，只保存 manifest/path/hash。

`.index/` 完全可重建。

---

# 19. Pi 中的 Tool 设计

不建议增加几十个 Tool。

Pi 原有：

```text
read
write
edit
bash
grep
glob
```

继续保留。

增加一个统一工具：

```text
research
```

或 CLI：

```text
researchctl
```

核心命令：

```text
research query

research trace

research sources

research history

research impact

research reindex

research reconcile
```

例如：

```text
research trace REPORT-003:C2
```

输出：

```text
REPORT-003:C2
↓
organized/EXP-017/result.md@a73bf
↓
R052
↓
raw/EXP-017/R052/
```

又例如：

```text
research history "long-context-performance"
```

输出：

```text
REPORT-001
  tentative

REPORT-002
  weak support

REPORT-003
  moderate support
```

---

# 20. Skill 与 Tool 的边界

Skill 负责：

> 怎么思考。

例如：

```text
research-retrieval
experiment-analysis
result-synthesis
report-writing
history-review
```

Skill 可以告诉模型：

> 遇到来源问题先 trace，不要猜。

但以下必须是确定性的 Tool / Hook：

```text
source validation
Git version binding
index rebuild
reference integrity
hash verification
report freezing
stale detection
```

原则：

> **模型负责理解信息，Harness 负责保证信息链不断。**

---

# 21. 不建议 MVP 做的东西

第一版不建议上：

```text
复杂 Graph DB
Neo4j
所有句子的 Claim ID
全项目 embedding-first RAG
自动科学推理
自动 Conclusion 更新
复杂知识图谱
几十种 entity schema
```

这些会让 Demo 的工程复杂度迅速上升，却没有解决最核心问题。

当前真正需要验证的是：

> 经过几十个间断 Task 和数周现实时间以后，Agent 能否仍然通过 Report → Organized → Raw 准确恢复研究依据与历史状态。

---

# 22. MVP 必须实现的 7 个能力

第一版我建议只做：

### P0-1 Current-first retrieval

默认从 `CURRENT.md` 开始。

### P0-2 Index navigation

自动维护 `INDEX.md`。

### P0-3 Organized → Raw

每个关键整理文件存在 Raw source reference。

### P0-4 Report → Organized

关键结论能够定位整理文件。

### P0-5 Historical source pinning

冻结 Report 时记录：

```text
path + Git commit/hash
```

### P0-6 Trace

提供：

```text
research trace
```

从结论一路向下到 Raw。

### P0-7 Reconcile

自动检测断链。

只要这七个成立，系统就已经具有非常明显的超长程价值。

---

# 23. P1 再增加

P1 可以加入：

```text
structured SQLite query
relation index
Research Event integration
stale impact analysis
history compare
semantic retrieval / RAG
cross-report conclusion evolution
```

---

# 24. 最终架构

```text
                         Text Agent
                             │
                             │ query
                             ▼
                    Retrieval Router
                             │
         ┌───────────────────┼──────────────────┐
         ▼                   ▼                  ▼
      Report              Index             Structured
      Retrieval          Retrieval            Query
         │                   │                  │
         └──────────────┬────┴──────────────────┘
                        ▼
                    Organized
                        │
                        ▼
                       Raw

                        ▲
                        │
                  Provenance Trace
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
         Git History          Research Events
```

旁边运行：

```text
Hooks
Gates
Reconciler
```

持续维护引用正确性。

---

# 25. 核心设计思想

整个系统可以压缩成五句话：

**第一，Report 是入口，不是唯一真源。**

**第二，Index 是导航，不是证据。**

**第三，Organized 是主要研究工作层。**

**第四，Raw 是最终可审计底座。**

**第五，历史来源必须引用“文件的具体历史版本”，而不能只引用当前文件路径。**

因此整个检索系统不是：

```text
Documents
↓
Embedding
↓
RAG
```

而是：

```text
Explicit Research Hierarchy
        +
Filesystem Retrieval
        +
Structured Metadata
        +
Provenance
        +
Historical Versioning
        +
Semantic Retrieval as fallback
```

这更符合当前超长程实验 Agent 的真实需求。

最终目标也不是让 Agent“记住所有历史”，而是：

> **让 Agent 即使忘记历史，也能沿着可靠、确定、可审计的路径重新找到它。**

这应该成为整个检索系统最核心的设计原则。