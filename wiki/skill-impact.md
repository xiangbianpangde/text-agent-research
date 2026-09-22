# 技能影响账本（skill-impact）

> 依据 WikiSkill 论文 §3.1/§3.2.4：记录每一次技能提案及其验收结果，
> 使**被拒绝的干预不再被重复提出**，并让技能演化可审计。
> `result`：accepted（验证通过并保留）/ rejected（验证不通过已回滚）/ pending。

| 时间 | 技能 | 变更 | 依据 | 结果 | 证据 |
|---|---|---|---|---|---|
| 2026-09-15T19:16:33+0800 | research-retrieval | 对齐 dsh-researchctl：14 个 action + research_log + Self-improvement loop 章节 | 论文 WikiSkill 的 Raw→Wiki→Skills 闭环需要调用日志可见 | accepted | pi -p 实跑两次通过；node --test 13/13 通过 |
| 2026-09-15T19:16:33+0800 | researchctl-wiki | 新建技能：WikiSkill 三层复利 + 问题登记判断规则（薄技能，常驻纪律移到 AGENTS.md） | arXiv:2608.27454 §3.1/§3.2；ISSUE-0002 等经验需要载体 | accepted | tools/wiki.py 冒烟通过（issue add/list/update、suggest、raw capture、lint、rebuild） |
| 2026-09-15T19:36:33+0800 | dsh-researchctl | runner.js 拆出 runProcess/runScript；新增 wiki 工具（tools/wiki.py 桥）；系统提示补充问题登记纪律 | ISSUE-0002/PAT-20260915-001；WikiSkill arXiv:2608.27454 | accepted | node --test 14/14；DSH 宿主实调 wiki(issue_list/suggest)；pi -p 实调 wiki(status) |
| 2026-09-16T08:28:35+0800 | computer-use（Pi 工具族 / 官方 computer-use 技能） | 新增 agent 侧使用纪律：①每次动作前重新取状态、不复用 element_index；②坐标只作兜底且必须先反解 origin；③文本写入走 set_value 而非 type_text；④每个写操作后用独立通道（剪贴板/文件字节）验证副作用；⑤不采信工具自报 ok | PAT-20260916-001：type_text 静默丢字符（ISSUE-0010，critical）与坐标/绑定语义未文档化（ISSUE-0009，high）都会让 Agent 在无错误信号下产生错误副作用 | pending | RAW-20260916-001；PAT-20260916-001；~/Projects/computer-use-boundary-test/ |
| 2026-09-22T19:08:12+0800 | research-retrieval | M2-2 未改技能，但记录了 journal 的状态入口契约：/research-status 等命令的答案必须携带数据来源（index basis / torn tail / anchor 一致），不得把 stale 或 unavailable 报成当前状态 | PAT-20260922-001 + ISSUE-0109：派生物与真源不一致时，静默给出'看起来正常'的答案是本项目已复现的失败模式 | accepted | journal/index.ts 的 IndexStatus.basis（fresh/created/rebuilt/stale/unavailable）与 journal/store.ts 的 ReadResult.torn_tail；docs/records/M2-2-journal-store.md §4 |
