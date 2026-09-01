# P1-B Contract — Definition Evolution（定义演化）

> 文档性质：P1-B 实施合同（draft contract）。内容经复核确认后，作为 DefinitionRevision 闭环的唯一边界依据。
>
> 依据：P0-Contract.md（§13 P1-02/03/07）、P1-A-Contract.md（已冻结 rev11，事务基础设施复用）、
> 技术方案 §10（revision 与 impact analysis）、§5.3（event schema）、§12.2（R-ICL v4 目录映射）、INV-009/INV-010、
> PRD §17（定义性文件）、§16.2 H-04（Definition Revision）、G-05，
> 及 Sol 审核（2026-08-31 NO-GO → rev2；rev2 复查 NO-GO → rev3；rev3 复查 NO-GO → rev4；rev4 复查 NO-GO → rev5；
> rev5 复查 NO-GO → rev6；rev6 复查 NO-GO → rev7；rev7 复查 NO-GO → rev8 按 P1-1 + P2-1~P2-6 修订；
> rev8 复查 GO（可冻结）→ rev9 按 P2-1~P2-4 清理（a–k 全文统一 + authority 三元组 + reason_code 映射表 + U34 分层）；
> rev9 复查 NO-GO（三元组 vs U34 冲突 + reason_code 映射表不一致 + §2.3 措辞残留）→ rev10 按 Sol rev9 意见统一（provenance 判据标准化 + change_type 映射表对齐合法 enum + lifecycle override 分离 + §2.3 措辞精确）；
> rev10 复查 NO-GO（§6.3 残留 immutable 校验 + 示例 reason_code 违规 + U34 无 PASS 分支 + hash domain 混淆）→ rev11 按 Sol rev10 意见闭合（删除 immutable 校验 + 示例改 upstream_scope_changed + U34 四子场景 + authority 验证统一 git show→sha256 + cardinality）。
> rev11 复查 GO（可冻结）→ 用户于 2026-09-01 批准最终冻结。后续修订需走变更流程。
>
> 当前状态：已确认（冻结）rev11（2026-09-01），冻结后不开始实现 → **已批准开始实现**。

---

## 0. 状态与范围

**范围（P1-B 唯一闭环）**：

```text
definition revision（H003@v1 → H003@v2：不可变版本 + supersedes 链接 + DefinitionRevised event，同一事务）
  → pre-commit impact planning（as-of basis，确定性）
  → post-commit materialization（replay planned impact → structured current state / stale projection）
  → 崩溃恢复 / 幂等 / zero canonical mutation 测试（复用 P1-A 事务基础设施）
```

**关键裁决**：

> 1. `definition revision` 与 `event append` 是**同一个纵向事务闭环**（沿用 P1-A 裁决 1）。
> 2. **INV-009**：definition revision **永不重写历史 Run 绑定**——已完成 Run 继续绑定旧版本。
> 3. **INV-010**：stale 标记**永不自动升级为 invalidated**；且此限制是 **schema-level hard invariant**
>    （DefinitionRevised 事件的 `impact` 枚举不含 invalidated，validator 拒绝，Sol P1-7）。
> 4. **历史 commit truth 不依赖 mutable 指针**（Sol P1-1）：APPROVED.yaml 是 current pointer，
>    不参与旧 revision 的 live historical validation；未来 APPROVED 变化不破坏旧 transaction。
> 5. **impact decision 属于 transaction planning**（pre-commit，as-of basis），
>    **materialization 属于 projection**（post-commit replay，不重新做 impact decision，Sol P1-2）。
> 6. 定义文件一旦发布即**不可变**（per-version 文件），禁止原地覆盖（PRD G-05）。
> 7. P1-B 复用 P1-A 事务/WAL/receipt mechanism/幂等/崩溃恢复/授权基础设施，但 **receipt 字段不复用
>    P1-A 的 report/manifest 字段名**（定义 P1-B 专用 schema，Sol P2-6）。
> 8. **P1-B 不修改 CURRENT.md**（Sol P2-7）：CURRENT 若引用旧 definition，
>    **由后续机制检测（如 freeze-report 或 reconcile 的 stale 传播）**，不定义为 P1-B 的 affected entity
>    （Sol rev4 P2-6：CURRENT 无 entity_id/version_ref 身份，不硬塞 entity record schema）。
> 9. **live APPROVED current-pointer invariant（Sol rev2 P1-1 + rev5 P2-3 闭合）**：live APPROVED.ref 必须等于
>    该 ENTITY 最新 valid committed DefinitionRevised 的 `approved_ref_after` **且** exact pointer hash 等于
>    `approved_after_hash`（ref + hash 双校验）。人工/非事务回拨或篡改 → `DEF_POINTER_DIVERGED`，
>    fail-closed（冻结 definition status 与新 revision），不得从错误 predecessor 开叉。
> 10. **invalidated 的 canonical write path 不在 P1-B（Sol rev2 P1-8）**：structured state 是纯投影，
>     禁止人工直接写 SQLite 作为科学裁决；invalidated 是 reserved state，未来只能通过 canonical
>     HumanDecision/ConclusionInvalidated 事件/对象进入投影（删 `.index/` 不丢失人工裁决）。

**不在 P1-B 范围**：semantic retrieval / RAG（P1-C）；自动科学结论更新；definition proposal 草稿自动迁移
（技术方案 §10.5）；presentation-only 语义 diff 的**自动**分类（change_type 由受控审批提供，Sol P2-3）；
把 stale 自动裁决为 invalidated；**v1 bootstrap**（P1-B 只做 revision，v1 由外部受控流程创建，Sol P2-5）。

**状态前提**：P0（A/B/C）与 P1-A 为 `implemented / tested / fixture-verified`。P1-B 不修改 P0/P1-A 基线。

---

## 1. 真源和物理落点

### 1.1 Definition 物理真源

| 层 | 物理位置 | 性质 |
|---|---|---|
| **Definition 版本（canonical，不可变）** | `fixture/definitions/<ENTITY>/<ENTITY>@<v>.yaml` | Git 管理、每版本一文件、不可修改 |
| **Approved pointer（current mutable pointer）** | `fixture/definitions/<ENTITY>/APPROVED.yaml` | 当前 approved 指针；**不是历史 commit truth 的验证对象**（Sol P1-1） |
| **Commit receipt（canonical，不可变）** | `fixture/events/EV-NNNNNN.commit` | DefinitionRevised 的 commit evidence（P1-B 专用 schema，§2.3） |
| **Plan snapshot（派生，不可变）** | `fixture/.index/tx/<tx_id>.plan.yaml` | 复用 P1-A in-flight WAL（不恢复原始 plan） |
| **Runtime state（派生，可变）** | `fixture/.index/tx/<tx_id>.state.yaml` | 复用 P1-A state（不参与任何 hash） |
| **Transaction marker（派生 cache）** | `fixture/.index/tx/<tx_id>.marker` | 复用 P1-A derived committed cache |
| **staging** | `fixture/.index/tx/staging/` | 复用 P1-A staging 生命周期 |
| **SQLite structured state（投影）** | `.index/research.sqlite` | 派生，可重建，不成为真源 |

**关键规则（Sol P1-1 闭合）**：

> 1. 版本文件 `definitions/<ENTITY>/<ENTITY>@<v>.yaml` 为 canonical 真源，发布后**永不修改/删除/重排**。
> 2. **历史 COMMITTED truth = DefinitionRevised Event + immutable definition version + receipt**
>    （+ 可选 immutable revision manifest）。**APPROVED.yaml 是 current mutable pointer，不参与旧 revision
>    的 live historical validation**；receipt 记录 `approved_before_hash` / `approved_after_hash` /
>    `approved_ref_after` 用于该事务的恢复与审计，但**绝不拿旧 receipt 的 after hash 与未来 live APPROVED 比较**。
> 3. plan/state/staging/marker 生命周期、`committed` 真值 = valid receipt + canonical 验证，沿用 P1-A §1.1/§3.5。
> 4. 只有 revision 事务产生 `DefinitionRevised` 事件；researchctl 不提供独立 definition-append 命令。

### 1.2 Definition 实体与版本命名

- 实体 ID：`H003`、`E017`、`M001`、`DS-001`、`B001`、`P001`、`TS-0043`、`CLAIM-001` 等（沿用 P0 entity_id 规则）。
- 版本：`<ENTITY>@v1`、`<ENTITY>@v2`，每版本一个不可变文件。
- **P1-B 只做 revision，不负责 v1 bootstrap**（Sol P2-5）：`definitions/<ENTITY>/` 至少存在一个
  已 approved 版本（由外部受控流程创建），P1-B 事务的 `previous` 必须存在且等于当前 APPROVED.ref。
- `subject` 由系统在锁内自动分配（`<ENTITY>@next_version`），**调用方不得自选 subject**（Sol P1-5）。

### 1.3 编号规则（Sol rev3 P1-1 闭合：successor 模型替代 max+1）

- `event_id` / `transaction_id`：沿用 P1-A §1.3（canonical max + 1；`.index/` 永不参与 ID authority）。
- **候选 subject（Sol rev3 P1-1）**：`candidate_subject = successor(--expected-previous)`
  （`H003@v1 → H003@v2`）——**只依赖请求参数，不读取 repository state，step 2 前即可确定**，
  fingerprint 稳定、same-key retry 身份不变。
- **PRE-GATE**：`candidate_subject` 路径不存在（已存在 → `DEF_VERSION_OCCUPIED`，不得跳号）；`--expected-previous == live APPROVED.ref`（chain CAS）。
- **不使用 `max(existing)+1`**：防止 orphan 版本导致 silent version skip（v1→v3 而非发现 v2 occupied）。
- `report_id` 等 P1-A 编号不受影响。

---

## 2. Event schema 与事件闭集

### 2.1 Domain Event 与 Transaction Event

沿用 P1-A §2.1：合一；`tx_state` 固定 `committed`；物理提交确认只由 receipt 承载。

### 2.2 DefinitionRevised 事件字段（无 self-hash；Sol P1-2/P1-7 闭合）

```yaml
event_id: EV-000002
event_type: DefinitionRevised       # P1-B 新增 domain 类型
schema_version: 1
command_version: revise-definition/v1   # 参与 request_fingerprint
transaction_id: TX-000002
tx_state: committed
idempotency_key: defrev-2026-08-31-01
request_fingerprint: "sha256:..."       # 请求身份（含 proposed_definition_hash，§6.1）
actor: text-agent
authorization_ref: AUTH-0001            # 执行权限
approval_ref: APR-000001                # 科学/定义变更批准（内容绑定，§6.3；全合同统一 ID 格式）
approval_digest: "sha256:..."           # 批准 artifact 的 canonical hash（durable evidence，Sol rev2 P1-6）
reason_refs: [D021]
basis_git_commit: "abc123..."
approved_before_hash: "sha256:..."      # APPROVED 更新前 hash（持久化进 Event，永久历史验证用，Sol rev3 P1-2）
occurred_at: 2026-08-31T10:00:00+08:00
recorded_at: 2026-08-31T10:00:01+08:00
subject: H003@v2                        # 系统自动分配（successor(expected_previous)）
previous: H003@v1                       # == --expected-previous == 事务 basis 的 APPROVED.ref
change_type: [scope_change]             # 受控 enum **数组**（P2-1 闭合，全合同统一为数组）
changed_fields: [population, outcome]   # 确定性 structural diff（**只 diff semantic body**，Sol rev3 P2-3）
proposed_definition_hash: "sha256:..."  # 包装后定义 payload hash（fingerprint 绑定，Sol P1-4）
impact_algorithm_version: definition-impact/v1   # 固定算法版本（Sol P1-2）
impact_basis_digest: "sha256:..."       # basis_git_commit + committed event frontier + algorithm version

input_refs:                             # 结构化（沿用 P1-A §2.2）
  - role: definition.previous
    path: definitions/H003/H003@v1.yaml
    content_hash: "sha256:..."          # 旧版本 bytes hash
    reference_scope: historical

output_refs:
  - role: definition
    path: definitions/H003/H003@v2.yaml
    content_hash: "sha256:..."          # proposed_definition_hash（不可变版本）

affected_entities:                      # pre-commit impact planning 结果（Sol P1-2）
  - entity_id: TS-0043
    version_ref: TS-0043@r1
    impact: stale                       # 硬限制枚举：stale | needs_review | superseded
    stale_reasons:                       # 结构化，无自由文本 detail（P2-3）
      - reason_code: upstream_scope_changed   # change_type=[scope_change] → §4.5 映射（Sol rev10 P2-1）
        via_relation: uses
    upstream_revision: H003@v2
  - entity_id: E017
    version_ref: E017@v3
    impact: needs_review
    stale_reasons:
      - reason_code: active_result_bundle
        via_relation: uses
    upstream_revision: H003@v2           # 每条 affected 必须含 upstream_revision（P2-5）

caused_by: []
```

**impact 枚举硬限制（INV-010 机器强制，Sol P1-7）**：

> `DefinitionRevised.affected_entities[].impact` 的合法值**仅**为 `stale | needs_review | superseded`。
> **schema validator / commit gate 拒绝 `invalidated`（也拒绝 `fresh`）**——任何内部代码试图让
> DefinitionRevised 输出 invalidated 都 fail-closed。全局 structured state 未来可支持 fresh/invalidated
> **（仅由未来 canonical HumanDecision/ConclusionInvalidated event/object materialize，禁止任何人工或
> 程序直接写 SQLite——Sol rev3 P1-4）**，但 DefinitionRevised 事件本身绝不产生。

**impact decision 时序（Sol P1-2 闭合）**：

> impact 是 **pre-commit transaction planning**（步骤 7，as-of basis）：基于
> `impact_basis = basis_git_commit + committed event frontier + impact_algorithm_version` 的
> canonical snapshot 计算 `affected_entities`，写入 plan 与 Event。
> **post-commit materialize 只 replay Event.affected_entities** 写 structured state /
> stale projection，**不重新做 impact decision**。`.index/` 重建时同样优先重放事件中已提交的
> affected_entities，绝不用"今天的状态"重算（防漂移，Sol P1-2 第二部分）。

**self-hash 循环消除（沿用 P1-A）**：Event 不含自身 hash；event_hash 绑定：
in-flight=plan.event_hash，committed=receipt.event_hash，derived=marker.event_hash。

### 2.3 Commit receipt（P1-B 专用 schema，Sol P2-6 闭合）

```yaml
# events/EV-000002.commit
event_id: EV-000002
transaction_id: TX-000002
event_hash: "sha256:..."                # Event 文件 canonical hash
definition_hash: "sha256:..."           # definitions/H003/H003@v2.yaml canonical hash
approved_before_hash: "sha256:..."      # APPROVED.yaml 更新前 hash（本事务恢复/审计）
approved_after_hash: "sha256:..."       # APPROVED.yaml 更新后 hash（**历史审计；绝不与未来 live APPROVED 比较**）
approved_ref_after: H003@v2             # 更新后 pointer ref（审计）
output_digest: "sha256:..."             # canonical(event_hash, definition_hash, approved_after_hash, approved_ref_after)（P2-3 闭合）
committed_at: 2026-08-31T10:00:01+08:00
```

- receipt 通过"临时文件 → fsync → 原子 rename"写入（步骤 15）；hash 在生成后计算（含真实 committed_at）；
  不在 plan 预计算（receipt 含 committed_at，P2-3 闭合）。

**valid receipt 的完整 binding validator（Sol rev3 P1-2 闭合：永久历史验证不依赖 plan）**：

```text
receipt 有效 ⇔ 以下全部成立（仅依赖 canonical 持久证据：Event + definition + receipt + canonical predecessor evidence；不依赖 plan/WAL/live APPROVED，Sol rev9 P2-1 措辞修正）：
a. receipt 存在且可解析（严格模式）
b. receipt.event_id == Event.event_id == 文件名 EV-NNNNNN
c. receipt.transaction_id == Event.transaction_id
d. sha256(canonical(actual Event)) == receipt.event_hash
e. sha256(canonical(actual definition file)) == receipt.definition_hash
f. Event.output_refs[definition].content_hash == receipt.definition_hash
   AND Event.proposed_definition_hash == receipt.definition_hash（payload 模型，§4.1）
g. receipt.approved_ref_after == Event.subject
h. receipt.approved_before_hash == Event.approved_before_hash（**Event 自身持久化该值**，
   not plan——plan 可删除，永久历史验证不得依赖 plan，Sol rev3 P1-2）
i. receipt.output_digest == canonical(receipt.event_hash, receipt.definition_hash,
                                     receipt.approved_after_hash, receipt.approved_ref_after)
j. **完整 identity validator（Sol rev5 P1-1 + rev6 P1-2 闭合）**：
   - definition path basename == Event.subject（`definitions/H003/H003@v2.yaml` ⇔ `H003@v2`）
   - actual_definition.entity_id == entity(Event.subject)
   - actual_definition.version_ref == Event.subject
   - actual_definition.previous == Event.previous
   - **Event.subject == successor(Event.previous)**——**不用 request-time expected predecessor**
     （该值不可持久化，historical validator 只依赖 canonical history，Sol rev6 P1-2）
   - **entity(Event.subject) == entity(Event.previous)**（lineage 统一实体）
k. **previous input_ref 验证（Sol rev7 P2-6 闭合）**：
   - Event.input_refs[definition.previous].path == path(Event.previous)
   - Event.input_refs[definition.previous].content_hash == predecessor canonical hash

```

- **staging validation（step 11）**：在 hash 校验之外，显式验证 staged definition 文件内
  entity_id/version_ref/previous 与 plan/Event 一致，任一不匹配 → `DEF_IDENTITY_MISMATCH`（U50）。

- **永久历史 COMMITTED 验证只依赖 Event + definition + receipt + canonical predecessor evidence（a–k），绝不依赖 plan/WAL/live APPROVED**；
  删 `.index/` 后历史验证仍成立（Sol rev3 P1-2；Sol rev8 P2-1 措辞精确化）。
- plan 中的 `approved_before_hash` 仅用于 in-flight/recovery consistency check，
  **不参与 committed-history validator**（§5.2 恢复场景单独校验）。
- `approved_after_hash` 仅作历史审计，**绝不与未来 live APPROVED 比较**（Sol P1-1 rev1）。
- receipt 是 canonical commit truth；trust model 沿用 P1-A §2.3（可检测 accidental/partial corruption；
  不能检测 coherent rewrite）。

### 2.4 事件闭集

```text
闭集 = { ReportFrozen, DefinitionRevised }
```

- 模型/工具不得发明闭集外事件类型。
- researchctl **不提供独立 definition append 命令**；DefinitionRevised 仅经 revise-definition 事务产生。
- P1-C 扩展语义类型时另行批准，不改已冻结事件。

### 2.5 不可变性（沿用 P1-A）

- 版本文件/事件/receipt 一旦 committed，**禁止修改、删除、重排**。
- 纠错只能通过后续事件 / 新 revision / 人工裁决；已提交内容不能回滚（§5.3）。

---

## 3. Transaction 状态机

### 3.1 状态

沿用 P1-A §3.1 状态机：PROPOSED → VALIDATED → WRITING → COMMITTED → MATERIALIZED；
REJECTED / ABORTED / NEEDS_RECONCILE 语义一致。

### 3.2 单事务内操作顺序（固定；Sol P1-3/P1-4 闭合，沿用 P1-A 形态）

```text
1. 获取锁（.researchctl/locks/freeze.lock，§6.2）
2. 仅从调用参数 + proposed definition bytes 计算 candidate request_fingerprint
   （command_version + actor + authorization_ref + approval_ref + reason_refs + definition
    + expected_previous + candidate_subject + change_type + proposed_definition_hash）
   ——**candidate_subject = successor(expected_previous) 只依赖请求参数，不读取 repository state**
   （不变量 A，Sol rev3 P1-1）
3. canonical idempotency lookup（§6.1）
4. unresolved transaction 全局检查（不变量 C）
5. 读 basis：git rev-parse HEAD；APPROVED-before（ref + hash）；expected_previous 版本 bytes hash；
   canonical provenance snapshot（committed event frontier）
6. **current-pointer invariant（§5.4）→ candidate_subject = successor(expected_previous)
   → DEF_VERSION_OCCUPIED 检查 → chain gate（§4.2）→ authorization + content-bound approval（§6.3）**
7. 确定性 structural diff（changed_fields，机械计算）+ **pre-commit impact planning 使用候选 subject**
   → affected_entities → impact_basis_digest
8. 分配 event_id / transaction_id（canonical ID 分配）
9. 写 plan（no-clobber，含 approved_at / approved_ref_after / approved_after_hash）+ state
10. staging 写入：<ENTITY>@<v>.yaml、EV-NNNNNN.yaml、**APPROVED@new.yaml**（含 approved_at + ref + basis commit，P1-2）
11. 校验 staging hash 与 plan 一致（回读解析后 canonical hash）
12. 最终 optimistic stale-basis 检查（HEAD / APPROVED before hash / previous hash 未变）
13. 原子 no-clobber install：**immutable definition → Event**（均 create，绝不覆盖）
14. atomic replace APPROVED.yaml（update 语义：optimistic before-hash check + 原子替换）——最后
15. 写 commit receipt（= COMMITTED）
16. 写 marker（derived cache）
17. materialize：**replay Event.affected_entities** → structured current state / stale projection
    （不重新做 impact decision）
18. 释放锁
```

**关键差异（对照 P1-A）**：

> - receipt 位于 APPROVED 更新之后（步骤 14→15），因此 **receipt 不属于 pre-pointer immutable set**。
> - APPROVED 是 `action:update`：**不能用 create-only no-clobber**，复用 CURRENT 的
>   optimistic before-hash check + atomic replace（Sol P1-3）。
> - materialize 只 replay，不重算（Sol P1-2）。

### 3.3 COMMITTED 边界与原子性语义

- COMMITTED = valid receipt（Event + definition version + receipt 绑定通过）+ canonical 验证；
  marker 为 derived cache（沿用 P1-A）。
- **mid-install 两阶段（沿用 P1-A §3.3）**：
  - 冲突发生在任一 canonical output 安装前 → `TARGET_OCCUPIED`，zero canonical mutation；
  - 至少一个 canonical output 已装后失败 → `TX_INCOMPLETE`：保留现场、不更新 APPROVED、不写 receipt、
    进 reconcile。
- 步骤 14 后、15 前崩溃（APPROVED 已更新、receipt 未写）：三态判定（§5.2 case2）。
- 步骤 15 后、16 前崩溃：receipt 存在、marker 缺失 → 补 marker（不改 APPROVED）。

### 3.4 Hook 定义

- materialize hook = replay `Event.affected_entities` → SQLite structured current state +
  stale projection。可重放、幂等、确定性；失败不撤销已提交内容 → state=needs_reconcile。
- 进度由 SQLite `last_event_id` 体现；marker 永不改写。

### 3.5 marker（沿用 P1-A §3.5）

derived committed cache；不绑定 plan；只在 committed 后写；损坏 = cache invalid → 重建。

### 3.6 fsync 保证范围（沿用 P1-A §3.6）

进程崩溃原子性保证；掉电不在范围。

### 3.7 plan snapshot（Sol P1-4 闭合：proposed bytes 明确为事务输入）

```yaml
transaction_id: TX-000002
event_id: EV-000002
command_version: revise-definition/v1
idempotency_key: defrev-2026-08-31-01
request_fingerprint: "sha256:..."
basis_digest: "sha256:..."
actor: text-agent
authorization_ref: AUTH-0001
approval_ref: APR-000001
approval_digest: "sha256:..."           # approval artifact canonical hash（P2-1 闭合，与 §6.3 一致）
reason_refs: [D021]
basis_git_commit: "abc123..."
created_at: ...
definition: H003
previous: H003@v1
proposed_definition_hash: "sha256:..."     # 事务输入（--definition-input 包装后 hash）
definition_before_hash: "sha256:..."       # H003@v1 bytes hash
change_type: [scope_change]                 # 受控 enum 数组（P2-1 闭合）
changed_fields: [population, outcome]      # 确定性 structural diff
impact_algorithm_version: definition-impact/v1
impact_basis_digest: "sha256:..."
approved_before_hash: "sha256:..."         # APPROVED.yaml 更新前 hash（chain CAS）
approved_ref_after: H003@v2                # 更新后 ref（P1-2）
approved_at: 2026-08-31T10:00:01+08:00     # 固定时间戳（P1-2：恢复时 exact bytes）
approved_after_hash: "sha256:..."          # 更新后 hash（APPROVED@new bytes hash）
files:
  - role: definition
    path: definitions/H003/H003@v2.yaml
    action: create
    content_hash: "sha256:..."
  - role: event
    path: events/EV-000002.yaml
    action: create
    content_hash: "sha256:..."
  - role: approved_pointer
    path: definitions/H003/APPROVED.yaml
    action: update
    before_hash: "sha256:..."
    after_hash: "sha256:..."
  - role: receipt
    path: events/EV-000002.commit
    action: create
    # content_hash 不预计算（P2-3 闭合）
```

### 3.8 runtime state（沿用 P1-A §3.8）

---

## 4. revise-definition 协议

### 4.1 命令形态（Sol P1-4/P1-5 闭合）

```text
researchctl revise-definition \
  --idempotency-key defrev-2026-08-31-01 \
  --definition H003 \
  --expected-previous H003@v1 \
  --definition-input <file> \
  --change-type scope_change \
  --reason-refs D021 \
  --approval-ref APR-000001 \
  --actor text-agent \
  --authorization-ref AUTH-0001
```

- **`--definition-input` 必填（Sol rev3 P2-2 闭合）**：输入是 definition **semantic payload（body-only）**，
**禁止携带 authoritative identity 字段**（entity_id / version_ref / previous / schema_version 是 reserved key，
出现任一 → `DEF_PAYLOAD_MISMATCH`）。researchctl 在候选 subject 确定后包装为：

```yaml
schema_version: 1
entity_id: H003                 # 来自 --definition（调用方不得在 input 内提供）
version_ref: H003@v2            # candidate_subject = successor(expected_previous)
previous: H003@v1               # 来自 --expected-previous
body:
  ...                           # --definition-input 的 semantic payload 原样
```

- **`proposed_definition_hash` 与 `semantic_payload_hash` 区分（Sol rev4 P1-1 闭合）**：
  - `semantic_payload_hash = canonical_hash(previous.body / proposed.body)`——只对 semantic body 计算
  - `definition_hash = canonical_hash(完整包装版本文件)`——含 version_ref/previous 等 metadata
  - **DEF_NO_CHANGE ⇔ `changed_fields == []`（structural_diff(previous.body, proposed.body) 为空）**
    ——不用 full version hash 比较（version metadata 每版必变，会让 no-op 判断永假，Sol rev4 P1-1）
- **validator 检查包装后的 staged definition identity 是否与 CLI/subject/Event 一致**
  （§2.3 j 完整 identity validator + step 11/U50；不是检查 body-only input 内的 reserved key，
  那些 key 在 input 中禁止存在，Sol rev6 P2-2）。
- 实现不得自行猜测内容来源（stdin/草稿/模型生成一律不接受，Sol P1-4）。
- **`--expected-previous` 必填**：调用方声明期望的前驱；系统在锁内校验 `previous == APPROVED.ref`
  （chain CAS）并**自动分配 `subject = <ENTITY>@next_version`**——调用方不得自选 subject（Sol P1-5）。
- 必须显式提供 `--authorization-ref` 与 `--approval-ref`，否则 REJECT（§6.3）。
- 只对 `definitions/<ENTITY>/` 下的 canonical 定义做 revision；不允许普通编辑覆盖（G-05）。

### 4.2 PRE-GATE（全部通过才写入；任一失败 → zero canonical mutation REJECT）

| Gate | 失败语义 |
|---|---|
| 锁可用 | `TX_LOCKED` |
| **current-pointer invariant（§5.4：ref + approved_after_hash）** | `DEF_POINTER_DIVERGED` |
| idempotency_key 未使用或可重放 | `IDEMPOTENCY_CONFLICT` / 幂等重放 |
| 同 key 半提交 / 存在任意 unresolved | `TX_INCOMPLETE`（不变量 C） |
| `--definition` 在 definitions/ 存在且已有 APPROVED | `DEF_NOT_FOUND` |
| **identity invariant（Sol rev4 P1-2）**：`--definition == entity(expected_previous)
  == entity(candidate_subject) == APPROVED.definition/ref entity` | `DEF_IDENTITY_MISMATCH` |
| **chain CAS：`--expected-previous == APPROVED.ref`** | `DEF_CHAIN_MISMATCH`（防 fork/skip，Sol P1-5） |
| **`--expected-previous` 版本文件存在且 hash 匹配（Sol rev6 P2-3：authority 来源明确）** | `DEF_VERSION_MISSING` / `DEF_HASH_MISMATCH` |

- previous hash 的 authority 来源：若 previous 是 P1-B committed revision → 与 its valid
  receipt.definition_hash 比较；若 previous 是 bootstrap v1 → 与 bootstrap 外部 pin 的 expected hash 比较。
| **`candidate_subject = successor(expected_previous)` 路径未被占用（不跳号）** | `DEF_VERSION_OCCUPIED` |
| **语义变化确认（Sol rev4 P1-1）**：`structural_diff(previous.body, proposed.body)` 非空
  （即 `changed_fields != []`）——**不用 full version hash 比较**（version metadata 每版必变） | `DEF_NO_CHANGE` |
| `--change-type` 为受控 enum 且非空 | `DEF_SEMANTIC_CHANGE_REQUIRED` / `DEF_CHANGE_TYPE_INVALID` |
| `--approval-ref` 内容绑定校验通过（§6.3） | `APPROVAL_REQUIRED` / `APPROVAL_BINDING_MISMATCH` |
| `--authorization-ref` 通过授权校验 | `AUTH_*` |
| **工作树完整 clean（Sol rev7 P1-1 闭合）**：`git status --porcelain` 为空——tracked modified / staged / conflict / **untracked canonical files 全部禁止**（含 definitions/、events/ 等 canonical namespace）；不等价于"已跟踪" | `DIRTY_WORKTREE` |

**失败语义**：PRE-GATE / 首个 canonical mutation 前 → zero canonical mutation；
WRITING 开始后失败 → TX_INCOMPLETE / NEEDS_RECONCILE，禁止自动删除/覆盖/回滚（沿用 P1-A §7）。

**change_type 受控 enum（Sol P2-4）+ 数组 canonicalization（Sol rev4 P2-2）**：

```text
enum（由 contract version 固定，不接受任意字符串）：
  scope_change | population_change | measurement_change | outcome_change |
  threshold_change | method_change | assumption_change | other_semantic

change_type 是集合语义：写入前 unique + 按上述 enum 顺序排序（去重、固定顺序）；
request_fingerprint、approval binding、Event 写入使用同一 canonical 数组。
```

- 否则同一科学审批仅因 CLI 顺序不同 → IDEMPOTENCY_CONFLICT / APPROVAL_BINDING_MISMATCH。

### 4.3 Definition 版本与 Approved pointer 的原子关系（Sol P1-1/P1-3 闭合）

- 同一事务内：`H003@v2.yaml` 创建（no-clobber）+ `DefinitionRevised` 事件创建（no-clobber）
  → `APPROVED.yaml` **原子替换**（update 语义，最后）。
- `APPROVED.yaml` 只记录 `ref: H003@v2` + 更新时间 + basis commit；不包含定义正文。
- **APPROVED 是 current pointer，不是历史 commit truth 的验证对象**（Sol P1-1）：
  历史验证永远只用 Event + 版本文件 + receipt。

**APPROVED.yaml 格式**：

```yaml
definition: H003
ref: H003@v2
approved_at: 2026-08-31T10:00:01+08:00
basis_git_commit: "abc123..."
```

### 4.4 Git pin 规则（沿用 P1-A §4.4）

- gate 时记录 `basis_git_commit`；`impact_basis_digest` 包含 basis commit 与 committed event frontier。
- P1-B 不自动 Git commit；revision 后工作树 dirty（新增 definition/Event/receipt + APPROVED modified）→
  下次 revision/freeze 前必须外部提交。
- **predecessor 必须在 basis commit 中（Sol rev7 P1-1 加强）**：对非-bootstrap predecessor，
  `git show <basis_git_commit>:definitions/.../<previous>.yaml` 必须存在，且
  hash == 该 predecessor 的 valid receipt.definition_hash；其 Event/receipt 也必须已进入 basis history。
  ——basis_git_commit 必须是真正的 as-of snapshot，不允许"HEAD + 一部分工作树历史"的混合态（U55）。

### 4.5 Pre-commit impact planning（确定性，步骤 7；Sol P1-2/P2-1/P2-2 闭合）

从 **as-of canonical snapshot**（basis_git_commit + max_committed_event_id + impact_algorithm_version，
Sol rev4 P2-5：frontier 用 `max_committed_event_id` 表示，不扩成第二套 snapshot protocol）
计算 `affected_entities`：

```text
closure 规则（**唯一确定函数，Sol rev2 P1-5 闭合**）：
  - **root = previous definition version**（H003@v1）
  - **遍历方向：沿 reverse dependency edges**（从 root 出发找下游引用者）：
    对 dependency relations {based_on, uses, references, caused_by}，沿 incoming/reverse 方向
    求 transitive closure（root 是被引用方，遍历出引用它的实体）
  - **supersedes 不参与 stale propagation**（只用于 lineage，明确排除，除非另有规则）
  - visited key = (entity_id, version_ref)，去重（多路径同实体只留一条）
  - 循环：visited 集合天然终止；不展开环
  - 优先级：needs_review > stale（同实体多路径同时命中时取最高优先级）
  - superseded/historical 为独立类别，不参与 needs_review/stale 竞争
  - **多路径 reason 确定性（P2-2/P2-5 闭合）**：同一实体多路径 stale 时，`stale_reasons[]` 数组保留全部
    去重后的 reason，**排序键 = (upstream_revision, canonical(change_type), reason_code, via_relation)
    严格 total order**（Sol rev4 P2-1）；**detail 已从 canonical Event 删除**（Sol rev7 P2-3：
    结构化字段即可跨实现确定，人读 detail 在 presentation 层生成）
  - **summary 只有两个独立维度（Sol rev7 P2-4）**：review_state（needs_review|stale|fresh）与
    historical_state（superseded|historical），**不生成 latest_impact 单值**
  - 输出排序：按 (entity_id, version_ref) 固定字典序（canonical bytes 稳定）
  - **lifecycle 的 canonical source**：从 committed events + definitions/records 的 committed 状态读取，
    不读 live 可变状态（影响 as-of basis，Sol P1-2 第二部分）

**reason_code 闭集（P2-3 闭合）**：`upstream_definition_changed | active_result_bundle |
upstream_method_changed | upstream_scope_changed | upstream_assumption_changed | other_upstream_change`
——canonical Event 不保留自由文本 detail（人读 detail 在 presentation 层生成）。

**reason_code 唯一映射（Sol rev9 P2-2 写死）**：合法 change_type enum 见 §4.2（scope_change / population_change / measurement_change / outcome_change / threshold_change / method_change / assumption_change / other_semantic）。映射表不包含非法 enum，不混入 lifecycle 分类。

**A. revision-change reason 映射**（change_type → reason_code，一一对应）：

| change_type | reason_code |
|---|---|
| `scope_change` | `upstream_scope_changed` |
| `method_change` | `upstream_method_changed` |
| `assumption_change` | `upstream_assumption_changed` |
| `population_change` | `upstream_definition_changed` |
| `measurement_change` | `upstream_definition_changed` |
| `outcome_change` | `upstream_definition_changed` |
| `threshold_change` | `upstream_definition_changed` |
| `other_semantic` | `other_upstream_change` |

**B. lifecycle override**（entity type × lifecycle 触发，不依赖 change_type 映射）：
| 场景 | reason_code |
|---|---|
| ResultBundle executed + uncommitted 引用旧版 | `active_result_bundle` |

同一 affected 实体的 stale_reasons 由上述映射表机械生成（`via_relation` 来自影响分析边）；
lifecycle override 优先于 revision-change 映射（Sol rev9 P2-2）；不允许自定义字符串。
**cardinality（Sol rev10 P2-4 闭合）**：change_type 是集合，对每个 canonicalized member 机械映射一个
reason_code，去重后进入 stale_reasons[]；lifecycle override 命中时以 override 规则取代（而非追加）
revision-change reasons。

分类矩阵（entity type × lifecycle，Sol P2-2）：
  Run          committed            → impact=superseded（仅记录 upstream_superseded；不重写绑定，INV-009）
  TaskSlice    not executed         → impact=stale
  ResultBundle executed, uncommitted → impact=needs_review
  Conclusion   committed            → impact=stale（绝不自动 invalidated，INV-010）
  ExperimentSpec/Observation/Inference/Claim 引用旧版本 → impact=stale
  其他引用者                        → impact=stale（明示为兜底，不允许隐性默认）
```

- **impact decision 在 commit 前完成并写入 Event**；materialize 只 replay（Sol P1-2）。
- `changed_fields` 由 **确定性 structural diff** 机械计算，**只 diff semantic body**
  （`structural_diff(previous.body, proposed.body)` 的 field-path diff，不包含 version_ref/previous
  等 revision metadata，Sol rev3 P2-3）；`change_type` 由受控审批提供（Sol P2-3）。
- **DEF_NO_CHANGE（Sol rev4 P1-1 闭合）**：`structural_diff(previous.body, proposed.body)` 为空
  （`changed_fields == []`）→ 强制 DEF_NO_CHANGE——**不用 full version hash 比较**
  （version metadata 每版必变，会让 no-op 永假）。

### 4.6 Stale propagation（INV-010 机器强制；Sol rev3 P1-4 措辞闭合）

- stale 是一等状态（技术方案 §10.4）：`fresh / stale / needs_review / superseded / invalidated`。
- **DefinitionRevised 事件只产生 stale / needs_review / superseded**；**invalidated 只能由未来 canonical
  HumanDecision / ConclusionInvalidated event/object 产生，structured state 仅 materialize 该 canonical
  decision——禁止任何人工或程序直接将 SQLite 作为科学裁决写入点**（Sol rev3 P1-4）。
- 每条 affected 记录：`impact` + `stale_reasons[]`（数组，P2-4）+ `upstream_revision`。
- stale 传播是确定性的（same input → same marks）；可重放（replay 事件）。

### 4.7 Structured current state（materialized 读模型；Sol P2-8 闭合）

materialize 后从 canonical + events 重建（可删除 `.index/` 后完整重建）：

```text
definition_state（每个定义实体）：
  entity_id, latest_approved_ref, supersedes_chain[], updated_at

affected_state（每条受影响实体，按 fact 保存，多 upstream 不覆盖，Sol P2-8）：
  (entity_id, version_ref, upstream_revision) → impact fact
  summary 聚合（P2-6 闭合：独立维度不压成单值）：
    review_state:    needs_review | stale | fresh     # 科学审查维度
    historical_state: superseded | historical         # 历史绑定维度
    stale_reasons[], upstream_revisions[], updated_at

查询（researchctl 命令）：
  definition status <ENTITY>      → 最新 approved + 状态
  definition affected <ENTITY>    → 受影响实体清单（按 fact 展开）
  definition history <ENTITY>     → supersedes 链
```

- 全部派生；真源仍是定义版本文件 + 事件 + receipt。

---

## 5. 崩溃恢复与 Reconcile

### 5.1 崩溃点矩阵（Sol P1-3 闭合）

| 崩溃发生在 | 现场特征 | 恢复动作 |
|---|---|---|
| prepare/validate 前 | 无写入 | ABORT |
| plan/state 后、staging 前 | 无 canonical | ABORT（pre-canonical 清理） |
| staging 中 | 无 canonical | ABORT |
| **definition install 后、Event 前** | definition 就位，Event/APPROVED 未动 | immutable set 校验 → 从 staging 补 Event → 三态 |
| **Event install 后、APPROVED 前** | definition+Event 就位，APPROVED 未动 | immutable set 校验 → 三态（APPROVED==before → case1） |
| APPROVED 已更新、receipt 未写 | 三件套就位，receipt 缺失 | 三态 case2：只补 receipt+marker，不改 APPROVED |
| receipt 已写、marker 未写 | receipt 存在 | 补 marker，不改 APPROVED |
| marker 后、materialize 前 | marker 存在 | 重放 materialize（replay affected，不重算） |
| materialize 中 | 派生投影半更新 | 重新 materialize（确定性幂等） |

### 5.2 半提交判定（Sol P1-3 闭合）

```text
以 plan snapshot 为基准：
step 0（immutable set，不含 receipt）：
  reconcile definition 版本 + Event 两个 create output
  （target 存在+hash 匹配 → OK；缺失+verified staging → no-clobber 补装；
   缺失且无 staging → NEEDS_RECONCILE；hash 不匹配 → NEEDS_RECONCILE）
step 1（APPROVED before/after/other 三态，仅当 immutable set 完整后；Sol rev5 P1-2 闭合）：
  **recovery basis check（P1-2）**：HEAD == plan.basis_git_commit AND
  actual previous_definition_hash == plan.definition_before_hash；否则 → STALE_BASIS / NEEDS_RECONCILE
  case 1: live APPROVED == before（ref+hash）→ 从 staging 取 **APPROVED@new.yaml exact bytes**
    原子替换 APPROVED（含 approved_at / approved_ref_after / basis commit）→ receipt → marker
  case 2: live APPROVED == planned after → 不改 APPROVED → 只补 receipt → marker
  case 3: 其他（人或进程已修改）→ STALE_BASIS / NEEDS_RECONCILE，绝不覆盖
```

**不变量 A/B/C/D 全部沿用 P1-A**（D：partial canonical + uncommitted 必须保留 WAL）。

### 5.3 已提交内容不可回滚（沿用 P1-A；P2-5 措辞修正）

Definition 版本/事件/receipt 永不自动删除或改写；APPROVED 是 current pointer，
**已提交事务不自动回滚其 pointer movement，后续合法 revision 可以再次移动 APPROVED**（Sol rev2 P2-5）；
纠错走新 revision。

### 5.4 Reconcile 扩展（P1-B）

**current-pointer invariant（Sol rev3 P1-3 闭合：ref + exact hash）**：

```text
对每个有 APPROVED 的定义实体：
  该实体最新 valid committed DefinitionRevised（按 event_id 单调序取最大，P2-7）
  ⇒ 期望：
    live APPROVED.ref == latest receipt.approved_ref_after
    AND
    hash(canonical(live APPROVED)) == latest receipt.approved_after_hash
  无 P1-B revision 的 bootstrap baseline（Sol rev5 P1-3 闭合）：
    trust root = **frozen fixture/deployment 配置中的不可变常量 bootstrap_commit**（外部 pin，
    **不从 BOOTSTRAP.yaml 自身取得，杜绝 self-reference**）；
    从该 commit 读取 APPROVED 与 v1 bytes，计算 hash，并验证
    BOOTSTRAP.yaml / live APPROVED / live v1 与外部 pin 一致。
  任一不匹配 → DEF_POINTER_DIVERGED：
    definition status fail-closed；新 revision PRE-GATE fail-closed（§4.2）；
    reconcile 报 divergence；
    若存在 unresolved WAL，先 TX_INCOMPLETE（APPROVED 可能处于已更新、receipt 未落的 crash window）
```

- **missing APPROVED（Sol rev5 P2-4 闭合）**：已有 valid committed DefinitionRevised history 的 entity
  其 APPROVED.yaml 缺失 → `DEF_POINTER_DIVERGED` / `PROVENANCE_BROKEN`（不跳过检查）。

- **identity invariant（Sol rev4 P1-2 闭合）**：Definition identity = directory entity = 文档 entity_id =
  Event subject entity = Event previous entity = CLI `--definition`；任一不一致 → `DEF_IDENTITY_MISMATCH`。

- **最新 committed revision 顺序**：按 `event_id` 单调序取最大（Sol rev3 P2-7）。
- **approval historical evidence（Sol rev3 建议收口）**：`git show <Event.basis_git_commit>:fixture/.auth/approvals/<approval_ref>.yaml` 的 canonical hash == Event.approval_digest——即使 live approval artifact 被篡改，历史批准仍可从 basis commit 验证；reconcile 检出不一致时报 `PROVENANCE_BROKEN` / `APPROVAL_EVIDENCE_MISMATCH`，但不使已 committed revision 回退。
- APPROVED 指向的版本文件缺失/损坏 → `PROVENANCE_BROKEN`
- **DefinitionRevised 事件 + 版本文件 + receipt 三者绑定不匹配（§2.3 a–k）→ `HASH_MISMATCH`**
  （**不比较 live APPROVED**——未来 APPROVED 变化不破坏旧 revision，Sol P1-1）
- 普通编辑覆盖已发布定义版本 → `DEF_VERSION_OCCUPIED`（fail_closed）
- structured state 与事件 affected_entities 不一致（materialize 后）→ `HASH_MISMATCH`
- `.index/` reset guard、WAL 生命周期沿用 P1-A §5.6/§6.2

---

## 6. 幂等、并发和权限

### 6.1 canonical hash / fingerprint（Sol P1-4 闭合）

- `request_fingerprint = sha256(canonical JSON of {command_version, actor, authorization_ref,
  approval_ref, reason_refs, definition, expected_previous, candidate_subject, change_type,
  proposed_definition_hash})`
  —— 请求身份，重试不变；**candidate_subject = successor(expected_previous) 只依赖请求参数**
  （不读取 mutable repository basis，不变量 A；Sol rev3 P1-1）。
- `basis_digest = sha256(canonical JSON of {basis_git_commit, definition_previous_hash,
  approved_before_hash, input_refs(...)})` —— 执行内容。
- 判定规则沿用 P1-A（先查 key 再建 basis；replay / conflict / incomplete / miss）。
- 全部机器生成文件 canonical hash = `sha256(canonical JSON bytes of parsed document)`。

### 6.2 并发（沿用 P1-A §6.2）

- 同一 global lock；单未决事务；cooperative writer 模型。
- `.index/` reset guard、unresolved 全局阻止沿用。

### 6.3 权限与授权（Sol rev2 P1-6 闭合：approval evidence durable pin）

**两个独立权限边界**：

```text
authorization_ref：执行权限——"你有权运行 researchctl revise-definition"（scope: revise-definition）
approval_ref：     科学/定义变更批准——"这个具体变更被批准了"（内容绑定）
```

**approval artifact 的 authority 语义（Sol rev8 P2-2 收窄）**：

- 实际 authority 是 **(basis_git_commit, approval_ref, approval_digest)** 三元组：
  - `approval_ref` 是身份
  - `approval_digest` 是证据（= approval artifact 在 basis_git_commit 中的 canonical hash）
  - `basis_git_commit` 是批准生效的 Git snapshot
- **provenance 规则（机器判定，Sol rev9 P1-1 统一）**：
  - authority 验证统一为：`git show <basis_git_commit>:fixture/.auth/approvals/<approval_ref>.yaml`
    → strict parse → canonical serialization → sha256 → **compare Event.approval_digest**
    （Git blob OID 是辅助 provenance metadata，不是 approval_digest，不参与 authority equality；Sol rev10 P2-3）
  - 若同一 APR path 在多个 Git commit 中有不同 content hash → 每个 (commit, approval_ref, content_hash) 三元组视为**独立批准证据**，
    不存在"同一个 APR 被改写"的冲突——历史 Event 永远按自己 Event.basis_git_commit + approval_digest 验证旧证据，不受影响
  - **新 transaction**：用新 basis_git_commit 中 APR 的 bytes；若新 APR content binding 匹配新请求
    → **合法的新独立 approval evidence，approval gate PASS**（不得因该路径过去在别处有过不同内容而拒绝）
  - 若新 APR 与请求不绑定 → `APPROVAL_BINDING_MISMATCH`
  - **唯一 provenance corruption 判据**：已 committed Event 的 approval_digest 与**它自己的**
    Event.basis_git_commit 中 APR bytes 不一致或缺失 → reconcile 报 `APPROVAL_EVIDENCE_MISMATCH` / `PROVENANCE_BROKEN`
  - 总结：*same path changed in another commit ≠ provenance corruption；
    stored Event digest disagrees with its own pinned basis = provenance corruption*（Sol rev9 P1-1）
- **术语清理**：删除"create-only / 不可原地改写"的声明，改为以上精确语义。

内容绑定（方案 A，Sol 推荐）：

```yaml
approval_id: APR-000001
definition: H003
previous: H003@v1
proposed_definition_hash: "sha256:..."   # 必须 == --definition-input 包装后 hash
change_type: [scope_change]               # 数组（P2-1）
approved_by: ...
valid: true
```

- **Event/plan 保存 `approval_ref`（identity）+ `approval_digest`（= approval artifact 的 canonical hash，historical evidence）**。
  approval_ref 是身份；approval_digest 是证据——未来重写 APR 不破坏历史 Event 的批准证据。
- **撤销不在 P1-B 范围（Sol rev4 P2-4 闭合）**：approval 的 authority 是 (basis, ref, digest) 三元组；
  P1-B 不承诺撤销机制（如未来需要，另行定义 canonical revocation source，不写入 P1-B）。
- **approval 必须在 basis_git_commit 中已存在（Sol rev6 P1-1 闭合）**：PRE-GATE 读取 basis 后、计划前，
  必须验证：`git show <basis_git_commit>:fixture/.auth/approvals/<approval_ref>.yaml` 存在且可解析，
  其 canonical hash == approval_digest，且内容绑定与事务请求一致。
  **live/uncommitted 工作树中的 approval 文件不可作为 authority**——P1-B 只消费已提交进 basis commit 的批准。
- `APPROVAL_BINDING_MISMATCH`：approval 的 definition/previous/proposed hash/change_type 任一
  与事务请求不一致，或 approval 不在 basis commit 中 → REJECT（长期 scope=revise-definition
  不等于"以后任何定义都批准"；未提交 approval 不可用）。
- registry 条目扩展（authorization 层）：

```yaml
  - ref: AUTH-0002
    grantee: text-agent
    scope: revise-definition
    valid: true
```

- 校验顺序：authorization（存在/格式/grantee+scope/valid）→ approval（basis 中存在 / strict parse
  → canonical approval_digest → content-binding / valid）——**不含 immutable 校验**（Sol rev10 P1 闭合：
  "immutable approval"概念已废弃；如需表达 Git commit 内容不可变，用 basis-pinned exact bytes validation）。
- researchctl 不自行颁发授权或批准；两者均由外部受控流程写入。

---

## 7. 错误语义（P1-B 新增，纳入 envelope）

沿用 P1-A 全部 15 error + REVIEW_REQUIRED，新增：

| 错误 | 场景 | 动作 |
|---|---|---|
| `DEF_NOT_FOUND` | `--definition` 不在 definitions/ 或尚无 APPROVED | REJECT zero canonical mutation |
| `DEF_CHAIN_MISMATCH` | `--expected-previous != APPROVED.ref`（fork/skip/non-current） | REJECT zero canonical mutation |
| `DEF_VERSION_MISSING` | `--expected-previous` 版本文件不存在 | REJECT zero canonical mutation |
| `DEF_HASH_MISMATCH` | `--expected-previous` 版本 hash 不匹配 | REJECT zero canonical mutation |
| `DEF_NO_CHANGE` | structural_diff(previous.body, proposed.body) 为空（changed_fields == []；不用 full version hash，Sol rev4 P1-1） | REJECT zero canonical mutation |
| `DEF_SEMANTIC_CHANGE_REQUIRED` | change_type 为空 | REJECT zero canonical mutation |
| `DEF_CHANGE_TYPE_INVALID` | change_type 不在受控 enum | REJECT zero canonical mutation |
| `DEF_VERSION_OCCUPIED` | candidate_subject 路径已被占用/覆盖（不跳号；definition-domain 用户可见错误，Sol rev4 P2-3） | REJECT zero canonical mutation（候选版本场景）/ fail_closed（reconcile） |
| `APPROVAL_REQUIRED` | 缺 approval_ref | REJECT zero canonical mutation |
| `APPROVAL_BINDING_MISMATCH` | approval 内容绑定与请求不一致 | REJECT zero canonical mutation |
| `IMPACT_INVALID` | 内部代码试图产生 invalidated/fresh impact | fail_closed（schema/commit gate） |
| `DEF_POINTER_DIVERGED` | live APPROVED.ref ≠ 最新 committed DefinitionRevised 的 approved_ref_after，或 exact pointer hash ≠ approved_after_hash（含手改/回拨，Sol rev4 P2-3） | fail_closed（reconcile / definition status / 新 revision） |
| `DEF_IDENTITY_MISMATCH` | --definition 与 expected_previous/candidate_subject/APPROVED/实际 definition 文档的 entity 身份不一致（Sol rev4 P1-2） | REJECT zero canonical mutation |
| `DEF_PAYLOAD_MISMATCH` | input payload 含 reserved identity key 或与 CLI 自动分配不一致（Sol rev2 P1-7） | REJECT zero canonical mutation |
| `APPROVAL_EVIDENCE_MISMATCH` | approval artifact 在 basis commit 的 canonical hash ≠ Event.approval_digest（live 篡改可检出，但不使已 committed revision 回退，Sol rev3 收口） | fail_closed（reconcile） |

**错误闭集 = 15（P1-A）+ 15（P1-B）= 30 个 error code** + REVIEW_REQUIRED（resolution action）。
失败语义沿用 P1-A §7 两阶段。

---

## 8. 测试矩阵与退出条件

### 8.1 测试矩阵（全部在 fixture 副本，不修改 P0/P1-A 基线；Sol 建议测试全部纳入）

| # | 场景 | 期望 |
|---|---|---|
| U1a | 正常 revision（H003@v1→v2，previous==APPROVED.ref，subject 自动分配） | 版本+Event+APPROVED+receipt+marker 就位，三者绑定一致 |
| U1b | materialize：replay affected_entities → structured state | 与 Event 内容一致，幂等 |
| U2 | 已 committed revision 后 APPROVED 指向新版本 | 定义可查询；历史 receipt 验证**不比较 live APPROVED** |
| U3 | 同 key 同 fp 重复 revision | replay，不重复写入 |
| U4 | 同 key 异 fp revision | `IDEMPOTENCY_CONFLICT`，零写入 |
| U5 | 缺 authorization/approval | `AUTH_REQUIRED` / `APPROVAL_REQUIRED`，零写入 |
| U6 | definition 不存在/无 APPROVED | `DEF_NOT_FOUND`，零写入 |
| U7 | **previous != APPROVED.ref（fork/skip）** | `DEF_CHAIN_MISMATCH`，零写入（Sol P1-5） |
| U8 | previous 版本缺失/hash 不匹配 | `DEF_VERSION_MISSING` / `DEF_HASH_MISMATCH`，零写入 |
| U9 | **same semantic body（version metadata 将变化但 body 不变）** | `DEF_NO_CHANGE`（changed_fields == []，不用 full version hash 比较，Sol rev4 P1-1），零写入 |
| U10 | change_type 为空/非法 | `DEF_SEMANTIC_CHANGE_REQUIRED` / `DEF_CHANGE_TYPE_INVALID`，零写入 |
| U11 | **approval 不绑定 proposed hash** | `APPROVAL_BINDING_MISMATCH`，零写入（Sol P1-6） |
| U12 | 崩溃注入（definition install 后、Event 前） | **immutable set 未完整前绝不推进 APPROVED**；从 staging 补 Event → 补齐并验证后才进入 case1 → APPROVED → receipt（P2-4 措辞修正） |
| U13 | 崩溃注入（Event install 后、APPROVED 前） | 补 Event/APPROVED/receipt/marker（case1） |
| U14 | 崩溃注入（APPROVED 后、receipt 前） | case2：只补 receipt+marker，不改 APPROVED |
| U15 | 崩溃注入（receipt 后、marker 前） | 补 marker；不改 APPROVED |
| U16 | 删除 .index/ 后重建 | 版本/事件/APPROVED 从 canonical 恢复；**affected 结果不漂移**（replay 事件） |
| U17 | **INV-009**：已完成 Run 绑定旧版本，revision 后不重写 | Run 的 historical ref 仍指向 H003@v1 |
| U18 | **INV-010 机器强制**：内部代码试图产生 invalidated | schema/commit gate **硬拒绝**（`IMPACT_INVALID`） |
| U19 | impact 分类矩阵正确 | Run(committed)→superseded；TaskSlice(未执行)→stale；ResultBundle(未提交)→needs_review；Conclusion→stale |
| U20 | **rev2→rev3 后，rev2 的 receipt/history 仍有效** | 旧 revision 验证通过（不比较 live APPROVED，Sol P1-1） |
| U21 | **impact 不漂移**：rev2 后 TaskSlice 状态改变 → 删 .index 重建 | affected 结果与 rev2 提交时一致（replay 事件，Sol P1-2） |
| U22 | **多 upstream stale 聚合** | fact 按 (entity, version, upstream) 保存，不 last-write-wins（Sol P2-8） |
| U23 | 篡改版本文件后 reconcile | `HASH_MISMATCH` / `PROVENANCE_BROKEN`，不提升 |
| U24 | 普通编辑覆盖已发布版本 | `DEF_VERSION_OCCUPIED`，fail_closed |
| U25 | 并发 revision（第二个持锁） | `TX_LOCKED` |
| U26 | 工作树 dirty 时 revision | `DIRTY_WORKTREE`，零写入 |
| U27 | different-key 到达时存在旧 unresolved | `TX_INCOMPLETE`，不覆盖旧 WAL |
| U28 | 成功后 definition 被改坏 → 同 key 同 fp 重试 | replay，不访问新 basis（不变量 A） |
| U29 | 同 key + **不同 proposed bytes** | `IDEMPOTENCY_CONFLICT`（fingerprint 绑定内容，Sol P1-4） |
| U30 | structured current state 查询 | definition status/affected/history 正确 |
| U31 | **v1 bootstrap 边界**：无 APPROVED 时 revision | `DEF_NOT_FOUND`（P1-B 不负责 bootstrap，Sol P2-5） |
| U32 | 篡改 old definition bytes | 按已 committed binding 检出，非"与自己当前 hash 比较" |
| U33a | **current-pointer divergence（ref 回拨）**：v1→v2→v3 后手改 APPROVED.ref 回 v1 | `DEF_POINTER_DIVERGED`：definition status / 新 revision / reconcile 均 fail-closed，不得创建 v4（Sol rev2 P1-1） |
| U33b | **current-pointer divergence（ref 不变、approved_at/basis/entity 被篡改）** | `DEF_POINTER_DIVERGED`：exact pointer hash != latest receipt.approved_after_hash（Sol rev3 P1-3） |
| U34 | **approval 三元组四子场景（Sol rev10 P2-2）**：① live/uncommitted APR 改写 → `DIRTY_WORKTREE`；② committed APR 在新 commit 历史被改 + 新 APR 绑定新请求 → **PASS**（合法新证据）；③ committed APR 被改 + 新 APR 不绑定请求 → `APPROVAL_BINDING_MISMATCH`；④ committed Event digest ≠ 它自己 basis 的 APR bytes → `APPROVAL_EVIDENCE_MISMATCH` / `PROVENANCE_BROKEN` | ① `DIRTY_WORKTREE`；② **PASS**；③ `APPROVAL_BINDING_MISMATCH`；④ `APPROVAL_EVIDENCE_MISMATCH` / `PROVENANCE_BROKEN` |
| U40 | **fingerprint 稳定性（successor 模型）**：第一次 commit 成功后同 key 同 payload 重试 | replay 而非 IDEMPOTENCY_CONFLICT（candidate_subject=successor(expected_previous) 只依赖请求参数，Sol rev3 P1-1） |
| U41 | **historical receipt 不依赖 plan**：commit → 删 .index → reindex | 历史 COMMITTED 验证（a–k）仍成立（approved_before_hash 来自 Event，非 plan，Sol rev3 P1-2） |
| U42 | **body-only payload**：--definition-input 含 reserved identity key（entity_id/version_ref/previous/schema_version） | `DEF_PAYLOAD_MISMATCH`，零写入（Sol rev3 P2-2） |
| U43 | **changed_fields 只 diff body** | v1→v2 的 changed_fields 不含 version_ref/previous（仅 body field-path，Sol rev3 P2-3） |
| U44 | **orphan 版本不跳号**：APPROVED=v1 且 v2.yaml 为 orphan/uncommitted | 新 revision → `DEF_VERSION_OCCUPIED`（candidate_subject=v2 已被占），不 silent skip 到 v3（Sol rev3 P1-1） |
| U47 | **bootstrap tamper（首次 revision 前）**：无 P1-B history 的 entity 的 APPROVED/v1 被篡改 | 与外部 bootstrap_commit 锚定的 bytes/digest 不一致（BOOTSTRAP.yaml 是 metadata 非 trust root，Sol rev6 P2-4）→ `DEF_POINTER_DIVERGED` / `PROVENANCE_BROKEN` |
| U48 | **identity mismatch（CLI）**：--definition H004 + --expected-previous H003@v1 | `DEF_IDENTITY_MISMATCH`，零写入（Sol rev4 P1-2） |
| U49 | **change_type 数组 canonicalization**：[scope_change, population_change] 与逆序视为同一请求 | fingerprint/approval 一致，不因 CLI 顺序不同产生冲突（Sol rev4 P2-2） |
| U50 | **staged definition 内部 identity 错误**：staged 文件内 version_ref/previous 被故障注入改错（hash 与 plan 随错误一致） | commit gate 必须 `DEF_IDENTITY_MISMATCH`（Sol rev5 P1-1） |
| U51 | **crash 恢复 basis 守恒**：crash 于 APPROVED 后、receipt 前，随后 HEAD 移动/previous 被改 | `STALE_BASIS` / `NEEDS_RECONCILE`，不得在新 basis 补 receipt（Sol rev5 P1-2） |
| U52 | **missing APPROVED**：有 committed history 的 entity 的 APPROVED.yaml 被删除 | `DEF_POINTER_DIVERGED` / `PROVENANCE_BROKEN`（Sol rev5 P2-4） |
| U53 | **approval 未提交进 basis commit**：APR 文件仅存在于工作树、未进入 basis_git_commit | `APPROVAL_BINDING_MISMATCH`（PRE-GATE reject，zero canonical mutation；POST/COMMIT reconcile 层才用 `APPROVAL_EVIDENCE_MISMATCH`，Sol rev7 P2-2） |
| U54 | **lineage corruption（v0→v2）**：Event+definition 同时被故障注入为 subject=v2, previous=v0，hash/receipt 随错误一致 | `DEF_IDENTITY_MISMATCH` / invalid receipt（Event.subject == successor(Event.previous) 破坏，Sol rev6 P1-2） |
| U55 | **Git clean 收窄漏洞**：v2 成功→外部只 commit APPROVED、v2 的 Definition/Event/receipt 保持 untracked→尝试 v3 | `DIRTY_WORKTREE`（完整 clean 要求 untracked canonical 文件也被禁止，Sol rev7 P1-1），zero canonical mutation |
| U45 | **stale_reasons 结构化+total order** | reason_code 闭集（P2-3）；排序 (upstream_revision, canonical(change_type), reason_code, via_relation) 严格全序，无 detail 字段（Sol rev5 P2-2 修正） |
| U46 | **latest_impact 维度分离** | review_state 与 historical_state 独立聚合，不压成单值（Sol rev3 P2-6） |
| U35 | **payload identity mismatch**：--definition-input 内含 entity_id=H004/错误 version_ref | `DEF_PAYLOAD_MISMATCH`，零写入（Sol rev2 P1-7） |
| U36 | **receipt 绑定错配**：改 receipt.event_hash/definition_hash/approved_ref_after 任一项 | `HASH_MISMATCH` / 不提升 committed（§2.3 a–k validator） |
| U37 | **impact reverse-edge 唯一性**：provenance 中 TS-0043 --uses--> H003@v1 | affected 从 root=H003@v1 沿 reverse edge 唯一确定（Sol rev2 P1-5） |
| U38 | **APPROVED@new exact bytes 恢复**：crash 于 Event→APPROVED 之间 | case1 从 staged APPROVED@new.yaml 恢复，bytes 与 plan.approved_after_hash 完全一致（Sol rev2 P1-2） |
| U39 | **直接写 derived SQLite 作科学裁决** | 被拒：structured state 是纯投影；invalidated 只能走未来 canonical flow（Sol rev2 P1-8） |

### 8.2 退出条件

1. P1-A T1a–T51 全部通过 + P1-B U1–U55 全部通过（fixture 副本 + 故障注入）；
2. revision 闭环端到端可用（含崩溃恢复、幂等、chain CAS、授权/批准、Git pin、index 重建、stale 传播）；
3. zero canonical mutation 语义在所有 REJECT 场景验证通过；
4. 无 receipt 的 DefinitionRevised 永不被当作已提交事件；
5. 删除 `.index/` 后完整重建（structured state 从事件 replay，affected 结果不漂移）；
6. 崩溃恢复不得覆盖人工修改（三态保护）；
7. **INV-009**：已完成 Run 绑定永不因 revision 重写；
8. **INV-010**：stale 永不自动升级为 invalidated，且为 schema-level hard invariant（IMPACT_INVALID）；
9. **历史 commit truth 不依赖 live APPROVED**（未来 pointer 变化不破坏旧 revision）；
10. impact decision 在 commit 前确定，materialize 只 replay；
11. 全部机器生成文件使用 canonical hash（跨序列化一致）；
12. fixture 原始工作树与 P0/P1-A Git 历史完全不变；
13. 未接 Pi、未碰真实目录、不迁移草稿定义、不修改 CURRENT。
14. **current-pointer invariant**：live APPROVED.ref == 最新 committed DefinitionRevised 的 approved_ref_after（U33a）；且 exact pointer hash == latest receipt.approved_after_hash（U33b）。
15. **approval evidence durable pin**：approval_ref + approval_digest 持久化，authority 是 (basis_git_commit, approval_ref, approval_digest) 三元组（U34）。
16. **payload identity binding**：--definition-input body-only，包装后 entity/version/previous 与自动分配一致（U35/U42）。
17. **invalidated 无 canonical write path**：structured state 纯投影，人工裁决走未来 canonical flow（U39）。
18. **fingerprint 稳定**：candidate_subject = successor(expected_previous)，same-key retry 不因版本推进变 conflict（U40）。
19. **历史验证不依赖 plan**：删 .index 后 a–k validator 仍成立（U41）；orphan 版本不跳号（U44）。
20. **staged definition 内部 identity**：entity_id/version_ref/previous 与 plan/Event 精确绑定（U50）。
21. **crash 恢复 basis 守恒**：恢复时 HEAD == basis 且 previous hash == plan，否则 STALE_BASIS（U51）。
22. **missing APPROVED 纳入 divergence**：有 committed history 的 entity 缺 APPROVED → fail-closed（U52）。
23. **approval basis-pinned**：approval 必须存在于 basis commit，live/untracked 不可用（U53）。
24. **lineage successor 守恒**：Event.subject == successor(Event.previous)，防 v0→v2 corruption（U54）。
25. **basis 必须是完整 as-of snapshot**：predecessor 必须在 basis_git_commit 中，untracked canonical 文件不得用于 revision（U55）。

---

## 9. 明确不做（P1-B）

- semantic retrieval / RAG（P1-C）
- 自动科学结论更新 / 自动 reviewer
- 把 stale 自动裁决为 invalidated（INV-010；人工科学裁决，且事件 validator 硬拒绝）
- **invalidated 的 canonical write path**（P1-B 只声明 reserved state；未来通过 HumanDecision /
  ConclusionInvalidated canonical event/object 进入投影，禁止直接改 derived SQLite，Sol rev2 P1-8）
- **v1 bootstrap**（P1-B 只做 revision；v1 由外部受控流程创建）
- definition proposal 草稿自动迁移进 definitions/（技术方案 §10.5）
- presentation-only 语义 diff 的**自动**分类（change_type 由受控审批提供；changed_fields 是机械 diff）
- **修改 CURRENT.md**（CURRENT 若引用旧 definition，由后续机制检测，不定义为 P1-B 的 affected entity）
- 独立 definition-append 命令（仅经 revise-definition 事务）
- 多事务并发调度、分布式锁
- 自动 Git commit、自动解决 merge 冲突
- 密码学签名 / 防伪权限模型
- 掉电恢复保证
- 修改 P0/P1-A 基线、合同、现有 Git 历史
- 接入真实研究目录、Pi Extension、Worker
- 发明闭集外事件类型
