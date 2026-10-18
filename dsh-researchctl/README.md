# dsh-researchctl

把本仓库（**ResearchCTL · 超长程实验 Agent 检索与科研状态系统**）装进
**DeepSeek Harness (DSH)** 的宿主插件：Agent 直接调用 `research` 工具做确定性检索，
每次调用都会落一条结构化日志，供后续按数据做优化迭代。

- 插件包：`dsh-researchctl/`（`@dsh-external/dsh-researchctl`）
- 运行依赖：**仅 node 内置模块**（无第三方依赖、无构建步骤，可直接被 DSH loader 加载）
- 底层引擎：`python3 -m researchctl`（本仓库 `researchctl/`，零第三方依赖）
- 姊妹集成：`.pi/extensions/research.ts`（pi coding agent）**复用同一份 core 与同一份日志**

---

## 1. 工具

### `research`

统一入口，`action` 分派到 researchctl CLI。参数与 CLI 一一对应（单一真源见 `core/actions.js`）。

| 族 | action | 说明 |
|---|---|---|
| 读 | `query` | 结构化查询 / 词面检索（`--entity` `--doc-type` `--status` `--raw` `--text`；`semantic` 仅 Layer 5 兜底） |
| 读 | `sources` | 来源与精确版本核验（pinned hash / git commit） |
| 读 | `trace` | 溯源下钻：结论 → Organized@commit → Run → Raw |
| 读 | `history` | 历史报告演化与 stale 判定（`as_of` 可回溯某时刻） |
| 读 | `impact` | 逆向依赖与下游影响链（`change_type` 预演语义变更） |
| 读 | `reconcile` | 完整性巡检（断链 / hash 不符 / 索引漂移 / 孤儿文件） |
| 维护 | `index` `generate-index` `ingest-raw` | 重建派生索引 / 刷新导航 / 导入原始数据 |
| 事务 | `freeze-report` `revise-definition` `tx-status` `tx-reconcile` `tx-reset-guard` | WAL 两阶段提交与崩溃恢复 |
| 评测 | `bench` | ResearchCTL-Bench 内部一致性套件 |

返回值：`{ ok, process_ok, action, root, kind, exit_code, duration_ms, layer, signals, rule_violations, notes, envelope, payload_path, log_dir, seq, text }`。

- `ok`：进程成功 **且** Envelope 未 Fail-Closed（业务语义上的「检索成功」）。
- `process_ok`：只看子进程是否成功退出 —— 两者分开，便于区分「CLI 崩了」和「确实没找到」。
- `signals` / `notes`：优化信号与给模型的直接提示（例如「结果为空」「规则误用」）。

### `wiki`

把开发/检索过程中出现的问题登记进仓库 wiki（`wiki/issues/`），供后续集中修——
**登记不阻塞当次任务**。参数与 `python3 tools/wiki.py --help` 完全一致（action + args 透传）：

| action | 说明 |
|---|---|
| `issue_add` / `issue_list` / `issue_show` / `issue_update` | 问题登记与状态机（`open→triaged→fixing→fixed→verified`，另有 `wontfix/duplicate`） |
| `pattern_add` / `pattern_list` | 失败模式与成功策略（含可执行对策） |
| `raw_capture` | 从 research 调用日志按优化信号抓取**不可变证据**（带 content_sha256） |
| `suggest` | 从调用日志归纳未登记的信号（Wiki Maintainer 的机械化部分，按 `--signals` 去重） |
| `impact` | 记录技能改动与验收结果（被拒绝的方案不再重复提出） |
| `lint` / `rebuild` | 机械体检 / 重建 `wiki/index.md` 与 `meta/registry.json` |
| `status` / `recall` | 看板 / 在问题·模式·证据·技能中召回 |

调用同样写入调用日志（`tool: "wiki"`、`route: "wiki"`、`action: "wiki:<action>"`），
因此 `research_log` 的统计里也能看到 wiki 使用情况。

### `research_log`

读取并聚合本插件自己写的调用日志（优化迭代的观测面）：

| scope | 内容 |
|---|---|
| `stats`（默认） | 调用量 / 成功率 / 空结果率 / 各动作耗时 / 层级分布 / Fail-Closed 错误码分布 / 每日趋势 / 最慢调用 / 最近失败 |
| `signals` | 优化信号聚合（含样例与最近带信号调用） |
| `recent` | 最近调用流水 |
| `failures` | 失败详情（argv + stderr + error_codes） |
| `paths` | 日志目录、文件清单、离线分析命令 |
| `export` | 全量统计 JSON |

过滤：`since`（`24h` / `7d` / ISO / `YYYY-MM-DD`）、`action`、`source`（`dsh` / `pi`）、`root`、`signal`、`limit`、`format`。

---

## 2. 注入到 DSH

```bash
# 注入器环境内（dsh-super-injector）
dev_inject_plugin {"dir": "<仓库>/dsh-researchctl"}
# 卸载
dev_uninject_plugin {"match": "dsh-researchctl"}
```

也可手工写进 profile patch（`~/.dsh/profiles/<profile>/cordis.patch.yml`）：

```yaml
- insert:
    - id: dsh-researchctl
      name: '<仓库>/dsh-researchctl/index.js'
      config:
        # 全部可选，见下表
        defaultRoot: '<仓库>/fixture'
```

### 配置项

| 键 | 默认 | 说明 |
|---|---|---|
| `pythonPath` | `python3` | Python 解释器 |
| `defaultRoot` | 自动探测 `<仓库>/fixture` → 仓库根 | 研究项目根目录（含 `reports/ organized/ runs/ raw/`） |
| `logDir` | `$RESEARCHCTL_LOG_DIR` → `~/.dsh/logs/dsh-researchctl` | 日志目录；主目录不可写时自动降级到 `<仓库>/.dsh-logs/researchctl` |
| `logEnabled` | `true` | 关闭后不写任何日志 |
| `timeoutMs` | `180000` | 单次调用超时（也可用参数 `timeout_seconds` 覆盖） |
| `slowMs` | `15000` | 超过即记 `slow_call` 信号 |
| `maxOutputChars` | `60000` | 返回给模型的文本上限 |
| `spillThreshold` | `20000` | 超过即把完整输出落盘到 `payloads/` |
| `maxBufferBytes` | `16777216` | 子进程输出缓冲上限 |
| `wikiTimeoutMs` | `120000` | `wiki` 工具（`tools/wiki.py`）单次调用超时 |
| `guidance` | `true` | 是否注入「检索纪律 + 问题登记纪律」系统提示段落（pi 侧等效内容见仓库根 `AGENTS.md`） |

---

## 3. 日志（本插件的核心资产）

目录：`~/.dsh/logs/dsh-researchctl/`（可用 `RESEARCHCTL_LOG_DIR` 覆盖）

```
calls-YYYY-MM-DD.jsonl   每次工具调用一行（按天轮转）
plugin.jsonl             插件生命周期事件（plugin-loaded / guidance-skipped / logger-ready …）
payloads/*.json          被截断的大输出全文（复盘用）
```

### 3.1 调用记录 schema `dsh-researchctl/call@1`

| 字段 | 含义 |
|---|---|
| `schema` `ts` `epoch_ms` `seq` `pid` `source` | 记录标识；`source` = `dsh`（本插件）/ `pi`（pi 扩展） |
| `tool` `action` `route` `layer` `closed` `mutating` | 调用形态；`layer` 是五层检索能力分层（L2/L3/L4/L5），`route` = read / maintenance / mutation / tx / bench / observability |
| `root` `args` `argv` | 目标项目、脱敏后的入参、最终 CLI argv |
| `ok` `process_ok` `kind` `exit_code` `duration_ms` `timeout_ms` | 结果与耗时 |
| `stdout_bytes` `stderr_bytes` `stderr_excerpt` | 输出规模与错误摘要 |
| `envelope` | Envelope 折叠摘要：`status` `authority` `error_codes` `issue_codes` `result_count` `empty` `entity_ids` `stale_count` `unavailable_count` `drift` `index_complete` |
| `semantic_requested` `rule_violations` | 是否请求语义检索、是否规则误用 |
| `signals` `notes` | **优化信号**与给模型的提示 |
| `payload_path` | 完整输出落盘位置（如被截断） |
| `session_id` `agent_id` `cwd` | 调用方上下文（用于按会话归因） |

### 3.2 优化信号（`signals`）

| 信号 | 触发条件 | 迭代含义 |
|---|---|---|
| `empty_result` | 检索成功但结果为空 | 检索路径/关键词选择可能有问题（优化候选） |
| `fail_closed` | Envelope `status=error` 或有 `error_codes` | 撞上 HASH_MISMATCH / INDEX_STALE / SOURCE_MISSING / NOT_FOUND / AMBIGUOUS_VERSION |
| `index_drift` | `drift=true` 或 `index_complete=false` | 派生索引过期，先 `index` |
| `semantic_on_closed_command` | 在溯源闭集动作上请求 `semantic` | **规则误用**（身份/版本/因果禁止语义猜测） |
| `stale_entity_seen` | 命中 `is_stale=true` 实体 | 结论断代，需要 re-verify |
| `reconcile_issue` | 巡检发现一致性问题 | 见 `issue_codes` |
| `slow_call` | `duration_ms >= slowMs` | 索引或查询范围问题 |
| `limit_ignored` | 传了 `limit` 但结构化查询返回更多 | researchctl 的 `--limit` 只作用于 `--semantic` 路径；已显式告知模型，勿当成「只有 N 条」 |
| `parse_error` | 进程成功但 stdout 不是 JSON | 与 CLI 的 JSON 契约不一致（真 bug） |
| `output_overflow` / `timeout` / `nonzero_exit` / `spawn_error` / `bad_args` / `bad_root` | 各类执行失败 | 插件自身或环境问题 |

规则误用与执行失败**都不改变执行结果**，只做可观测化——日志是证据，不是拦截器。

### 3.3 离线分析（不需要 DSH）

```bash
node dsh-researchctl/lib/core/analyze.js --scope stats    --since 7d
node dsh-researchctl/lib/core/analyze.js --scope signals  --since 30d
node dsh-researchctl/lib/core/analyze.js --scope failures
node dsh-researchctl/lib/core/analyze.js --scope recent   --limit 50
node dsh-researchctl/lib/core/analyze.js --format json > stats.json
```

---

## 4. 优化迭代闭环

1. **跑任务**：Agent 正常使用 `research`，日志自动积累（DSH 与 pi 的调用混在同一份日志里，用 `source` 区分）。
2. **读信号**：`research_log(scope="signals")` 或 `analyze.js --scope signals`，看哪些信号在涨。
3. **定位**：`scope="failures"` 看 stderr 与 argv；`scope="stats"` 看 `by_action` / `by_layer` / `empty_by_action`。
4. **改**：常见动作——补工具描述/参数的指引、修技能里的检索决策树、修 `defaultRoot`/超时/索引、修 researchctl 本身。
5. **验证**：`since` 切到改动之后的时间窗再跑 `scope="stats"`，对比 `empty_result` / `fail_closed` / `semantic_on_closed_command` / `p95` 的变化。

`semantic_on_closed_command` 与 `empty_result` 最能反映「Agent 检索行为是否退化」；
`parse_error` 与 `spawn_error` 则是插件/环境自身的健康度指标。

---

## 5. 热重载（改完代码立即生效，无需重启 DSH）

```bash
dev_reload_package {"packageName": "dsh-researchctl"}   # ← 用「包目录子串」
```

**匹配串用包目录子串（`dsh-researchctl`）最直观**；即使用入口文件名
（`dsh-researchctl/lib/index.js`），注入器也会按入口反推包目录、自动把整棵模块子树
（入口 + `lib/core/*`）一起清缓存（ISSUE-0002 已修）。

无论用哪种匹配串，都建议看一眼返回消息里的模块数：多文件插件正常应显示
`清缓存 7 模块`（入口 + 6 个 core 模块）；若只显示 `1 模块`，说明改的 `lib/core/*`
没有真正生效——这是最容易踩的坑。

---

## 6. 开发与测试

```bash
cd dsh-researchctl
node --test test/smoke.test.mjs test/plugin.e2e.test.mjs
```

- `test/smoke.test.mjs`：动作表 argv 构造、参数校验、真实 researchctl 调用、Envelope 摘要、信号推导、日志写入与聚合。
- `test/plugin.e2e.test.mjs`：用假 ctx 模拟 DSH loader，端到端验证工具注册、调用、日志落盘与 `research_log` 聚合。

代码结构：

```
lib/index.js        插件装配：配置解析、三个工具（research / research_log / wiki）、系统提示段落、服务暴露
lib/core/actions.js  动作表单一真源（argv / 必填参数 / 分层 / 闭集语义）
lib/core/executor.js 调用编排（执行 → 摘要 → 信号 → 日志 → 渲染），DSH / pi 共用
lib/core/runner.js   通用子进程执行（runProcess/runResearchctl/runScript）+ Envelope 摘要 + 优化信号推导
lib/core/logger.js   JSONL 写入、按天轮转、payload 落盘、降级
lib/core/wiki.js     wiki 工具桥（tools/wiki.py 的 action 映射、执行、留痕、ID 提取）
lib/core/analyze.js  日志读取、聚合、Markdown 渲染、离线 CLI
test/                node --test 冒烟测试 + 假 ctx 端到端测试
```

> 说明：`lib/` 是**源码而非构建产物**（本插件零构建、零第三方依赖）。沿用 `lib/index.js`
> 是因为 DSH loader 与 dsh-super-injector 的热重载通道都按该约定定位入口——
> 这样 `dev_reload_package` 能在不重启宿主的条件下热重载插件，支撑「改 → 重载 → 看日志」的迭代闭环。
