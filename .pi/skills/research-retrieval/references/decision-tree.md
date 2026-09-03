# 典型科研问题的检索决策树（Decision Tree）

依据《超长程实验 Agent 检索系统设计方案.md》§17 冻结规范。

---

## 路线 A：“目前关于 X 的结论是什么？”

1. **直接读取当前报告**：`read reports/CURRENT.md`。
2. **在报告中定位章节**：阅读结论、核心数据指标与证据引用。
3. **导航辅助**：若目标主题不清晰，查阅 `INDEX.md` 的主题索引（Topic Index）。
4. **铁律**：绝不一开始就全量执行向量/语义检索。

---

## 路线 B：“为什么得到这个结论？”（推导依据）

1. **查阅当前来源清单**：`researchctl sources CURRENT` 或读取 `reports/CURRENT.sources.yaml`。
2. **定位对应的 Organized 整理文件**：如 `organized/EXP-017/result.md`。
3. **阅读 Organized 整理内容**：查看分析章节与支持证据。
4. **深入底层证据**：若需追溯数据根源，执行溯源下钻：`researchctl trace CURRENT`。

---

## 路线 C：“这个数据具体怎么来的？”（原始实验下钻）

1. **下钻定位 Raw ID**：通过 `trace` 确定支撑该数据的 Raw ID（如 `R052`）。
2. **核验 Raw 元数据**：检查 `raw/EXP-017/R052/STATUS.yaml` 或 `runs/R052/manifest.yaml`。
3. **直接查阅原始执行事实**：
   - 读 `execution.log`（命令、环境、stdout、执行状态）。
   - 读 `metrics.csv`（真实数值测量点）。
4. **严禁越过 Raw 确认结论**：数据指标不可仅凭总结文件中的口述数字。

---

## 路线 D：“两周前不是这么说的吗？”（历史演化与差异追溯）

1. **调用历史演化查询**：`researchctl history`。
2. **定位历史报告版本**：找到两周前的历史报告（如 `REPORT-002`）。
3. **对比报告正文**：比较 `REPORT-002` 与当前 `CURRENT.md` 在同一议题上的表述差异。
4. **对比来源锁定版本**：查阅 `researchctl sources REPORT-002`，对比两个报告当时引用的 Organized 文件版本与 Git commit。
5. **判定演化原因**：通常是由于后续新增了实验运行、或底层定义发生了修订导致旧结论成为 `stale`。

---

## 路线 E：“修改这个实验定义会对全系统产生什么影响？”（逆向影响分析）

1. **调用影响链分析**：`researchctl impact <entity>`（例如 `researchctl impact H003@v1` 或 `researchctl impact R051`）。
2. **获取逆向依赖图谱**：
   - 依赖该定义的下游 Experiment。
   - 使用该定义的历史或进行中 Run。
   - 引用该实验数据的 Organized 整理文件。
   - 最终受到波及的科研报告与决策项。
3. **变更预演**：配合 `--change-type contract_tightened` 预演评估哪些实体将被标记为 `stale` 或 `needs_review`。

---

## 路线 F：“我记得之前讨论过某个概念，但记不清在哪里”（模糊线索召回）

1. **作为末级兜底启用语义检索**：`researchctl query --text "<线索>" --semantic`。
2. **评估置信度**：若返回附带 `SEMANTIC_LOW_CONFIDENCE` warning，表示词面匹配较弱，仅供参考。
3. **切换回显式阅读**：一旦根据语义检索定位到可能的文件路径，立即切换到路线 A/B，通过显式结构阅读确证。

---

## 路线 G：“某个 Run 到底使用的是哪个版本的定义？”

1. **读取该 Run 的 RunManifest**：如 `runs/R052/manifest.yaml`。
2. **查看其显式声明的 spec 引用**：查看 `experiment_ref` 与引用的版本号（如 `E017@v4`）。
3. **严禁使用词向量相似度去猜**：版本号属于精确因果事实，绝不能靠语义检索推断。
