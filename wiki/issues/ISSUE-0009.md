---
id: "ISSUE-0009"
title: "computer_use click 坐标系是窗口局部坐标、且绑定会在未重新取状态时陈旧"
status: "open"
severity: "high"
area: "pi-extension"
discovered_at: "2026-09-16"
discovered_by: "agent（实测 + 官方二进制 strings + Pi 扩展源码）"
tags:
  - "computer-use"
  - "coordinates"
  - "window-binding"
signals:
  - "window_not_found"
evidence: "~/Projects/computer-use-boundary-test/evidence/EVIDENCE.md#E2；窗口真值由 osascript AX 枚举取得；审计 ~/.pi/agent/direct-computer-use/audit/direct-computer-use.jsonl"
related: []
fix_ref: null
summary: "computer_use click 坐标系是窗口局部坐标、且绑定会在未重新取状态时陈旧"
---

## 现象

按截图像素或屏幕绝对坐标点击会落在错误位置；窗口移动后未重新快照的动作按过期原点解析并报 windowNotFoundAtPosition

## 复现

坐标空间标定（用 click 越界报错 windowNotFoundAtPosition 作为 oracle）：

input(0,0)     -> 解析为屏幕 (146,71)   ; key window 在 (146,71)   => origin = 窗口原点
input(18,50)   -> 解析为屏幕 (164,121)  ; +18/+50 精确成立
input(0,1000)  -> 解析为屏幕 (146,1071) ; 1:1，无 Retina 缩放
input(0,700)   -> 解析为屏幕 (400,1000) ; 窗口已移到 (400,300)，origin 同步刷新
input(0,2000)  -> 解析为屏幕 (150,2420) ; 再次刷新

结论：click/drag 坐标 = key window 左上角为原点的窗口局部逻辑点，1:1，原点在每次取状态/动作时刷新。
截图不是坐标系：get_app_state 截图约 600x510 px（窗口 603x505 pt 的 2x Retina 渲染），照抄像素坐标会偏移。

窗口绑定（binding 陈旧 + 焦点无关）：
1) 未命名.rtf 被移到 (400,300) 后，未重新快照的 click(0,0) 仍按旧 origin (820,220) 解析
   -> windowNotFoundAtPosition((820.0, 220.0))   [陈旧绑定直接证据]
2) 重新 get_app_state 后 origin 正确变为 (400,300)
3) 用 AX 把 typed.txt 设为 AXMain 后，get_app_state 仍返回 未命名.rtf
4) 随后一次 click 命中 typed.txt 区域，绑定即切换为 typed.txt（此后快照为 typed.txt）
5) 前台 app 实测为 "stable"（非 TextEdit），不影响 binding

多窗口不可达：任一时刻快照只含 1 个窗口；menu bar 仅作节点列出，无坐标动作。

## 影响

盲点点击：坐标语义未在任何官方文档/SKILL.md 中说明，官方 macos/computer.md 仅 140 字节（只讲 cua.getApp）。照抄截图坐标会静默点错，Agent 可能误改真实 UI（发送/删除/提交）

## 根因

坐标由官方 Computer Use 服务按 active-app lease 选定的窗口换算；绑定窗口与其原点被缓存，只有重新取状态才刷新。Pi 扩展 ARCHITECTURE.md 记录 '获取状态后紧邻的一个动作共享同一 runtime/thread 以保活 lease'

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
