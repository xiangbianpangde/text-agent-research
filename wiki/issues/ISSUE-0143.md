---
id: "ISSUE-0143"
title: "test-product 缺研究项目根时打印 SKIP 后仍以 0 退出并输出 ALL PASS，且 test:legacy 入口传裸 --root 从不执行"
status: "fixed"
severity: "critical"
area: "researchctl-cli"
discovered_at: "2026-09-23"
discovered_by: "agent"
tags: []
signals:
  - "gate_exits_zero_without_running_any_suite,skip_rendered_as_all_pass,broken_npm_entrypoint_never_executes_suites,fail_open_gate"
evidence: "修复前（fa7ea21 之前）实证：cd /tmp/headchk && python3 -m researchctl.tests.test_product --legacy; echo $? → 'SKIP: 未找到研究项目根' 后紧跟 '结果: ALL PASS'，exit=0；python3 -m researchctl.tests.test_product --legacy --root /nonexistent → 同样 'SKIP: 指定的根不是有效研究项目' 后 '结果: ALL PASS'，exit=0。另：researchctl-product/package.json 的 test:legacy 原为 'python3 -m researchctl.tests.test_product --legacy --root'，裸 --root 触发 argparse 'expected one argument'，exit=2，该入口在任何环境下都只打印 usage 错误；在 fresh checkout 上实测 'npm run test:legacy' → exit=2 且从未运行任何套件。修复见 fa7ea21。"
related: []
fix_ref: "researchctl-product@fa7ea21"
summary: "test-product 缺研究项目根时打印 SKIP 后仍以 0 退出并输出 ALL PASS，且 test:legacy 入口传裸 --root 从不执行"
updated_at: "2026-09-23"
---

## 现象

门禁以「未运行」冒充「已通过」，且失效方向是最危险的一侧：一个从未跑过任何 legacy 套件的环境（fresh checkout、CI、新 worktree）与真正跑过 443 checks 的环境在退出码上完全一致（均为 0），差别只在一行 stderr 文本。同时 test:legacy 入口因裸 --root 从未执行，使「443 checks 无回归」这一 G0 条件在自动化路径上长期不可达且无人察觉——因为两条路径都不报错。正确语义：SKIP 必须有自己的退出码（已定为 2 INCOMPLETE），需显式 --allow-skip 才回到 0；入口必须可执行并被回归测试锁定。

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

## 处置记录 2026-09-23T08:50:42+0800

已修复：退出码 0=通过/1=失败/2=INCOMPLETE（套件未运行）；--allow-skip 显式恢复旧语义并在输出中标注；test:legacy 去掉裸 --root，另加 test:legacy:fresh 走 --materialize 一站式路径。新增 4 条回归测试锁定退出码语义、无效根不静默降级、npm 脚本无裸 --root；变异验证（回退退出码判定 → 3 条测试变红）。
