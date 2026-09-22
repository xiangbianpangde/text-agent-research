---
id: "ISSUE-0094"
title: "同一仓库两个 worktree 各自把 research-retrieval 技能从 1.0.0 独立演进到 1.1.0，语义版本号冲突且语义不同"
status: "open"
severity: "medium"
area: "wiki"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "skill-version-collision,cross-worktree-semver-collision"
evidence: "git worktree list：main=01b4cd0(/Users/xbpd/Projects/文字Agent检索系统)，product/researchctl-pi-retrieval-journal=6f7d4cc(/Users/xbpd/Projects/researchctl-product)。两处技能基线同为 01b4cd0 的 v1.0.0。main worktree 未提交改动把 SKILL.md 改为 version 1.1.0、CHANGELOG 日期 2026-09-15（内容是 DSH 对齐 + 日志自优化，mtime Sep 16），而 _2.01b4cd0 refactor: reorganize project structure into docs/ and bench/reports/ 28eeef5 docs & chore: format files, add README, license, and pytest config aa5dfae docs: checkpoint P1B baseline solvability (CP-0016) 1499ff0 feat(bench): independent-filegraph-v1 baseline + B1 workspace ledgers - 48/48 public instances solvable at score 1.0 49d7f73 docs: checkpoint P1B canaries + evaluation engine (CP-0015) 0c78ae1 chore(bench): re-issue P0.4 attestation under P1 harness bytes (25a07a30...), add run_seed transport 926e704 feat(bench): P1B evaluation engine - prediction/v2, run-seed schedule, same-runner repetitions, missingness 737aa7b feat(bench): P1B hidden-validity/v1 with 16 deterministic canary probes - all blocked under sandbox-exec 0b043ce docs: checkpoint P1B campaign progress (CP-0014) df3d456 feat(bench): P1B campaign runner (T0-T3 with opening verification) + participant tar binding a9ba0e6 feat(bench): P1B campaign lifecycle state machine - 9 states, 9 transitions, commitment formulas, event chain 617175d feat(bench): P1A gate runner (G01-G08 all PASS), frozen source-tree closure, regenerated public root 32ec1bc test(bench): P1A G01-G08 mechanical acceptance gates - all pass 39e8082 docs: checkpoint P1A generator completion (CP-0013) 6d7a10e feat(bench): P1A universe generator, 8 task families, 144-instance quota, public root with byte-identical rebuild 01f208a feat(bench): P1A generator foundations - cjson, KDF, tree, task families, identity chain c9d8a37 docs: freeze ResearchCTL-Bench P1 contract after Sol audit PASS (aad0919c) 8c20d80 docs: checkpoint completed P0 harness state 2385e91 feat(bench): complete P0 negative-control harness c47e3b5 feat(bench): cut over to Oracle-only evaluation be62ec1 fix(bench): close P0.3B Oracle trust gaps 0d20baa feat(bench): migrate all scenarios to Oracle shadow 9c3209f feat(bench): establish P0 harness and Oracle shadow b1ce835 feat(bench): 落地 ResearchCTL-Bench 基准评测套件与自动化评分引擎 (32类场景/宪法级指标/S级认证) 6172109 docs: 闭合 Sol 终审指出之 7 大 P1 机械合同规范 (DSL Schema, Envelope Schema, Precedence Arbiter, CLE 算法等) 3c6ac85 docs: 编制《ResearchCTL-Bench》评测方案 v1.0 规范，闭合全部 P0 与 P1 机械合同 39618bc test: 固化 Sol 终审建议反例 N1-13（frontmatter 优先于 document ID 匹配），全系统 443 项测试全绿 39cf0bd fix(audit): 闭合 P1-5（manifest_tmp 临时文件原子清理保证）与 P1-8（删除 H003 硬编码与非 frontmatter 关联），全量 442 项测试通过 4e71142 fix(audit): 闭合 Sol 第二轮审阅指出的 5 个 P1 阻断项（版本精确存在性、ingest 失败原子回滚、严格 spec 存在性、方案 §12 原文四维导航与五态分类） fa111f8 fix(audit): 闭合 Sol 实现级复审全部 9 P1 与 9 P2（严格路径约束、前置存在性校验、方案 §12 原文四维导航、新鲜度门禁、全对抗性测试） 2183091 feat: 实现 INDEX.md 四维导航自动生成 (方案 §12) 与 Raw Ingest Hook (方案 §14) edab130 docs: 增加技术软件架构图 (technical-architecture) 并完善汇报文档 5909f16 docs: 增加组会汇报架构全景图与配套展示文档 (遵循 wendang 嵌入标准) 0ee07ff feat(pi): 增加 Pi 检索工具扩展 research.ts 封装 researchctl 核心命令 7dd0bd8 feat(cli): 暴露 researchctl impact 命令支持逆向依赖与影响链查询 b884569 P1-C: 实现 Semantic Retrieval 语义检索与 V1–V23 全部验收测试 fc7b15e P1-C-Contract rev12: 已确认(冻结, 2026-09-03) — Sol GO c2c9007 P1-B 实现修复第八轮（Sol 实现级复审 1 P1 + 1 P2 全部闭合） 4849139 P1-B 实现修复第七轮（Sol 实现级复审 2 P1 + 1 P2 全部闭合） 5511435 P1-B 实现修复第六轮（Sol 实现级复审 2 P1 + 2 P2 全部闭合） d44c6e4 P1-B 实现修复第五轮（Sol 实现级复审 2 P1 + 2 P2 全部闭合） 9bced55 P1-B 实现修复第四轮（Sol 实现级复审 4 P1 + 2 P2 全部闭合） 11012bd P1-B 实现修复第三轮（Sol 实现级复审 5 P1 + 4 P2 全部闭合） 344cc7f P1-B 实现修复第二轮（Sol 实现级复审 10 P1 + 3 P2 全部闭合） db475f2 P1-B 实现修复（Sol 实现级复审 P1-1/P1-2/P1-3 + P2-1） 0ecd49b P1-B Definition Evolution 实现完成（rev11 冻结，已验收） f415154 P1-A: freeze-report 事务闭环实现 (Evented Historical Freeze) 5f882fa P1-A-Contract rev11: 已确认(冻结, 2026-08-31) — Sol GO ab09d25 P1-A-Contract rev11: Sol rev10 复查修订 (WAL cleanup 收紧 + P2 残留) b885a63 P1-A-Contract rev10: Sol rev9 复查修订 (WAL 生命周期 + P2 残留) 1cdb7bb P1-A-Contract rev9: Sol 窄范围 NO-GO 修订 (P1-1~P1-4 + P2 残留) 92c6574 P1-A-Contract rev8: Sol 审核 NO-GO 修订 (P1-1~P1-3 + P2-1~P2-10) 3c503cf P0-P1A: researchctl 检索内核 (P0-A/B/C 完成) + 合同 (P0-Contract, P1-A-Contract rev7) + 设计文档 在两处都只显示 fa111f8 一条。"
related: []
fix_ref: null
summary: "同一仓库两个 worktree 各自把 research-retrieval 技能从 1.0.0 独立演进到 1.1.0，语义版本号冲突且语义不同"
---

## 现象

两个 worktree 从同一基线各自独立声明同一语义版本号 1.1.0，内容完全不同且互不知晓；merge 时 CHANGELOG 与版本号无法自动区分，容易丢掉一方的行为变更

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
