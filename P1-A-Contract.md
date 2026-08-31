# P1-A Contract — Evented Historical Freeze

> 文档性质：P1-A 实施合同（frozen contract）。内容经确认后，作为 Evented Freeze 闭环的唯一边界依据。
>
> 依据：P0-Contract.md（§13 P1-01/02/07）、2026-08-30 P1 边界裁决、五轮阻断项修订
> 及 Sol 审核（2026-08-31 NO-GO → rev8；窄范围 NO-GO → rev9；rev9 复查 → rev10 按 WAL 生命周期 + P2 残留修订）。
>
> 当前状态：起草中（修订版 10），冻结前不开始实现。

---

## 0. 状态与范围

**范围（P1-A 唯一闭环）**：

```text
event append / transaction 基础
  → freeze-report（CURRENT → REPORT-NNN + sources manifest）
  → ReportFrozen event（与 freeze 同一事务）
  → 崩溃恢复 / 幂等 / 并发 / zero canonical mutation 测试
```

**关键裁决**：

> `freeze-report` 与 `event append` 是**同一个纵向事务闭环**。不得先写报告、以后再补 Event；也不得先写 Event、再补报告。二者要么同时提交，要么同时不写。

**不在 P1-A 范围**（属 P1-B/P1-C）：definition revision、impact analysis、stale propagation、structured current state、semantic retrieval、F08 故障注入。

**状态前提**：P0（P0-A/B/C）为 `implemented / tested / fixture-verified`。P1-A 不修改 P0 基线文件与 Git 历史；所有测试在 fixture 副本上通过故障注入完成。

---

## 1. 真源和物理落点

### 1.1 Event 物理真源

| 层 | 物理位置 | 性质 |
|---|---|---|
| **Event 真源（canonical）** | `fixture/events/EV-000001.yaml` … | Git 管理、append-only、每事件一文件、不可修改 |
| **Commit receipt（canonical，不可变）** | `fixture/events/EV-000001.commit` | CURRENT 提交的**可验证 canonical commit evidence**；CURRENT rename 完成后写入；不可删除 |
| **Plan snapshot（派生，不可变）** | `fixture/.index/tx/<tx_id>.plan.yaml` | **in-flight WAL / recovery journal**：事务计划不可变快照（写后不修改）；committed 后完成使命，删除 `.index/` 后**不恢复原始 plan**（§5.5 只重建 derived marker，P2-2） |
| **Runtime state（派生，可变）** | `fixture/.index/tx/<tx_id>.state.yaml` | 可变运行状态（proposed…needs_reconcile），**不参与 plan_hash** |
| **Transaction marker（派生，不可变）** | `fixture/.index/tx/<tx_id>.marker` | **derived committed cache**：COMMITTED 缓存标志（绑定 Event/receipt/output_refs 的 canonical-derived fields，**不绑定 plan**）；`committed` 真值由 canonical receipt 承载，marker 丢失 ≠ 事务回退；可从事件+receipt+文件一致性重建（§5.5） |
| **staging** | `fixture/.index/tx/staging/` | 临时文件区，可清理 |
| **SQLite events 表（投影）** | `.index/research.sqlite` | 永远派生，可重建，不成为真源 |
| **Agent Execution Log** | 不属于 Event 真源 | 严格分离，不写入 events/ |

**关键规则（修订版 6）**：

> 1. `commit receipt` 是 **canonical 且不可变**的 CURRENT 提交证据，位于 `events/`（Git 管理），**不随 `.index/` 删除而丢失**。
> 2. **plan 与运行时状态分离**：`plan.yaml` 是不可变快照（marker 只 hash 它）；`state.yaml` 是可变状态（`needs_reconcile` 等），**不参与任何 hash**。改变 state 不会使 marker 失效。
> 3. receipt 是"报告/Event/CURRENT 全部提交"的**可验证 canonical commit evidence**：它在 CURRENT rename 完成后写入；半提交时不存在。
> 4. 只有 **Event + report + manifest + receipt 四者一致**（receipt 内部绑定 a–h 含 event_hash 验证）才能重建 committed marker（§5.5）；半提交永不提升（T30）。
> 5. **Canonical COMMITTED 真值 = 有效 receipt + Event/report/manifest canonical 校验通过**；marker 只是 derived committed cache
>    （丢失后事务仍 committed，仅 `materialized_marker=false`，P2-1）。
> 6. **plan = in-flight WAL**：事务 committed 后完成使命；删除 `.index/` 后重建的是 derived marker，不声称恢复原始 plan bytes（P2-2）。
> 7. **WAL 生命周期（Sol P1-1）**：`.index/tx/` 的 plan/state/staging 在**事务未 committed 前不是可重建派生数据**，而是唯一恢复证据（recovery authority）。
>    `.index/` reset/delete/rebuild **只有在不存在任何 unresolved/nonterminal transaction 时才允许**（§6.2，T50）；
>    committed 后的 `.index/` 删除保证限定为 quiescent/committed-state deletion。

### 1.2 与现有 Worklog 的关系

- 在 fixture 隔离域内，`events/` 是**唯一事件真源**，不存在并列真源。
- 未来接入真实研究目录时，事件真源与现有唯一 worklog 的映射关系**必须另行裁决**；P1-A 不预设、不创建第二全局日志，也不修改任何真实目录。
- Event 与 Agent Execution Log 不得合并（沿用 P0 开发者约束 7）。

### 1.3 编号规则

- `event_id`: `EV-000001` 起，按 `events/` 目录现有最大编号 +1 分配。
- `transaction_id`: `TX-000001` 起；**next = max(transaction_id in canonical `events/EV-*.yaml` + `events/EV-*.commit`) + 1**；
  `.index/` 永远不参与 ID authority——删 `.index/` 后不得重新分配已用编号（P2-8，T44）。
- 编号分配在事务 prepare 阶段完成，与写入同锁。

---

## 2. Event schema 与事件闭集

### 2.1 Domain Event 与 Transaction Event

**合一**（不分开两个流）。P1-A 的 domain 事件 `ReportFrozen` 本身携带 transaction 信息（`transaction_id`、`tx_state`）；事务的 prepare/commit 状态通过 `.index/tx/` plan + state + marker 表达，**不产生独立事务事件流**。

`tx_state` 是事件内容的一部分，**固定为 `committed`**（语义：事件描述的事实以提交意图写入）；事务的物理提交确认**只由 receipt 承载**（valid receipt + canonical output validation = committed；marker 是 derived cache，缺失≠半提交）。**无有效 receipt 的事件文件视为半提交**：reindex 不得将其当作已提交事件索引（除非通过 §5.5 重建，且 receipt 必须存在）。

### 2.2 事件字段（结构化 input_refs / output_refs，无 self-hash）

```yaml
event_id: EV-000001
event_type: ReportFrozen        # P1-A 闭集内唯一 domain 类型
schema_version: 1
command_version: freeze-report/v1   # 参与 request_fingerprint；持久化以便 .index 删除后重新计算（Sol P2）
transaction_id: TX-000001
tx_state: committed             # 固定值；物理确认只由 receipt 承载（marker 是 derived cache）
idempotency_key: freeze-2026-08-30-01   # 必填
request_fingerprint: "sha256:..."       # 请求身份指纹（仅调用方参数，§6.1）
actor: text-agent               # 执行者；非授权者
authorization_ref: AUTH-0001    # 显式授权引用（§6.3）
reason_refs: []                 # 触发原因引用（如 D021）；既参与 fingerprint，也持久化作审计
basis_git_commit: "abc123..."   # gate 时 git rev-parse HEAD（§4.4）
occurred_at: 2026-08-30T12:00:00+08:00  # 业务发生时间（冻结动作发起）
recorded_at: 2026-08-30T12:00:01+08:00  # 记录写入时间
subject: REPORT-004             # 受影响实体

input_refs:                     # 结构化：每项含 role + path + content_hash + reference_scope
  - role: current.md
    path: reports/CURRENT.md
    content_hash: "sha256:..."      # 冻结前 bytes hash
    reference_scope: current
  - role: current.sources.yaml
    path: reports/CURRENT.sources.yaml
    content_hash: "sha256:..."      # 冻结前 bytes hash
    reference_scope: current
  - role: source
    path: organized/EXP-017/result.md
    source_type: file               # file | directory（继承 P0 Source Reference verifier，§4.2/§6.1，P2-5）
    content_hash: "sha256:..."      # 每个 source 的 pinned hash（冻结前；directory 为 SHA256(sorted manifest)）
    reference_scope: current

output_refs:                    # 结构化：每项含 role + path + content_hash
  - role: report
    path: reports/history/REPORT-004.md
    content_hash: "sha256:..."
  - role: sources_manifest
    path: reports/history/REPORT-004.sources.yaml
    content_hash: "sha256:..."
  - role: current.md
    path: reports/CURRENT.md
    content_hash: "sha256:..."      # 冻结后 bytes hash（after，审计记录，非重建验证条件，§5.5）

caused_by: []                   # 触发原因的事件引用（可空）
```

**self-hash 循环消除（关键规则）**：

> Event 文件**不包含自身 hash**。`output_refs` 中不存在 `role: event` 条目。Event 文件的 bytes hash 由 **plan snapshot 与 marker** 保存（`event_hash` 字段），reconcile/重建时对 `events/EV-NNNNNN.yaml` 实际内容计算 canonical hash 并与 plan/marker 比对。事件内容不依赖自身 hash，无循环定义。

### 2.3 Commit receipt schema（canonical，不可变，完整绑定）

```yaml
# events/EV-000001.commit
event_id: EV-000001             # 必须与事件文件名/事件 event_id 一致
transaction_id: TX-000001       # 必须与事件 transaction_id 一致
event_hash: "sha256:..."        # Event 文件 bytes hash（canonical，§6.1）——绑定事件实际内容
report_hash: "sha256:..."       # REPORT-NNN.md 实际 bytes hash
manifest_hash: "sha256:..."     # REPORT-NNN.sources.yaml 实际 bytes hash
current_after_hash: "sha256:..."    # CURRENT.md rename 后 bytes hash（审计）
output_digest: "sha256:..."     # canonical(report_hash, manifest_hash, current_after_hash) 的统一摘要
committed_at: 2026-08-30T12:00:01+08:00
```

- receipt 通过“临时文件 → fsync → 原子 rename”写入（§3.2 步骤 14）。
- **receipt 的 hash 不在 plan 阶段预计算**（receipt 含 `committed_at` 真实提交时间，计划时未知——P2-3 闭合）：
  plan 的 files[receipt] 只含 role/path/action；步骤 14 生成实际 receipt 后，其 content_hash 由 marker 的 `receipt_hash` 绑定；
  reconcile 对 receipt 实际内容重新计算并比对。
- receipt **不可删除、不可改写**（canonical 不可变层）。
- **receipt 是"报告/Event/CURRENT 全部提交"的可验证 canonical commit evidence**：它只在 CURRENT rename 完成后写入；半提交（CURRENT 未 rename）时 receipt 不存在。
- **信任模型**：本证据在"所有 canonical 写入必须经 researchctl 受控写入路径"的信任模型下可验证；普通 YAML 文件本身**不是密码学防伪证据**。P1-A 不引入签名/权限模型，故措辞为"**可验证的 canonical commit evidence**"，而非"不可伪造"。
  - 因此**能检测**：结构不一致、与 Event/report/manifest 绑定不匹配的篡改（T34）。
  - **能检测**：意外损坏（accidental corruption）、局部/不一致篡改（partial/incoherent mutation）。
  - **不能检测**：拥有 canonical filesystem 写权限的主体对 Event/report/manifest/receipt 及其中全部 hash 的
    **一致重写（coherent rewrite）**——无签名、无 append-only 外部锚点（P2-9）。

### 2.4 事件闭集（P1-A）

```text
闭集 = { ReportFrozen }
```

- 模型/工具不得发明闭集外的事件类型。
- researchctl **不提供独立 event append 命令**；事件仅经 freeze-report 事务产生（内部 API）。
- P1-B 扩展 `DefinitionRevised` 等类型时另行批准，不改 P1-A 已冻结事件。

### 2.5 不可变性

- 事件文件一旦 committed（**valid receipt + canonical outputs 验证通过**；marker 缺失/损坏不影响 committed，仅重建 cache），**禁止修改、删除、重排**。
- 纠错只能通过后续事件或新 revision；已提交内容不能回滚（§5.3）。

---

## 3. Transaction 状态机

### 3.1 状态

```text
PROPOSED → VALIDATED → WRITING → COMMITTED → MATERIALIZED
    │          │           │
    │          └── REJECTED（gate 失败，零写入）
    │
    └── ABORTED（prepare 前取消，零写入）

WRITING / COMMITTED 中途崩溃 → 恢复后判定为 NEEDS_RECONCILE 或补全为 COMMITTED
```

| 状态 | 含义 |
|---|---|
| PROPOSED | 输入已收集（actor/授权/sources/目标 REPORT 号），未做任何写入 |
| VALIDATED | 全部 gate 通过（§4.2），准备写入 |
| WRITING | plan/staging/rename 进行中（可崩溃，可恢复） |
| COMMITTED | **receipt 已写且绑定验证通过（§5.5 a–h）** = canonical commit 真值；Event/report/manifest canonical 校验通过；marker 为 derived cache（存在则写入，缺失不回退真值，P2-1） |
| MATERIALIZED | SQLite 派生索引与 INDEX.md 已更新 |
| NEEDS_RECONCILE | hook/恢复无法自动判定（记录在 state.yaml，不影响 plan/marker hash） |

### 3.2 单事务内操作顺序（固定）

```text
1. 获取锁（`.researchctl/locks/freeze.lock`，§6.2）
2. **仅从调用参数规范化并计算 candidate request_fingerprint**（command_version + actor + authorization_ref + reason_refs）——**此步骤不读取 CURRENT/HEAD/source**（幂等 replay 必须先于任何 mutable basis 读取，Sol P1-1）
3. **canonical idempotency lookup（§6.1）**：按 idempotency_key 查 canonical Event/receipt——
   已 committed 且 request_fingerprint 相同 → 直接返回原事务/事件结果（不依赖当前 CURRENT 可否读取，T49）；
   已 committed 但 request_fingerprint 不同 → IDEMPOTENCY_CONFLICT，REJECT；
   同 key 存在 staging/半提交 → TX_INCOMPLETE，REJECT
4. **unresolved transaction 全局检查（Sol P1-4）**：若存在**任意** unresolved/nonterminal 事务 journal 或 canonical half-commit
   （无论 idempotency_key 是否相同）→ TX_INCOMPLETE，REJECT——先清完旧事务才能分配新 ID；
   P1-A 任一时刻最多一个未决事务（不变量 C）
5. 仅当需要创建新事务时：读取 basis_git_commit = git rev-parse HEAD；读取 CURRENT.md + CURRENT.sources.yaml before hash
6. 计算 basis_digest（执行内容摘要，§6.1）
7. PRE-GATE 全部校验（§4.2）
8. 分配 event_id / transaction_id（§1.3 canonical authority）
9. 写 plan snapshot（.index/tx/<tx_id>.plan.yaml，schema 见 §3.7，写后不可变；**创建必须 no-clobber**，防覆盖旧事务 WAL，Sol P1-4）
   + 写 runtime state 初始（.index/tx/<tx_id>.state.yaml，state: validated）
10. staging 写入：REPORT-NNN.md、REPORT-NNN.sources.yaml、EV-NNNNNN.yaml、CURRENT.md@new
11. 校验 staging 各文件 hash 与 plan snapshot 一致
12. 最终 **optimistic stale-basis 检查**（rename 前，§6.2 cooperative writer 模型）：重新读取 CURRENT.md/CURRENT.sources.yaml hash
    与 basis_git_commit，任一与步骤 5/6 记录的 basis_digest 不一致 → STALE_BASIS，ABORT（清理 staging/plan/state）
13. 原子 rename 顺序：**报告/Event → CURRENT.md**（CURRENT 最后 rename）；
    所有 `action: create` 使用 **atomic no-clobber install**（§4.3）：目标已存在 → TARGET_OCCUPIED / TX_INCOMPLETE，绝不覆盖（P1-2）；
    **多文件 install 中途失败语义见 §3.3（两阶段，Sol P1-2）**
14. 写 commit receipt（events/EV-NNNNNN.commit，临时文件 → fsync → 原子 no-clobber rename）——CURRENT 已提交的证据；
    receipt 的 hash 在**生成后**计算（含真实 committed_at），由 marker 的 receipt_hash 绑定（P2-3，不在 plan 预计算）
15. marker 写入：写临时 marker 文件 → fsync → 原子 rename 到 .index/tx/<tx_id>.marker
16. post-commit hook：materialize（SQLite events 表 + 派生索引 + INDEX.md）
17. 释放锁
```

### 3.3 COMMITTED 边界与原子性语义

- **CURRENT.md 属于 COMMITTED 边界**，且其提交证据是 **receipt**（§2.3），不是 hash 记录。
- COMMITTED = **有效 receipt（绑定验证 §5.5 a–h 通过）+ Event/report/manifest canonical 校验通过**；marker 为 derived cache（P2-1）。
- 步骤 1–12 失败：零写入（或仅派生 staging/plan/state 残留，可清理），ABORTED/REJECTED。
- **多文件 install 中途失败（两阶段，Sol P1-2）**：
  - 冲突发生在**任一 canonical output 安装之前** → `TARGET_OCCUPIED`，zero canonical mutation（正常 REJECT）；
  - 至少一个 canonical output 已成功安装后，后续 no-clobber 失败（如 Event 目标被外部创建）→ **`TX_INCOMPLETE`**：
    保留 plan/staging/正式现场，**不再写 CURRENT、不写 receipt**，进入 reconcile——不得伪装成普通 REJECT。
- 步骤 13 后、14 前崩溃（CURRENT 已 rename 或未 rename）：**receipt 不存在 → 半提交判定**（§5.2），reindex 永不提升为 committed（T30）。
- 步骤 14 后、15 前崩溃：receipt 存在、marker 缺失 → 可恢复：补 marker（§5.2/§5.5）。
- 步骤 14 中崩溃（receipt 临时文件未 rename 完成）：损坏/缺失 receipt → 半提交判定。
- 步骤 16 失败：事务已 COMMITTED，hook 可重放；持续失败 → state.yaml 记录 NEEDS_RECONCILE（**不影响 marker 有效性**）。

### 3.4 Hook 定义

- post-commit hook = **materialize**：SQLite events 表更新 + 派生索引重建 + `INDEX.md` 生成。
- P1-A 只有这一个 hook；它位于 COMMITTED 之后（§3.2 步骤 16），可重放、幂等，失败不撤销已提交内容，进入 NEEDS_RECONCILE（写 state.yaml）。
- materialize 进度由 SQLite `index_metadata.last_event_id` 体现（已物化到哪个事件），marker 永不改写。
- 不引入其他独立 hook 阶段。

### 3.5 marker schema（derived cache——marker 只在 canonical transaction 已 committed 后物化；创建不产生 commit truth；不绑定 plan）

**marker 定位（P2-1 闭合）**：marker 是 **derived committed cache**——`committed` 真值来自 canonical receipt；
marker 丢失 → 事务仍 committed（`committed=true, materialized_marker=false`），reconcile/reindex 按 §5.5 重建缓存。

```yaml
# .index/tx/<tx_id>.marker
# 定位（P2-1/P2-2 闭合）：derived committed cache，committed 真值来自 canonical receipt。
# marker 缺失 → 事务仍 committed（仅 materialized_marker=false），reconcile/reindex 重建 cache。
# plan_snapshot_hash 已淘汰（plan 是 in-flight WAL，marker 不绑定其 hash）。
transaction_id: TX-000001
event_id: EV-000001
event_hash: "sha256:..."          # Event 文件 bytes hash（由 plan snapshot 保存）
receipt_hash: "sha256:..."        # events/EV-000001.commit 的 content hash
commit_state: committed           # 唯一合法值；marker 只在 canonical transaction 已 committed 后写入（创建不产生 commit truth）
output_refs_manifest:             # 快照，用于 marker 一致性校验
  - role: report
    path: reports/history/REPORT-004.md
    content_hash: "sha256:..."
  - role: sources_manifest
    path: reports/history/REPORT-004.sources.yaml
    content_hash: "sha256:..."
committed_at: 2026-08-30T12:00:01+08:00
```

- **`commit_state` 恒为 `committed`**（无 `inconsistent` 值）；半提交由**无有效 receipt** 及 canonical/WAL 状态表达（marker 无效只是 cache invalid，不写进 marker）。
- **plan_snapshot_hash 已从 marker schema 删除**（Sol P2-2：plan 是 in-flight WAL，marker 是 committed cache，两者生命周期解耦；删 .index 后重建 marker 不绑定 plan hash）。
- runtime state 变化（`needs_reconcile` 等）不影响 marker 的 canonical-derived fields → marker 永不因状态变化失效（T1c 兼容）。
- marker 通过"临时文件 → fsync → 原子 rename"写入，避免半写入。
- 损坏 marker（校验失败、格式异常、event/receipt hash 不匹配）→ **marker cache invalid**：
  **删除/重建 derived marker（§5.5）**；只要 valid receipt + canonical outputs 验证通过，**canonical transaction 仍 committed**，不是半提交（Sol P2-1）。
- materialize 状态不写入 marker；由 SQLite `last_event_id` 表达（§3.4）。

### 3.6 fsync 保证范围（明确声明）

- P1-A 的 fsync（文件写入前/rename 前）保证**进程崩溃**后的原子性：进程在任意步骤被杀，文件系统层面不会出现半写的正式文件或 marker/receipt/plan/state。
- **掉电恢复**不在 P1-A 保证范围：掉电后的行为依赖底层文件系统与 OS 保证；P1-A 测试只覆盖进程崩溃注入（kill -9 / 模拟中断），不覆盖掉电。
- 实现约束：receipt/marker/plan/state 均先写临时文件 → `fsync` → 原子 `rename` → 目录 `fsync`（如平台支持）。

### 3.7 plan snapshot schema（不可变；canonical serialization 见 §6.1）

```yaml
# .index/tx/<tx_id>.plan.yaml  （写后永不修改）
transaction_id: TX-000001
event_id: EV-000001
command_version: freeze-report/v1   # 参与 request_fingerprint；持久化以便 .index 删除后重新计算（Sol P2）
idempotency_key: freeze-2026-08-30-01
request_fingerprint: "sha256:..."
basis_digest: "sha256:..."         # 执行内容摘要（§6.1：basis_commit + CURRENT before + sources pin）
actor: text-agent
authorization_ref: AUTH-0001
reason_refs: []                 # 持久化（与事件一致）
basis_git_commit: "abc123..."
created_at: 2026-08-30T12:00:00+08:00
current_before_hash:
  current_md: "sha256:..."
  current_sources: "sha256:..."
current_after_hash:
  current_md: "sha256:..."        # CURRENT.md@new 的 bytes hash
files:
  - role: report
    path: reports/history/REPORT-004.md
    action: create
    content_hash: "sha256:..."
  - role: sources_manifest
    path: reports/history/REPORT-004.sources.yaml
    action: create
    content_hash: "sha256:..."
  - role: event
    path: events/EV-000001.yaml
    action: create
    content_hash: "sha256:..."    # Event 文件 bytes hash（plan 保存，事件自身无 self-hash）
  - role: receipt
    path: events/EV-000001.commit
    action: create
    # content_hash 不在此预计算（receipt 含真实 committed_at，P2-3）；提交后由 marker.receipt_hash 绑定
  - role: current.md
    path: reports/CURRENT.md
    action: update
    before_hash: "sha256:..."
    after_hash: "sha256:..."
```

### 3.8 runtime state schema（可变；不参与任何 hash）

```yaml
# .index/tx/<tx_id>.state.yaml
transaction_id: TX-000001
state: validated | writing | committed | needs_reconcile | aborted
updated_at: ...
notes: []                        # 例如 "materialize failed, replayable"
```

- state 变化**不影响** marker（canonical-derived fields）/ receipt。
- `needs_reconcile` 只记录在此文件；reconcile 读取后进入人工/重放处置。

---

## 4. freeze-report 协议

### 4.1 命令形态

```text
researchctl freeze-report \
  --idempotency-key freeze-2026-08-30-01 \
  --actor text-agent \
  --authorization-ref AUTH-0001 \
  --reason-refs D021（可选，持久化于事件/plan）
```

- 只冻结 `CURRENT.md` 当前状态；目标报告号自动分配（REPORT-NNN）。
- **REPORT-NNN 编号 authority（Sol 非阻断定义）**：`next_report_id = max(existing reports/history/REPORT-NNN.md, committed Event.subject REPORT-NNN) + 1`，
  在 global lock 内分配，最终由 no-clobber install 做覆盖保护。
- 命令必须显式提供 `--authorization-ref`，否则 REJECT（§6.3）。
- `--reason-refs` 既参与 fingerprint，也持久化于事件与 plan snapshot（§2.2/§3.7）。

### 4.2 PRE-GATE（全部通过才写入；任一失败 → zero canonical mutation REJECT）

| Gate | 失败语义 |
|---|---|
| 锁可用 | `TX_LOCKED` |
| idempotency_key 未使用或可重放 | `IDEMPOTENCY_CONFLICT` / 幂等重放（§6.1） |
| 同 key 存在 staging/半提交；或**存在任意 unresolved 事务**（无论 key，不变量 C） | `TX_INCOMPLETE` |
| CURRENT.md + CURRENT.sources.yaml 存在且可解析 | `SOURCE_MISSING` |
| 每个 source：path 存在、hash 匹配（current scope；**继承 P0 Source Reference verifier**：file → SHA256(raw bytes)，directory → SHA256(sorted manifest)，P2-5） | `SOURCE_MISSING` / `HASH_MISMATCH` |
| CURRENT 与 sources.yaml 无冲突 | `CURRENT_CONFLICT` |
| 授权存在且格式合法且作用域匹配 | `AUTH_NOT_FOUND` / `AUTH_INVALID` / `AUTH_SCOPE_DENIED` |
| 工作树无未提交变更（fixture git clean） | `DIRTY_WORKTREE` |
| 目标 REPORT 号未被占用 | `TARGET_OCCUPIED` |

**失败时零写入**：不创建任何报告/事件/正式文件；仅允许派生 plan/staging/state 残留（可清理），且必须清理。

**create 目标保护（P1-2）**：PRE-GATE 的 `TARGET_OCCUPIED` 只是预检查；正式保护由 **atomic no-clobber install** 承担（步骤 10→13）：
gate 后、rename 前若目标被外部创建 → no-clobber 失败 → `TARGET_OCCUPIED` / `TX_INCOMPLETE`，**绝不覆盖**（T42）。

### 4.3 CURRENT 与 Historical 的原子关系

- 同一事务内：`CURRENT.md` 更新与 `REPORT-NNN.md + .sources.yaml + EV-NNNNNN.yaml + EV-NNNNNN.commit` 同时提交。
- **`CURRENT.md@new` 的机器更新格式**（不覆盖 T0 人维护叙事）：

```markdown
# CURRENT — 当前研究认知

（人维护的叙事主体，保持不变）

---

<!-- researchctl:freeze-marker -->
> 已冻结快照：REPORT-004（2026-08-30T12:00:00+08:00）
> 冻结前 hash: sha256:...
> 本区块由 researchctl 维护；人工编辑会被 reconcile 检测
<!-- /researchctl:freeze-marker -->
```

- researchctl 只在 CURRENT.md **末尾追加/更新** `researchctl:freeze-marker` 区块；人维护的叙事主体不被改写。
- reconcile 检测 freeze-marker 区块是否与最新 marker/事件一致（人工篡改 → `HASH_MISMATCH`）。
- 冻结不是删除 CURRENT：CURRENT 继续存在供下一轮维护，其叙事主体保持人读。
- CURRENT rename 顺序：报告/Event 先 rename → CURRENT 最后 rename（§3.2 步骤 13）。
- 若 CURRENT 在 gate 后被改动（含最终 optimistic stale-basis 检查，§3.2 步骤 12）→ `STALE_BASIS`，REJECT 零写入。

**确定性冻结变换（P2-4 闭合，T46）**：

```text
report_bytes = CURRENT_before 的 bytes，去除末尾唯一合法的 researchctl:freeze-marker 区块
              （含 `<!-- researchctl:freeze-marker -->` … `<!-- /researchctl:freeze-marker -->` 完整标记）后的内容
Managed region 完整 byte grammar：
  [分隔行] = "\n---\n" 或文件末尾无分隔行（首次冻结时 CURRENT 不含 marker）
  [开始标记] = "<!-- researchctl:freeze-marker -->\n"
  [内容] = 任意字节（不含关闭标记）
  [关闭标记] = "<!-- /researchctl:freeze-marker -->"
  managed region 包含分隔行与完整标记；strip 操作 = 去除从最后一个分隔行至关闭标记的全部字节。
historical_source_ref = 每个 current source_ref 复制：
    reference_scope := historical
    git_commit := basis_git_commit
    除上述两字段外不得静默修改任何 source identity 字段
```

- 若 CURRENT_before 不含 managed 区块 → report_bytes = 原始 bytes（首次冻结）。
- 若含多个/非法 managed 区块 → 不静默 strip，reconcile 报 `HASH_MISMATCH`，人工处置。
- **第二次 freeze 的 REPORT-NNN 不得携带上一次的 freeze-marker**（T46）。

**CURRENT 并发模型（P1-2 闭合，cooperative writer）**：

> freeze 期间所有 CURRENT canonical mutation 必须经 researchctl 同一事务锁（§6.2）。
> **非 cooperating editor 与 researchctl 的并发编辑不在 P1-A 保证范围**。
> 在此模型下，步骤 12 的检查称 **optimistic stale-basis check**（非原子 CAS）：锁内无并发写者，检查–rename 窗口内 CURRENT 不会变化；
> 模型外（人工在检查与 rename 之间编辑）不承诺检测/保护（T41 验证边界语义）。

### 4.4 Git pin 规则（闭合）

- gate 时记录 `basis_git_commit = git rev-parse HEAD`。
- Historical manifest（REPORT-NNN.sources.yaml）中每个 source 的 `git_commit` **使用该 basis commit**（工作树 clean + hash 匹配 ⇒ source 内容与 HEAD 一致）。
- **P1-A 不自动创建 Git commit**。
- freeze 后工作树必然变 dirty（新增 REPORT/Event/receipt、CURRENT 修改）→ **下一次 freeze 前必须由外部流程完成 Git commit**，否则 gate 报 `DIRTY_WORKTREE`。
- rename 前最终 optimistic stale-basis 检查再次比对 `basis_git_commit`，HEAD 在 gate 后变化 → `STALE_BASIS`（§3.2 步骤 12）。

---

## 5. 崩溃恢复与 Reconcile

### 5.1 崩溃点矩阵（依据 plan snapshot + receipt 判定，非散装 hash）

| 崩溃发生在 | 现场特征 | 恢复动作 |
|---|---|---|
| prepare/validate 前 | 无写入 | 直接 ABORT，清理锁 |
| plan/state 写入后、staging 前 | plan/state 存在，无 staging 正式文件 | 删除 plan/state，ABORT |
| staging 中 | plan + staging 存在，无正式文件 | 删除 staging + plan/state，ABORT |
| rename 中（报告/Event 已 rename、CURRENT 未 rename） | plan + 部分正式文件，无 receipt，无 marker | 半提交判定（§5.2）：**先 immutable set 完整性校验（step 0），再做三态**；CURRENT 未提交 → 不补 CURRENT（除非 case 1 通过） |
| CURRENT 已 rename、receipt 未写 | 报告/Event/CURRENT 已就位，receipt 缺失 | **三态判定（§5.2 B，P1-3）**：case 2（live == planned after）→ 补 receipt + marker，**不改 CURRENT**；否则 NEEDS_RECONCILE |
| receipt 写入中（临时文件未 rename 完成） | 损坏/缺失 receipt | 视同无 receipt，半提交判定 |
| receipt 已写、marker 未写 | receipt 存在，marker 缺失 | 补 marker（幂等）；**receipt 有效则不改 CURRENT**（CURRENT 可能已被人工修改，T38） |
| marker 写入中（临时文件未 rename 完成） | 损坏 marker（校验失败） | **marker cache invalid**：删除/重建 derived marker（§5.5）；valid receipt + outputs 则 canonical 仍 committed |
| marker 写入后、materialize 前 | marker 存在，索引旧 | 重放 materialize（幂等） |
| materialize 中 | marker 存在，索引半更新 | 重新 materialize |
| hook（INDEX.md）失败 | marker 存在，INDEX.md 未更新 | state.yaml 记 NEEDS_RECONCILE，可重放 hook |

### 5.2 半提交判定规则（无有效 receipt 或 marker 但正式文件存在）

```text
以 plan snapshot 为基准：逐一比对 plan 中每个文件（role/path/hash）与正式路径实际 hash。
A. receipt 存在且绑定验证通过（§5.5 a–h）：
   → CURRENT 已提交（receipt 是证据）；**不再比较 CURRENT live hash**（CURRENT 可能在提交后被人工修改，T22/T38）
   → 验证 report/manifest 文件存在且 hash 匹配；
   → 直接补写 marker（含 event_hash/receipt_hash），不改 CURRENT → **COMMITTED**（Sol P2-4）
   → 再 replay materialize（SQLite events 表 + INDEX.md hook）→ 成功后才 **MATERIALIZED**
   → report/manifest 缺失或 hash 不匹配 → NEEDS_RECONCILE
B. receipt 缺失（CURRENT 未提交或 receipt 半写）→ **先完成 immutable create-set 完整性校验（不变量 B，Sol P1-3）**：
   step 0: 对 report / sources_manifest / event 三个 `action: create` 输出逐一 reconcile（以 plan 为基准）：
     target 存在且 hash == plan    → OK
     target 缺失但 staging 副本存在且 hash 已验证 → atomic no-clobber install → OK
     target 缺失且无可用 staging 副本 → NEEDS_RECONCILE，**不碰 CURRENT**
     target 存在但 hash != plan    → NEEDS_RECONCILE，**不碰 CURRENT**
   step 1: **仅当三个 immutable outputs 全部就位且与 plan 一致后**，再做 before/after/other 三态：
   case 1: live CURRENT == plan.current_before_hash 且 CURRENT.sources == before 且 HEAD == basis
     → CURRENT 尚未提交 → optimistic stale-basis 校验通过 → 补 CURRENT rename → 写 receipt → 补 marker（幂等）
   case 2: live CURRENT == plan.current_after_hash 且 CURRENT.sources == before 且报告/Event/manifest 全部匹配 plan 且 HEAD == basis
     → CURRENT rename 已完成 → **不再改 CURRENT** → 直接补 receipt → 补 marker（幂等）
   case 3: live CURRENT != before 且 != planned after（或 sources/HEAD 不匹配）
     → 人或其他进程已修改 → STALE_BASIS / NEEDS_RECONCILE，**绝不覆盖**
C. 其他部分一致 → NEEDS_RECONCILE：保留现场，不自动删除、不自动回滚
D. 无 plan 且无 marker → 使用 §5.5 重建规则
```

**receipt 有效时 CURRENT 的处理（关键规则）**：

> 一旦 receipt 有效（绑定验证通过），CURRENT 的提交已被证明；此后 CURRENT 的任何人修改都是正常可变状态（T22）。
> 恢复**只验证 receipt、Event、report、manifest 的绑定**，**不比较 CURRENT live hash，不改 CURRENT**（T38）。
> 只有在 receipt 缺失（CURRENT 未提交）时才需要 stale-basis 保护性补写 CURRENT（T31）。

**恢复补写 CURRENT 前的 optimistic stale-basis 保护（仅 receipt 缺失场景）**：

> 崩溃恢复补写 CURRENT 时，必须重新比对：
> `current_before_hash`、`current_sources_before_hash`、`basis_git_commit` 三项与 plan snapshot 记录一致。
> **任一不一致（例如人在恢复前修改了 CURRENT）→ `STALE_BASIS` / `NEEDS_RECONCILE`，不得覆盖人的新内容**（T31）。

- **禁止**在无明确一致性证据时删除正式文件或自动回滚。
- 恢复动作只允许：清理 staging/plan/state（未提交时）、补 CURRENT rename（immutable set 完整 + case 1 通过）、补 receipt、补 marker、重放 materialize/hook。

**全局不变量（Sol 三核心，冻结门槛）**：

> **A. 幂等 replay 必须在读取 mutable basis 之前完成**——同 key 同 fp 已 committed → 返回原结果，不依赖当前 CURRENT/HEAD 可否读取（T49）。
> **B. CURRENT/receipt 永远不得先于完整且 verified 的 immutable output set**（report + manifest + event 全部就位且 hash 匹配 plan 后才能碰 CURRENT/receipt；§5.2 step 0）。
> **C. P1-A 任一时刻最多一个未决事务**——存在任意 unresolved journal 或 canonical half-commit 时（无论 key 是否相同）不得分配新 TX（§3.2 步骤 4，T48）。

### 5.3 已提交内容不可回滚

- COMMITTED 后的事件、Historical Report、sources manifest、receipt、CURRENT **永不自动删除或改写**（沿用 P0 历史报告不可变）。
- 发现错误 → 只能通过后续事件 / 新 revision / 人工裁决修正。
- `reconcile` 对半提交的处置：确定性可修复 → 自动修复；涉及语义 → `review_required` 报人工。

### 5.4 CURRENT 可见性语义（精确三态）

```text
CURRENT rename 前崩溃          → 直接读取旧 CURRENT（报告/Event 可能已存在，无 receipt，无 marker）
CURRENT rename 后、有效 receipt 前 → 直接读取完整的新 CURRENT（文件已就位），
                                   但 researchctl 查询必须 fail_closed + TX_INCOMPLETE
有效 receipt（marker 为 derived cache，缺失不影响 committed 真值）→ 视为 committed，正常可见
```

- `researchctl sources CURRENT` / freeze 相关查询在"无有效 receipt 且有半提交残留"时返回 `fail_closed` + `TX_INCOMPLETE`，不返回半提交状态。
- 直接文件读取不受 control，但语义如上精确描述（新 CURRENT 是完整文件，非截断）。

### 5.5 无 plan/marker 时从 canonical 重建 COMMITTED marker（删除 .index/ 后恢复）

```text
扫描 events/ 下所有事件文件（正则 EV-\d{6}\.yaml）
对每个事件：
  1. 读取 output_refs，获取 report / sources_manifest 的路径与 hash
     （output_refs 不含 current.md 的 after hash 验证条件；current.md after 仅为审计记录）
  2. 读取对应 commit receipt（events/EV-NNNNNN.commit），逐项验证：
     a. receipt 存在且可解析
     b. receipt.event_id == 事件 event_id 且 == 文件名 EV-NNNNNN
     c. receipt.transaction_id == 事件 transaction_id
     d. receipt.event_hash == 事件文件实际 canonical hash
     e. receipt.report_hash == 事件 output_refs 的 report hash 且 == 报告文件实际 hash
     f. receipt.manifest_hash == 事件 output_refs 的 manifest hash 且 == manifest 文件实际 hash
     g. receipt.output_digest == canonical(receipt.report_hash, receipt.manifest_hash, receipt.current_after_hash)
     h. receipt.current_after_hash == 事件 output_refs 中 current.md 的 content_hash（**内部历史绑定**：receipt↔Event 同源验证；
        绝不与 live CURRENT.md bytes 比较，P2-10）
  3. 上述 a–h 全部通过 → 补写 **derived marker**（Sol P2-2：不声称恢复原始 plan——plan 是 in-flight WAL，committed 后即完成使命；
     **marker 不含 plan_snapshot_hash**；event_hash 从事件实际内容计算；
     receipt_hash 从 receipt 实际内容计算），标记为 committed（committed 真值来自 receipt，不依赖 marker）
  4. 任一不满足（含 receipt 缺失/篡改）→ 标记 NEEDS_RECONCILE（不索引该事件，不提升为 committed）
```

**关键规则（与 CURRENT 生命周期解耦 + 半提交不可伪造）**：

> 1. 重建 committed marker **不比较当前 CURRENT.md live bytes**（CURRENT 可变，T22/T32）。
> 2. 重建的充分必要证据 = **Event + report + sources_manifest + receipt 四者完整且内部绑定一致**（receipt 内部绑定含 event/transaction/hash，§5.5 a–h 的 d 项验证 event_hash）。
>    receipt 的存在性是 CURRENT 曾完成提交的可验证证据——半提交（CURRENT 未 rename）时 receipt 不存在，
>    因此**永远不会把半提交提升为 committed**（T30）。
> 3. `current_after_hash` 参与 receipt ↔ Event 的**内部历史绑定**（§5.5 h），但**绝不与 live CURRENT.md bytes 比较**（P2-10）。

- 反例验证：freeze → CURRENT=A → 人工修改 CURRENT=B → 删 `.index/` → reindex 重建 marker 成功（Event+report+manifest+receipt 均不可变）→ 旧 Event 完整恢复。
- 这与 P0"删除 .index/ 后可完整 reindex"完全一致。

### 5.6 Reconcile 扩展（P1-A）

reconcile 新增检查：

- 无 receipt/marker 的正式文件/事件（半提交）→ 按 §5.2 判定；无 receipt 的 Event 按 §5.5 处理（永不提升）
- marker 存在但 receipt 缺失 → `PROVENANCE_BROKEN`（fail_closed）
- marker 存在但事件缺失 → `PROVENANCE_BROKEN`（fail_closed）
- marker 的 event_hash/receipt_hash 与实际内容 hash 不一致 → `HASH_MISMATCH`
- receipt 内部绑定不匹配（event_id/transaction_id/hash）→ `HASH_MISMATCH`
- 事件存在但报告文件缺失 → `SOURCE_MISSING`
- 事件 output_refs hash 与文件实际 hash 不一致 → `HASH_MISMATCH`
- **旧 Event 与 CURRENT 的关系（范围写死）**：
  - 旧 Event 的 `current_after_hash` **永远只作历史审计**，不参与任何当前校验
  - reconcile **只验证最新事务**的 CURRENT freeze-marker 区块与最新 marker/事件一致
  - **不得**用当前 live CURRENT 或最新 freeze-marker 区块判定旧 Event 损坏（T32）
- `NEEDS_RECONCILE` 状态持久化于 state.yaml（不影响 plan/marker hash），reconcile 可读取并报告

---

## 6. 幂等、并发和权限

### 6.1 canonical hash / fingerprint 与序列化规则

**两类内容 hash 统一为 canonical hash**（消除 YAML 序列化差异）：

> P1-A 所有机器生成文件（Event、plan snapshot、marker、receipt、state、sources_manifest）的 `content_hash` 统一为：
> `canonical_hash = sha256(canonical JSON bytes of parsed document)`
>
> 即：解析该文件 → 序列化为 canonical JSON（规则如下）→ 对 JSON bytes 计算 SHA-256。
> 同一文档无论用何种 YAML 风格/缩进/引号生成，canonical JSON 相同 → hash 相同（跨实现可重建一致）。

**canonical JSON 序列化规则**（适用于 hash 计算与 fingerprint）：

```text
1. 键按 UTF-8 字节字典序排序（递归）
2. 数组保持原始顺序（source_refs 按 (path, role, reference_scope) 字典序全序排序后写入，P2-6 total ordering）
3. null 值字段省略（不写入 JSON）；**schema 约定「缺字段 ≡ 显式 null」**（禁止 schema 区分二者，消除歧义，P2-6）
4. 空数组保留为 []
5. 字符串 UTF-8 编码；**不修改字符串内容**（不 trim 内部/首尾空白；「无尾随空白」仅指 serializer 输出层不产生多余空白）
6. 布尔 true/false、数字不带引号
7. 文件末尾无尾随换行
```

**YAML 解析边界（保证跨 parser 得到相同 JSON）**：

```text
1. 时间字段（occurred_at/recorded_at/committed_at/created_at/updated_at）一律按字符串处理，
   不做 timestamp 类型推断（保留原始字符串，如 "2026-08-30T12:00:01+08:00"）
2. 禁止重复 key：解析时检测，重复 → 解析失败（HASH_MISMATCH 语义）
3. 数字类型固定：整数按 int、浮点按 float；不依赖 parser 的自动类型推断差异
   （fixture 内数值字段仅 seed: 42 等整数，无浮点）
4. 字符串统一按 YAML 标量解析后转为 JSON string；引号风格（单/双）不进入 JSON
5. 键顺序无关（canonical JSON 会排序）；缩进/换行无关
```

**人维护文件（report.md、CURRENT.md）的 hash 规则**：

> report.md 与 CURRENT.md 按**原始文件 bytes** 计算 SHA-256（人维护，字节身份重要），不使用 canonical JSON。

**请求身份与执行内容分离（P1-1 闭合，T3/T4）**：

```text
request_fingerprint（请求身份，重试不变） = sha256(canonical JSON of {
  command_version, actor, authorization_ref, reason_refs })
basis_digest（执行内容，本次实际冻结了什么） = sha256(canonical JSON of {
  basis_git_commit,
  current_before_hash(current_md, current_sources),
  input_refs(role/path/source_type/content_hash/reference_scope) })
```

- `reason_refs` 既参与 request_fingerprint，也持久化于事件/plan（§2.2/§3.7）。
- **关键：request_fingerprint 不含任何「事务执行后必然改变」的 server 状态**（不含 CURRENT before/after hash、
  不含 basis_git_commit、不含 input_refs）。第一次 freeze 成功后 CURRENT 已变（H0→H1）、外部 commit 后 HEAD 也变，
  但同一 idempotency_key 重试的 request_fingerprint 保持不变 → 「提交成功但客户端不知道结果」的幂等重放可达（T3）。
- `basis_digest` 记录本次实际冻结状态（冻结前 CURRENT hash、basis commit、sources pin），用于 stale-basis 校验（§3.2 步骤 12）与审计。
- 判定规则（顺序执行，§3.2 步骤 3–4）：
  1. 按 idempotency_key 查 canonical Event/receipt（`events/EV-*.yaml` + `events/EV-*.commit`）；
  2. 已 committed 且 request_fingerprint 相同 → 返回原事务/事件结果，不重复写入；
  3. 已 committed 但 request_fingerprint 不同 → `IDEMPOTENCY_CONFLICT`，REJECT 零写入；
  4. 存在 staging/半提交，或**存在任意 unresolved 事务**（无论 key，不变量 C）→ `TX_INCOMPLETE`，不得新建事务，也不得直接返回成功；
  5. 未命中 → 继续建 basis（读取 CURRENT/HEAD）并执行事务。

### 6.2 并发

- freeze 全程持有 **`.researchctl/locks/freeze.lock`**（文件锁，非阻塞获取；**锁不属于可删的 `.index/`**，P2-7，T43）。
- **reindex / `.index/` reset 必须先获取同一 global mutation lock**——防止 freeze 持锁期间 `.index/` 被删导致互斥失效（P2-7，T43）。
- **`.index/` reset/delete/rebuild 的 unresolved 前置（Sol P1-1，T50）**：同一 global lock 下：
  ```text
  acquire freeze.lock
  scan .index/tx for nonterminal WAL (plan/state/staging)
  if unresolved exists:
      TX_INCOMPLETE
      不删除任何 tx plan/state/staging/report
  else:
      reset / reindex（quiescent/committed-state deletion）
  ```
  —— 未提交阶段的 plan/staging 是唯一 recovery authority，禁止在存在 unresolved transaction 时删除 `.index/`。
- **cooperative writer 模型（P1-2）**：所有 CURRENT canonical mutation（freeze、reconcile 补写）必须经上述同一锁；
  模型外的并发编辑不在 P1-A 保证范围（§4.3）。
- 第二个 freeze 到达 → `TX_LOCKED`，REJECT（不排队等待）。
- 同一时刻只允许一个 freeze 事务；P1-A 不做多事务并发调度。

### 6.3 权限与授权（fixture authorization registry）

**P1-A 提供最小 fixture authorization registry**（真实授权仍由外部系统负责，P1-A 用 registry 做可验证替身）：

- 位置：`fixture/.auth/registry.yaml`（Git 管理，fixture 副本内）
- 结构：
  ```yaml
  schema_version: 1
  authorizations:
    - ref: AUTH-0001
      grantee: text-agent
      scope: freeze-report
      valid: true
  ```
- freeze gate 验证三件事：
  - **存在性**：ref 在 registry 中 → 否则 `AUTH_NOT_FOUND`
  - **格式**：`AUTH-\d+` 且字段完整 → 否则 `AUTH_INVALID`
  - **作用域**：grantee 匹配 actor、scope 含 `freeze-report`、valid=true → 否则 `AUTH_SCOPE_DENIED`
- researchctl 不自行颁发授权；授权记录由外部流程写入 registry。
- 测试覆盖：缺授权（`AUTH_REQUIRED`）、不存在（`AUTH_NOT_FOUND`）、格式非法（`AUTH_INVALID`）、作用域不匹配（`AUTH_SCOPE_DENIED`）。

### 6.4 旧版本冻结 / Git merge

- 冻结基线必须是**当前** CURRENT；若 CURRENT 已变化 → `STALE_BASIS`（§4.3/§3.2 步骤 12）。
- 工作树有未提交改动（含 merge 冲突）→ `DIRTY_WORKTREE`，REJECT；P1-A 不自动解决 merge。
- Git merge 冲突由人解决后再 freeze；reconcile 不自动改写冲突结果。

---

## 7. 错误语义（P1-A 新增，纳入 envelope）

| 错误 | 场景 | 动作 |
|---|---|---|
| `AUTH_REQUIRED` | 缺 authorization_ref | REJECT 零写入 |
| `AUTH_NOT_FOUND` | 授权引用不在 registry | REJECT 零写入 |
| `AUTH_INVALID` | 授权格式非法 | REJECT 零写入 |
| `AUTH_SCOPE_DENIED` | grantee/scope/valid 不匹配 | REJECT 零写入 |
| `IDEMPOTENCY_CONFLICT` | 同 key 不同 fingerprint | REJECT 零写入 |
| `TX_INCOMPLETE` | 同 key 存在 staging/半提交；或存在任意 unresolved 事务（不变量 C） | REJECT，不得新建或返回成功 |
| `STALE_BASIS` | CURRENT/HEAD 在 gate 或 stale-basis 检查后变化 | REJECT 零写入 |
| `DIRTY_WORKTREE` | 工作树未提交变更 | REJECT 零写入 |
| `TX_LOCKED` | 并发 freeze | REJECT 零写入 |
| `TARGET_OCCUPIED` | 目标 REPORT 号已占用 | REJECT 零写入 |
| `NEEDS_RECONCILE` | hook/半提交无法自动判定 | 进入 reconcile / 人工（写 state.yaml） |
| `PROVENANCE_BROKEN` | marker/receipt 存在但事件缺失等 | fail_closed（reconcile） |
| `CURRENT_CONFLICT` | CURRENT 与 sources 冲突 | REJECT 零写入（沿用 P0） |
| `SOURCE_MISSING` | source 缺失 | REJECT 零写入（沿用 P0） |
| `HASH_MISMATCH` | source/绑定 hash 不匹配 | REJECT 零写入（沿用 P0） |
| `REVIEW_REQUIRED` | 半提交/恢复涉及语义判断 | 不自动处置，报人工（resolution action，非 error semantic） |

**错误闭集 = 15 个 error code**（`SOURCE_MISSING` 与 `HASH_MISMATCH` 分行计数）+ `REVIEW_REQUIRED`（resolution action，不计入 error 数）。
全部写入类命令失败语义（**两阶段，Sol P2-3**）：
- **PRE-GATE / 首个 canonical mutation 之前** → fail-closed，**zero canonical mutation**（不得修改 reports/、不得提交 events/、不得修改 CURRENT canonical state）；
  仅允许派生 journal/staging/plan/state（可清理，残留可被 TX_INCOMPLETE/reconcile 检测）。
- **WRITING 开始后失败（已产生部分 canonical output）** → fail-closed，**允许存在 partial canonical mutation**，返回 `TX_INCOMPLETE` / `NEEDS_RECONCILE`，
  **禁止自动删除/覆盖/回滚**已产生的 canonical 文件（与 §3.3 状态机一致，T42b）。
`NEEDS_RECONCILE`、`PROVENANCE_BROKEN`、`REVIEW_REQUIRED` 完整进入 envelope（errors/warnings + error_semantic）。

---

## 8. 测试矩阵与退出条件

### 8.1 测试矩阵（全部在 fixture 副本，不修改 P0 基线）

| # | 场景 | 期望 |
|---|---|---|
| T1a | 正常 freeze — canonical commit | 报告+manifest+Event+**CURRENT 更新**+**receipt**+**marker** 全部就位，hash 一致 |
| T1b | 正常 freeze — post-commit materialize | materialize 最终成功，SQLite events 表+INDEX.md 更新，last_event_id 推进 |
| T1c | materialize 失败 → NEEDS_RECONCILE | marker 仍有效（canonical-derived fields 不变），state.yaml=needs_reconcile；重放后恢复 |
| T2 | 冻结后 CURRENT 仍存在且指向最新 REPORT | 状态正确，current_before/after_hash 可校验，叙事主体未被覆盖 |
| T3 | 同 key 同 request_fingerprint 重复 freeze（**含成功后重试：第一次已 committed、CURRENT 已变 H0→H1**） | 返回原结果，不重复写入（P1-1：fingerprint 不含执行后状态） |
| T4 | 同 key 不同 request_fingerprint（如 actor 不同）重复 freeze | `IDEMPOTENCY_CONFLICT`，零写入 |
| T5 | 缺授权 freeze | `AUTH_REQUIRED`，零写入 |
| T6 | source 缺失 freeze | `SOURCE_MISSING`，零写入 |
| T7 | source hash 不匹配 freeze | `HASH_MISMATCH`，零写入 |
| T8 | CURRENT 与 sources 冲突 freeze | `CURRENT_CONFLICT`，零写入 |
| T9a | 崩溃注入（报告/Event rename 后、CURRENT rename 前 → receipt 前） | immutable create-set 完整性校验（§5.2 step 0）通过后再三态：case 1（live==before）→ 补 CURRENT+receipt+marker；否则 case 3 → NEEDS_RECONCILE |
| T9b | 崩溃注入（marker 写入中 → 损坏 marker） | 损坏 marker = cache invalid：valid receipt + outputs 验证 → 删除/重建 marker，canonical 仍 committed（非半提交） |
| T9c | 崩溃注入（receipt 后 marker 前） | 补 marker，幂等恢复 |
| T9d | 崩溃注入（marker 后 materialize 前） | 重放 materialize，幂等恢复 |
| T9e | 崩溃注入（report install 后、manifest/event install 前） | **不推进 CURRENT/receipt**（不变量 B）；manifest/event 缺失 → NEEDS_RECONCILE 或从 staging 补装，CURRENT 保持 before |
| T9f | 崩溃注入（report+manifest install 后、event install 前） | **不推进 CURRENT/receipt**（不变量 B）；event 缺失 → NEEDS_RECONCILE 或从 staging 补装，CURRENT 保持 before |
| T10 | 删除 .index/ 后重建（含已提交 Event） | plan/marker/state 丢失，从 canonical（**Event+report+manifest+receipt 四件套**）重建 marker，SQLite 完整恢复 |
| T11 | 并发 freeze（第二个持锁） | `TX_LOCKED` |
| T12 | 工作树 dirty 时 freeze | `DIRTY_WORKTREE`，零写入 |
| T13 | 冻结后 reconcile 无新增 issue | 事件/receipt/报告/manifest/CURRENT freeze-marker/marker 全部一致 |
| T14 | 删除 marker 后 reconcile | 按 plan snapshot+receipt 排查（plan 也丢失 → §5.5 重建），不误删正式文件 |
| T15 | 无有效 receipt 的 Event 不被 reindex 直接索引（除非 §5.5 重建且 receipt 存在） | 无 receipt → 不索引；有 receipt 且 Event+report/manifest 匹配 → 补 marker 并索引 |
| T16 | 事件闭集外类型被拒绝（内部 API） | 拒绝写入 |
| T17 | 授权不存在/格式非法/作用域不匹配 | `AUTH_NOT_FOUND` / `AUTH_INVALID` / `AUTH_SCOPE_DENIED`，零写入 |
| T18 | 同 key 存在 staging 时重试；或 different-key 到达时存在任意 unresolved 事务 | `TX_INCOMPLETE`，不新建事务、不返回成功（不变量 C，T48） |
| T19 | freeze 后再次 freeze（未外部 commit） | `DIRTY_WORKTREE`；外部 commit 后可继续 |
| T20 | 目标 REPORT 号占用 | `TARGET_OCCUPIED`，零写入 |
| T21 | CURRENT.sources.yaml 在 gate 后变化 | `STALE_BASIS`，REJECT 零写入 |
| T22 | 已完成 freeze 后 CURRENT 正常人工修改 | CURRENT 可编辑（非冻结），不触发回滚 |
| T23 | 半提交期间 sources CURRENT 查询 | `fail_closed` + `TX_INCOMPLETE`（不返回半提交状态） |
| T24 | Event self-hash 循环验证 | 事件文件不含 `role: event` 自身 hash；event_hash 由 plan/marker 保存且可校验 |
| T25 | 人工修改 CURRENT 后删除 .index 重建 | 旧 Event 仍恢复（§5.5 不比较 live CURRENT，依赖 receipt） |
| T26 | plan/marker 损坏 | 损坏 marker = cache invalid → 删除/重建（§5.5），valid receipt + outputs 则仍 committed；**已 committed 事务的 plan 损坏/丢失 → 不重建 plan**（完成使命），canonical validation + derived marker/reindex；**unresolved 事务的 plan 损坏 → recovery authority 丢失 → NEEDS_RECONCILE / REVIEW_REQUIRED，不伪造 plan**（Sol P2-2） |
| T27 | Git HEAD 在 gate 后变化（最终 stale-basis 检查） | `STALE_BASIS`，REJECT 零写入 |
| T28 | CURRENT.md gate 后、stale-basis 检查前被修改 | `STALE_BASIS`，REJECT 零写入 |
| T29 | freeze-marker 区块被人工篡改 | reconcile 检出 `HASH_MISMATCH` |
| T30 | 报告/Event 已 rename、CURRENT 未 rename → 删 .index → reindex | **不得提升为 committed（receipt 缺失）→ NEEDS_RECONCILE，不索引** |
| T31 | 崩溃恢复补写 CURRENT 前，人已修改 CURRENT | **stale-basis 校验失败（case 3）→ STALE_BASIS / NEEDS_RECONCILE，不覆盖人的新内容** |
| T32 | 两次 freeze → 修改 CURRENT → 删 .index → reindex | **两个旧 Event 均恢复（receipt 均在）；旧 Event 不被 live CURRENT 判定损坏** |
| T33 | receipt 缺失/损坏时重建 | **不提升 committed；reconcile 报 NEEDS_RECONCILE / PROVENANCE_BROKEN** |
| T34 | 篡改导致结构不一致，或与 Event/report/manifest 绑定不匹配（如改 receipt 的 report_hash 但不改 Event） | 可检测：HASH_MISMATCH / PROVENANCE_BROKEN，不提升 committed。（**文档化限制**：能检测意外损坏与局部/不一致篡改；不能检测对 canonical 写权限主体的 coherent rewrite——§2.3/§9，P2-9） |
| T35 | state 变化不影响 marker（materialize 失败后 marker 仍有效） | T1c 基础上：marker.canonical-derived fields 不变，marker 不被判损坏 |
| T36 | 跨序列化：同文档以不同 YAML 风格生成，canonical hash 一致 | canonical JSON bytes hash 相同（§6.1） |
| T37 | reason_refs 持久化 | 事件与 plan 中均含 reason_refs，且参与 fingerprint |
| T38 | receipt 后、marker 前崩溃 → 人修改 CURRENT → 恢复 | receipt 有效 → 直接补 marker，不比较 CURRENT live hash、不改 CURRENT；恢复后 committed，CURRENT 保持人的新内容 |
| T39 | 崩溃注入（**CURRENT rename 成功 → kill → receipt 尚未 rename**） | 三态 case 2（live==planned after）→ 补 receipt+marker，**不改 CURRENT**（P1-3 边界测试） |
| T40 | 崩溃注入（receipt 临时文件 fsync 后、rename 前 kill） | 视同无 receipt → 三态判定（case 2 场景：补 receipt+marker） |
| T41 | race-cas-current：最终 stale-basis 检查后、CURRENT rename 前模拟外部修改 | cooperative writer 模型（§6.2）下锁内不会发生；模型外不承诺检测/保护（文档化边界，不静默宣称原子 CAS） |
| T42a | race-target-create（首个 canonical output 安装前冲突） | atomic no-clobber install 检出已存在 → `TARGET_OCCUPIED`，zero canonical mutation（Sol P1-2 两阶段） |
| T42b | mid-install target collision（report 已 install 后 manifest/event 目标被外部创建） | 已产生 canonical output → `TX_INCOMPLETE`，保留现场、不写 CURRENT/receipt、进 reconcile；已有 report 不被覆盖/误删（Sol P1-2） |
| T43 | concurrent-index-delete：freeze 持锁时删除/rebuild `.index/` | 锁在 `.researchctl/locks/` 不受影响；reindex 先取同一锁 → 互斥不失效（P2-7） |
| T44 | tx-id-after-reindex：删除 `.index/` 后新事务 | TX ID 从 canonical events/receipts 取 max+1，不重复（P2-8） |
| T45 | directory-source-freeze：P0 directory source（SHA256(sorted manifest)）正常冻结 | 继承 P0 Source Reference verifier，Event input_ref 含 source_type: directory（P2-5） |
| T46 | second-freeze-transform：第二次 freeze 的 REPORT-NNN 不携带上一次 freeze-marker | 确定性 transform（§4.3）生效：strip 唯一 managed 区块，其余 bytes 原样（P2-4） |
| T47 | auth-change-after-gate：gate 后 auth registry 改变 | gate 时验证并写入 plan 的 authorization_ref；进行中事务不受 registry 变化影响；下次 freeze 重新验证（确定语义） |
| T48 | different-key 到达时存在旧 unresolved journal（K1 crash after plan/staging but before Event） | 全局 unresolved 检查（不变量 C）→ `TX_INCOMPLETE`，不分配/不覆盖 TX ID，K1 plan 保持原样（Sol P1-4） |
| T49 | 成功后 CURRENT 被改坏/删除或 repo dirty → 同 key 同 fp 重试 | 幂等 replay 先于 basis 读取（不变量 A）→ 返回原 committed 结果，不访问新 basis（Sol P1-1 强测试） |
| T50 | K1 crash after REPORT-only install（plan/staging 尚在）→ 尝试 `.index/` reset | 未决 WAL 存在 → `TX_INCOMPLETE`，不删除 plan/staging/report；reconcile 能恢复 K1（Sol P1-1 WAL 生命周期） |

### 8.2 退出条件

1. T1a–T50 全部通过（fixture 副本 + 故障注入）；
2. 冻结闭环端到端可用（含崩溃恢复、幂等、授权、Git pin、index 重建）；
3. **zero canonical mutation** 语义在所有 REJECT 场景验证通过（允许派生 journal/staging 残留且可被 TX_INCOMPLETE/reconcile 检测）；
4. 无 receipt 的 Event 永不被当作已提交事件（§5.5 强制要求 receipt + 内部绑定验证）；
5. 删除 `.index/` 后 reindex 完整恢复（含已提交 Event，不依赖 live CURRENT，不伪造半提交）；
6. 崩溃恢复不得覆盖人工修改的 CURRENT（optimistic stale-basis 三态保护：before/after/other，P1-3）；
7. 旧 Event 不受可变 CURRENT / 最新 freeze-marker 影响；
8. Event 文件无 self-hash 循环；
9. plan snapshot 与 runtime state 分离，state 变化不使 marker 失效；
10. 全部机器生成文件使用 canonical hash（跨序列化一致）；
11. fixture 原始工作树与 P0 Git 历史完全不变；
12. 未接 Pi、未碰真实目录。
13. **冻结门槛四项**：crash-current-after（T39）、crash-receipt-temp（T40）、race-cas-current（T41）、race-target-create（T42a/T42b）通过；
14. TX ID 从 canonical history 分配，删 `.index/` 后不重复（T44）；
15. 连续两次 freeze 不互相污染（确定性 transform，T46）；
16. **三条核心不变量（Sol）**：A. 幂等 replay 先于 mutable basis 读取（T49）；B. CURRENT/receipt 不先于完整 immutable set（T9e/T9f/T42b）；C. 任一时刻最多一个未决事务（T48）。
17. **WAL 生命周期**：`.index/` reset/delete/rebuild 仅在无 unresolved transaction 时允许（T50）；未提交 plan/staging 是唯一 recovery authority，不因可删语义丢失（Sol P1-1）。

---

## 9. 明确不做（P1-A）

- definition revision / impact analysis / stale propagation（P1-B）
- structured current state（P1-B）
- semantic retrieval / RAG（P1-C）
- 独立 event append 命令（事件仅经 freeze-report 事务产生）
- 多事务并发调度、事务队列、分布式锁
- 自动 Git commit、自动解决 merge 冲突
- 自动科学结论更新、自动 reviewer
- 密码学签名 / 防伪权限模型（receipt 是可验证 evidence：能检测意外损坏与局部/不一致篡改；
  不能检测对 canonical 写权限主体的 coherent rewrite，§2.3/§9，P2-9）
- 掉电恢复保证（P1-A 只保证进程崩溃；掉电依赖底层 FS/OS）
- 修改 P0 基线、P0 合同、现有 Git 历史
- 接入真实研究目录、Pi Extension、Worker
- 发明闭集外事件类型