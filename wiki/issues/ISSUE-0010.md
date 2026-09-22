---
id: "ISSUE-0010"
title: "computer_use type_text 静默丢弃 ASCII 特殊字符与非 ASCII，且无报错"
status: "open"
severity: "critical"
area: "pi-extension"
discovered_at: "2026-09-16"
discovered_by: "agent（实测 + strings SkyComputerUseService）"
tags:
  - "computer-use"
  - "type-text"
  - "char-loss"
signals:
  - "char_loss"
  - "silent_data_loss"
evidence: "~/Projects/computer-use-boundary-test/evidence/EVIDENCE.md#E1；不可变证据 wiki/raw/RAW-20260916-001.md"
related:
  - "RAW-20260916-001"
fix_ref: null
summary: "computer_use type_text 静默丢弃 ASCII 特殊字符与非 ASCII，且无报错"
---

## 现象

type_text 输入含 !$()|:;<>?[]{}~\^_ 或中文/emoji 的文本时，这些字符被静默丢弃；工具仍返回 outcome=ok

## 复现

type_text('DET !!$$(()),,:;<<>>??[[\\]]^^__``{{||}}~~ /END3') -> 实际落入 'DET  /END3'。反证：cmd+A/cmd+C 后 pbpaste|xxd = 4445 5420 202f 454e 4433

## 影响

静默数据损坏：Agent 以为写入了正确内容。用于填表/提交/发消息时会产生语义错误的输入而不自知（例如丢失 $ ! ( ) 使内容含义改变）；中文与 emoji 完全无法输入。危险等级高因为无任何错误信号

## 根因

SkyComputerUseService 用虚拟键码 + 当前键盘布局下发按键（字符串锚点：Unable to get current keyboard layout. / <SAIVirtualKeyPress: %d, %04x, %@>）。非当前键位可表达的字符无法生成键码，被静默丢弃。本机 HIToolbox 当前输入源为 SCIM.ITABC（中文），ABC 布局在启用列表但非当前项

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

绕过：set_value(element_index=<文本控件>) 零丢失；已验证 cmd+S 后落盘字节与输入完全一致
