---
type: 普通
状态: 进行中
tags: [普通, 待晋升]
创建时间: 2026-08-28
更新时间: 2026-08-28
中间名: 科研系统方案
---

# 基于 Pi 的现实时间超长程实验 Agent 架构 v0.1

> 文档性质：项目级架构提案（proposed architecture），可直接进入后续设计评审，但不等于实施授权、科学冻结或当前指针变更。
>
> 来源：2026-08-27 对话“分支 · 设计实验Agent-1”及 R-ICL v4.0 当前物理文件系统、worklog、intercom、实验 runner 现场。
>
> 适用范围：面向医疗与 LLM 实验研究的 Text Agent、Experiment Coding Agent、长期状态与文件治理。
>
> 核心口号：**Minimal core, maximal extensibility, deterministic persistence.**

## 0. 摘要与状态边界

本方案要解决的不是“让一个模型在一个上下文里思考更久”，而是：

> 让多个短时、可替换、可能失败的 Agent 会话，在数周到数月的现实时间里，仍能共同维护一条可追溯、可复现、不会被静默改写的研究历史。

总体架构由五部分组成：

1. 以 Pi 风格的极简 Agent loop 作为 Text Agent 与临时 worker 的运行底座；
2. 以确定性的 Research Harness 管理 identity、version、transaction、event、permission 与 immutable record；
3. 以常驻的逻辑 Text Agent 维护研究方向、解释证据并派发 TaskSlice；
4. 以非常驻 Experiment Coding Agent 执行受限切片，只提交 ResultBundle，不直接拥有 canonical state；
5. 以 Hook、Gate、Reconciler 和 materialized research state 把长期正确性从“模型记得维护”升级为“系统必然维护”。

### 0.1 本项目已存在与本方案拟议的边界

| 类别 | 当前已存在 | 本方案新增或提升 |
|---|---|---|
| Agent 基础 | Pi 会话、Skills、intercom 指针通信 | Text Agent / worker 的明确生命周期与插件接缝 |
| 物理治理 | fs_new、fs_index、wiki_lint、唯一当前、双归档桶 | managed path 写入网关、定义 revision、影响分析 |
| 过程记录 | 唯一 worklog：LOG / HEAD / COMPACT | 三种日志语义、研究事件 schema、materialized research state |
| 实验执行 | tools/ricl_harness/：配置、preflight、split guard、runner、artifact writer | ExperimentSpec、RunManifest、TaskSlice、provenance、不可变 Run |
| 协作 | pi-intercom + intercom-guard；路径 + SHA-256 + 状态指针 | HandoffBundle、确认回执、幂等 attempt、失败恢复 |
| 查询 | 文件定位、文本检索、库.json、Wiki read-model | 结构化实体查询、provenance trace、可重建 SQLite 索引 |

当前 tools/ricl_harness/ 是 R-ICL 的领域实验运行器，不是本文完整的超长程 Research Harness。它可以在后续作为 runner / domain plugin 接入，但目前没有实现本文所述的全局实体库、事件事务、TaskSlice 调度、定义 revision 或 Reconciler。

---

## 1. 项目目标与核心理念

### 1.1 项目目标

系统应在模型上下文被压缩、会话重启、worker 更换、实验跨天运行、人工介入和文件合并之后，仍能准确回答：

- 当前研究问题、协议与假设分别是哪一个固定版本；
- 某个 Run 使用了哪个 ExperimentSpec、代码、数据、模型、prompt、环境和 seed；
- 某条 Observation、Inference、Conclusion、Decision 分别来自哪些证据；
- 为什么出现 E017@v4，它与 E017@v3、D018、R052 有什么因果关系；
- 哪些依赖因为定义修订而 stale，哪些只是需要复核，哪些已经被明确 invalidated；
- 第 28 天接手的 worker 为什么被派发 T042，它实际改了什么，验证了什么，留下了什么；
- 一次失败是基础设施失败、数据失败、测量失败，还是对假设不利的科学结果。

### 1.2 六条核心理念

1. **Agent session ≠ research state**

   会话只是临时推理容器；研究状态必须独立持久化。

2. **Model is not the maintainer**

   模型负责理解、推理、提出变更和解释变更；系统负责约束、验证、提交、传播、维护和修复。

3. **Conversation is not the database**

   对话可作为来源和审计材料，但不能承担 identity、version、status 或 provenance 的唯一真值。

4. **Evidence before summary**

   摘要、dashboard、RAG 命中和 materialized state 都是投影；固定版本的定义、manifest、事件和 artifact hash 才能回答历史事实。

5. **Functionality can be pluggable; invariants cannot be optional**

   文献检索、统计、调度、UI 可以按需加载；不可变 ID、事务、权限、事件审计和 frozen Run 保护不能因插件缺失而消失。

6. **Automate structural facts, not scientific judgment**

   系统可以自动确认引用、版本、哈希、状态和 stale 传播；不能自动把“依赖的 Run 失效”升级为“科学结论错误”。

### 1.3 四种连续性

| 连续性 | 要回答的问题 | 主要机制 |
|---|---|---|
| Temporal continuity | 跨小时、天、周、月，项目是否还是同一个项目 | event log、materialized state、reconciliation |
| Epistemic continuity | 可能、推断、支持、成立是否发生语义漂移 | 实体分型、证据引用、定义 revision、人工裁决 |
| Causal continuity | 为什么做这个实验、结果改变了什么 | provenance graph、Decision、parent relation |
| Execution continuity | 不同 worker / 模型 / 机器能否像连续团队一样工作 | TaskSlice、Handoff、RunManifest、artifact hash |

### 1.4 明确不做

- 不用超长 context 代替持久状态；
- 不让一个永不退出的 Agent 进程成为单点真值；
- 不把所有信息先 embedding 再用 RAG 回答精确版本问题；
- 不用多 Agent 群聊代替权限、任务包和科学裁决；
- 不让 Skill 或 prompt 承担“不得覆盖 Run”这类 correctness 责任；
- 不让 Experiment Coding Agent 直接修改 canonical definition；
- 不把 harness 退出码 0 当作科学结论成立；
- 不在 R-ICL v4 中另建第二当前、第二 worklog、第二 Wiki、第二库.json 或第二通信账本。

---

## 2. 现实时间超长程与传统 long-horizon

传统 long-horizon agent 往往把“长”理解为单次任务中的 token 数、工具步数、规划深度或连续运行时长。本文关注的是 **reality-time long-horizon**：任务经历真实世界中的等待、换人、换模型、换机器、失败重试、数据审批、实验排队与定义修订。

| 维度 | 传统 long-horizon | 现实时间超长程研究 |
|---|---|---|
| 时间尺度 | 分钟到小时，通常连续 | 数周到数月，间歇运行 |
| 主体 | 一个 Agent / 一个上下文 | 多个临时会话、worker 与人 |
| 主要困难 | 规划深度、context、工具序列 | 状态腐烂、定义漂移、文件维护、交接与审计 |
| 世界变化 | 仓库在任务内相对稳定 | 数据、协议、模型、环境、人员均可能变化 |
| 成功判据 | 到达最终答案或通过测试 | 研究状态可追溯、证据可复现、裁决边界不漂移 |
| 恢复方式 | 从当前 context 继续 | 从 canonical records + event replay + materialized state 恢复 |
| 错误积累 | 一次任务内暴露 | 小错误可能在几十个 TaskSlice 后形成语义腐烂 |
| 核心资产 | 当前 working tree / 对话 | identity、version、provenance、immutable history |

现实时间超长程的典型风险不是模型突然完全失忆，而是：

~~~text
E017 已经修订为 v4
→ 某个 active Task 仍引用 v3

H003 的范围发生变化
→ 旧 summary 继续用新表述解释旧 Run

R052 被判定 invalid
→ materialized state 仍把它计入 positive evidence

D018 改变后续路线
→ roadmap、open questions 和 task queue 未同步
~~~

因此，系统目标不是“延长单次注意力”，而是让每一次短会话都只能在受控边界内读取、提议、提交和交接。

---

## 3. 常驻 Text Agent 与非常驻 Experiment Coding Agent

### 3.1 总体结构

~~~text
                         学生 / 导师回路
                    科学冻结、授权、主张裁决
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Logical Resident Text Agent                                 │
│ 研究建模、状态解释、TaskSlice 设计、证据综合、下一步提议       │
└───────────────────────┬──────────────────────────────────────┘
                        │ mutation proposal / dispatch
                        ▼
┌──────────────────────────────────────────────────────────────┐
│ Research Harness                                             │
│ Gate → Transaction → Event → Hook → Materialize              │
│ identity / version / permission / provenance / reconciliation │
└───────────────┬──────────────────────────────┬───────────────┘
                │ TaskSlice                    │ canonical commit
                ▼                              ▼
┌────────────────────────────┐       ┌──────────────────────────┐
│ Ephemeral Coding Worker    │       │ Durable Research State   │
│ Pi / Codex / Claude Code   │       │ definitions / records    │
│ isolated workspace         │       │ artifacts / event stream │
└───────────────┬────────────┘       └─────────────┬────────────┘
                │ ResultBundle                     │
                └──────────────────────────────────┘
~~~

### 3.2 “常驻”是逻辑角色，不是永不退出的进程

Text Agent 可以重启、换模型或丢失当前上下文。只要它能从以下材料恢复，就仍是同一个逻辑角色：

1. materialized research state；
2. active TaskSlice 与未决问题；
3. 最近 Research Event；
4. canonical entity 的精确版本；
5. 必要的 provenance 子图；
6. 当前项目权限与学生授权指针。

系统不能把 Text Agent 的私有 conversation history 当作恢复前提。

### 3.3 Text Agent 的职责

- 把研究目标分解成受限 TaskSlice；
- 区分 Observation、Inference、Hypothesis、Conclusion、Decision；
- 选择需要读取的精确实体和 provenance 范围；
- 提出 definition revision、实验设计和科学解释；
- 综合多个 ResultBundle，形成待人审的主张；
- 对 Gate 拒绝、Reconciler issue 和 stale dependents 做语义处置；
- 把科学歧义升级到学生—导师回路。

Text Agent 不直接：

- 覆盖 frozen definition 或 completed Run；
- 绕过 mutation gateway；
- 把 RAG 结果当作版本真值；
- 用一次 worker 报告自动修改科学结论；
- 通过聊天消息授予执行权限。

### 3.4 Experiment Coding Agent 的职责

Experiment Coding Agent 是一次性或短时 worker。它接收固定 TaskSlice，在隔离 workspace 内：

- 修改被允许的代码或配置；
- 执行预先声明的命令、实验或验证；
- 保存 stdout、stderr、环境、diff、metrics 与 artifacts；
- 报告完成、失败、阻断、偏差和未验证项；
- 生成 ResultBundle 并等待 Harness 提交。

worker 不拥有 canonical state 写权限。即使 worker 与 Text Agent 使用同一模型，也必须视为不同权限主体。

### 3.5 Pi 在架构中的位置

第一阶段不 fork Pi，也不重写成熟 coding agent 能力：

- Pi 提供轻量 Agent loop、基础文件/命令工具、Session 与扩展入口；
- Research Harness 以 Pi extension + expctl/typed tool 的方式暴露受控能力；
- worker plugin 可以启动新的 Pi 会话执行 TaskSlice；
- Research Harness 截获 managed path mutation，Pi 的普通 edit 只能操作 workspace 或自由文本区；
- 实验方法论通过按需 Skill 加载，不塞入永久 system prompt。

如果未来更换 Agent runtime，只替换 adapter；entity、event、manifest 与 artifact 合同不随模型迁移。

---

## 4. TaskSlice 与 Handoff 协议

### 4.1 TaskSlice 是最小可交付执行单元

TaskSlice 必须做到：范围有限、输入固定、权限明确、退出可判定、失败可恢复、结果可验收。

建议最小 schema：

~~~yaml
task_slice_id: TS-0042
revision: 3
objective: "验证 E017@v4 在 fixture 上的三臂公平性门"
authority:
  authorization_ref: AUTH-0012
  protocol_ref: P003@v2
inputs:
  - E017@v4
  - DATA02@v7
  - CODE:8fd9012
allowed_paths:
  read:
    - tools/ricl_harness/
    - tools/tests/fixtures/ricl_harness/
  write:
    - workspaces/TS-0042/
allowed_tools:
  - read
  - edit
  - bash:test
expected_outputs:
  - result_bundle.json
  - execution.log
  - diff.patch
validation:
  - command: "python3 -m unittest tools.tests.test_ricl_harness"
stop_conditions:
  - protocol_hash_mismatch
  - unexpected_dirty_path
  - test_split_visible
deadline: null
handoff_to: text-agent
~~~

### 4.2 TaskSlice 生命周期

~~~text
Proposed
  → Ready        输入、权限、验收条件已冻结
  → Claimed      worker + attempt 已绑定
  → Running
  → Succeeded    执行完成，尚未等于 canonical commit
  → Submitted    ResultBundle 已提交
  → Accepted     Harness 校验并提交事件

异常分支：
  Running → Blocked
  Running → Failed
  Running → Cancelled
  Submitted → Rejected
  Ready/Claimed → Superseded
~~~

Completed 只表示 TaskSlice 合同完成，不表示假设成立。失败 slice、被拒 bundle 和 superseded 任务都保留记录。

### 4.3 HandoffBundle

Handoff 不传一段自由文本“请继续”，而传一个可验的文件包：

| 字段 | 作用 |
|---|---|
| handoff_id | 全局唯一交接 ID |
| task_slice_ref | 精确 TaskSlice revision |
| attempt | 重试序号；同 attempt 幂等 |
| sender / intended_receiver | 身份双绑定 |
| bundle_path | 交接包物理路径 |
| bundle_sha256 | 接收前复算 |
| state_pointer | 当前 TaskSlice / Run / issue 状态 |
| created_at | 时间 |
| expires_at | 可选，防旧包复活 |
| acknowledgement | received / rejected / accepted |

ResultBundle 至少包含：

- TaskSlice 与 attempt；
- worker/runtime/model/session identity；
- input hashes；
- 实际读写路径；
- command、exit code、stdout/stderr 指针；
- diff 或生成文件 manifest；
- tests observed；
- deviations、blockers、unverified；
- artifact hashes；
- 建议事件，但不直接宣布科学结论。

### 4.4 与当前 ricl-handoff / intercom 的兼容

当前树级协议要求消息只传“文件路径 + SHA-256 + 状态指针”。本方案完全沿用：

~~~text
intercom message
  = pointer envelope

HandoffBundle / TaskSlice / ResultBundle
  = repository or artifact-store file
~~~

消息不传完整定义、患者数据、凭据、授权正文或科学裁决。接收方必须先复算 SHA，再确认 intended identity 与 TaskSlice 状态；任一不符即拒收，不通过口头补充绕过。

### 4.5 幂等与失败恢复

- 同一 TaskSlice 可以有多个 attempt，但每个 attempt 只能提交一次；
- at-least-once 消息投递不得造成 double commit；
- worker 崩溃只丢失 workspace，不丢失 canonical state；
- ResultBundle 校验失败不能部分写入 entity/event/index；
- 重试创建新 attempt，不覆盖旧执行日志；
- 旧 TaskSlice revision 被 supersede 后，未开始 attempt 自动拒绝；已开始 attempt 可完成执行，但提交时必须进入人工审查。

---

## 5. 三层日志与 materialized research state

### 5.1 三层是语义分工，不是三份竞争的全局 LOG.md

| 语义层 | 记录什么 | 权威范围 | 推荐物理形式 |
|---|---|---|---|
| Execution Log | 命令、stdout/stderr、tool call、资源、重试、运行异常 | 某个 TaskSlice / Run 的执行事实 | ResultBundle 或 Run artifact 内的不可变日志 |
| Research Event Log | entity 创建、revision、Run 完成、Observation、Decision、stale 传播 | 研究状态变化顺序 | 唯一 append-only 事件流 |
| Agent Handoff Log | dispatch、claim、ack、reject、return、attempt | Agent 间责任与交接事实 | Research Event Log 中的 HANDOFF 事件 + HandoffBundle |

Execution Log 不承担研究解释；Research Event Log 不存大段 stdout；Agent Handoff Log 不复制 TaskSlice 或证据本体。

### 5.2 当前 R-ICL v4 的单日志约束

本项目已经规定全树只有一个活 worklog：

~~~text
04_长期运行系统/04_03_运行/worklog/
├── LOG.md
├── HEAD.md
└── COMPACT.md
~~~

因此本方案在 R-ICL 的 MVP 映射是：

- Execution Log 放在 90_工作底稿_raw/05_实验/<run_id>/ 或对应 ResultBundle 内，不新建全局 execution.log；
- Research Event 只把满足现有八类闭集的过程事实写入唯一 worklog；
- Agent Handoff 使用现有 HANDOFF 类型，并让正文只留 bundle 指针；
- 更细粒度的 entity revision 先由 canonical record + provenance edge 表达，不另建第二全局日志；
- 若未来确需结构化 event store，必须作为 worklog 的受控后端或替代架构另行批准，不能与现 worklog 并列为双真值。

### 5.3 Research Event 最小结构

~~~yaml
event_id: EV-000184
event_type: DefinitionRevised
occurred_at: 2026-08-28T10:32:00+08:00
actor: text-agent
transaction_id: TX-0091
subject: H003@v2
previous: H003@v1
reason_refs:
  - D021
input_hashes:
  - sha256:...
output_hashes:
  - sha256:...
task_slice_ref: TS-0042
caused_by:
  - EV-000181
~~~

Event append 后不得原地改写。纠错通过 Correction event 指向原 event；压缩只能生成投影，不能删除受保护事件。

### 5.4 Materialized research state

materialized research state 是从 canonical entities + immutable events 重建出的当前读模型，用于回答：

- active hypotheses / experiments / tasks；
- latest approved definition pointer；
- running / blocked / stale / needs_review；
- current evidence map；
- unresolved decisions；
- 最近 Run、失败和 handoff；
- 下一步候选。

它可以是 SQLite、JSON、HEAD.md 或 dashboard，但必须满足：

1. generated，禁止手改；
2. 可删除并从 source replay 重建；
3. 带 source watermark / last_event_id / schema version；
4. 不拥有科学批准权；
5. 不使用“latest”替代 manifest 中的固定版本；
6. 与 source 不一致时，source 胜出，Reconciler 报 drift。

当前 HEAD.md 是过程层的人读 materialized view；库.json 是文件元数据索引。二者都不能被误称为本文完整的 research state，也不能替代唯一当前指针。

---

## 6. 物理文件管理系统

### 6.1 文件维护必须进入 Harness

对于 managed path，禁止：

~~~text
LLM → raw edit → canonical file
~~~

必须变成：

~~~text
LLM proposes mutation
  → Mutation Gateway
  → permission + schema + invariant Gate
  → atomic commit
  → append Event
  → post-commit Hook
  → rebuild materialized state
~~~

普通 read/write/edit/bash 工具仍可用于 workspace 和自由文本；对 definitions、state、runs、events 等路径必须被 filesystem gate 拦截，并返回正确的 typed mutation 接口。

### 6.2 四种维护等级

| 等级 | 内容 | 写入规则 |
|---|---|---|
| L0 Derived | index.sqlite、dashboard、summary cache、HEAD、关系图 | 工具生成，可删重建，Agent 禁手改 |
| L1 Managed state | active task、current research projection、status board | 通过 API / transaction 更新 |
| L2 Canonical definitions / evidence | Hypothesis、ExperimentSpec、Metric、DatasetManifest、Observation、Decision、Conclusion | versioned、gated、provenance-bound |
| L3 Free-form knowledge | meeting note、brainstorm、文献批注、scratch | 允许普通编辑，但不能冒充 canonical |

RunManifest、Research Event、历史 Decision 和已提交 artifact manifest 属于 L2 中更严格的 immutable subset。

### 6.3 与当前物理文件制度的映射

| 研究对象 | 当前 R-ICL 落点 | 边界 |
|---|---|---|
| 当前方向 | 04_长期运行系统/04_00_索引/04_索引_当前.md | 全树唯一；本文不修改 |
| 科学定义材料 | 05_草稿箱/05_问题与定义/002_问题与定义_统一定义_20260801.md 及后续学生—导师裁决 | 不由 Agent 自行冻结 |
| 协议 / ExperimentSpec 上游 | 03_交叉实验设计/ | formal 前必须已冻结 |
| 执行产物 | 90_工作底稿_raw/05_实验/<run_id>/ | 底稿/产物，不自动成为证据 |
| 人读证据 | 02_已有实验证据梳理/ | 经过审查后晋升 |
| 数据 / 文献 manifest | 08_资料库/ | 患者本体与受控数据不进 Git |
| 全局过程 | 04_长期运行系统/04_03_运行/worklog/ | 唯一活 worklog |
| 概念 read-model | 06_wiki/ | 不承载 Run、当前或科学批准 |
| 系统 / 科学失败 | 07_归档/系统失败 与 07_归档/科学负结果 | 不混桶 |
| 运行代码 | tools/ricl_harness/ | 当前是 domain runner |
| Agent 交接 | pi-intercom + bundle 文件 | 消息只传 path + SHA + state |

### 6.4 当前工具的复用方式

- fs_new：创建项目 Markdown，保证命名与 frontmatter；
- fs_index：生成目录索引与库.json；
- wiki_lint：执行物理路径、唯一当前、worklog、Wiki 等门禁；
- worklog_head：唯一 worklog 的 append / compact / materialize；
- intercom-guard：发送者、接收者、intended identity 与指针边界；
- ricl_harness：领域 preflight、三臂公平性、split guard、runner 与 artifact writer；
- Git / SHA-256：内容身份、diff、回滚与交接校验。

本方案不得直接照抄通用目录而破坏上述落点。任何 managed state 新路径、事件 taxonomy 扩展或 04_ 制度变更都必须另走学生确认。

---

## 7. Canonical state、immutable records、artifacts、workspace、derived index

### 7.1 五层分工

| 层 | 典型对象 | 是否可变 | 谁能写 | 恢复方式 |
|---|---|---|---|---|
| Canonical state | active pointer、Hypothesis revision、ExperimentSpec、Metric、DatasetManifest | 只通过 revision / transaction 变化 | Mutation Gateway | version chain + event |
| Immutable records | RunManifest、Event、历史 Decision、Observation record、Handoff attempt | append-only | Harness commit | 原记录保留 |
| Artifacts | predictions、metrics、模型输出、图、日志、环境快照 | 内容不可变；可增加新 bundle | Artifact manager | content hash / external store |
| Workspace | worker checkout、临时脚本、scratch、cache | 可自由修改、可丢弃 | 当前 worker | TaskSlice inputs 重新建立 |
| Derived index | SQLite、graph、search index、HEAD、dashboard | 只能重建 | Indexer / Reconciler | replay canonical + events |

### 7.2 单次 mutation 事务

一个 canonical mutation 必须原子完成：

1. 读取 expected_version；
2. 校验 actor permission；
3. 运行 schema / reference / invariant Gates；
4. 写新 revision 或 immutable record；
5. 计算 SHA-256；
6. 追加 Research Event；
7. 提交 transaction；
8. 运行 post-commit Hook；
9. 更新 materialized state；
10. 失败时不留下“文件写了但事件没写”的半提交。

插件崩溃不得破坏已提交 canonical state；非关键 post-commit Hook 可重放，关键 Hook 失败应把 transaction 标记为 needs_reconcile 并阻止继续依赖。

### 7.3 权威顺序

回答精确事实时，查询顺序应为：

~~~text
exact ID / manifest
  → structured query
  → provenance trace
  → lexical search
  → semantic retrieval
~~~

RAG 适合论文、会议记录和长篇历史讨论；不适合回答“R0043 用的是 E001@v2 还是 v3”。

---

## 8. ExperimentSpec、RunManifest、provenance、version 与 identity

### 8.1 Identity 不是文件名

| 概念 | 示例 | 含义 |
|---|---|---|
| entity_id | E017 | 跨 revision 稳定的语义身份 |
| versioned_ref | E017@v4 | 某一冻结定义 |
| content_hash | sha256:... | 某次具体字节内容 |
| path | 03_交叉实验设计/... | 物理位置，可迁移但不能改变身份 |
| run_id | R0048 | 一次执行；永不复用 |
| event_id | EV-000184 | 一次状态变化；永不覆盖 |
| transaction_id | TX-0091 | 一次原子提交 |

同一个 entity 可以有多个 revision；同一个 ExperimentSpec 可以被多次 Run；相同配置重跑也必须产生新的 run_id。

### 8.2 推荐实体类型

- H：Hypothesis；
- E：ExperimentSpec；
- P：Protocol；
- M：Metric；
- DATA：DatasetManifest；
- B：Baseline；
- T / TS：Task / TaskSlice；
- R：Run；
- OBS：Observation；
- INF：Inference；
- C：Conclusion / Claim；
- D：Decision；
- A：Artifact；
- EV：Event。

Core 不需要理解这些语义；它只理解 entity、type、version、mutation、event 与 reference。实体 schema 由 Research OS / domain plugin 注册。

### 8.3 ExperimentSpec

ExperimentSpec 是“准备执行什么”的冻结定义。最小字段：

~~~yaml
experiment_id: E017
version: 4
status: frozen
tests_hypothesis: H003@v2
protocol_ref: P003@v2
dataset_ref: DATA02@v7
metrics:
  - M04@v1
baselines:
  - B01@v3
code_ref:
  repository: R-ICL
  commit: 8fd9012
model:
  id: model-x
  revision: provider-pinned-revision
prompt_sha256: sha256:...
parameters:
  temperature: 0.7
seed_policy: fixed
acceptance_criteria:
  - "三臂非 arm 字段指纹一致"
stop_conditions:
  - test_leak
  - protocol_hash_mismatch
created_by: text-agent
approved_by:
  - AUTH-0012
supersedes: E017@v3
~~~

一旦任何 Run 引用 E017@v4，该 revision 永久冻结。修改必须创建 E017@v5。

### 8.4 RunManifest

RunManifest 是“实际执行了什么”的不可变事实：

~~~yaml
run_id: R0048
experiment_ref: E017@v4
task_slice_ref: TS-0042@r3
attempt: 1
started_at: ...
completed_at: ...
status: completed
worker:
  runtime: pi
  session_id: ...
code_commit: 8fd9012
dataset_hash: sha256:...
prompt_hash: sha256:...
environment_hash: sha256:...
model_revision: ...
parameters_hash: sha256:...
seed: 42
parent_runs:
  - R0043
failure_class: null
artifact_manifest_ref: A0091
execution_log_ref: A0092
manifest_sha256: sha256:...
~~~

RunManifest 不使用 latest、current 或可漂移的目录别名。completed / failed / invalidated Run 都不可覆盖；后续纠错通过新事件或新 Run 表达。

### 8.5 Provenance

provenance 是 typed edge graph，而不是摘要中的自然语言暗示：

~~~text
E017@v4 --tests--> H003@v2
R0048    --generated_by--> E017@v4
R0048    --uses--> DATA02@v7
OBS-012  --observed_in--> R0048
INF-007  --based_on--> OBS-012
C-004    --supported_by--> R0048
D-021    --motivated--> E017@v4
E017@v4 --supersedes--> E017@v3
~~~

常用查询：

- trace H003；
- why E017@v4；
- parents R0048；
- conclusions using R0048；
- active dependents of DATA02@v7；
- stale dependents after H003@v2。

MVP 用 SQLite entities + edges 即可，无需 Neo4j。

### 8.6 Observation、Inference、Conclusion 必须分离

~~~text
Observation:
  R031 accuracy = 72.3%
  R032 accuracy = 77.1%

Inference:
  temperature 可能改善该 fixture 上的结果

Conclusion:
  在已冻结条件与可比性门通过后，对目标 estimand 的有限主张
~~~

压缩和汇总不得把“可能”逐步写成“已证明”。Conclusion 必须引用 evidence IDs，并保留 claim status 与适用范围。

---

## 9. Hook、Gate、Reconciler 与 executable invariants

### 9.1 三者分工

| 机制 | 时机 | 作用 | 失败语义 |
|---|---|---|---|
| Gate | mutation / run 之前 | 防止非法状态发生 | reject，零写入 |
| Hook | commit 之后 | 自动做配套维护 | 可重放；失败进入 reconcile |
| Reconciler | startup / periodic / merge 后 | 比较 expected 与 observed，发现漂移 | 安全修复或 maintenance issue |

~~~text
Mutation proposal
  → PRE GATE
  → atomic commit
  → POST HOOK
  → valid materialized state
  → periodic reconciliation
  → repair deterministic drift / raise issue
~~~

### 9.2 典型 Gate

- Run 引用不存在或未冻结的 ExperimentSpec → REJECT；
- ExperimentSpec 使用 latest dataset → REJECT；
- completed Run 被修改 → REJECT；
- immutable ID 被复用 → REJECT；
- Definition 被普通 edit 覆盖 → REJECT；
- Conclusion 无 evidence reference → REJECT；
- TaskSlice 写入未授权路径 → REJECT；
- formal Run 的协议、数据或代码 hash 不匹配 → REJECT；
- plugin 未声明 schema migration 却改变 canonical schema → REJECT；
- required integrity plugin 未加载 → research profile 启动失败。

### 9.3 典型 Hook

| 事件 | 自动维护 |
|---|---|
| ExperimentCreated | 校验引用、登记 entity、更新 index、追加 event |
| RunStarted | 生成 run_id、冻结 manifest、绑定 TaskSlice attempt |
| RunCompleted | hash artifacts、冻结 RunManifest、登记 provenance、更新任务执行状态 |
| ObservationAdded | 校验 source_run、创建 evidence edge、更新 observation index |
| DefinitionRevised | 冻结旧版本、生成新版本、计算影响面、标记 stale |
| DecisionCommitted | 校验 evidence refs、登记决策、更新受影响计划投影 |
| HandoffSubmitted | 校验 bundle SHA、记录 sender/receiver/attempt、等待 ack |

### 9.4 Reconciler 检查

- Run 目录存在但没有 RunManifest 或 completion event；
- manifest 指向缺失 artifact；
- event 已提交但 materialized state 未更新；
- active Task 引用 superseded definition；
- current projection 仍引用 invalidated Run；
- artifact hash 与登记值不一致；
- 手工 Git merge 造成 duplicate ID；
- Definition revision 已存在但 provenance edge 缺失；
- Handoff 显示 claimed，但 worker attempt 已过期；
- 索引 source watermark 落后于事件流。

自动修复只限确定性动作，例如重建索引、补投影、重放幂等 Hook。遇到缺失 source、hash 冲突、科学解释或多候选修复时，必须创建 maintenance issue，不能猜。

### 9.5 Executable invariants

不变量应写成测试或 machine-checkable rule，而不是只写进 AGENTS.md：

~~~text
INV-001  completed Run content hash never changes
INV-002  entity_id is globally unique
INV-003  every canonical mutation emits exactly one committed event
INV-004  every Run references an exact ExperimentSpec version
INV-005  every artifact reference resolves and matches SHA-256
INV-006  every Conclusion has one or more evidence references
INV-007  workspace writes cannot cross TaskSlice allowlist
INV-008  derived indexes are rebuildable and never authoritative
INV-009  definition revision never rewrites historical Run bindings
INV-010  stale marking never automatically becomes scientific invalidation
INV-011  Handoff attempt commit is idempotent
INV-012  missing required integrity rule fails closed
~~~

AGENTS.md 只保留人和 Agent 需要始终看到的短不变量；执行真值在 Gate、Hook、schema 与测试中。

---

## 10. 定义性文件的 revision 与 impact analysis

### 10.1 定义不是普通文本

以下对象属于 semantic schema / canonical definition：

- Hypothesis；
- ExperimentSpec；
- Metric；
- DatasetManifest；
- Baseline；
- Protocol；
- Terminology / label provenance；
- TaskSlice acceptance criteria；
- Claim scope。

对它们的“润色”也可能改变历史实验意义，因此 managed path 必须禁止普通覆盖。

### 10.2 Revision 流程

~~~text
propose revision
  → classify change
  → semantic diff
  → authority check
  → create H003@v2
  → link supersedes H003@v1
  → impact analysis
  → mark dependents stale / needs_review
  → human scientific adjudication where required
  → update approved pointer
~~~

建议 revision 记录：

~~~yaml
entity: H003
from: H003@v1
to: H003@v2
change_type:
  - scope_change
reason_refs:
  - D021
changed_fields:
  - population
  - outcome
affected_entities:
  - E017@v3
  - E021@v1
  - TS-0043@r1
approval_ref: AUTH-0019
~~~

纯排版、拼写和语义变化也要分类。只有可证明不改变 machine-readable meaning 的 presentation-only 变化，才可由受控工具自动处理；不能由模型自行宣称“只是润色”。

### 10.3 Impact analysis

定义修订后，从 provenance graph 计算：

1. 哪些 ExperimentSpec 直接引用旧版本；
2. 哪些 Run 已按旧版本完成；
3. 哪些 active TaskSlice 尚未执行；
4. 哪些 Observation / Inference / Conclusion 使用相关 Run；
5. 哪些 Decision 与 roadmap 依赖这些结论；
6. 哪些 materialized views 和索引需要重建。

处理规则：

- 历史 Run 继续绑定旧版本，不重写；
- 未执行 TaskSlice 可自动阻止并要求 rebase；
- 已执行未提交 ResultBundle 进入 needs_review；
- Conclusion 先标 stale，不自动标 false；
- 只有学生—导师科学回路可以把 stale 进一步裁决为仍适用、限缩、contradicted 或 invalidated。

### 10.4 Stale 是一等状态

stale 表示“上游发生了可能影响解释的变化”，不是：

- 文件损坏；
- 实验一定无效；
- 结论一定错误；
- 应删除历史记录。

推荐状态最少包括 fresh、stale、needs_review、superseded、invalidated，并记录 stale_reason 与 upstream revision。

### 10.5 R-ICL 当前科学权边界

本项目的科学定义仍以 05_草稿箱/05_问题与定义/002_问题与定义_统一定义_20260801.md 及后续学生—导师裁决为上游材料。本文只能提出 revision 机制，不能把当前草稿静默迁入新 definitions/，也不能由 Harness 自动冻结“成立 / 不成立”。

---

## 11. Core Harness、Research OS plugins 与 Domain skills

### 11.1 三层架构

~~~text
Layer 1 — Minimal Core Harness
  agent/session adapter
  plugin & tool lifecycle
  entity identity
  transaction
  event bus
  permission
  immutable record
  hook/gate registration

Layer 2 — Research OS plugins
  filesystem manager
  research state
  event/worklog bridge
  TaskSlice
  worker manager
  artifact manager
  provenance
  query/index
  reconciler

Layer 3 — Domain plugins / Skills
  R-ICL runner
  medical LLM evaluation
  experiment design
  ablation
  statistics
  literature
  reproducibility audit
  claim review
~~~

Core 不知道什么叫 Hypothesis。它只知道：

~~~text
entity_id
entity_type
version
mutation
event
permission
transaction
artifact_ref
~~~

Research state plugin 定义 H / E / R / OBS / C / D；medical-LLM plugin 再定义具体 schema、门禁和 Skill。

### 11.2 Core 收录标准

满足任一条件才进入 Core：

- 缺失会造成数据损坏；
- 缺失会造成权限绕过；
- 缺失会破坏事件审计；
- 所有插件都依赖；
- 它定义插件生命周期本身。

否则默认插件。RAG、Neo4j、自动 reviewer、多 Agent 协商、云调度、模型路由、复杂 planner 不进入 MVP Core。

### 11.3 必需插件与可选插件

“插件化”不等于“可随意缺失”。Research profile 应声明 required plugins：

~~~yaml
profile: research
required:
  - research-state
  - research-integrity
  - event-store
  - artifact-store
  - reconciler
optional:
  - literature
  - semantic-retrieval
  - dashboard
~~~

required plugin 未加载、版本不兼容或迁移失败时，系统 fail closed；不能退化为普通文件直写模式。

### 11.4 稳定 Plugin Contract

插件只能通过受控 context：

~~~text
ctx.entities.get()
ctx.entities.propose_revision()
ctx.mutations.propose()
ctx.events.emit()
ctx.artifacts.register()
ctx.tasks.create()
ctx.hooks.register()
ctx.gates.register()
ctx.tools.register()
ctx.query.execute()
~~~

Core 负责 locking、transaction、schema validation、permissions、audit、idempotency 与 rollback；插件负责领域语义。

### 11.5 插件包

~~~text
medical-llm-evaluation/
├── plugin.yaml
├── tools/
├── hooks/
├── gates/
├── schemas/
├── skills/
├── migrations/
└── tests/
~~~

一个插件可以同时携带 Tool + Hook + Gate + Schema + Skill，但不能直接访问核心数据库文件或绕过 mutation API。

### 11.6 当前 ricl_harness 的定位

| 当前模块 | 未来插件角色 |
|---|---|
| config / preflight | domain Gate |
| split_guard | medical-data integrity Gate |
| prompt_builder / retriever | R-ICL domain execution |
| llm_adapter | model adapter |
| scorer | metric plugin |
| artifact_writer | artifact adapter，需升级到 manifest + transaction |
| runner | worker-side runner |

现有 runner 的测试通过只能证明其已覆盖的工程合同，不证明 Research Harness、正式实验或科学主张已完成。

---

## 12. 推荐目录结构

### 12.1 可移植逻辑结构

下列结构用于描述组件职责，不要求在 R-ICL v4 中原样创建：

~~~text
experiment-agent/
├── core/
│   ├── runtime/
│   ├── entities/
│   ├── transactions/
│   ├── events/
│   ├── permissions/
│   └── plugins/
├── adapters/
│   └── pi/
├── plugins/
│   ├── research-state/
│   ├── research-integrity/
│   ├── taskslice/
│   ├── worker-pi/
│   ├── provenance/
│   ├── artifact-store/
│   └── reconciler/
├── profiles/
│   └── research.yaml
├── schemas/
├── migrations/
├── tests/
└── expctl

project-state/
├── definitions/       # versioned canonical definitions
├── records/           # immutable Run / Event / Decision
├── artifacts/         # content-addressed manifests or pointers
├── workspace/         # disposable worker state
└── derived/           # rebuildable index / materialized views
~~~

### 12.2 R-ICL v4 推荐映射

在不修改现行制度前，采用映射而不是新增第二套 project-state：

~~~text
tools/
├── ricl_harness/              # 已有 R-ICL runner / domain execution
├── team-skills/               # 已有 domain workflow
└── <future research layer>    # 仅在单独实施授权后创建

03_交叉实验设计/                # protocol / frozen experiment inputs
05_草稿箱/                     # definition proposal / revision proposal
90_工作底稿_raw/05_实验/        # Run artifacts / execution logs
02_已有实验证据梳理/            # reviewed evidence projection
04_长期运行系统/04_03_运行/worklog/
                                # 唯一全局过程事件面
04_长期运行系统/04_00_索引/      # generated project indexes
08_资料库/                     # literature / dataset manifests
07_归档/                       # system failure / scientific negative
~~~

### 12.3 目录约束

- 本架构文档继续留在 90_工作底稿_raw/04_科研系统方案/；
- 不把 proposed architecture 晋升为 04_ 制度；
- 不在根目录新建 .research、runs、events、state 或 plugins；
- 不创建三个全局日志目录；
- 新 Markdown 继续走 fs_new；
- 索引与库.json 继续由 fs_index 生成；
- 敏感数据本体继续仓库外置，仓库只存 manifest、许可、版本与 hash；
- 未来新增代码包或 managed state 路径必须有实施任务包、回滚点和 lint 规则。

---

## 13. MVP 与阶段性实现优先级

### 13.1 MVP 的唯一闭环

MVP 只需证明一条端到端链：

~~~text
Text Agent 创建一个已冻结 ExperimentSpec
  → 创建 TaskSlice
  → worker-pi 执行一次 fixture Run
  → 返回 ResultBundle
  → Harness 校验并写 RunManifest / artifact hashes
  → 追加唯一 Research Event / HANDOFF 指针
  → materialize 当前状态
  → 删除 derived index 后可完整重建
  → Reconciler 检出并报告一个人为制造的 drift
~~~

验收重点不是模型输出质量，而是 persistent correctness。

### 13.2 阶段顺序

| 阶段 | 优先级 | 内容 | 退出条件 |
|---|---:|---|---|
| P0 合同冻结 | 最高 | ID、version、event、TaskSlice、Handoff、ExperimentSpec、RunManifest、invariants | schema + fixtures + contract tests |
| P1 单机持久内核 | 最高 | transaction、event append、artifact hash、SQLite derived index、reconciler check | crash/重放/重建测试通过 |
| P2 Pi 单 worker | 高 | Pi adapter、managed path gate、TaskSlice → Pi → ResultBundle | 一次端到端闭环，失败可恢复 |
| P3 R-ICL 接入 | 高 | 把现有 ricl_harness 作为 domain runner plugin | 旧 runner 测试不回归，manifest 完整 |
| P4 多 worker | 中 | claim、lease、attempt、并发锁、调度 | duplicate delivery 不 double commit |
| P5 高级检索 | 低 | semantic RAG、文献插件、graph UI | 不影响精确 identity 查询 |
| P6 自动化增强 | 最后 | reviewer、模型路由、云调度、自动 planning | 每项独立证据与权限审查 |

### 13.3 第一版必须有

- Research Event / worklog bridge；
- TaskSlice + Handoff protocol；
- materialized research state；
- ExperimentSpec + RunManifest；
- identity / version / provenance；
- immutable artifact manifest；
- Gate / Hook / Reconciler；
- 一个 Pi worker adapter；
- 合同测试、crash recovery 与 replay 测试。

### 13.4 第一版明确不要

- 向量数据库作为主检索；
- Neo4j；
- 多 Agent 自由协商；
- 自动科学 reviewer；
- 自动更新 hypothesis；
- 云调度；
- dashboard 优先；
- “万能 memory Agent”；
- 复杂 planner / executor / reviewer 状态机；
- 自动把失败 Run 晋升 correction memory。

---

## 14. 关键设计原则与主要风险

### 14.1 关键设计原则

1. 核心尽可能小，长期正确性必须强；
2. 文件位置、entity identity、version 与 content hash 明确分离；
3. canonical mutation 必须事务化、事件化、可审计；
4. completed Run、历史 Decision 与 Event 不覆盖；
5. 维护跟事件走，不跟模型记忆走；
6. Gate 防非法状态，Hook 维护合法状态，Reconciler 修复漂移；
7. stale 不等于 false，结构维护不越权做科学裁决；
8. TaskSlice 是执行边界，HandoffBundle 是责任边界；
9. 非常驻 worker 只提交 bundle，不直接写 canonical state；
10. materialized state 是投影，必须可删重建；
11. 精确事实先查 manifest / provenance，RAG 最后；
12. 功能可插件化，不变量不可因插件缺失而消失；
13. Skills 负责方法论，不能承担 correctness；
14. 当前 R-ICL 的唯一当前、唯一 worklog、intercom 与物理文件制度继续有效；
15. 所有医学主张保留 label provenance、数据权限、人工监督和适用范围。

### 14.2 主要风险

| 风险 | 典型后果 | 缓解 |
|---|---|---|
| 语义漂移 | “可能支持”在摘要中变成“已证明” | 实体分型、claim status、evidence refs、人工裁决 |
| 定义静默覆盖 | 历史 Run 被今天的定义重新解释 | revision-only、frozen ref、impact analysis |
| 双真值 | worklog、event store、dashboard 各说一套 | 单 writer、projection 标识、现行唯一 worklog |
| Hook 半失败 | 文件写入但 event/index 未更新 | atomic transaction、outbox、replay、reconciler |
| 插件绕过 Core | 权限、审计或 schema 被破坏 | capability API、沙箱、required profile、fail closed |
| 重试重复提交 | 同一 Run / Handoff 计两次 | idempotency key、attempt、unique constraint |
| worker 越权 | 改定义、看 test、污染无关 dirty | allowlist、隔离 workspace、preflight、path gate |
| provenance 缺失 | 无法解释为什么有某结论 | typed edges、manifest required fields、Gate |
| artifact 漂移或丢失 | 指标无法复核 | content hash、manifest、外部 store 校验 |
| 敏感数据泄漏 | 医疗数据进入 Git / 日志 / 消息 | 外置本体、redaction、路径门禁、最小日志 |
| derived state 过期 | Agent 读取错误“当前” | watermark、startup reconciliation、source 优先 |
| 过度工程化 | 先做图数据库和调度，核心闭环迟迟不可用 | P0–P3 薄切片，RAG / UI / multi-worker 后置 |
| runtime 锁定 | Pi 变化导致系统不可迁移 | adapter 层、稳定 file/schema contracts |
| 科学权力漂移 | Harness PASS 被写成科学成立 | 学生—导师 Gate、状态轴分离、明确 claim boundary |
| 人工直接改 managed files | Hook 被绕过，形成 drift | filesystem intercept、Git hook、Reconciler、审计 issue |

### 14.3 最小成功标准

系统真正成功，不是因为它能连续调用很多 Agent，而是因为：

> 第 37 个临时 worker 在第 28 天完成一个 TaskSlice 后，系统仍能准确说明它读取了什么固定版本、做了什么、产生了什么、哪些状态因此变化、哪些结论仅变 stale 而尚未被科学裁决，并且任何人都能从 manifest、event 和 artifact 重建这条链。

---

## 15. 结论与后续决策门

本方案建议把项目从“Pi + 实验 Skills”升级为：

> **Pi 的轻量 Agent runtime + Minimal Research Harness + Research OS plugins + Domain skills。**

新增的真正核心不是更多 Agent 角色，而是 **persistent correctness**：

~~~text
strong model
+ controlled filesystem
+ evented research state
+ immutable experiment history
+ plugin architecture
~~~

后续若进入实施，应先由学生批准 P0 合同切片，再单独创建实施任务包。P0 之前不应：

- 修改现有 tools/ricl_harness 行为；
- 新建 managed state 根目录；
- 扩展 worklog 事件闭集；
- 改 04_ 制度或唯一当前；
- 启动正式实验；
- 把本文提案描述为已实现系统。

本文当前只完成架构整理与项目落盘，不产生科学结论。
