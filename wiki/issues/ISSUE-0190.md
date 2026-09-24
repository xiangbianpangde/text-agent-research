---
id: "ISSUE-0190"
title: "M3 早期回合的 env 继承把 3 个真实 API key 值送入模型上下文，需持有人轮换（代码修复不消除已发生的暴露）"
status: "open"
severity: "critical"
area: "env"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "archived_call_shape_14_not_24"
  - "counts_depend_on_unrecorded_rule"
  - "exposure_confined_to_recovery_results_jsonl"
  - "exposure_not_confined_to_one_file"
  - "live_api_key_values_entered_model_context requires_credential_rotation_unfixed_by_code fix_closed_channel_not_exposure archive_appendonly_cannot_be_scrubbed"
  - "self_correction_retracted_single_file_claim"
  - "tracked_archive_contains_one_exposure"
evidence: "暴露窗口 = 沙箱与环境擦除生效（commit 9fe8676，2026-09-24 14:50）之前的付费回合。机制：子进程继承 parent 环境，而 `PI_` 是 `API_KEY` 的子串，故模型为找本项目变量而自然写出的 `env | grep -i -E 'PI_|RESEARCH'` 会匹配到全部 `*_API_KEY`。实测选择面（本机环境变量名，只列名不列值）：`PARATERA_API_KEY`、`DEEPSEEK_V4_API_KEY`、`OPENROUTER_API_KEY` 三个**其值即凭据**；另有 `MINIMAX_API_KEY_FILE`、`PI_SESSION_FILE` 泄漏路径、8 个无害变量，共 13 个命中。归档内计数（`catalog/test/recovery-results.jsonl`，59 行）：符合条件的 `env|grep` 调用 13 次 / 12 个 scenario；同族的任何 `env|grep` 共 27 次 / 20 个 scenario；**与 commit 9fe8676 自述的「24 calls across 18 scenarios」不一致**（该口径未记录，无法复现，见下方备注）。重要边界（已核验）：**归档里没有 key 值**——`grep -cE 'sk-[A-Za-z0-9_-]{16,}|eyJ[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}'` 命中 0；只记录 call 的 `args`，不记 tool 输出。故这是**对 provider 的一次性实时暴露，不是持久化泄漏**——该区分决定处置强度，不应让「泄漏」一词夸大或缩小事实。另核验：归档中没有任何回合读过凭据文件（`auth.json|antigravity-accounts|models.json|models-store|vision.json` 命中 0 次调用）。"
related: []
fix_ref: null
summary: "M3 早期回合的 env 继承把 3 个真实 API key 值送入模型上下文，需持有人轮换（代码修复不消除已发生的暴露）"
updated_at: "2026-09-24"
---

## 现象

三个真实 API key 的**值**在付费回合中被 `env | grep` 打印并进入模型上下文（因而也发往了 provider）。源头 commit 9fe8676 已把该通道封死（环境擦除 + 凭据替换 + egress 关闭），但**修复通道不等于回收暴露**：这些 key 在暴露窗口内可能已被第三方（日志、provider 侧、后续归档）留存。ISSUE-0184 状态为 `fixed`，其 wiki 正文**未提及这三个变量名、也未登记轮换动作**，故单读 0184 会得出「已闭环」的错误结论——这是本节存在的理由。归档 append-only 且**不可擦除**（设计使然，见 9fe8676 对「safe by construction rather than cleanup」的论证），因此不存在「清理归档」这一选项，只有「轮换凭据」这一条路。

## 复现

（待补充：最小复现命令 / 输入 / 环境）

## 影响

残留风险限于持有这三个 key 的账户：密钥若仍有效，任何接触过该模型上下文的一方都能以其配额发起请求。影响面可控且可逆（轮换即消除），但**必须由授权持有人执行**，代码侧无法完成。不轮换的后果是：暴露窗口结束，但凭据本身仍等同于已公开。

## 根因

环境继承是默认行为，而「为本项目变量命名」的惯用词 `PI_` 恰好是 `API_KEY` 的子串——两个各自无害的设计相遇产生泄漏，且泄漏路径正是被测模型最自然的探索动作。更深一层：ISSUE-0184 的处置只覆盖了**通道**（通道已修，状态 `fixed` 合理），但**同一事件**还含一条运维动作（轮换），它不因通道修复而消失，却没有被登记到任何状态可追踪的位置。结构教训：一次暴露事件应同时登记「通道修复」与「凭据回收」两个可独立验收的动作，否则前者达成就地把后者一起标成完成。

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-24T18:10:45+0800

【执行者-2 补充】读取侧范围已收敛到单文件（非自述，按 call args 逐条解析）：catalog/test/recovery-results.jsonl = 14 次调用 / 13 个 scenario；baseline-results.jsonl（50 行，calls 为字符串）与 trigger-results.jsonl（25 行）= 0 命中。**与 commit 9fe8676 自述的 24 calls / 18 scenarios 不一致**，该口径未记录、无法复现，故不采用其数字。归档内 key 值命中 0，故仍为实时暴露而非持久化泄漏——处置强度（轮换）不因此改变，但「暴露面有多广」的陈述已收窄到一处。

## 处置记录 2026-09-24T18:13:40+0800

【执行者-2 更正】我先前在 0190 写的「读取侧限于单文件」**不成立，已撤回**。三个方法缺陷：(a) trigger-results.jsonl 的 calls 是字符串非对象，第一轮按 dict 解析把该文件漏成 0；(b) 仓库内 catalog/test/archive/ 还有两个**已纳入版本控制**的 trigger 结果，第一轮未查；(c) 我先引的「27/20」出自更宽松规则（会匹配 grep -i research 之类非凭据模式），与「选中凭据变量」不是同一件事，该数字作废。统一判据（该 env|grep 模式是否真的会选中凭据**变量名**，只读名不读值）重算全部 6 个结果文件：recovery-results.jsonl 13 次/12 scenario（59 行，gitignored）、trigger-results.jsonl 0（25 行）、baseline-results.jsonl 0（50 行）、archive/…midfix-0146 **1 次/1 scenario（tracked）**、archive/…allfix 0、archive/…pre-0146 0；合计 **14 次/13 scenario**。更正**双向**：(1) 暴露**并非限于单文件**，其中 1 次落在**已提交进版本库**的归档文件里——这比原先估计**更该重**，因该文件任何人可随时检出；(2) 9fe8676 的 24/18 仍复现不出（14/13），但这些结果文件被 gitignore 且已被改写，**无不可变历史可对账**，故我只能声明「以现存字节计 14/13」并注明这是**快照而非性质**，不能断言 24/18 为假。不受影响的结论：变量名层命中 4 个（三者的值即凭据：PARATERA_API_KEY / DEEPSEEK_V4_API_KEY / OPENROUTER_API_KEY；MINIMAX_API_KEY_FILE 是路径）；归档不含 key 值；无回合读过凭据文件。**处置（轮换）不因此改变**。
