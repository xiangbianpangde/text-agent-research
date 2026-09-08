# 超长程实验 Text Agent 检索与研究状态系统 PRD

## 0. 文档信息

**项目名称**：Long-Horizon Research Agent / 超长程实验 Text Agent  
**当前阶段**：Demo / P0  
**基础 Harness**：Pi  
**核心用户**：研究者 + 常驻 Text Agent  
**下游执行者**：一个或多个非常驻 Experiment Coding Agent  
**文档目的**：

1. 向开发 Agent 解释项目真实问题，而不仅是描述功能；
2. 明确 P0 边界；
3. 固化关键设计原则，避免开发过程中被“优化”成普通 RAG / 普通 Coding Agent；
4. 为检索、文件维护、日志、provenance 和未来插件化提供统一约束。

---

# 1. 背景

## 1.1 当前工作方式

当前研究过程基本遵循：

```text
实验执行
   ↓
产生 Raw 文件
   ↓
整理 Raw
   ↓
形成 Organized 文件
   ↓
基于所有 Organized 文件建立 Index / Directory
   ↓
阶段性综合
   ↓
形成 Report / 汇报文件
```

实际使用时则反向读取：

```text
Report
  ↓
如果信息不够
  ↓
Index / Directory
  ↓
定位相关 Organized
  ↓
如果仍需审计
  ↓
Raw
```

这是当前用户已经验证有效的工作方式。

本项目不应破坏这一工作流。

系统的目标不是重新发明科研知识管理，而是：

> **让 Agent 能够稳定、长期、自动地维护和使用这套层级。**

---

# 2. 核心问题

本项目面对的不是传统意义上的“长上下文”问题。

传统 Long-Horizon Agent 通常是：

```text
一次连续任务
↓
持续数十分钟或数小时
↓
模型上下文不断增长
```

而本项目中的“超长程”指：

```text
现实世界时间：

Day 1
   ↓
Task A

Day 4
   ↓
Task B

Day 12
   ↓
Task C

Day 28
   ↓
Task D
```

其中可能发生：

- 实验运行数小时或数天；
- 人工实验操作；
- 会议；
- 新数据生成；
- 不同模型参与；
- 不同 Agent 执行；
- 数天没有任何 Agent 会话；
- 历史定义发生变化；
- 当前研究方向发生调整。

因此真正的问题不是：

> “模型能不能记住 1M context？”

而是：

> **几十个彼此间断的 Task Slice 之后，系统是否仍然知道当前研究状态是什么、为什么变成这样、历史上发生过什么，以及某个结论来自哪里。**

---

# 3. 产品定位

本项目不是：

- 普通 RAG；
- 知识库聊天机器人；
- 单一 Coding Agent；
- 单纯实验管理系统；
- 完整多 Agent runtime；
- MLOps 平台。

本项目应被理解为：

> **以 Pi 为基础 Harness、以常驻 Text Agent 为 Research Control Plane、以非常驻 Experiment Coding Agent 为 Execution Plane 的超长程实验研究系统。**

核心结构：

```text
                    Human
                      │
                      ▼
             Persistent Text Agent
             Research Control Plane
                      │
                      │ TaskSlice
                      ▼
          Experiment Coding Worker(s)
                      │
                      │ Result / Raw
                      ▼
                Research Files
                      │
                      ▼
                Text Agent ingest
```

---

# 4. 为什么先做 Text Agent

Experiment Coding Agent 的大部分能力已经可以复用成熟 Coding Agent 技术：

- read；
- write/edit；
- bash；
- grep/glob；
- Git；
- testing；
- runtime；
- sandbox；
- code execution。

当前真正缺失的是：

```text
跨 Session 状态连续性
文件长期维护
结论来源
实验版本关系
阶段性综合
历史认知
研究事件
Task Slice 影响
```

因此开发优先级必须是：

> **先完成 Text Agent / Research Control Plane，再复用 Coding Agent 作为 Worker。**

---

# 5. 核心架构原则

## 5.1 Pi 只负责当前 Agent 运行

Pi 解决：

> 当前这一轮 Agent 如何使用模型和工具工作。

Research Core 解决：

> 一个持续数周或数月的项目如何保持连续。

原则：

> **Pi 负责 Agent，Research Core 负责时间。**

---

## 5.2 Model is not the maintainer

模型不能被视为可靠的长期文件维护器。

不能依赖：

- system prompt；
- Agent 自觉；
- “结束前记得更新文件”；
- Skill；
- 长上下文记忆。

原因：

随着超长程任务推进，模型必然受到：

- 上下文噪声；
- 注意力偏移；
- 压缩丢失；
- 幻觉；
- 局部任务目标；
- 多版本文件；
- 历史信息污染

的影响。

因此：

> **模型负责语义判断，Harness 负责状态正确性。**

---

# 6. 系统必须解决的核心失效模式

## FM-01 文件语义漂移

多个文件分别经过局部合理修改后，不再描述同一个研究世界。

---

## FM-02 定义漂移

例如：

```text
H003
Metric M02
Dataset D04
Experiment E017
```

其含义在后续任务中被模型无意修改。

---

## FM-03 历史覆盖

旧实验、旧 Report 或旧结论被新内容覆盖，导致无法恢复当时为什么这么判断。

---

## FM-04 Provenance 断链

存在结论：

```text
A 优于 B
```

但无法找到它具体来自：

```text
哪个 Organized
哪个实验
哪个 Raw
```

---

## FM-05 Summary Laundering

信息不断经历：

```text
Raw
→ Summary A
→ Summary B
→ Report
```

最后结论只知道自己来自另一个总结，而无法追到原始资料。

---

## FM-06 Index 成为第二真源

索引文件与真实文件不一致，Agent 却继续相信索引。

---

## FM-07 RAG 混淆版本

语义检索返回“相似但错误版本”的 Experiment / Report / Definition。

---

## FM-08 Worker 状态泄漏

Coding Agent 自己的上下文被误认为研究项目的长期状态。

---

## FM-09 日志污染

Raw execution log 与 Research Event 混在一起，使长期历史难以理解。

---

## FM-10 自动维护篡改语义

维护程序擅自：

```text
old definition
→ latest definition
```

导致历史实验语义被改变。

---

# 7. 信息层级

P0 必须正式支持四层：

## L0 Raw

原始实验材料。

特征：

- immutable；
- 可 hash；
- 可外部存储；
- 不进行语义重写。

---

## L1 Organized

Raw 整理后的主要研究文件。

特征：

- Markdown / YAML / CSV 等人类可读格式；
- 可持续修改；
- Git versioned；
- 必须能向下指向 Raw。

---

## L2 Index

项目导航与目录。

特征：

- 可自动生成；
- 可重建；
- 不是证据；
- 不成为 canonical truth。

---

## L3 Report

阶段性综合结论。

分为：

```text
CURRENT.md
```

和：

```text
Historical Reports
```

CURRENT：

- 当前认知；
- 可持续维护。

Historical Report：

- 时间点快照；
- freeze 后不可自动修改。

---

# 8. 核心检索设计

## 8.1 默认阅读路径

```text
Report
↓
Index
↓
Organized
↓
Raw
```

这是默认 progressive disclosure。

---

## 8.2 Provenance 路径

```text
Report Conclusion
↓
Exact Organized Version
↓
Experiment / Run
↓
Raw
```

Index 不属于强制 provenance。

---

# 9. 检索工具分层

## 9.1 Layer 1：Filesystem Retrieval

工具：

```text
glob
find
ls
```

解决：

- 文件在哪里；
- 有哪些实验；
- 有哪些 Report；
- 有哪些 Run。

---

## 9.2 Layer 2：Lexical Retrieval

工具：

```text
grep
read
```

解决：

- 找关键词；
- 找 ID；
- 找标题；
- 找错误；
- 找某个实验变量。

---

## 9.3 Layer 3：Structured Retrieval

使用可重建 SQLite 索引。

支持查询：

```text
某 Hypothesis 的所有实验
某 Report 的所有来源
某 Definition 的引用者
某状态下的 Task
某 Run 的 ExperimentSpec
```

SQLite 永远是 derived index。

---

## 9.4 Layer 4：Provenance Retrieval

支持关系：

```text
generated_from
organized_from
based_on
uses
derived_from
supersedes
invalidates
motivated_by
supports
contradicts
```

P0 至少提供：

```text
trace
sources
history
impact
```

---

## 9.5 Layer 5：Semantic Retrieval

RAG 为 fallback。

适合：

- 论文；
- meeting notes；
- 自由文本；
- 长日志；
- 不知道具体路径的模糊回忆。

禁止用 semantic retrieval 作为以下问题的权威来源：

- identity；
- exact version；
- ExperimentSpec；
- Run status；
- historical provenance；
- Definition version。

---

# 10. 文件组织

P0 建议：

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
├── tasks/
│
├── runs/
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

---

# 11. Report 来源系统

每个 Historical Report：

```text
REPORT-003.md
REPORT-003.sources.yaml
```

示例：

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

核心要求：

> Report 必须引用具体历史版本，而不是引用 latest file。

---

# 12. 关键结论引用

不是每句话都需要结构化。

只有高价值结论建议加入：

```markdown
<!-- sources:
organized/EXP-017/result.md@a73bf §4.2
organized/EXP-021/analysis.md@b12ac §3.1
-->
```

原则：

> 重要结论必须可以向下追。

---

# 13. Organized 来源

Organized 必须能定位 Raw。

例如：

```yaml
---
experiment: EXP-017

sources:
  - raw/EXP-017/R051/
  - raw/EXP-017/R052/
  - raw/EXP-017/R053/
---
```

不要求 P0 把每个 observation 都拆成 entity。

---

# 14. Historical Report

阶段结束：

```text
CURRENT.md
↓
freeze
↓
REPORT-NNN.md
```

冻结动作必须：

1. 保存 Report；
2. 生成 sources manifest；
3. pin source Git revision；
4. 校验 source existence；
5. 写入 Research Event；
6. 更新 Index。

Historical Report 禁止：

```text
自动重新生成
自动升级 source
跟随 Organized 最新版本变化
```

---

# 15. Research Event Log

Research Event 是项目现实时间的历史。

与 Pi Session Log 分离。

P0 事件建议：

```text
ProjectCreated
TaskCreated
TaskCompleted
RawIngested
OrganizedUpdated
ExperimentCreated
ExperimentRevised
RunStarted
RunCompleted
ReportFrozen
DefinitionRevised
SourceInvalidated
```

Research Event：

> 描述研究世界发生了什么。

Agent Execution Log：

> 描述模型和工具具体做了什么。

二者不可混淆。

---

# 16. Hook / Gate / Reconciler

## 16.1 Gate

防止非法状态。

P0 Gate：

### G-01

Frozen Report 禁止普通 edit。

### G-02

Frozen ExperimentSpec 禁止 overwrite。

### G-03

Completed Run 禁止 overwrite。

### G-04

Historical Report 的 source 不得自动升级。

### G-05

Definition semantic change 必须产生新版本。

---

## 16.2 Hook

事件发生后自动维护。

### H-01 Raw Ingest

自动：

- metadata；
- hash；
- index update。

### H-02 Organized Update

自动：

- 更新 Index；
- 验证 Raw refs；
- 写 event。

### H-03 Report Freeze

自动：

- 解析 source；
- pin exact revision；
- 生成 source manifest；
- 更新 Index；
- 写 event。

### H-04 Definition Revision

自动：

- 创建新 version；
- impact scan；
- mark stale references。

---

## 16.3 Reconciler

系统启动或周期执行：

检查：

```text
missing source
dangling ref
orphan Organized
orphan Raw
index mismatch
missing manifest
broken Git revision
stale CURRENT reference
```

能自动确定性修复的：

自动修复。

涉及科学语义的：

```text
review_required
```

---

# 17. 定义性文件

以下内容视为 Canonical Definition：

```text
Hypothesis
Metric
Dataset
Protocol
Baseline
ExperimentSpec
重要 Terminology
```

这些不能依赖 Agent 注意力维护。

修改规则：

```text
Definition@v1
↓ semantic change
Definition@v2
```

禁止原地覆盖历史语义。

---

# 18. Current 与 Historical 分离

CURRENT：

> 当前应该相信什么。

Event / Report History：

> 当时为什么相信。

这两个概念必须同时存在。

系统不得因为当前结论变化而改写历史 Report。

---

# 19. Task Slice

一个 Worker 每次只完成整个研究过程中的一个切片。

TaskSlice 至少包含：

```yaml
task_id:

objective:

inputs:

scope:

constraints:

expected_outputs:

status:

result_refs:
```

Coding Worker 不负责：

> 判断整个研究问题是否成立。

它只负责：

> 完成本地实验切片并产生结构化 Handoff。

---

# 20. Worker Handoff

建议 Worker 输出：

```yaml
task_id:
status:

did:

runs:

outputs:

anomalies:

unresolved:

changed_files:

notes:
```

Text Agent ingest 后再判断整体影响。

---

# 21. Pi 集成原则

P0 不修改 Pi 核心。

采用：

```text
Pi
↓
Extension
↓
Research Core
```

Research Core 应尽量独立。

建议：

```text
packages/
  research-core/
  research-fs/
  research-events/
  research-index/

extensions/
  research-runtime/
  research-integrity/
```

未来必须允许：

```text
Pi adapter
↓
DeepSeek Harness adapter
```

而不迁移 Research Data。

---

# 22. Plugin Strategy

Core 必须极薄。

Core 应只知道：

```text
Entity
Version
Mutation
Event
Permission
Session
Hook
Gate
```

不要让 Core 内建：

```text
LLM experiment
statistics
literature
biology
RAG
dashboard
```

这些未来通过 plugin / skill 增加。

原则：

> **功能可插件化，数据正确性不可插件化成可选能力。**

---

# 23. Skill 与确定性机制边界

Skill 负责：

```text
怎么设计实验
怎么分析结果
怎么写 Report
怎么判断异常
```

Harness 负责：

```text
不能覆盖历史
source 必须存在
revision 必须固定
index 必须可重建
mutation 必须产生 event
```

不能使用 Skill 代替 Gate。

---

# 24. P0 用户故事

## US-01

作为研究者，我进入项目后希望 Agent 能直接告诉我当前研究结论，而不重新扫描所有 Raw。

验收：

```text
读取 CURRENT.md 即可完成大部分回答。
```

---

## US-02

我问：

> 为什么得到这个结论？

Agent 能从 Report 找到对应 Organized。

---

## US-03

我继续问：

> 我想看原始实验。

Agent 能从 Organized 定位 Raw。

---

## US-04

我问：

> 两周前我们是不是有不同判断？

Agent 能找到 Historical Report。

---

## US-05

我问：

> 当时为什么这么判断？

Agent 能定位 Historical Report 的 exact Organized source version。

---

## US-06

某 Organized 文件今天被修改。

旧 Report 的历史来源不能改变。

---

## US-07

某 source 被删除或移动。

Reconciler 能检测 broken provenance。

---

## US-08

Agent 想直接改 Frozen Report。

系统拒绝。

---

# 25. P0 功能范围

必须实现：

1. Current Report；
2. Historical Report；
3. Report freeze；
4. Report source manifest；
5. Organized → Raw source reference；
6. Index；
7. `trace`；
8. `sources`；
9. Research Event Log；
10. Basic Hook；
11. Basic Gate；
12. Reconciler；
13. Git revision pinning；
14. SQLite derived index；
15. Pi Extension 接入。

---

# 26. P0 不实现

明确推迟：

- Graph DB；
- Neo4j；
- 全项目 RAG；
- 自动科学结论更新；
- 多 Agent negotiation；
- 完整 scheduler；
- GUI；
- Dashboard；
- 复杂权限系统；
- 每句话 Claim ID；
- 全量 Evidence ontology；
- 自动 planner；
- 自动 reviewer；
- 云部署；
- 分布式 Artifact Store。

---

# 27. P1 候选

P1 再考虑：

- semantic RAG；
- cross-report conclusion history；
- impact analysis；
- structured provenance graph；
- literature retrieval；
- multi-worker；
- scheduler；
- dashboard；
- timeline UI；
- Definition diff；
- worker routing；
- statistics skill；
- automatic stale detection。

---

# 28. 核心 Tool API

P0 推荐一个统一工具：

```text
research
```

或：

```text
researchctl
```

最少支持：

```text
research query
research trace
research sources
research history
research freeze-report
research reindex
research reconcile
```

---

# 29. 示例

用户：

> 我们现在关于 long-context 的判断是什么？

Agent：

```text
read reports/CURRENT.md
```

---

用户：

> 为什么？

Agent：

```text
research sources REPORT-CURRENT:long-context
```

得到：

```text
organized/EXP-017/result.md
organized/EXP-021/analysis.md
```

---

用户：

> 我想看原始数据。

Agent：

```text
read Organized source metadata
```

得到：

```text
raw/EXP-017/R052/
raw/EXP-021/R061/
```

---

用户：

> 8 月 10 日不是这么说的。

Agent：

```text
research history long-context
```

找到：

```text
REPORT-001
```

再：

```text
research sources REPORT-001:long-context
```

得到当时 exact Git revision。

---

# 30. 验收标准

P0 Demo 至少需要构造一个跨多个阶段的模拟研究项目。

建议：

```text
阶段 1
Raw A/B
→ Organized
→ REPORT-001

阶段 2
更新 Organized
→ CURRENT 改变
→ REPORT-002

阶段 3
某 Raw invalid
→ 新 CURRENT
→ REPORT-003
```

然后验证系统可以正确回答：

### A

当前结论是什么？

### B

当前结论来自哪些 Organized？

### C

这些 Organized 来自哪些 Raw？

### D

REPORT-001 当时的来源是什么？

### E

REPORT-001 来源文件后来是否修改？

### F

为什么 REPORT-001 与 REPORT-003 不同？

### G

旧 Report 是否保持原历史语义？

### H

删除一个 source 后 Reconciler 是否报警？

如果这些能力稳定，就说明 P0 成功。

---

# 31. 非功能要求

## 可审计

任何关键 Report 能够机械向下追。

## 可恢复

删除 `.index/` 后可以 rebuild。

## 可迁移

Research Data 不依赖 Pi 私有内部格式。

## 人类可读

主要状态使用：

- Markdown；
- YAML；
- JSON；
- CSV。

## 最小隐藏状态

禁止将核心研究信息只放：

- SQLite；
- vector DB；
- Agent session；
- memory。

## Fail-closed

发现不一致时：

```text
无法确定
```

优于：

```text
自动猜最新版本。
```

---

# 32. 开发 Agent 禁止事项

开发过程中不得擅自：

### 1

把整个系统改造成 embedding-first RAG。

### 2

把 SQLite 变成唯一 source of truth。

### 3

让 Index 成为 canonical truth。

### 4

允许 Historical Report 自动刷新。

### 5

自动把旧 reference 升级到新 Definition。

### 6

通过 prompt 代替 Gate。

### 7

把 Research Event 与 Agent Execution Log 合并。

### 8

为了“减少文件数量”删除历史 snapshot。

### 9

让 Coding Worker 自己维护整个研究状态。

### 10

为了扩展性过早实现完整 Multi-Agent Runtime。

---

# 33. 项目真正要验证的研究假设

本 Demo 的核心假设不是：

> “更复杂的 RAG 能让 Agent 做更长任务。”

而是：

> **超长程任务的主要瓶颈之一，是持久研究状态在多个间断 Agent episode 之间发生语义漂移、历史断链和文件状态腐烂。**

进一步假设：

> **通过显式文件层级 + 历史版本绑定 + Research Event + Hook/Gate/Reconciler，可以让 Agent 即使忘记过去，也能可靠恢复过去。**

因此核心评价指标不是：

```text
一次 Session 能跑多长
```

而是：

```text
经过多少个间断 Task 后，
系统仍能正确回答：

现在是什么？
过去是什么？
为什么改变？
证据在哪里？
```

---

# 34. 一句话产品定义

> **一个建立在 Pi 之上的 filesystem-native 超长程研究 Agent 基础设施，通过 Report → Index → Organized → Raw 的分层检索、可追溯历史来源以及确定性文件维护，使 Text Agent 能在数周或数月的间断实验任务中持续保持研究状态的一致性。**

---

# 35. 最终设计原则

本项目所有实现决策都应优先遵守以下五条：

1. **当前结论应当容易获得。**
2. **任何重要结论应当能够向下追溯。**
3. **任何历史结论都不能因为今天的文件变化而被重新解释。**
4. **长期正确性不能依赖模型注意力。**
5. **Agent 可以忘记，但系统不能忘记。**
