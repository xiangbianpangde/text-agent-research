# ResearchCTL Wiki —— 三层知识复利与问题登记

本目录实现 [WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill
Evolution](https://arxiv.org/abs/2608.27454)（arXiv:2608.27454）的三层知识架构，
把「原始经验 / 沉淀知识 / 可执行技能」在物理上分开，让经验持续编译进知识库，
供后续技能演化反复复用；同时提供一个**问题登记账本**：任何人在任何时刻发现问题
（工具异常、文档与实现不一致、检索策略退化），登记进来即可，不必当场修完。

```
Raw Layer     wiki/raw/          不可变执行证据（调用日志切片 / 命令输出 / 手工观察）
Wiki Layer    wiki/              patterns/ + issues/ + logs.md + skill-impact.md + index.md + meta/
Skills Layer  .pi/skills/        可执行技能（SKILL.md 描述能力，PURPOSE.md 回指驱动它的 wiki 模式）
```

## 1. 与论文的对应关系

| 论文（WikiSkill） | 本项目落地 | 说明 |
|---|---|---|
| Inference Agent 的 rollout 轨迹 τ | `~/.dsh/logs/dsh-researchctl/calls-*.jsonl` | 每次 `research` 调用即一条轨迹：action / argv / 层级 / Envelope 摘要 / 优化信号 |
| Raw Layer（不可变轨迹） | `wiki/raw/RAW-*.md` | 用 `raw capture` 把日志切片固化成不可变证据（带 `content_sha256`，`lint` 校验是否被改写） |
| Wiki Maintainer（归纳失败/成功模式） | `wiki.py suggest` + `pattern add` | `suggest` 机械地把反复出现的优化信号归纳出来；`pattern add` 沉淀根因与对策 |
| Wiki Layer 的 `patterns/` | `wiki/patterns/PAT-*.md` | 失败模式与成功策略，含可执行 workaround |
| Wiki Layer 的 `logs.md` | `wiki/logs.md` | 跨迭代演化日志（append-only） |
| Wiki Layer 的 `skill-impact.md` | `wiki/skill-impact.md` | 技能提案与验收结果——**被拒绝的方案不再重复提出** |
| Skill Proposer（基于 wiki 改技能） | 人工 / Agent 依 `wiki/index.md` + `skill-impact.md` 改 `.pi/skills/*` | 每次改动都要写 `impact` |
| Gating & Rollback | `issue update --status verified` + 测试证据 | 技能与修复都要有回归证据；wiki 本身不回滚 |
| **额外**：问题登记 | `wiki/issues/ISSUE-*.md` | 论文未显式覆盖的工程侧需求：发现即登记，后续集中修 |

## 2. 问题登记（发现问题 → 登记 → 一起修）

登记的语义是**「留痕不阻塞」**：发现问题的人只负责写清现象与证据，不负责当场修完。
状态机：

```
open → triaged → fixing → fixed → verified
  ↘ wontfix / duplicate（需写理由）
```

- 严重度：`critical | high | medium | low`
- 领域：`researchctl | researchctl-cli | dsh-plugin | pi-extension | wiki | bench | docs | env`

```bash
# 登记（Agent 或人）
python3 tools/wiki.py issue add \
  --title "researchctl --limit 对结构化查询不生效" \
  --area researchctl-cli --severity low \
  --signals limit_ignored \
  --evidence "calls-2026-09-15.jsonl argv=['query','--limit','2'] → 13 条" \
  --symptom "传 limit=2 仍返回 13 条" --discovered-by "dsh-researchctl 调用日志"

python3 tools/wiki.py issue list --status open
python3 tools/wiki.py issue list --json            # 给 Agent / 脚本
python3 tools/wiki.py issue show ISSUE-0001
python3 tools/wiki.py issue update ISSUE-0001 --status fixed --fix-ref "commit:abc123" --note "…"
```

## 3. 从调用日志自动归纳（Wiki Maintainer 的机械化部分）

```bash
python3 tools/wiki.py suggest --since 7d            # 只报告，不改动
python3 tools/wiki.py suggest --since 7d --apply    # 把未登记的信号直接登记成 issue 草稿
python3 tools/wiki.py raw capture --from-signal fail_closed --since 30d --limit 10
```

`suggest` 会对照现有 issue 的 `signals` 字段去重——**同一个信号不会被重复登记**。

## 4. 机械体检与确定性投影

```bash
python3 tools/wiki.py lint      # 重复 ID / 非法枚举 / 断链 / 不可变证据被改写（有问题退出码 1）
python3 tools/wiki.py rebuild   # 重建 index.md 与 meta/registry.json（派生数据，可随时重建）
python3 tools/wiki.py status    # 看板：未关闭问题 / 模式 / 证据
python3 tools/wiki.py recall 沙箱 哈希   # 在 问题/模式/证据/技能 中召回
```

## 5. 铁律（与项目既有治理一致）

1. **Raw 不可变**：`wiki/raw/` 只增不改；`lint` 会比对 `content_sha256`，改写即报错。
2. **logs.md 只追加**：历史更正用新的 `CORRECTION` 行表达，严禁覆盖或重排。
3. **index / registry 是导航不是证据**：可随时删除重建（确定性投影）。
4. **登记不阻塞**：发现问题先写 `issue`，修复另起动作；证据必须可解析（日志 seq / 命令 / 路径）。
5. **技能改动必须留 `impact`**：被拒绝的方案写进 `skill-impact.md`，防止重复提出。
6. **检索期不读 wiki 当证据**：`research` 工具的证据链永远是 Report → Organized@commit → Raw，
   wiki 是经验沉淀层，不能替代原始事实（对应论文 §5.1「训练时限制 wiki 访问」的教训）。
