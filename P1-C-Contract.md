# P1-C Contract — Semantic Retrieval（语义检索）

> 文档性质：P1-C 实施合同（frozen contract）。内容经复核确认后，作为 Semantic Retrieval 闭环的唯一边界依据。
>
> 依据：P0-Contract.md（§13 P1-06、§14 开发者约束、§3 QueryResult schema）、
> P1-A-Contract.md（已冻结 rev11）、P1-B-Contract.md（已冻结 rev11）、
> 技术方案 §10、PRD §9.5（Layer 5）、设计方案 §7（Layer 5：Semantic Retrieval / RAG），
> 及 Sol 审核（延续持久会话 6a950f42：rev1 NO-GO → rev2 按 3 P1 + 6 P2 + 2 P3 修订）。
>
> rev1（Sol 审核 NO-GO：3 P1 + 6 P2 + 2 P3）→ rev2 按全部意见修订；
> rev2（Sol 审核 NO-GO：2 P1 + 6 P2 + 2 P3）→ rev3 按全部意见修订；
> rev3（Sol 审核 NO-GO：1 P1 + 6 P2 + 2 P3）→ rev4 按全部意见修订（base_index_fresh 共享谓词、
> event frontier 进入 query freshness、generate_ngrams 单一函数、corpus/candidate 机器定义、
> score 计算顺序冻结、condition precedence、freeze.lock 继承、V19 authority 修正、disclaimer 措辞）；
> rev4（Sol 审核 NO-GO：P1=0，7 P2 + 2 P3）→ rev5 按全部意见修订（semantic_corpus predicate、
> integrity invariants 修正、path 真全序、score 整数量化 + math.fsum、schema lifecycle + NOT_INDEXED 语义、
> max_event_id validator dispatch、V1–V22 退出条件、V19 extension 清单、停用词去重）；
> rev5（Sol 审核 NO-GO：P1=0，4 P2 + 2 P3）→ rev6 按全部意见修订（query TF-IDF vector 定义、
> document_count invariant 移到 freshness 后、NOT_INDEXED/CORRUPT 唯一化、§2.2/§4 旧 score/order 清理、
> V13 determinism 作用域、N=|semantic corpus| 措辞）；
> rev6（Sol 审核 NO-GO：P1=0，4 P2 + 2 P3）→ rev7 按全部意见修订（doc_id ∈ corpus 检查移到 freshness 后、
> build-time INDEX_STALE 与 query-time SEMANTIC_INDEX_STALE 分离、LOW_CONFIDENCE 仅非空结果触发、
> semantic table schema/type corruption → CORRUPT 闭集、V15 覆盖 schema 破坏、§7 限定 ranked payload）；
> rev7（Sol 审核 NO-GO：P1=0，5 P2 + 2 P3）→ rev8 按全部意见修订（§2.4 build stale 唯一化为 INDEX_STALE、
> build/query 共用 validate_semantic_generation_structure() 结构校验器 + row-value typeof/finite 冻结、
> LOW_CONFIDENCE 阈值 authority 固定为 rank_score/score_q、score_q==0 过滤域、排序字段统一为 versioned_ref、
> |N|→N、rev6→rev7 文案）；
> rev8（Sol 审核 NO-GO：P0=0，P1=1 + P2=2 + P3=1）→ rev9 按全部意见修订（build 校验改两阶段：
> schema-only preflight（步骤 7）+ post-write 全量校验（步骤 14），首次建索引可达；
> §2.2 query 流程显式同步 §5 判定顺序 1–4（NOT_INDEXED → structural CORRUPT → STALE → invariants））；
> rev9（Sol 审核 NO-GO：P0=0，P1=0 + P2=5 + P3=4）→ rev10 按全部意见修订（§2.5 freshness 中
> build_complete 检查移归 §5 structural validator、schema compatibility 机器谓词冻结（列集合/NOT NULL/PK 精确相等）、
> metadata per-key canonical encoding 冻结、V2 明确 results=null、V1 clean-state 前置、文案同步（过滤域判定与旧字段名
> 表述不再在 changelog 中复写禁用字面量））；
> rev10（Sol 审核 NO-GO：P0=0，P1=0 + P2=4 + P3=2）→ rev11 按全部意见修订（§2.4 弱化 schema 重述与 §5 强定义同步、
> §2.5 freshness 中 algorithm_version 移出归 structural、metadata 必含键 machine grammar 与 no-event none 哨兵冻结、
> shared validator 补全各表 text 列 runtime type 谓词、V15 补全 schema 各维度、§4 明确 storage 至 JSON 映射）；
> rev11（Sol 审核 NO-GO：P0=0，P1=0 + P2=2 + P3=2）→ rev12 按全部意见修订（§2.4 step 7 schema
> 声明谓词三表逐列统一强定义、base_index_fresh 与 query freshness 引入 normalize_event_id 解决 no-event
> 空串与 null 归一化冲突、V15 增加 V15f-h 空字符串与键数目用例、新增 V23 no-event 端到端验收用例并扩充退出条件至 V1-V23）。
> rev12 复查 GO（P0=0, P1=0, P2=0, P3=0，全部闭合）→ 用户于 2026-09-03 批准正式冻结。
>
> 当前状态：**已确认（冻结，rev12，2026-09-03，Sol 审核 GO）**。后续修订需走变更流程；实现按 §7 退出条件进行。

---

## 0. 状态与范围

### 问题

现有 P0 检索内核提供四层能力（physical → lexical → structured → provenance），
但没有模糊/统计召回能力。当用户：

- 不确定具体文件名或实体 ID；
- 只记得某次讨论的片段；
- 关键词有拼写/断词差异；
- 希望"找到所有关于 X 的讨论"；

时，只能依赖 SQLite `LIKE` 子串匹配，召回率低且无排名。

### 能力定位（免责声明，Sol rev1 P3-2）

> P1-C 的 "Semantic" 是**产品层名称**。本合同当前方案采用的是
> **statistical lexical / fuzzy retrieval（TF-IDF cosine + character n-gram）**，
> 目标是 **high-recall fuzzy lexical fallback**。
>
> **不承诺**无词面重叠的 synonym / paraphrase recall（那需要 embedding，
> 被 P0-Contract §14 与零第三方依赖约束排除）。
> 未来若需 embedding 层，另立合同并单独审批，不改本冻结合同。

### 解决范围

1. **TF-IDF + cosine 排名**：对候选文档做相关性排序（纯 Python stdlib）
2. **character n-gram 模糊匹配**：拼写/断词/中英文混合变化时仍可召回
3. **分层检索策略**：exact/structured/provenance 永远是 authority path；semantic 只做 candidate discovery + ranking
4. **索引一致性协议**：semantic 索引绑定 P0 source watermark，stale 即 fail-closed

### 明确不在 P1-C 范围

- 引入 embedding 模型 / 向量数据库 / 外部 LLM / RAG 框架
- **BM25**（rev2 只冻结 TF-IDF；BM25 若需要另立 revision，避免两套 ranking semantics，Sol rev1 P3-1）
- **topic clustering / 主题聚类**（rev1 的"语义分组"承诺删除）
- **paragraph-level retrieval**（rev2 只做 document-level；段落级另立 revision）
- 替代结构化查询：identity / exact version / ExperimentSpec / Run status / historical provenance / Definition version **永不**由 semantic 回答
- 自动更新 CURRENT.md / events / definitions
- 修改 P0/P1-A/P1-B 冻结合同、基线、fixture 原始树、P0 authority 枚举语义
- 接入真实研究目录、Pi Extension、Worker

---

## 1. 真源和物理落点

| 层 | 物理位置 | 性质 |
|---|---|---|
| **P0 派生索引** | `fixture/.index/research.sqlite`（documents / entities / index_metadata） | 复用，不修改 schema |
| **semantic terms 表** | 同库 `terms(term, doc_id, tf)` | 派生 D1，可重建 |
| **semantic ngrams 表** | 同库 `ngrams(ngram, doc_id)` | 派生 D1，可重建 |
| **semantic metadata** | 同库 `semantic_metadata(key, value)` | 派生 D1，含 source watermark 绑定 |
| **检索结果缓存** | 无 | 每次查询实时计算 |

### 关键规则

> 1. semantic 全部表是派生数据（D1），删除 `.index/` 后可完整重建；真源仍是 canonical 文件。
> 2. SQLite 不是唯一 source of truth（P0 不变量）；semantic 表更不是。
> 3. **semantic 不引入新 authority**（Sol rev1 P1-1）：semantic 查询结果的
>    `authority` 仍是 `"derived"`；语义模式通过新增字段表达（见 §4）。
> 4. `content_hash` / `git_commit` / `versioned_ref` / `status` 一律沿用 P0 既有
>    canonical/derived metadata 计算，**绝不由 semantic score 推断**。
> 5. semantic 与 structured/provenance 结论冲突时，后者权威优先。

---

## 2. Retrieval 策略

### 2.1 路由闭集表（closed table，Sol rev1 P2）

**唯一权威路由表**；实现不得自行扩展 semantic 触发面。

| 查询形态 | 是否走 semantic | 说明 |
|---|---|---|
| `query --entity X` | **否** | identity 精确查询，authority path |
| `query --doc-type / --status / --raw` | **否** | 结构化过滤，authority path |
| `query --text T`（无 `--semantic`） | **否** | P0 lexical LIKE，行为完全不变 |
| `query --text T --semantic` | **是** | 唯一 semantic 入口 |
| `sources <owner>` | **否** | provenance，禁止 semantic |
| `trace <entity>` | **否** | causality，禁止 semantic |
| `history` | **否** | historical，禁止 semantic |
| `reconcile` / `index` | **否** | 非检索命令 |
| `query --version / --versioned-ref / exact hash + --semantic` | **否** | exact version 永不 semantic（V3） |
| `query --text T --semantic --status stale` 等混合 flags | **structured wins** | `--status/--doc-type/--raw` 等结构化 selector 与 `--text --semantic` 共存时，结构化路径优先，semantic 被忽略（V3） |

> 违反本表（例如 `--entity` 带 `--semantic` 时改用 semantic）→ 实现必须忽略 semantic
> 并保持结构化路径（测试 V3）。

### 2.2 semantic 查询流程

```text
1. 按 §5 判定顺序 step 1：三张 semantic 表全部不存在 → SEMANTIC_NOT_INDEXED
2. 按 §5 判定顺序 step 2：调用 validate_semantic_generation_structure() →
   任一失败 → SEMANTIC_INDEX_CORRUPT（fail_closed，results=null）
3. 按 §5 判定顺序 step 3：§2.5 freshness 校验 → 任一不符 → SEMANTIC_INDEX_STALE
   （fail_closed，results=null）
4. 按 §5 判定顺序 step 4：fresh 后校验 current-corpus invariants →
   任一不一致 → SEMANTIC_INDEX_CORRUPT（fail_closed，results=null）
5. 分词查询串（§2.3 tokenizer）
6. 若 token 集为空 → SEMANTIC_EMPTY_QUERY 语义：返回空 results，status=success，非错误
7. 计算 cosine(TF-IDF) 得分
8. 计算 n-gram 命中率得分
9. final_score = 0.7 × cosine + 0.3 × ngram_ratio
10. 排序：按 §2.3 的 score_q（整数量化）降序 + entity_id/versioned_ref/path 真全序
11. 全部 rank_score < 200_000_000（对应约 0.2 的量化阈值；authority = rank_score/score_q，不换算回 final_score 判断）→ 若 returned results 非空，仍返回结果并附 SEMANTIC_LOW_CONFIDENCE warning；
    candidate 为空或全部被 score_q == 0 剔除 → results=[]，不产生 LOW_CONFIDENCE（Sol rev6 P2-3）
12. 输出 envelope：authority="derived"，retrieval_mode="semantic"
```

> **判定顺序唯一性（Sol rev8 P2-1 闭合）**：§2.2 步骤 1–4 与 §5 判定顺序 1–4 完全一致，
> 单一判定链（NOT_INDEXED → structural CORRUPT → STALE → invariants），实现不得另起顺序。

### 2.3 唯一确定算法（determinism contract，Sol rev1 P2-1）

**冻结以下全部细节；任何偏离都是合同违约。**

#### Tokenizer

**两个概念分离**（Sol rev2 P2-1）：

- `tokenize(text)` → 保留重复的 token **sequence**（用于 `raw_tf` 计数）
- `query_unique_terms` → 首次出现顺序去重（仅用于 `cosine` 的 query vector 枚举）

```text
tokenize(text) 步骤（保留重复）：
1. Unicode NFKC 归一化
2. 转小写（ASCII）
3. 切分：按 [^a-z0-9_\u4e00-\u9fff]+ 切
4. CJK 段：对连续 CJK 串生成全部相邻 2-char bigram（如 "长上下文" → 长上, 上下, 下文）
   CJK bigram 保留重复（"上上" 出现两次则 raw_tf 计数 2）
5. 非 CJK token：长度 < 2 者丢弃
6. 停用词过滤（下表，精确匹配，大小写已归一）
7. 输出 token sequence（保留重复，保留原始顺序）

query_unique_terms（仅 query 用）：
- 对 tokenize(text) 结果按首次出现顺序去重
- 用于 cosine 的 numerator 枚举（Σ_t∈q）
```

**raw_tf(t, d) 的计数来源**：从 `tokenize(doc_text)` 的完整 output sequence 中
计数词 t 的出现次数（非去重序列）。

**停用词闭集**（不可增删；扩充需 revision）：

```text
the a an of to in is are was were be been being and or but if then than
that this these those it its as at by for from on with without do does did
not no yes can could will would should may might must have has had
i you he she we they me him her us them your their my our
what which who whom when where why how all any both each few more most
other some such only own same so too very s t just now
的 了 和 是 在 我 有 也 就 不 人 都 一 一个 上
```

#### TF-IDF

**document 与 query 使用对称的同一套权重定义**（Sol rev5 P2-1 闭合）：

```text
# document side
raw_tf(t, d)      = 词 t 在 tokenize(doc_text) 中出现次数

tf(t, d)          = 0                     若 raw_tf == 0
                  = 1 + ln(raw_tf)        否则（sublinear）

N                 = |semantic corpus| = document_count
                    （zero-token 文档也计入 N，即使无 terms 行；不是 COUNT(DISTINCT terms.doc_id)）
df(t)             = terms 表中含 t 的 doc_id 数
idf(t)            = ln((N + 1) / (df(t) + 1)) + 1        # 平滑，恒 > 0
w(t, d)           = tf(t, d) × idf(t)
||d||₂            = sqrt(math.fsum(w(t,d)² for t in doc terms))

# query side（与 document 对称，Sol rev5 P2-1）
raw_tf(t, q)      = 词 t 在 tokenize(query_text) 中出现次数

tf(t, q)          = 0                     若 raw_tf == 0
                  = 1 + ln(raw_tf)        否则（与 document 同一 sublinear）

idf(t)            = 与 document 共用同一个 idf(t)（corpus 计算）
w(t, q)           = tf(t, q) × idf(t)
||q||₂            = sqrt(math.fsum(w(t,q)² for t in query_unique_terms))

cosine(q, d)      = math.fsum(w(t,q)·w(t,d) for t in query_unique_terms)
                    / (||q||₂ × ||d||₂)
                    # 全非负 → cosine ∈ [0, 1]
                    # ||q||₂ 或 ||d||₂ == 0 → cosine = 0
```

> **归一化保证**：cosine 天然 ∈ [0,1]，不使用 rev1 的 `Σtfidf / query_length`
> （该式无上界，与 score ∈ [0,1] 矛盾，Sol rev1 P2-1）。

#### n-gram 模糊匹配

**generate_ngrams(text)：document 与 query 共享的唯一函数**（Sol rev2 P2-3 + rev3 P2-2 闭合）：

```text
generate_ngrams(text):
  1. 对原始文本（不经 tokenizer 变换）做 NFKC 归一化 + ASCII lowercase
  2. 按 [^a-z0-9_\u4e00-\u9fff]+ 切分
  3. 每个连续 CJK 串（长度 >= 2）：直接对该原串生成全部相邻 character 2-gram 与 3-gram
     （如 "长上下文" → 2-gram: 长上/上下/下文；3-gram: 长上下/上下文）
     —— 注意：不是对 tokenizer 的 CJK bigram 输出再生成（避免两套结果）
  4. 每个非 CJK token（长度 >= 2）：生成全部相邻 character 2-gram 与 3-gram
  5. 去重：同一 ngram 多次出现只保留一次
  6. 输出：去重后的 ngram 集合

Q_ng   = generate_ngrams(query_text)
D_ng   = generate_ngrams(doc_text)，存储于 ngrams 表
ngram_ratio(q, d) = |Q_ng ∩ D_ng| / |Q_ng|
                    # 分母固定为查询 n-gram 集合大小 → ∈ [0, 1]
                    # |Q_ng| == 0 → ratio = 0
```

> 冻结语义：document 与 query 使用同一 `generate_ngrams`，禁止对两侧使用不同规则。

#### semantic corpus 与 candidate set（Sol rev2 P2-2 + rev3 P2-1/P2-4 + rev4 P2-1 机器定义）

**semantic_corpus(doc) 唯一 predicate（Sol rev4 P2-1 闭合）**：

```text
semantic_corpus(doc) iff:
  doc ∈ P0 documents 表
  AND path 后缀 ∈ 冻结 allowlist
  AND canonical bytes strict UTF-8 decode 成功

冻结 path 后缀 allowlist（不可增删；扩充需 revision）：
  .md  .yaml  .yml  .txt  .csv  .json  .log

semantic corpus =
  { doc : semantic_corpus(doc) == true }

零-token 文档（tokenize 后为空）仍计入 document_count（N），但不产生 terms/ngrams 行。

N = document_count = |semantic corpus|

df(t)   = terms 表中含词 t 的 doc_id 计数
idf(t)  = ln((N + 1) / (df(t) + 1)) + 1

candidate set =
  { doc_id : 存在至少一个 query term 的 terms 命中 }
  ∪ { doc_id : 存在至少一个 query ngram 的 ngrams 命中 }

result inclusion：
  - score_q == 0 的 candidate 不返回（按 score_q 单一 authority，Sol rev7 P2-NEW-3）
  - 默认 limit = 50（无 P0 全局 limit 时）；超出部分截断，不补页
  - candidate set 为空 → 返回空 results（非错误）
```

#### 最终得分、排序与 candidate set（Sol rev2 P2-2/P2-4 + rev3 P2-3 确定论）

**计算顺序全部冻结**（Sol rev3 P2-3 + rev4 P2-3/P2-4 闭合）：

```text
query term 遍历顺序 = query_unique_terms 中的首次出现顺序
文档 term 遍历顺序 = 该文档 terms 表中 term 的 UTF-8 字节字典序
math.log = 自然对数（底数 e）
math.sqrt = 平方根
浮点求和 primitive = math.fsum（禁止 sum()/手工累加，Sol rev4 P2-4A）
全部浮点计算按 IEEE-754 double precision

final_score(q, d) = 0.7 × cosine(q, d) + 0.3 × ngram_ratio(q, d)
                    # 权重固定；∈ [0, 1]

score_q = round(final_score * 1_000_000_000)     # 整数量化到 1e-9（Python round half-even）
rank_score = score_q                              # 排序仅使用整数量化值
排序键（真全序，Sol rev4 P2-3）：
  1. rank_score 降序
  2. entity_id 升序（UTF-8 字节字典序）
  3. versioned_ref 升序（同上；缺省视为空串）
  4. path 升序（UTF-8 字节字典序）       # 终键：同实体多 path 同分时消除歧义

API 输出 score = JSON number（score_q / 1e9，不要求固定尾零位；Sol rev4 P2-4B）

置信阈值：仅当 returned results 非空 且所有 rank_score < 200_000_000（对应约 0.2 的量化阈值；authority = rank_score/score_q，不换算回 final_score 判断）
→ SEMANTIC_LOW_CONFIDENCE warning。
Candidate 为空或全部候选被 score_q == 0 剔除 → results=[]，不产生 LOW_CONFIDENCE（Sol rev6 P2-3）。
```

N == 0 时 cosine = 0；|Q_ng| == 0 时 ngram_ratio = 0。

### 2.4 semantic 索引构建（原子全量重建，Sol rev1 P1-3 + rev3 P2-6 lock 继承）

**必须在单个 SQLite transaction 内完成，且必须继承 P1-A 的全局 mutation lock**（Sol rev3 P2-6）：

```text
1. acquire .researchctl/locks/freeze.lock（P1-A 全局 mutation lock，防止并发 reindex/reset）
2. BEGIN IMMEDIATE;
3. 校验 base_index_fresh(root) == true（§2.5）
    不满足 → ROLLBACK → INDEX_STALE（build-time 固定复用 P0 码，Sol rev6 P2-2 + rev7 闭合）→ release lock，不写任何行
4. CREATE TABLE IF NOT EXISTS terms (term TEXT NOT NULL, doc_id TEXT NOT NULL, tf REAL NOT NULL, PRIMARY KEY (term, doc_id));
5. CREATE TABLE IF NOT EXISTS ngrams (ngram TEXT NOT NULL, doc_id TEXT NOT NULL, PRIMARY KEY (ngram, doc_id));
6. CREATE TABLE IF NOT EXISTS semantic_metadata (key TEXT NOT NULL PRIMARY KEY, value TEXT);
7. **schema-only 前置校验（Sol rev8 P1 + rev9 P2-NEW-2 + rev11 P2-REV11-1 闭合）**：对已有表检查
   schema 声明是否与 §2.4 冻结 schema 完全兼容：
   terms / ngrams / semantic_metadata 每张表均要求**列集合精确相等**，且每一列的
   **name / declared type / NOT NULL / PRIMARY KEY** 与冻结 DDL 精确一致；
   **不允许额外列、缺失列或任何上述属性差异**；**不检查数据行值/metadata 内容**；
   不满足 → ROLLBACK → SEMANTIC_INDEX_CORRUPT → release lock，不写任何行
   （CREATE IF NOT EXISTS 不修正已存在坏表；首次构建时三表为新创空表，此项必过，
   不会因 metadata 未写入而误判 CORRUPT）
8. DELETE FROM terms;
9. DELETE FROM ngrams;
10. DELETE FROM semantic_metadata;
11. 从 documents 表读全部 semantic_corpus 文档，按 §2.3 分词，插入完整 terms
12. 插入完整 ngrams（按 §2.3 generate_ngrams）
13. 写 semantic_metadata（含 build_complete="1" 与 source watermark），最后一步
14. **post-write 全量校验（Sol rev8 P1 闭合）**：写完后调用 §5
    validate_semantic_generation_structure() 全量结构校验器（schema / metadata 完整性 /
    row runtime types / finite numeric / 重复行），此时 metadata 已含 build_complete="1"
    与 watermark，必通过；任一失败 → ROLLBACK → SEMANTIC_INDEX_CORRUPT → release lock
15. COMMIT;
16. release freeze.lock
```

- 失败/崩溃 → ROLLBACK → 查询只能看到**完整旧 generation**或**完整新 generation**，
  绝不出现半代索引。
- `build_complete` 只在同一 transaction 内最后写入，作为 generation 完整标记。
- 文档从 corpus 删除后，其 terms/ngrams 行随全量 DELETE 一并清除，**不得残留**（V12）。
- **两阶段校验（Sol rev8 P1 + rev10 P2-REV10-1 闭合）**：build 使用两类校验，避免首次构建不可达：
  1. **schema-only preflight（步骤 7）**：检查已有三表 schema 声明是否与 §2.4 冻结 schema 完全兼容
     （列集合精确相等：name/declared type/NOT NULL/PRIMARY KEY；不允许额外列、缺失列或约束差异），
     不查数据/元数据内容；首次构建三表新创必过，坏 schema 表被拦为 CORRUPT。
  2. **post-write 全量校验（步骤 14）**：写完后调用 §5 共享校验器
     `validate_semantic_generation_structure()`（含 metadata 完整性、row runtime types、
     finite、重复行），此时 metadata 已含 build_complete="1" 与 watermark，必通过；
     用于防止 build 自身写坏数据。
- **共享结构校验器（query 侧必调，build 侧 post-write 调用）**：
  `validate_semantic_generation_structure()` 的检查项：
  - schema 声明与 §2.4 冻结 schema 完全兼容（列集合精确相等：name/declared type/NOT NULL/PRIMARY KEY；
    不允许额外列、缺失列或约束差异）；
  - 行值 runtime type 谓词（针对 SQLite 非 STRICT 表特性逐行验证，Sol rev10 P2-REV10-4 闭合）：
    - `terms` 表每一行：`typeof(term) == 'text' ∧ length(term) > 0`，`typeof(doc_id) == 'text' ∧ length(doc_id) > 0`，`typeof(tf) ∈ {"integer","real"} ∧ math.isfinite(tf) ∧ tf > 0`；
    - `ngrams` 表每一行：`typeof(ngram) == 'text' ∧ length(ngram) > 0`，`typeof(doc_id) == 'text' ∧ length(doc_id) > 0`；
    - `semantic_metadata` 表每一行：`typeof(key) == 'text' ∧ length(key) > 0`，`typeof(value) == 'text'`；
  - metadata 必含键精确为 6 键（不允许缺失键或额外键），且每个 value 编码符合 §2.5 per-key canonical encoding；
  - terms/ngrams 中无 (term,doc_id)/(ngram,doc_id) 重复行；
  任一失败统一映射 `SEMANTIC_INDEX_CORRUPT`，任何 SQLite 原生异常（如
  sqlite3.OperationalError）都归一化为该码，不得泄漏到调用方。

**NOT_INDEXED 语义**（Sol rev4 P2-5 + rev5 P2-3 唯一化）：仅当 terms / ngrams / semantic_metadata
三张表全部不存在时为未构建（NOT_INDEXED）；schema 已初始化但缺少完整 generation 标记
（含 build_complete != "1"）→ CORRUPT（不存在"schema 已建但从未 build"的独立生命周期）。

### 2.5 source watermark 绑定与 stale 协议（Sol rev1 P1-2 + rev2 P1-2 + rev3 P1 闭合）

`semantic_metadata` 必含键（value 列类型为 TEXT，全量归 §5 structural validator 校验）：

```text
algorithm_version        = "semantic-tfidf/v1"          # 精确字符串匹配
source_scan_fingerprint  = 正则 ^sha256:[0-9a-f]{64}$  # 带 sha256: 前缀的 64 位小写十六进制
source_last_event_id     = 正则 ^(?:EV-[0-9]{6}|none)$  # 有事件为 EV-xxxxxx，无事件为 "none" 哨兵
source_index_built_at    = 正则 ^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$ # RFC 3339 / ISO-8601 时间戳
document_count           = 正则 ^(?:0|[1-9][0-9]*)$    # 十进制非负整数（无前导零）
build_complete           = "1"                         # 精确字符串
```

> **per-key canonical encoding 与机器校验（Sol rev9 P2-NEW-3 + rev10 P2-REV10-3 + rev11 P2-REV11-2 闭合）**：
> 1. **格式与值域**：各 key 必须满足上述独立机器文法（machine grammar）。`typeof(value) != 'text'`、
>    缺少任一指定键、存在额外未定义键、或任一键值不符合上述文法正则 → 由 `validate_semantic_generation_structure()`
>    统一判为 `SEMANTIC_INDEX_CORRUPT`。
> 2. **无 committed Event 时的 null 哨兵编码与归一化**：
>    - 若 P0 无 committed Event（P0 last_event_id 表现为 null 或空串 `""`），`semantic_metadata.source_last_event_id`
>      必须存为规范哨兵字符串 `"none"`；
>    - 若 P0 存在 committed Event，则存为对应的 `"EV-xxxxxx"` 字符串；
>    - 统一归一化函数：`normalize_event_id(x) = null if (x is null or x == "" or x == "none") else x`；
>    - base_index_fresh 比较：`normalize_event_id(P0 index_metadata.last_event_id) == max_event_id(...)`；
>    - 查询前置校验比较：`normalize_event_id(semantic_metadata.source_last_event_id) == normalize_event_id(P0 index_metadata.last_event_id)`；
>    - JSON 序列化：在 `source_watermark.semantic` 中输出为 JSON `null`（若值为 `"none"`）或 JSON 字符串（若值为 `"EV-xxxxxx"`）。
> 3. **权责切分**：文法/类型/结构不匹配属于 structural CORRUPT；文法有效但值与当前 P0 base 不一致
>    （fingerprint/event_id/built_at 不匹配，或 base 不 fresh）属于 generation STALE。

**共享 base_index_fresh(root)（build 与 query 唯一共同前置，Sol rev3 P1 + rev11 P2-REV11-2 闭合）**：

```text
base_index_fresh(root) iff:
  P0 index_metadata.index_complete == true
  AND P0 index_metadata.drift == false
  AND P0 index_metadata.scan_fingerprint == current_fingerprint(root)
  AND normalize_event_id(P0 index_metadata.last_event_id) ==
      max_event_id(valid canonical COMMITTED events)   # 见下

normalize_event_id(x):
  null if (x is null or x == "" or x == "none") else x

max_event_id(valid canonical COMMITTED events)：
  在 canonical events 中，按事件类型使用对应的 frozen receipt validator 验证通过的 committed Event 的最大 event_id：
  - event_type == "ReportFrozen" → P1-A 的 verify_receipt（四件套验证）
  - event_type == "DefinitionRevised" → P1-B 的 verify_definition_receipt（a–k 验证）
  - 其他 event_type → 不属于 valid canonical COMMITTED frontier（Sol rev4 P2-6）
  若无任何 committed Event → 返回 null。
  （P1-A index_metadata.last_event_id 只是“已 materialize 到哪个 Event”的进度，
   可能合法落后于 canonical COMMITTED frontier；因此 base_index_fresh 必须
   直接与 canonical COMMITTED frontier 比较，不能用 materialize 进度自证。）
```

**构建前置校验**（不满足即拒绝构建，不写任何行）：

```text
base_index_fresh(root) == true
```

**查询前置校验**（单一 freshness predicate，Sol rev2 P1-2 + rev3 P1 + rev10 P2-REV10-2 + rev11 P2-REV11-2；不满足即 fail-closed）：

```text
base_index_fresh(root) == true
AND semantic_metadata.source_scan_fingerprint == P0 index_metadata.scan_fingerprint
AND normalize_event_id(semantic_metadata.source_last_event_id) ==
    normalize_event_id(P0 index_metadata.last_event_id)
AND semantic_metadata.source_index_built_at == P0 index_metadata.index_built_at
```

任一不符 → `SEMANTIC_INDEX_STALE`，`status="fail_closed"`，`results=null`，
**绝不返回旧 semantic 结果**（继承 P0 INDEX_STALE + fail_closed，杜绝 FM-06 "Index 成为第二真源"）。

> **判定权责切分（Sol rev9 P2-NEW-1 + rev10 P2-REV10-2 闭合）**：本节 freshness 只负责 **generation freshness**
> （source watermark 与 P0 base 一致）。
> - `build_complete == "1"` 与 `algorithm_version == "semantic-tfidf/v1"` **不在此处检查**——它们属于结构完整性与规范编码，
>   完全由 §5 判定 step 2 的 `validate_semantic_generation_structure()` 管理（任一不符 → `SEMANTIC_INDEX_CORRUPT`，不是 STALE）；
> - §5 判定链严格按由高到低顺序执行：structural CORRUPT 先命中后不再走到本节的 STALE；
> - 本节仅在 structural validation 已 PASS 后执行，专职校验 generation 同步性。

> **P0 base 自身健康也必须验证**（Sol rev2 P1-2）：即使 filesystem bytes 未再变化，
> 若 P0 reconcile 已把 `drift=true`，semantic query 仍必须 fail_closed——
> semantic 不得从 P0 已声明不可靠的 derived index 返回结果。

> **last_event_id 的机器唯一表述**：`normalize_event_id(P0 last_event_id) == max_event_id among valid canonical
> COMMITTED events`（按 receipt 验证通过的 committed Event 的最大 event_id），
> 不使用 "latest materialized"（避免自证退化的解读）。

> 反例（rev1 漏洞，rev2 必须挡住）：canonical 文件从 C1 改到 C2 → P0 index 已 stale
> 但未 reindex → 此时 `index --semantic` 必须被前置校验拒绝；即使绕过，
> `query --semantic` 的查询前置校验也会因 fingerprint 不符而 fail-closed。

---

## 3. 命令形态

```text
researchctl index --semantic                    # 原子全量重建 semantic 索引
researchctl query --text <T> --semantic         # semantic fallback 检索
researchctl query --text <T>                    # P0 lexical（行为不变）
researchctl query --entity <X> --semantic       # semantic 被忽略，走结构化路径
```

- `index --semantic` 是**唯一**写 `.index/` 中 semantic 表的入口；只写派生数据，
  不触碰 T0–T3 canonical 文件（V8 hash assertion，Sol rev2 P3-2 修正）。
- 不新增独立 daemon / 常驻进程 / 缓存文件。

---

## 4. 输出格式（backward-compatible extension，Sol rev1 P1-1 + rev2 P1-1）

**P0 QueryResult 字段一个都不得删除、改名、改变类型或改变语义**。
SemanticQueryResult = P0 QueryResult + optional 新增字段。

### P0 QueryResult（冻结 §3，引用）

```json
{
  "query_id": "query-...",
  "query_type": "current",
  "as_of": "2026-09-01T10:00:00+08:00",
  "status": "success",
  "authority": "derived",
  "source_watermark": {
    "index_built_at": "...",
    "last_event_id": "EV-000001",
    "scan_fingerprint": "sha256:...",
    "index_complete": true,
    "drift": false
  },
  "results": [...],
  "warnings": [],
  "errors": [],
  "error_semantic": null
}
```

### P0 ResultItem（冻结 §3，引用）

```json
{
  "entity_id": "R051",
  "versioned_ref": null,
  "path": "raw/EXP-017/R051/execution.log",
  "content_hash": "sha256:...",
  "git_commit": "abc123...",
  "section": null,
  "status": {...},
  "relation_type": null,
  "is_stale": false,
  "is_available": true
}
```

### SemanticQueryResult（P0 + optional 新增字段）

```json
{
  "query_id": "query-...",
  "query_type": "current",
  "as_of": "2026-09-01T10:00:00+08:00",
  "status": "success",
  "authority": "derived",
  "retrieval_mode": "semantic",
  "ranking_authority": "advisory",
  "source_watermark": {
    "index_built_at": "...",
    "last_event_id": "EV-000001",
    "scan_fingerprint": "sha256:...",
    "index_complete": true,
    "drift": false,
    "semantic": {
      "algorithm_version": "semantic-tfidf/v1",
      "source_scan_fingerprint": "sha256:...",
      "source_last_event_id": "EV-000001",
      "source_index_built_at": "2026-09-01T10:00:00+08:00",
      "document_count": 12,
      "build_complete": true
    }
  },
  "results": [
    {
      "entity_id": "R051",
      "versioned_ref": null,
      "path": "raw/EXP-017/R051/execution.log",
      "content_hash": "sha256:...",
      "git_commit": "abc123...",
      "section": null,
      "status": {...},
      "relation_type": null,
      "is_stale": false,
      "is_available": true,
      "score": 0.850000000
    }
  ],
  "warnings": [],
  "errors": [],
  "error_semantic": null
}
```

### 分层语义

```text
authority          = derived           # 沿用 P0 枚举，不新增
retrieval_mode     = semantic          # 新增可选字段；lexical 路径缺省不出现（V17）
ranking_authority  = advisory          # 排名是建议性，非真值（P0 original 字段不受影响）
```

- `score` 仅在 `retrieval_mode="semantic"` 时出现；值为 **JSON number**，等于 `score_q / 1_000_000_000`，
  不要求尾随零（Sol rev5 P2-4B）。
- 非 semantic 查询的 envelope 与 P0 完全一致，所有新增字段**缺省不出现**（V17）。
- lexical authority 完全沿用 P0 原结果语义（`canonical/derived/unresolved`），不因 `--semantic` 开关改变。

### source_watermark.semantic 字段与存储映射（Sol rev10 P3-REV10-2 闭合）

从 SQLite `semantic_metadata` 表到 JSON envelope `source_watermark.semantic` 的 canonical 映射规则：

| 字段 | SQLite 存储类型与格式 | JSON 输出类型 | 映射规则 |
|---|---|---|---|
| `algorithm_version` | TEXT，精确 `"semantic-tfidf/v1"` | JSON string | 原样输出为 JSON string |
| `source_scan_fingerprint` | TEXT，正则 `^sha256:[0-9a-f]{64}$` | JSON string | 原样输出为 JSON string |
| `source_last_event_id` | TEXT，正则 `^(?:EV-[0-9]{6}\|none)$` | JSON string \| null | 若值为 `"none"` 输出为 JSON `null`；否则原样输出为 JSON string（如 `"EV-000001"`） |
| `source_index_built_at` | TEXT，RFC 3339 时间戳 | JSON string | 原样输出为 JSON string |
| `document_count` | TEXT，正则 `^(?:0\|[1-9][0-9]*)$` | JSON number (integer) | `int(document_count)`，数值输出为 JSON integer（非 string） |
| `build_complete` | TEXT，精确 `"1"` | JSON boolean | 若值为 `"1"` 输出为 JSON `true`；非 `"1"` 属于 CORRUPT 不到此处 |

---

## 5. 语义条件码闭集（condition code closed set，Sol rev2 P2-6 + rev3 P2-5 precedence 冻结）

**判定顺序**（由高到低，命中即止，Sol rev6 P2-1/P2-2/P2-3/P2-4 + rev7 5P2 闭合）：

```text
1. 三张 semantic 表（terms / ngrams / semantic_metadata）**全部不存在**
   → SEMANTIC_NOT_INDEXED
2. 其余情况 / structural CORRUPT（不依赖当前 corpus 数量）＝
   **validate_semantic_generation_structure() 任一失败**（§2.4 冻结；query 侧必调，build 侧 post-write 调用，Sol rev7 P2-4 + rev8 P1 + rev10 P2-REV10-1/P2-REV10-4 闭合）：
   - 仅部分表存在 / metadata 必含键不精确为 6 键（缺失键或存在额外键）/ 任一 metadata value 不符合 §2.5 per-key canonical encoding / build_complete 不是精确字符串 "1"
   - semantic 三表 schema 与 §2.4 冻结 schema 不完全兼容（列集合不精确相等 / declared type 不符 / NOT NULL 不符 / PRIMARY KEY 不符 / 存在额外列或缺失列）
   - 任一行值不满足 runtime type 谓词（typeof(term/ngram/doc_id/key/value) != 'text'，或字符串长度为 0，或 typeof(tf) ∉ {"integer","real"}，或 not math.isfinite(tf)，或 tf <= 0）
   - terms/ngrams 中 (term,doc_id)/(ngram,doc_id) 重复
   - 读取 semantic tables 时出现结构/解码错误（含 sqlite3.OperationalError，归一化后不得泄漏）
   → SEMANTIC_INDEX_CORRUPT
3. 结构完整，但 §2.5 查询前置校验任一不符（含 base_index_fresh 失败）
   → SEMANTIC_INDEX_STALE（query-time generation stale）
4. **仅当 generation fresh 后**才校验（Sol rev6 P2-1/P2-4）：
   - document_count == |current semantic_corpus|
   - 每一 terms.doc_id ∈ current semantic_corpus
   - 每一 ngrams.doc_id ∈ current semantic_corpus
   任一不一致 → SEMANTIC_INDEX_CORRUPT
5. 全部通过 → valid（进入 tokenizer/query）
```

> **修正说明（Sol rev5 P2-2 + rev6 P2-1）**：document_count 与 terms/ngrams.doc_id ∈ corpus 的检查
> 必须放在 **freshness PASS 之后**（步骤 4），与当前 generation fresh 后的 current semantic_corpus
> 比较。若在 freshness 前比较，正常 stale generation（canonical 新增/删除文档 → P0 reindex）
> 会被误判 CORRUPT 而无法走到 STALE。zero-token / stopword-only 文档计入 corpus 但不产生
> terms 行，合法。

| 码 | 分类 | 效果 |
|---|---|---|
| `SEMANTIC_NOT_INDEXED` | blocking error | `status="fail_closed"`，`results=null`，提示先 `index --semantic` |
| `SEMANTIC_INDEX_CORRUPT` | blocking error | `status="fail_closed"`，`results=null` |
| `SEMANTIC_INDEX_STALE` | blocking error | `status="fail_closed"`，`results=null` |
| `SEMANTIC_EMPTY_QUERY` | empty query（非错误） | `status="success"`，`results=[]`，`error_semantic`/`warnings` 中不写码 |
| `SEMANTIC_LOW_CONFIDENCE` | warning | `status="success"`，`warnings[]` 含该码，结果正常返回 |

- blocking error 在 `error_semantic` 存放码值。
- **build-time base stale → 复用 P0 `INDEX_STALE`（Sol rev6 P2-2 固定，不新造码）**；
  query-time generation stale → `SEMANTIC_INDEX_STALE`。
- 全部码为 P1-C 新增闭集；不得发明闭集外语义条件码。

---

## 6. 测试矩阵（全部在 fixture 副本；不修改 P0/P1-A/P1-B 基线）

| # | 场景 | 期望 |
|---|---|---|
| V1 | **clean-state 首次构建**：fixture 中 semantic 三表全部不存在 → `index --semantic` → success → 查询已知主题词 | 相关文档排名靠前，score ∈ [0,1] |
| V2 | 未建索引即 `--semantic` | `SEMANTIC_NOT_INDEXED`，`status="fail_closed"`，`results=null` |
| V3 | `--entity` 带 `--semantic` | semantic 被忽略，走结构化路径，authority 不变 |
| V4 | 拼写/断词偏差（n-gram） | 仍可召回 |
| V5 | 全低相关查询 | 结果返回 + `SEMANTIC_LOW_CONFIDENCE` warning |
| V6 | 删 `.index/` 后重建 | 排名与 tie order 完全一致（幂等） |
| V7 | 空/纯停用词查询 | `SEMANTIC_EMPTY_QUERY` 语义：空 results，success |
| V8 | **canonical hash assertion**：`index --semantic` 前后对 T0–T3 + events + definitions 全量文件 hash | **逐文件完全不变**（可机验，非"不修改"泛述） |
| V9 | **stale 洗白反例**：改 canonical → 不 reindex → `index --semantic` | 构建被拒（`INDEX_STALE`），零 semantic 写入 |
| V10 | **查询期 stale**：建好 semantic 索引后改 canonical 并 reindex P0 | `query --semantic` → `SEMANTIC_INDEX_STALE`，`results=null` |
| V11 | **partial rebuild 不可见**：构建中途注入失败（模拟 crash/异常） | ROLLBACK；查询只见完整旧 generation，绝不见半代 |
| V12 | **删除文档无残留**：删一个文档 → 重建 → 查其独有 n-gram | 不再命中（terms/ngrams 无残留行） |
| V13 | **determinism**：同一 corpus 重复构建 + 重复查询 | ranked semantic payload（ordered [(entity_id, versioned_ref, path, score_q)]）逐字节/逐值一致（**不要求完整 envelope bytes 一致**——query_id/as_of 天然每次不同，Sol rev5 P2-4 作用域限定） |
| V14 | **tokenizer determinism**：Unicode NFKC / 中文 bigram / 大小写 / 停用词 | 固定输出序列，跨运行一致 |
| V15 | **corrupt index**：手工破坏 terms/ngrams/metadata（非法 tf、非有限数值、行值非文本、V15f 空字符串字段、metadata 编码非法、V15g 缺失必含键、V15h 存在额外键、重复行）以及手工破坏 semantic 表 schema 各维度（V15a 缺列、V15b 多列、V15c declared type 不符、V15d NOT NULL 不符、V15e PRIMARY KEY 不符） | 全部统一映射 `SEMANTIC_INDEX_CORRUPT`，`status="fail_closed"`，`results=null`（Sol rev6 P2-4 + rev10 P3-REV10-1 + rev11 P3-REV11-1） |
| V16 | `sources` / `trace` / `history` 加 `--semantic` | 全部忽略 semantic（closed table） |
| V17 | **向后兼容**：非 semantic 查询 envelope | 与 P0 完全一致，无新增字段出现 |
| V18 | score 边界 | 全部 ∈ [0,1]；cosine/ngram 分量各自 ∈ [0,1] |
| V19 | **lexical 与 semantic authority 区分**：`query --text T`（无 --semantic）vs `query --text T --semantic` | lexical authority 完全沿用 P0 原结果；semantic authority == derived；所有 semantic-only extension 仅为 `retrieval_mode` / `ranking_authority` / `source_watermark.semantic` / `ResultItem.score`（Sol rev3 P3-1 + rev4 P2-7C） |
| V20 | P0/P1-A/P1-B 回归 | 50/32/139/85 全通过，semantic 不影响既有行为 |
| V21 | **event frontier lag 反例**（Sol rev3 P1 回归）：P0 materialize 到 EV-10，EV-11 canonical COMMITTED 但 materialize 故障 → `query --semantic` | `SEMANTIC_INDEX_STALE`，`results=null` |
| V22 | **drift-only 反例**（Sol rev3）：filesystem 未变，P0 reconcile 把 `drift=true` → `query --semantic` | `SEMANTIC_INDEX_STALE`，`results=null`（即使 semantic source fingerprint 仍匹配，P0 自身已声明不可靠） |
| V23 | **no-event end-to-end**：无 committed Event 环境（P0 last_event_id 为 null 或 `""`）→ `index --semantic` → `source_last_event_id` 存为 `"none"`；`query --semantic` base fresh 通过；JSON envelope `source_watermark.semantic.source_last_event_id` 输出为 `null`（Sol rev11 P3-REV11-2） | 完整通过，返回成功语义结果 |

---

## 7. 退出条件

1. P0-B 50/50 + P0-C 32/32 + P1-A 139/139 + P1-B 85/85 回归全通过；V1–V23 全通过；
2. `index --semantic` + `query --text --semantic` 端到端可用；
3. **零第三方依赖**（仅 stdlib：sqlite3 / hashlib / math / re / unicodedata / collections）；
4. semantic 全部表可随 `.index/` 删除后完整重建；ranked semantic payload
   （ordered [(entity_id, versioned_ref, path, score_q)]）逐值一致（V6/V13，Sol rev6 P3-2）；
5. **不新增 authority 枚举值**：semantic 结果 `authority="derived"`，仅经
   `retrieval_mode` / `ranking_authority` 表达（V17/V19）；
6. **stale 协议生效**：构建前置 + 查询前置双重 watermark 校验，stale 一律 fail_closed
   且 `results=null`（stale 反例：V9/V10/V21/V22；no-event 状态正向验收：V23）；
7. **原子重建**：单 transaction 全量重建，崩溃/失败 ROLLBACK，绝不暴露半代索引（V11）；
8. **确定性算法冻结**：tokenizer / 停用词 / TF / IDF / cosine / n-gram / 权重 / tie-break
   全部按 §2.3 唯一实现，跨运行与跨实现一致（V13/V14/V18）；
9. canonical T0–T3、events、definitions 在 semantic 操作前后逐文件 hash 不变（V8）；
10. 路由 closed table 生效：exact / version / status / sources / trace / history **永不** semantic（V3/V16）；
11. **semantic condition code 闭集 5 码**（3 blocking error + 1 non-error + 1 warning），无闭集外码；corrupt/stale 一律 fail_closed（V15/V10）；
12. 未接 Pi、未碰真实目录、不修改 P0/P1-A/P1-B 冻结合同与基线。

---

## 8. 明确不做（P1-C）

- embedding 模型 / 向量库 / 外部 API / LLM RAG 框架
- BM25（另立 revision）
- topic clustering / 语义分组
- paragraph-level retrieval
- synonym / paraphrase recall 保证（rev2 明确不承诺）
- 新 authority 枚举值
- semantic 回答 identity / version / causality / history
- 修改 P0 检索行为（`--text` 无 `--semantic` 时逐字节不变）
- 常驻进程、结果缓存、增量索引（rev2 只全量原子重建）
- 密码学签名、分布式索引、掉电恢复保证
