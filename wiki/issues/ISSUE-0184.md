---
id: "ISSUE-0184"
title: "M3 子进程私有配置目录把认证文件暴露给被测模型的 shell 工具"
status: "fixed"
severity: "critical"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "model_child_can_read_auth_copy"
evidence: "/Users/xbpd/Projects/researchctl-product/catalog/test/trigger.ts:105 将 PI_CODING_AGENT_DIR 设为 childConfigDir()；:336-390 从 ~/.pi/agent 复制 CHILD_CONFIG_FILES（含 auth.json）到该目录；:584 对 childConfigDir 整棵目录添加 `(allow file-read* file-write* (subpath ...))`。Pi Bash 实现 `/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/tools/bash.js:54` 使用 `env ?? getShellEnv()`；`dist/utils/shell.js:115-125` 的 `getShellEnv()` 展开 `...process.env`，故 Bash 子进程继承 PI_CODING_AGENT_DIR。零成本、同 sandbox profile 探针仅执行 `test -r '$PI_CODING_AGENT_DIR/auth.json'`（未读取文件内容），输出 `config_dir_set=yes; auth_file=readable`。没有证据证明已发生凭据读取或外传。"
related:
  - "ISSUE-0189"
  - "ISSUE-0190"
fix_ref: "9fe8676"
summary: "M3 子进程私有配置目录把认证文件暴露给被测模型的 shell 工具"
updated_at: "2026-09-24"
---

## 现象

为使 Pi 子进程启动而将 auth.json 复制到 sandbox allow-read 的私有目录后，被测 Agent 的 Bash 工具继承 PI_CODING_AGENT_DIR 并能读取认证文件；模型可将凭据内容带入对话/工具输出，造成敏感认证材料暴露风险。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

（待评估：影响面 / 是否有 workaround）

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-24T14:51:12+0800

按执行者-2 的要求完成：(1) 模型工具无法读取认证材料——两条路径均修复（环境变量按类别剔除 + 配置目录仅写非 nonce）；(2) 负向探针已加入 preflight（检查 10/11/12），并做变异验证：删 scrub → FAIL 列出 5 个变量；重新复制凭据文件 → FAIL 定位到 antigravity-accounts.json；(3) 干净状态已提交 9fe8676，test:catalog 229/229、typecheck 0 错误、preflight 全通过；(4) 全程 0 个模型回合。

## 处置记录 2026-09-24T18:05:44+0800

【执行者-2 补充】本 issue 的**通道**已修（状态 fixed 成立），但**同一事件**还含一条未被登记的运维动作：暴露窗口内 3 个真实 API key 的值曾进入模型上下文（见 ISSUE-0190）。ISSUE-0184 正文未提及变量名与轮换，单读本页会误判为已闭环；请与 ISSUE-0190 一并阅读。另经核验：归档本身不含 key 值（59 行，0 命中），归档中亦无任何回合读过凭据文件。
