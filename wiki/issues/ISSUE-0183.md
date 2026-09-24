---
id: "ISSUE-0183"
title: "M3 沙箱拒绝 ~/.pi/agent 致子进程无法启动，语料把装置故障记成模型行为（零调用零 token）"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "sandbox_denies_agent_config_dir child_cannot_start_eprem_trust_lock zero_call_zero_token_recorded_as_empty_turn apparatus_fault_as_model_behaviour pi_coding_agent_dir_missing npm_reinstall_eats_turn_budget settings_packages_reinstall child_exit_code_discarded"
evidence: "实测链：给 deny 列表加 `/Users/xbpd/.pi/agent` 后实跑 `sandbox-exec -f deny.sb pi --version` → rc=0（不加载配置，故无感）；`pi auth print-api-key --provider google` → stderr `Error: Failed to resolve credential`；`pi --help` → `Error: EPERM: operation not permitted, mkdir '/Users/xbpd/.pi/agent/trust.json.lock'`（stack: acquireTrustLockSync）。真实回合（rec-semantic-document-added，digest 035fb5c59f57fef8）落盘 calls=0、input/output tokens 均 null、无 error 字段，仅 `inconclusive: 0 empty turn(s)`。修复①：保留 deny + `PI_CODING_AGENT_DIR` 指向私有配置目录（白名单 6 文件）。修复后 rc=0。修复②：私有目录无 package.json → 每回合跑完整 `npm install`，实测 stderr 四轮 `added N packages, and audited N packages`（63s，最长 >190s），240s 截止到期；补 package.json 后 `pi list` 由 63s 降至 0.9s、npm 行 0。修复③：复制 settings.json 原样带 `packages` 列表 → 子进程仍重装（同一 hang 的第二条路径）；剔除 packages/extensions/skills 后 0.9s。修复④：`child.on('close', () => finish())` 丢弃退出码 → 启动即死与模型沉默不可区分；现按非零退出 + 空回合记 apparatus error。最终验证：rec-semantic-document-added PASS，27 次真实调用，tainted=false，digest 56a6074f4764bc9a；test:catalog 220/220。"
related:
  - "ISSUE-0146"
  - "ISSUE-0151"
  - "ISSUE-0152"
  - "ISSUE-0179"
fix_ref: null
summary: "M3 沙箱拒绝 ~/.pi/agent 致子进程无法启动，语料把装置故障记成模型行为（零调用零 token）"
---

## 现象

沙箱为围堵答案而拒绝 `~/.pi/agent`，而该目录同时是 pi 自身凭据与 trust 锁的所在：子进程启动即失败（EPERM mkdir trust.json.lock → No API key found），回合以**零工具调用、零 input token、无 error 字段**结束——与「模型没说话」在落盘形态上**逐字节相同**，故 `isEmptyTurn` 把它记成模型的空回合。三处独立缺陷叠加才呈现为「模型无输出」：配置目录被拒、缺 package.json 触发每回合 npm 重装、settings.json 的 packages 列表二次触发重装。每修一个才暴露下一个。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

若未发现：cap=6 的 6 个回合会被记成「模型未产生回合」并全部计入 inconclusive，用户会看到一次「跑了但模型不答」的结果，而实际**一个模型都没被问过**；已花掉的 3 个回合全部落在装置侧。若这套装置曾用于往期读数，同一形态的故障会把装置问题永久记成模型能力问题（本项目第 4 次同型：ISSUE-0146/0151/0152）。此外该缺陷会**反向作用于严格性**：越收紧围堵越容易造出『模型不答』的假象。

## 根因

`~/.pi/agent` 同时承载两类内容：pi 运行所需的凭据/模型清单/trust 锁，与答案相关的技能源码/扩展/logs/session。围堵要求整体 deny，但 pi 启动要求可读可写，两者在**同一路径**上冲突。原 deny 列表只验证了『数据是否被隐藏』，从未验证『子进程能否启动』——preflight 的 8 项检查全过，而装置根本无法跑一个回合。叠加的两条 npm 重装路径使故障表现为 hang（240s 超时）而非即时崩溃，进一步远离真实原因。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）
