---
id: "ISSUE-0178"
title: "pi-intercom: 'acknowledged' 回执被当作投递成功，且提示语谎称『已注入接收方上下文』；接收方忙且非交互时消息被静默丢弃"
status: "triaged"
severity: "critical"
area: "env"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "ack_not_delivery"
  - "acknowledged_ranked_above_injected"
  - "false_injection_claim"
  - "silent_message_drop"
  - "busy_noninteractive_receiver"
  - "receipt_as_proof"
evidence: "pi-intercom/reliable.ts:155 处 `if (status === \'injected\' || status === \'acknowledged\') { this.settle(active, \'acked\', undefined, \'...已注入接收方上下文（第 N 次尝试，\' + status + \'）\') }` —— status=acknowledged 时提示语仍声称『已注入接收方上下文』；reliable.ts:79-88 的 RECEIPT_RANK 把 acknowledged 记为 3、injected 记为 2，即把『被收下』排在『已注入』之上。pi-intercom/index.ts:1381 `emitMessageReceipt(receivedMessage.id, \'acknowledged\', \'accepted by receiver\')` 在 index.ts:1388 的忙闲判断**之前**发出；index.ts:1388-1405 分支：若 `!activeContext.isIdle() && !activeContext.hasUI`，则回一条『cannot respond』并 return —— 消息从未进入接收方上下文。实测：向 01a0ccd1 发送 handle 6396232d，receipts 显示 `✅ 01a0ccd1 [6396232d] acked, attempt 1/3, 9s ago`；发送时该 session 为 `[same cwd, thinking]`、上下文 98%（266k/272k），属忙态；用户随后确认『他没有收到』。佐证：channels.json 只有 channelId/members 而无消息存储，sessions-state.json 的 mailbox 为空数组（0 items），故该消息不存在任何可达副本。"
related:
  - "ISSUE-0176"
  - "ISSUE-0177"
fix_ref: null
summary: "pi-intercom: 'acknowledged' 回执被当作投递成功，且提示语谎称『已注入接收方上下文』；接收方忙且非交互时消息被静默丢弃"
updated_at: "2026-09-24"
---

## 现象

发送方被告知消息『已注入接收方上下文』并据此认为对方已收到，但接收方从未看到该消息。接收方处于忙态且非交互（subagent-chat）时，消息被接受、回执、然后丢弃，全链路没有任何一处报告失败——发送方拿到的是最强的成功信号（acked）。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

本仓库把『有回执』当作送达证据，而这类裁决/授权完全依赖送达：一条声称『已送达授权方』的申请若其实没到，等待就变成无限空等，且看起来一切正常。更严重的是同类错误方向——与 ISSUE-0176『把被拒的尝试当成读取』同族：都是拿代理信号（回执/尝试）冒充本体（送达/读取）。

## 根因

『被接收』(acknowledged) 与『进入上下文』(injected) 是两个不同事件，后者才是送达；但可靠投递把前者当作充分条件结清（settle），又在文案里把前者说成后者。回执在真正决定去留的分支之前发出，使得『注定被丢弃』的消息也先拿到 acknowledged。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-24T09:45:39+0800

已独立复核：发送句柄 6396232d 与 76f287cd 均**已送达**（接收方 session 转录 idx=580/665，display:true，元数据 injected；接收方并在 idx=667 回复确认）。故原『消息被静默丢弃』的判定不成立，本条降级为『回执文案与排名语义误导』：reliable.ts:155 把 acknowledged 与 injected 等同结清、RECEIPT_RANK 把 acknowledged(3) 排在 injected(2) 之上，且对忙态接收方的丢弃分支不产生任何失败信号——发送方无从区分『已注入』与『已接受但被丢弃』。根因（拿代理信号冒充本体）仍成立。
