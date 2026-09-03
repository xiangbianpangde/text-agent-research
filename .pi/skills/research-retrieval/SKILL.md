---
name: research-retrieval
description: Guides deterministic research retrieval in ultra-long-horizon experimental text agent systems (researchctl). Enforces explicit structure over semantic guessing: starts with CURRENT.md, traces provenance down to raw data, audits historical evolution, inspects downstream impact, and restricts semantic search to fallback. Use when querying research status (当前结论是什么、依据来源、历史演化、实验溯源、定义变更影响、researchctl 相关操作). Do not use for generic web search, routine single-file code inspection, or normal codebase grep.
compatibility: Pi coding agent
metadata:
  version: "1.0.0"
  status: "active"
  layer: "task"
  priority: "30"
  triggers: "research-retrieval,trace-provenance,query-research-status,impact-analysis"
---

# Research Retrieval

Deterministic research state retrieval for ultra-long-horizon text agent experiments.

## Outcome

Agent retrieves reliable, verifiable, auditable research state without semantic hallucination:
- Finds current valid conclusions directly from `reports/CURRENT.md`.
- Traces provenance mechanically from Conclusion down to Organized and Raw data.
- Verifies exact Git commits and SHA-256 hashes instead of relying on path assumptions.
- Audits historical evolution and stale status across report versions.
- Evaluates downstream impact before modifying definitions or hypotheses.

## Trigger boundary

- **Use when**:
  - 用户询问“当前结论是什么 / 为什么成立 / 依据来自哪里”；
  - 需追踪实验原始数据（Raw Manifest / execution.log / metrics.csv）；
  - 需核查两周前历史结论与当前差异、判定结论是否 stale；
  - 需分析某项实验定义（Definition/Spec）修改对全系统下游实体的冲击；
  - 运行 `researchctl` 或 `research` 工具进行科研检索与完整性校验。
- **Do not use when**:
  - 普通工程代码编写或单文件重构；
  - 通用 Web 搜索（使用 `web_search`）；
  - 简单的全库字符串查找（直接使用 `grep`）；
  - 纯文档排版与格式转换。

## Workflow

1. **识别问题类型并选定检索路线**：
   - 查当前结论 → 路线 A（直接读 `reports/CURRENT.md`）。
   - 查依据来源与推导链 → 路线 B（查 `sources` 并下钻 `trace`）。
   - 查原始实验数据 → 路线 C（通过 `trace` 获知 Raw ID，核验 Raw Manifest 与日志）。
   - 查历史演化与差异 → 路线 D（调用 `history` 比较不同 Report 及其来源版本）。
   - 查定义修改影响 → 路线 E（调用 `impact` 逆向依赖图分析）。
   - 模糊回忆与线索召回 → 路线 F（使用 `query --text <T> --semantic` 作为 fallback）。
   详细决策树见 [references/decision-tree.md](references/decision-tree.md)。

2. **按分层优先级执行检索**（[references/layer-rules.md](references/layer-rules.md)）：
   - Layer 1（物理路径）+ Layer 2（词面检索）优先处理具名实体。
   - Layer 3（结构化元数据）回答关联关系与文档分类。
   - Layer 4（Provenance Trace）回答因果链与版本锁定。
   - Layer 5（Semantic Retrieval）仅在位置不明或词面偏差时作为末级兜底。

3. **核验证据链完整性**：
   - 若出现引用丢失、内容哈希不符或索引漂移，先运行 `researchctl reconcile`。
   - 绝不使用“猜测的”版本号（如 E017@v3 vs v4 必须查 RunManifest 确定）。

4. **输出结构化结论与证据锚点**：
   - 阐明当前有效状态（fresh）与历史状态（stale）。
   - 提供从 Report 到 Raw 的完整下钻证据路径。

## Constraints

- **严禁语义猜测**：Identity、Version、Causality、History 必须通过显式结构恢复，绝对禁止用向量相似度猜结果。
- **Report 不是唯一真源**：Report 是叙述入口，最终可审计底座是 Raw。
- **来源必须锁定精确版本**：历史来源引用必须绑定具体 Git commit / content_hash，不可只记相对路径。
- **Index 是导航不是证据**：`INDEX.md` 仅用于快速跳查，不作为事实证明。
- **遵循路由闭集表**：精确查询（`--entity`, `--status`, `--doc-type`）与溯源命令严禁混入 semantic。

## Verification

在向用户给出科研结论前完成自检：
1. 涉及当前结论时，是否基于 `reports/CURRENT.md` 验证？
2. 涉及实验事实时，是否已下钻到具体 Raw ID 与执行哈希？
3. 涉及历史变更时，是否已通过 `history` 确认新旧版本的具体差异？
4. 是否在无依据的情况下使用了模型脑补？

## Completion

汇报时明确提供：
- 核心结论与状态（fresh / stale / valid / completed）；
- 完整证据路径（`Report → Organized → Raw`）；
- 关键实体 ID 及版本（如 `E017@v4`、`R052`）；
- 涉及影响面时的受影响实体清单。
