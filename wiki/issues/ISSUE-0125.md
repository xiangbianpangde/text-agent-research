---
id: "ISSUE-0125"
title: "wiki raw capture --text 内含反引号时被 shell 命令替换静默篡改，且改写后仅靠 lint 才发现"
status: "open"
severity: "medium"
area: "env"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "backtick_shell_substitution_in_cli_text_argument"
evidence: "2026-09-22 R64: python3 tools/wiki.py raw capture --text '...成对反引号围绕 found and valid...' 时 bash 执行了命令替换：bash 报 'found: command not found'，正文中反引号内文字被吞掉、一对中文引号也被去掉；随后我直接改文件被 lint 拦下（RAW-20260922-003: 不可变证据被改写 content_sha256 bcee485fbb05 != 实际）；撤回后以 heredoc 重新采集成功（RAW-20260922-003 sha256:8623ab762716f75e...）"
related: []
fix_ref: null
summary: "wiki raw capture --text 内含反引号时被 shell 命令替换静默篡改，且改写后仅靠 lint 才发现"
---

## 现象

长文本证据经 --text 传入时被 shell 展开（反引号、$ 变量）后落盘，破坏原文且不可逆；REST API/工具路径（wiki(action=raw_capture)）不经 shell，但 CLI 路径会

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
