---
id: "ISSUE-0185"
title: "子进程继承父环境凭据，且 `PI_` 是 `API_KEY` 的子串，使按项目变量过滤的 grep 打印出真实密钥值（24 次调用 / 18 场景）"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "child_inherits_parent_credentials api_key_substring_pi_ grep_pattern_prints_secret_values credentials_in_model_context preexisting_leak_outside_pi_dirs credential_env_scrub"
evidence: "实测：`scrubbedChildEnv()` 返回的 env 含 PARATERA_API_KEY(25)、DEEPSEEK_V4_API_KEY(35)、OPENROUTER_API_KEY(73)；经 `sandbox-exec -f gradingProfilePath()` 以子进程真实身份执行 `env | grep -i -E 'PI_|RESEARCH' | cut -d= -f1` 确认三类变量均被匹配（因 `PI_` ⊂ `API_KEY`）。扫描全部 59 行付费观测：24 次 bash 调用（跨 18 个场景）使用了能匹配密钥名的 grep 模式；其中 2 次带 sed 脱敏（rec-stale-index-absent call#9、rec-semantic-rebuilt-before-p0 call#10），其余 22 次未脱敏。**归档自身未被污染**：以值的前 12 字符逐一检索 59 行 JSON（含 text 字段）→ 0 命中（行内只存调用参数，不存工具输出）。修复验证：剔除后同一 `env | grep -icE 'paratera_api|deepseek_v4_api|openrouter_api'` 返回 0；变异（删掉 scrub 块）→ preflight 的 ISSUE-0184 检查 FAIL 并列出全部 5 个变量名。"
related:
  - "ISSUE-0184"
  - "ISSUE-0183"
  - "ISSUE-0182"
fix_ref: null
summary: "子进程继承父环境凭据，且 `PI_` 是 `API_KEY` 的子串，使按项目变量过滤的 grep 打印出真实密钥值（24 次调用 / 18 场景）"
---

## 现象

子进程通过 `{...process.env}` 继承父进程全部环境变量，而父进程环境里有三个真实 API key。失效形状之所以隐蔽，是因为「按本项目变量名过滤」的写法与「匹配到密钥」的写法在同一个正则里重叠：`PI_` 是 `API_KEY` 的子串，于是 `env | grep -i -E "PI_|RESEARCH"` 看起来像在筛 `PI_*` 项目变量，实际把每个 `*_API_KEY` 连值一起打印。该模式在 18 个场景中出现，属于模型自然会用的探索动作，不是异常行为。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

真实密钥值被送入模型上下文（第三方 provider 可见），且发生在**付费观测**过程中；若模型将其写入 `text`，则会永久留在只可追加、无法擦除的归档里（本次核查为 0 命中，属侥幸而非设计）。另一条更严重的后果已实测：凭 `OPENROUTER_API_KEY` 的存在，子进程可解析出**内置 provider** 并发起真实 completion，绕过 harness 配置的 provider，即「测量装置意外提供了通往真实网络的路径」。此路径独立于 ISSUE-0184 的配置文件路径，早于后者存在。

## 根因

两个设计缺口叠加：(1) 环境变量是全量继承的，没有按类别剔除；(2) 凭据命名与项目命名空间共享子串（`API_KEY` 含 `PI_`），使按项目前缀过滤的正则不可能同时排除凭据。更深层的是：harness 的围堵目标一直定义为「答案不可读」，凭据从未纳入威胁模型——所以 8 项 preflight 检查全部通过，而模型实际持有的权限里包含五个可用凭据。威胁模型的范围错误，比任何单项检查缺失都更根本。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
