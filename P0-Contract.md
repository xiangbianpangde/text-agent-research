# P0 Contract — Text Agent 检索内核

> 文档性质：P0 实施合同（frozen contract）。内容经学生确认后，作为 P0-A/B/C 实现的唯一边界依据，不随设计偏好变化。
>
> 依据：2026-08-30 设计评审（"超长程实验 Text Agent 检索与研究状态系统" PRD、设计方案、技术方案）及 D1–D4 裁决。
>
> 当前状态：已确认（2026-08-30）

---

## 0. 决策记录

| 编号 | 决策项 | 结论 | 来源 |
|---|---|---|---|
| D1 | `CURRENT.md` 定位 | 收紧版：人读权威入口，sources.yaml 来源契约，派生数据冲突时不得自动选边 | 评审 二 / 裁决 |
| D2 | 试点项目 | `fixture/` 合成数据，不引用真实 R-ICL，不产生科学结论 | 评审 十 / 裁决 |
| D3 | Git / hash 策略 | `content_hash = SHA-256(file bytes)` 主身份，`git_commit` 辅助，blob hash 不单独存 | 评审 三 / 裁决 |
| D4 | P0 边界 | P0-A 合同+Fixture / P0-B 只读检索 / P0-C 完整性检测；P0-C 不写真源 | 评审 七 / 裁决 |

---

## 1. 分阶段范围

### P0-A：合同与 Fixture

**内容**：
- 本文件（P0 Contract）冻结
- `fixture/` 三阶段合成研究项目（手工构造，每阶段 Git commit）
- 四份核心 schema 定义（见 §2–§5）
- 最小实体类型清单（见 §6）

**退出条件**：
- 决策记录已确认
- `fixture/` 目录结构完整，三阶段 history 可验证
- 四份 schema 经复核无误

---

### P0-B：只读检索

**内容**：
- 四层检索实现（physical → lexical → structured → provenance；semantic retrieval 放 P1）
- 固定检索顺序：exact ID / manifest → structured query → provenance trace → lexical search
- `researchctl` 最小命令集：`query` / `sources` / `trace` / `history`
- 查询结果 envelope 实现（§3）
- 固定检索路线（§8）

**启动前置条件**：
- 首次索引构建（从 canonical 文件构建 SQLite 派生索引）
- 初始建索引属于 P0-B 的启动依赖；P0-C 的 `reindex` 对应删除后的重建与漂移检测

**退出条件**：
- 对 fixture 三阶段所有问题（A–H，见 §9）能返回正确结果
- 历史 Report 指向精确版本而不是 latest
- 断链场景下返回正确错误语义而不是猜测

---

### P0-C：完整性

**内容**：
- `reindex`：从 canonical 文件重建 SQLite 派生索引
- `reconcile`：检测断链、hash 不匹配、索引漂移、缺失 source
- 故障注入验收（§10）

**退出条件**：
- 删除 `.index/` 后 `reindex` 恢复完整检索能力
- 以下故障能被正确检测，不返回错误结果：
  - 移动 Raw 文件
  - 修改历史 Organized
  - 删除 Report source
  - 篡改内容 hash
  - 索引落后于文件（scan fingerprint 不一致）
  - 查询不存在或有歧义的版本

**P0-C 禁止写入**：
- `CURRENT.md`
- Historical Report
- Organized
- Raw
- Definition
- 任何科学结论

P0-C 的自动写入仅限派生索引（`.index/`）和检测报告。

**INDEX_STALE 规则**：
- 依赖索引的结构化查询（sources、trace、history 等）发现索引指纹不匹配 → `INDEX_STALE` + `fail_closed`，不返回旧结果
- 不依赖索引的查询（直接读取 CURRENT.md、glob/find/grep）可继续执行，不受索引状态影响

---

## 2. 真源层次与冲突规则

### 2.1 真源优先级

| 等级 | 内容 | 可写性 | 冲突时 |
|---|---|---|---|
| **T0** | `CURRENT.md` + `CURRENT.sources.yaml` | 人维护 | 权威叙事入口 |
| **T1** | Historical Report + `.sources.yaml` | 冻结后不可变 | 历史快照，不可重写 |
| **T2** | Organized + YAML 元信息 | 持续维护 | 引用 T2 时须 pin 版本 |
| **T3** | Raw | 不可变 | 内容 hash 校验 |
| **D0** | SQLite 派生索引 | 自动重建 | 永远不赢 T0–T3 |
| **D1** | Index / INDEX.md | 自动生成 | 永远不赢 T0–T3 |
| **D2** | materialized state | 自动生成 | 永远不赢 T0–T3 |

### 2.2 冲突检测与失败语义

当任意 T0–T3 与派生数据不一致时：

| 场景 | 返回 |
|---|---|
| 当前引用：`CURRENT.md` 引用的 Organized 文件当前路径不存在 | `SOURCE_MISSING` |
| 历史引用：`git_commit + path` 在 Git 历史中无法恢复该文件 | `SOURCE_MISSING` |
| 当前引用：当前文件 bytes 的 SHA-256 与记录不匹配 | `HASH_MISMATCH` |
| 历史引用：按 `git_commit + path` 恢复的字节 hash 与记录不匹配（历史损坏） | `HASH_MISMATCH` |
| 历史引用：历史版本可恢复，但当前路径文件已变化 | `SOURCE_CHANGED_SINCE_PIN`（drift warning，不判损坏） |
| 同一 source 存在两个候选版本 | `AMBIGUOUS_VERSION` |
| 派生索引与文件系统状态明显不一致 | `DRIFT_DETECTED` |
| 冲突发生在 `CURRENT.md` 本身与 sources.yaml 之间 | `CURRENT_CONFLICT` |
| hash 存在但原文件无法恢复 | `SOURCE_UNAVAILABLE` |
| 查询的 entity ID 不存在 | `NOT_FOUND` |
| 索引未重建或落后于文件系统（scan fingerprint 不一致） | `INDEX_STALE` |
| 来源链中某环断裂 | `PROVENANCE_BROKEN` |
| 以上任一情况发生，且系统无法确定 | 回答"当前状态无法可靠确定"，不自动选边 |

**SOURCE_MISSING 与 SOURCE_UNAVAILABLE 的区别**：

```text
SOURCE_MISSING：     指定路径或指定历史对象不存在（无法定位）
SOURCE_UNAVAILABLE： 有引用或 hash 记录，但无法从任何来源恢复字节（有身份，无字节）
```

---

## 3. 查询结果 Envelope

```text
QueryResult {
  query_id:      string                  // 每次查询唯一 ID
  query_type:    "current" | "sources" | "trace" | "history" | "reindex" | "reconcile" | "status"
  as_of:         timestamp               // 查询时间（投影 / 精确版本）
  status:        "success" | "warning" | "error" | "fail_closed"
  authority:     "canonical" | "derived" | "unresolved"
  source_watermark: {
    index_built_at:      timestamp | null
    last_event_id:       string | null   // P0 恒为 null，P1 启用
    scan_fingerprint:    string | null   // P0 主依据：filesystem scan fingerprint
    index_complete:      boolean
    drift:               boolean
  }
  results:       []ResultItem | null     // 查询结果
  warnings:      []Warning               // 非阻断性异常
  errors:        []ErrorDetail           // 阻断性异常
  error_semantic: string | null          // 见 §2.2 错误语义枚举
}
```

其中 `ResultItem` 至少包含：

```text
ResultItem {
  entity_id:       string
  versioned_ref:   string | null      // e.g. "E017@v4"
  path:            string
  content_hash:    string | null      // SHA-256
  git_commit:      string | null
  section:         string | null
  status:          StateModel         // 六轴状态，见 §5；未适用轴为 null / not_applicable
  relation_type:   string | null      // provenance 边类型
  is_stale:        boolean
  is_available:    boolean
}
```

---

## 4. Source Reference Schema

这条 schema 同时用于 `CURRENT.sources.yaml`、Historical Report `.sources.yaml` 和 Organized 来源元信息。

```yaml
# Source Reference 记录
source_ref:
  path:             string              # 相对项目根路径
  source_type:      "file" | "directory"  # 默认 file
  content_hash:     string              # 主身份，规则见下
  reference_scope:  "current" | "historical"  # 默认 current
  git_commit:       string | null       # historical 时必须存在；current 时可选
  section:          string | null       # 具体章节/标题/锚点
  entity_id:        string | null       # 如果引用的是实体
  versioned_ref:    string | null       # 如果引用的是特定版本

# git_commit 约束
git_commit_required:
  rule: >
    reference_scope=historical 时 git_commit 为必填，
    用于在 Git 历史中定位精确字节；
    reference_scope=current 时可选

# content_hash 规则
hash_rule:
  file:       "SHA-256(file bytes)"
  directory:  "SHA-256(sorted manifest)"

# 目录 hash 序列化规则
directory_hash_serialization:
  algorithm:  "SHA-256(sorted manifest)"
  manifest_format: |
    按 POSIX 相对路径排序（UTF-8 字典序）
    每行格式: <relative_path>:<sha256_hex>
    换行符: LF (0x0a)
    无尾随空行
  example: |
    data/experiment.csv:abcdef123456...
    logs/run.log:7890defabc...
    parameters.json:4567890abc...
```

**解析与校验规则**：

```text
Current file:
  path → 读取当前字节 → 校验 file hash

Current directory:
  path → 读取目录树 → 生成排序后的 manifest → 校验 directory hash

Historical file:
  git_commit + path → 恢复文件字节 → 校验 file hash

Historical directory:
  git_commit + directory path → 恢复目录树 → 生成排序后的 manifest → 校验 directory hash

（当前路径文件/目录变化只记录 SOURCE_CHANGED_SINCE_PIN，不判历史损坏）
```

- `content_hash` 是必须的必填字段
- 定位与验证分离：
  - path / git_commit 负责定位（找到字节的来源）
  - content_hash 负责验证（确认字节未被篡改）
- `git_commit` 仅供历史定位，不参与主身份校验
- 定位失败 → 对应错误语义；定位成功但 hash 不匹配 → `HASH_MISMATCH`
- 当前引用：path 不存在 → `SOURCE_MISSING`；bytes hash 不匹配 → `HASH_MISMATCH`
- 历史引用：`git_commit + path` 无法恢复 → `SOURCE_MISSING`；恢复字节 hash 不匹配 → `HASH_MISMATCH`；当前文件已变化但历史可恢复 → `SOURCE_CHANGED_SINCE_PIN`（drift）

---

## 5. 六轴状态模型

以下六个轴彼此独立，不得合并为一个 `status` 字段。

P0 未覆盖的实体类型（TaskSlice、Conclusion、Claim、Definition）相关轴值为 `null / not_applicable`；P0 只验证实际使用的轴。

```yaml
# 状态记录
state_model:
  execution:
    values:   [running, completed, failed]
    applies_to: [Run, TaskSlice]
    note:     "completed 不等于实验成功或假设成立"

  data:
    values:   [valid, corrupted, missing]
    applies_to: [Organized, Raw, Artifact]
    note:     "corrupted 指内容 hash 校验失败，不涉及科学判断"

  research:
    values:   [fresh, stale, needs_review]
    applies_to: [Report, Conclusion, Observation]
    note:     "stale 仅表示上游变化后需重新审查，不自动升级为 invalidated"

  scientific:
    values:   [supports, contradicts, inconclusive, unassessed]
    applies_to: [Conclusion, Claim]
    note:     "只有学生—导师科学回路可以裁决 scientific 状态"

  task:
    values:   [proposed, active, blocked, accepted, rejected, superseded]
    applies_to: [Task, TaskSlice]
    note:     "accepted 表示 TaskSlice 合同完成，不表示科学结论成立"

  review:
    values:   [unreviewed, reviewed, approved]
    applies_to: [Report, Conclusion, Definition]
    note:     "reviewed 不自动等于 approved"
```

**stale 语义**（单独定义，跨轴使用）：

```yaml
stale:
  definition: >
    "上游实体发生可能影响本实体解释的变化，需重新审查"
  NOT:   false, invalidated, corrupted, to_be_deleted
  can_be_upgraded_by: 仅学生—导师科学回路
  propagate:  |
    定义修订 → 影响面标记 stale
    stale 不自动传播为 scientific 轴变化
```

---

## 6. 最小实体类型（P0）

P0 只识别以下实体类型。Core 不感知 H/E/M/DATA 等语义类型（放 P1 插件注册）。

| 类型 ID | 名称 | P0 是否必须 | 说明 |
|---|---|---|---|
| `report` | 报告 | 是 | CURRENT.md + Historical Report |
| `source_ref` | 来源引用 | 是 | 绑定 Report 与 Organized 版本 |
| `organized` | 整理文件 | 是 | L1 研究文件 |
| `raw` | 原始材料 | 是 | L0 不可变底座 |
| `run` | 执行记录 | 是 | 一次实验执行；fixture 含最小只读 RunManifest |
| `experiment` | 实验分组 | 是 | 组织多个 Run；fixture 含最小只读 ExperimentSpec manifest |
| `entity` | 通用实体 | 是 | 含 id/type/version/status |
| `event` | 研究事件 | 否（P1） | P0 不实现事件机制；fixture 可预置只读事件记录作参考数据 |
| `definition` | 定义 | 否（P1） | Hypothesis / Metric / Dataset 等 |

---

## 7. 版本与 Hash 规则

```yaml
version_rules:
  identity:
    entity_id:      "E017"                     # 跨版本稳定
    versioned_ref:  "E017@v4"                  # 精确版本
    content_hash:   "sha256:abc123..."         # 主校验身份

  hash_priority:
    primary:        "content_hash = SHA-256(file bytes)"
    auxiliary:      "git_commit"
    not_saved:      "Git blob hash"            # P0 不单独保存

  source_record_minimum:
    - path
    - content_hash
    - reference_scope   # 必填：current | historical
    - git_commit        # reference_scope=historical 时必填；current 时可选
    - section           # 可选

  recovery:
    rule: >
      SOURCE_MISSING：指定 path 或 git_commit + path 无法定位
      SOURCE_UNAVAILABLE：有 locator 或 hash，但从任何授权来源都无法恢复字节/目录 manifest
      两者都不能当作"已成功追溯"
```

---

## 8. 固定检索路线

> 说明：physical / lexical / structured / provenance 是**能力层级**；exact → structured → provenance → lexical 是**默认查询路线**。二者不可混淆。

| 问题类型 | 检索路线 | 禁止 |
|---|---|---|
| 当前结论 | `CURRENT.md` →（需引证时）`sources.yaml` → Organized | 跳过 Report 直接搜 Raw |
| 结论来源 | `CURRENT.sources.yaml` / Report `.sources.yaml` → 具体 Organized 版本 | RAG 猜版本 |
| 来源的 Raw | Organized YAML 元信息 → Raw 路径 | 把 Organized 当最终证据 |
| 历史结论 | `REPORT-NNN.md` → 其 `.sources.yaml` → 当时 Organized 精确版本 | 用当前 Organized 解释历史 |
| 历史 vs 当前 | 分别查历史版本与当前版本，对比 | 自动用最新覆盖旧 |
| 实验/Run 详情 | `experiments/` / `runs/` 只读 manifest | 用语义检索替代 manifest |
| 模糊回忆 | lexical（P0）；semantic fallback 放 P1 | 用 semantic 回答版本/身份问题 |
| 版本引用 | exact `content_hash` / `versioned_ref` | 用 latest 或"最新版本" |

---

## 9. 验收标准（A–H）

基于 fixture 三阶段项目，验证以下 8 个问题。

### 阶段构造

```text
阶段 1 (commit 1):
  Raw: A, B
  → Organized: EXP-017/result.md (baseline)
  → REPORT-001 (freeze)

阶段 2 (commit 2):
  Organized: EXP-017/result.md 更新 (new data)
  → CURRENT 改变
  → REPORT-002 (freeze)

阶段 3 (commit 3):
  Raw: A 被标记 invalid
  → CURRENT 再改变
  → REPORT-003 (freeze)
```

### 验收问题

| # | 问题 | 预期 |
|---|---|---|
| A | 当前结论是什么 | 读取 `CURRENT.md` 正确回答 |
| B | 当前结论来自哪些 Organized | `sources` 查询返回精确版本路径 |
| C | 这些 Organized 对应哪些 Raw | Organized YAML 元信息定位 Raw |
| D | REPORT-001 当时的来源是什么 | 返回 `REPORT-001.sources.yaml` 中的精确版本 |
| E | REPORT-001 来源文件后来是否修改 | 按 `git_commit + path` 恢复历史字节并校验 hash（通过）；当前路径变化 → `SOURCE_CHANGED_SINCE_PIN` 漂移告警 |
| F | 为什么 REPORT-001 与 REPORT-003 不同 | 通过历史 chain 解释变化 |
| G | 旧 Report 是否保持原样 | 内容 + sources.yaml 不变 |
| H | 删除一个 source 后 Reconciler 是否报警 | 当前引用 → `SOURCE_MISSING`；历史引用仍可按 `git_commit + path` 恢复，报 `SOURCE_CHANGED_SINCE_PIN` drift |

---

## 10. 故障注入清单

P0-C 验收时逐条注入以下故障，验证系统 fail-closed 行为：

| # | 注入故障 | 预期系统行为 |
|---|---|---|
| F01 | 删除 `.index/` | `reindex` 后完整恢复，不丢数据 |
| F02 | 移动 Raw 目录 | `SOURCE_MISSING` 或 `PROVENANCE_BROKEN` |
| F03 | 修改历史 Organized 内容（当前路径变化） | 当前引用 → `HASH_MISMATCH`；历史引用仍可按 `git_commit + path` 恢复 → `SOURCE_CHANGED_SINCE_PIN` drift |
| F04 | 删除 Historical Report 的 source 文件（当前工作区） | pinned commit 可恢复 → `SOURCE_CHANGED_SINCE_PIN`；pinned commit 也无法恢复 → `SOURCE_MISSING` |
| F05 | 伪造重复 entity ID | `DRIFT_DETECTED`（不归为版本歧义） |
| F06 | 篡改 Organized 文件 content hash（改内容不更新 sources.yaml） | `HASH_MISMATCH` |
| F07 | 索引落后于文件（不 rebuild 就查询） | `INDEX_STALE` + `fail_closed`，不返回旧索引结果；直接读取 `CURRENT.md` 的查询仍可继续 |
| F09 | 查询不存在的 entity ID | `NOT_FOUND` |
| F10 | 查询存在歧义的版本（两个候选） | `AMBIGUOUS_VERSION`，不自动选最新 |

> 注：F08（定义 v1→v2，历史 Run 引用未更新 → `research=stale`）依赖 Definition/Event 机制，迁至 P1（见 §13 P1-08）。

---

## 11. 不变量

### P0 不变量

以下不变量在 P0 范围内必须始终成立：

```text
INV-001  completed Run 的内容 hash 不可变
INV-002  entity_id 全局唯一
INV-004  每个 Run 引用精确的 ExperimentSpec 版本（如 R052 → EXP-017@v1）
INV-005  每个 source_ref 的 content_hash 可校验
INV-007  派生索引可重建，永远不成为真源
INV-008  stale 不自动等于 false 或 invalidated
INV-009  缺少必需完整性规则时 fail closed
INV-010  查询结果不自动选择冲突方
INV-011  历史来源按 `git_commit + path` 恢复并校验 hash；当前文件变化仅记为 drift，不得改写历史语义
```

### P1 不变量

随 P1 机制落地后生效：

```text
INV-003  （P1）每次 canonical mutation 产生一个 committed event   ← 随 Event 机制落地
INV-006  （P1）每个 Conclusion 至少有一个 evidence 引用        ← 随 Conclusion 实体落地
```

### 目录 hash 序列化规则

```text
directory_hash:
  algorithm:  "SHA-256(sorted manifest)"
  manifest_format: |
    按 POSIX 相对路径排序（UTF-8 字典序）
    每行格式: <relative_path>:<sha256_hex>
    换行符: LF (0x0a)
    无尾随空行
  example: |
    data/experiment.csv:abcdef123456...
    logs/run.log:7890defabc...
    parameters.json:4567890abc...
```

---

## 12. 项目结构

```text
文字Agent检索系统/
│
├── P0-Contract.md                   # 本文件
├── 超长程实验 Text Agent 检索与研究状态系统 PRD.md
├── 超长程实验 Agent 检索系统设计方案.md
├── 超长程实验 Agent 技术方案.md
│
└── fixture/                         # 合成测试项目（P0-A）
    ├── .git/
    ├── reports/
    │   ├── CURRENT.md
    │   ├── CURRENT.sources.yaml
    │   └── history/
    │       ├── REPORT-001.md
    │       ├── REPORT-001.sources.yaml
    │       ├── REPORT-002.md
    │       ├── REPORT-002.sources.yaml
    │       ├── REPORT-003.md
    │       └── REPORT-003.sources.yaml
    ├── index/
    │   └── INDEX.md
    ├── organized/
    │   └── EXP-017/
    │       ├── result.md
    │       └── analysis.md
    ├── raw/
    │   └── EXP-017/
    │       ├── R051/
    │       ├── R052/
    │       └── R053/
    ├── experiments/
    │   └── EXP-017/
    │       └── spec.yaml              # 最小只读 ExperimentSpec（frozen）
    ├── runs/
    │   ├── R051/manifest.yaml         # 最小只读 RunManifest（immutable）
    │   ├── R052/manifest.yaml
    │   └── R053/manifest.yaml
    ├── tasks/
    ├── events/                        # P1 启用；P0 不实现事件机制
    └── .index/
        └── research.sqlite            # 派生索引，可重建
```

**fixture 约束**：
- 只包含合成数据，不引用真实 R-ICL 数据
- 不代表生产研究状态
- Agent 不得将 fixture 结果描述为科学结论
- 派生索引只放在 `fixture/.index/`
- 不接 Pi、不启动 Worker

---

## 13. 后续阶段（P1 先行）

P1 首次引入受控写入操作：

```text
P1-01  freeze-report          # 冻结 CURRENT → Historical Report + sources.yaml
P1-02  event append           # 追加 Research Event；启用 last_event_id 与事件基 INDEX_STALE
P1-03  definition revision    # 创建新版本 + impact analysis
P1-04  stale propagation      # 自动标记受影响实体（含 F08 语义：research=stale，不自动升级 invalidated）
P1-05  structured current state # 可选：引入结构化当前状态（D1 预留）
P1-06  semantic retrieval     # 从 P0 范围移出，P1 作为 lexical fallback 引入
P1-07  INV-003 / INV-006      # 随 Event / Conclusion 实体落地
P1-08  故障注入 F08           # 定义 v1→v2 历史 Run 未更新 → research=stale
```

P0 不实现上述任何写入操作。

---

## 14. 开发者约束

1. 不得把整个系统改成 embedding-first RAG
2. 不得让 SQLite 成为唯一 source of truth
3. 不得让 Index 成为 canonical truth
4. 不得允许 Historical Report 自动刷新
5. 不得自动把旧 reference 升级到新 Definition
6. 不得通过 prompt 代替 Gate
7. 不得把 Research Event 与 Agent Execution Log 合并
8. 不得为"减少文件数量"删除历史 snapshot
9. 不得让 Worker 自己维护整个研究状态
10. 不得为扩展性过早实现完整 Multi-Agent Runtime