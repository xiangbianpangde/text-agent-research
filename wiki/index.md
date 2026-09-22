# Wiki 索引（确定性投影，可随时由 `python3 tools/wiki.py rebuild` 重建）

> 生成时间：2026-09-16T08:28:35+0800｜依据 WikiSkill 论文 §3.1（index 是派生导航，不是证据本身）

## 未关闭问题

| id | 状态 | 严重度 | 领域 | 标题 |
|---|---|---|---|---|
| ISSUE-0007 | open | medium | bench | bench/tests 有 4 个环境相关失败（基线即失败） |
| ISSUE-0008 | open | medium | env | Open-WebUI 0.11.x：未在 model 表登记的模型对非管理员完全不可见（管理员可见 → 新账号模型列表为空） |
| ISSUE-0009 | open | high | pi-extension | computer_use click 坐标系是窗口局部坐标、且绑定会在未重新取状态时陈旧 |
| ISSUE-0010 | open | critical | pi-extension | computer_use type_text 静默丢弃 ASCII 特殊字符与非 ASCII，且无报错 |
| ISSUE-0011 | open | low | pi-extension | computer_use app 名解析仅接受英文名/bundle id，中文应用名报 identity_rejected |

## 已收口问题

| id | 状态 | 标题 | fix_ref |
|---|---|---|---|
| ISSUE-0001 | fixed | researchctl --limit 对结构化查询不生效 | researchctl/queries.py:cmd_query + researchctl/cli.py（--limit 默认 None） |
| ISSUE-0002 | fixed | dev_reload_package 只清入口模块，lib/core/* 仍是旧代码 | try/dsh-super-injector/lib/index.js（reload 自动扩展包目录子树） |
| ISSUE-0003 | wontfix | pi 在 DSH 沙箱下启动即 EPERM（trust.json.lock） | - |
| ISSUE-0004 | fixed | 全局技能副本与项目版漂移（~/.pi/agent/skills/task/research-retrieval） | ~/.pi/agent/skills/task/{research-retrieval,researchctl-wiki} 符号链接 + ~/.agents/skills/ 同名链接 |
| ISSUE-0005 | wontfix | 溯源闭集动作上的 semantic 请求（规则误用信号样例） | - |
| ISSUE-0006 | fixed | wiki CLI 的 --json 只能在子命令之前使用，工具调用踩坑 | tools/wiki.py（parents=[json_parent]） |

## 模式库（3）

| id | kind | 命中 | 标题 |
|---|---|---|---|
| PAT-20260916-001 | failure | 3 | computer_use 动作静默偏离预期：必须以独立通道验证副作用 |
| PAT-20260915-002 | failure | 1 | 沙箱边界：需要写工作区外目录的工具会被拒 |
| PAT-20260915-001 | failure | 3 | 宿主模块缓存：改核心模块后热重载不生效 |

## 不可变证据（2）

- `RAW-20260916-001`｜manual｜computer_use type_text 静默丢弃 ASCII 特殊字符与非 ASCII 字符｜`wiki/raw/RAW-20260916-001.md`
- `RAW-20260915-001`｜call-log｜call-log 证据 RAW-20260915-001｜`wiki/raw/RAW-20260915-001.md`

## 技能层（2）

- `research-retrieval`｜Guides deterministic research retrieval in ultra-long-horizon experimental text agent sys…
- `researchctl-wiki`｜WikiSkill 三层知识复利与问题登记的**判断规则**：遇到工具异常、文档与实现不一致、同类问题复发、检索策略退化时，判断该登记成什么（问题 / 模式 / 不可变证据 / …

## 账本

- 演化日志：[`logs.md`](logs.md)（append-only）
- 技能影响：[`skill-impact.md`](skill-impact.md)
