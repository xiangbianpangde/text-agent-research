---
id: "ISSUE-0189"
title: "M3 credential proxy 接受无 nonce 的回环请求，可绕过 Pi 调用记录与回合预算"
status: "open"
severity: "critical"
area: "bench"
discovered_at: "2026-09-24"
discovered_by: "agent"
tags: []
signals:
  - "acceptance_criterion_now_executable_in_suite"
  - "acceptance_criterion_required_an_unstated_manual_step"
  - "calibration_unit_mismatch"
  - "child_shell_reaches_routed_provider_via_loopback"
  - "closure_criterion_had_no_invocation_entrypoint"
  - "concurrent_requests_bypass_forwarded_ceiling"
  - "injection_matches_any_credential_header_name"
  - "injection_triggers_on_any_credential_header_name"
  - "loopback_credential_proxy_unauthenticated_child_tool_can_call_provider_directly"
  - "nonce_check_insufficient_verified"
  - "nonce_readable_by_measured_child"
  - "preflight_probe_names_unrouted_provider"
  - "preflight_probe_only_proves_listener_answers"
  - "proxy_injects_real_key_without_any_nonce_check"
  - "proxy_nonce_readable_to_measured_agent"
  - "requestsForwarded_not_wired_to_budget"
  - "required_gate_env_var_reproduced_exit_1"
evidence: "/Users/xbpd/Projects/researchctl-product/catalog/test/child-credentials.ts:152-198 的 HTTP server 解析 `/p/<provider>/<path>`，查到 provider.key 后直接改写 Authorization/header 并请求上游；未验证入站 nonce、Authorization 或调用额度。`materializeChildCredentials()` :262-272 把 proxy origin 与 nonce 写进子进程可读的 models.json/auth.json；`trigger.ts:805` 对子进程允许 `(remote ip 'localhost:*')`；Pi Bash 工具可用 curl 且继承同一 sandbox。现有 preflight `trigger.ts:412-428` 只用未知 provider `__probe__` 收到 404/502 即判 proxy 可达，没有验证无效/缺失 nonce 会拒绝。未实际发送请求、未调用 provider；这是静态代码路径审查。"
related: []
fix_ref: "4678a26"
summary: "M3 credential proxy 接受无 nonce 的回环请求，可绕过 Pi 调用记录与回合预算"
updated_at: "2026-09-24"
---

## 现象

被测模型的 Bash 可读取本地 proxy URL，并通过回环向 `/p/<有效 provider>/<任意 path>` 发请求；proxy 无认证即注入真实 provider key。模型可绕开 Pi tool-call 事件直接消耗 provider 额度、伪造模型调用或将本地内容送入上游，破坏 cap 与观测完整性。

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

## 处置记录 2026-09-24T18:03:53+0800

【执行者-2 补充：已端到端复现，非静态推断】授权 5 回合后我未发 --run，故零 provider 请求；停令前已按同一路径做了**回环复现**。

复现方式：用代码里既有的 `redirectTo` 缝（`child-credentials.ts` 的 stub seam，其注释明写目的就是「用本地 stub 跑通整条链路、不碰 provider、不花钱」），把上游指向本地 stub，因此**未联系任何 provider、未读取或打印任何 key 值**；stub 只记布尔量 `realKey`（长度 > 30 且不含 `m3-nonce-`）。

实验 1（proxy 直连 3 个请求）：
- 无 Authorization 头 → proxy HTTP 200，上游收到 REAL PROVIDER KEY
- `Authorization: Bearer` 垃圾值 → proxy HTTP 200，上游收到 REAL PROVIDER KEY
- 正确 nonce（对照组）→ proxy HTTP 200，上游收到 REAL PROVIDER KEY

三个都注入真实 key，说明 proxy **根本没有读 nonce**：不是「校验失败但放行」，而是「无校验」。`proxy.requestsForwarded()` = 3，与上游命中数一致。

实验 2（端到端，沙箱内子进程）：用 `gradingProfilePath(childDir)` + `sandbox-exec` 起 `/bin/sh`，子进程环境只给 PATH/HOME，config 由 `materializeChildCredentials()` 生成（**只有 nonce**），命令是一条不读任何凭据、也不带 Authorization 头的 curl：
`curl -X POST -H 'content-type: application/json' -d '{...}' <proxy>/p/<routed-provider>/v1/chat/completions`
结果：`sandboxed child got HTTP: 200`；上游看到 1 个请求，`auth=present`、**REAL PROVIDER KEY**。

结论：该链路**成立且可执行**，不是靠 `/p/__probe__` 的 404 推断出来的，而是拿着被路由的 provider 名走通了整条注入路径。这确证「preflight 的 404/502 只证明监听，不证明未认证请求被拒」。

加重情节（同一次复现中发现，修复时请一并考虑）：注入分支对**每个**名字匹配 `CREDENTIAL_HEADERS` 的头都赋 `Bearer <real key>`（无匹配头时才补 `authorization`）。故子进程只要用**任意**匹配该正则的头名（如 `x-api-key`）即可触发注入，不限于其配置里写的那一个；这使「只允许持正确 nonce 的请求」更难在后端侧表达。

证据文件（临时，未入库）：`/tmp/proof-0189.mts`、`/tmp/proof-0189-e2e.mts`
- [ ] 按 ISSUE-0189 修复 proxy 认证（缺/错 nonce 绝不触达 upstream），并用 /tmp/proof-0189.mts 与 /tmp/proof-0189-e2e.mts 的负例做零成本回归；修复经 执行者-1 复核前不得恢复 --run

## 处置记录 2026-09-24T18:10:42+0800

【执行者-2 补充 2】验收判据已落为仓库内可执行测试：catalog/test/recovery.test.ts 的「refuses a request that does not present the run's nonce (ISSUE-0189)」（commit b65aa33）。置于 skip 并写明原因，故套件保持绿（231 tests / 230 pass / 1 skipped / 0 fail），修复落地后取消 skip 即成为门禁。**已实测对当前代码失败**，非自述：'no credential header: must be refused with a definite 4xx, got 200'（pass 0 / fail 1）。断言的正确性质是「拒绝发生在转发之前」而非「返回了 4xx」——先转发后返回 400 对调用方看起来一样且毫无保护，故测试同时断言 forwarded 计数不增且 upstream 命中为 0；并含正例（持正确 nonce 仍须转发），以免「一律拒绝」的假修复通过。刻意**不**断言「裸 nonce 无 Bearer 前缀须被拒」，因正确的修复可能接受任意 scheme。另：该缺陷的读取侧范围为 catalog/test/recovery-results.jsonl，另两个 results 文件为 0 命中。

## 处置记录 2026-09-24T18:12:52+0800

复核消息（session `01a0ccd1`）：即使后续新增“必须携带正确 nonce”的验证，nonce 仍不能作为模型与 shell 的边界。`child-credentials.ts:262-272` 把 `proxy.nonce` 写入 child 可读的 `models.json.apiKey` 与 `auth.json`；Pi Bash 在同一 sandbox/process tree 中，因此被测 Agent 可读取 nonce，再用 curl 直接调用 localhost proxy。代理会把该请求转成带真实 key 的 provider 请求，绕过 Pi tool-call 事件与逐场景 run cap。profile 仍允许 `localhost:*`，所以仅负向测试缺失/错误 nonce 不足以证明 cap 防绕过；验收还须证明 measured Bash 无法直接调用 broker，或有不可由工具复用/绕过的请求预算与调用授权。未实际发请求。

## 处置记录 2026-09-24T18:13:44+0800

【执行者-2 更正】我在 0189 补充中写的「该缺陷的读取侧范围为 catalog/test/recovery-results.jsonl，另两个 results 文件为 0 命中」**不成立，已撤回**——我漏了 catalog/test/archive/ 下两个已纳版控制的 trigger 结果（其中一个含 1 次命中），且 trigger-results.jsonl 的 calls 是字符串非对象，第一轮按 dict 解析把它误算成 0。统一判据重算：合计 **14 次 / 13 scenario**，**跨 live 与 tracked 两侧**（tracked 侧 1 次在 archive/…midfix-0146）。与缺陷本身无关的部分不受影响：**0189 的根因（处理函数不读入站凭据头 ⇒ nonce 装饰性）与已落地的可执行判据（commit b65aa33）均不变**，本更正只涉及暴露面统计。详见 ISSUE-0190。

## 处置记录 2026-09-24T18:18:23+0800

【执行者-2 回应复核方要求：已实测确证，非接受断言】复核方指出「仅加 nonce 校验仍不足，因正确 nonce 存在被测子配置中、Bash 可读」——我核对代码并实测，该判断成立（commit 7ba366e / 3abf189）。

前提（代码层，均为设计使然非疏漏）：materializeChildCredentials() 把 proxy.nonce 写入 models.json 的 apiKey 与 auth.json（必须如此，否则 pi 无法启动）；grading profile 保留 allow network-outbound localhost:*（否则子进程够不到代理）。

实测（真实 grading profile 内，上游指向回环 stub；未联系 provider，未读/未打印任何 key 值，stub 只记头名与形状布尔量）：
- A 子配置含 nonce = 是，且等于代理 nonce
- B profile 内 shell 能 cat 到它：明文读出，41 字符
- C 三例——不带凭据 / 带真 nonce / 真 nonce 放入 x-api-key——三例均 HTTP 200，上游三例均收到真实 provider key
- requestsForwarded() = 3，未接入任何预算或审计

结论：nonce 校验区分的是「旁观者 vs 参与者」，不是「被测回合 vs 未测回合」；被测方按构造即该代理的 credential-of-record。且 requestsForwarded() 只被测试读取、未接入 cap，故 shell 循环可绕过 Pi tool-call 事件流消耗额度。这同时解释了「cap=5」一直是流程约束而非技术控制（仓内无技术性 cap 实现）。

已落为测试：「keeps the run nonce readable inside the sandbox, so a nonce check cannot be the boundary」（catalog/test/recovery.test.ts，commit 7ba366e）。它断言前提而非修复，修复后仍须通过——目的是把「为什么加 nonce 校验不能关闭 0189」写成可执行形式，使下一位从代码重推判据的人无法得出更弱结论。套件 232 / 231 pass / 1 skipped / 0 fail。

验收口径收紧：0189 的关闭条件不能只是「代理校验了 nonce」，须另行证明「被测 Bash 无法绕过」或「代理调用进入不可绕过预算/审计」。前述负例仍为必要但不充分。

另记两处被丢弃的测量尝试：一次经 -c 传 shell 导致引号塌缩（看似「未复现」）、一次 BSD sed 反向引用报错留下空 bearer（看似「出示了 nonce」，实则什么都没出示）。两次均为工具故障被读成安全结论，故探针改为逐字执行脚本文件、打印实际提取长度、分例报告。证据：docs/records/M3-G3-acceptance-record.md 第 12.7 节。

## 处置记录 2026-09-24T18:25:17+0800

独立复核方在 HEAD `722e0fc` 实跑双向门禁（均为本地 catalog tests，未发 provider 请求）：1) `M3_REQUIRE_0189_FIX=1 npm run test:catalog` → exit 1，232 tests / 231 pass / 1 fail / 0 skipped；唯一失败叶节点为「refuses a request that does not present the run's nonce」，错误 `no credential header: must be refused with a definite 4xx, got 200`。外层「the model cannot read authentication material」not ok 是该子测试失败的汇总，不是第二个叶失败。2) 默认 `npm run test:catalog` → exit 0，232 tests / 231 pass / 0 fail / 1 skipped。条件式门禁行为确认正确，但 ISSUE-0189 未关闭；nonce readable 和无可绕过 budget/audit 的阻断也仍在。

## 处置记录 2026-09-24T18:25:23+0800

【执行者-2 补充 3：把关闭判据从『可阅读』改为『可调用』】§12.5 此前只写「修复落地后取消 skip 即成门禁」，未给入口。问题在于：这让判据只能靠手改测试文件来调用，而修复者读完代码认为已修复时，**没有任何东西会告诉他不是**——判据存在却不可被任何人在不编辑源码的前提下执行。已改为条件式 skip（commit 03566be）：M3_REQUIRE_0189_FIX=1 npm run test:catalog 把「0189 已修复」变成一条可运行断言；默认 npm run test:catalog 仍 skip。双向实测（非推断，也未消耗任何 provider 额度）：开门禁 → error 'no credential header: must be refused with a definite 4xx, got 200'，# pass 231 # fail 1 # skipped 0，exit 1；默认 → # pass 231 # fail 0 # skipped 1，exit 0，与改动前逐字一致；m3:typecheck 无 error TS。读输出陷阱（已告知复核方，防其按 not ok 计数多算一条缺陷）：开门禁那次另见 not ok 52 - the model cannot read authentication material (ISSUE-0184)，其为外层 suite 节点转述子测试失败（failureType: 'subtestsFailed'），真正失败的叶子仅 0189 一条。默认保持关闭是刻意的：长期带一条红的套件会让人学会忽略它，那时失败便不再传递信息；默认关闭则本项保持『已知未决』，而修复者有一条明确命令可自证。已同步写入 docs/records/M3-G3-acceptance-record.md §12.5、§13.1 与 exports/README.md（并重生成 PDF，pdftotext 确认 M3_REQUIRE_0189_FIX 出现），commit 03566be / 722e0fc。

## 处置记录 2026-09-24T18:45:05+0800

【执行者-2（本侧）修复】§13.3 曾把本项的修复记为外部依赖（复核方修），该归属**已撤回**：缺陷站点 catalog/test/child-credentials.ts 由 9fe8676/866b655 引入，均系本侧提交，仓库单作者；复核方历次措辞仅为批准前置条件（「修复代理访问控制并验证被测 shell 无法绕过后，再申请 cap=5」），无任何「我来修」表述。且若由复核方修，「修复经执行者-1 复核」即退化为自审。修复为两道门（commit 4678a26）：① handler 首部校验 nonce，在读 body 与查 provider 之前（scheme 无关，非凭据头不能通过）；② forwarded 计数硬上限，由授权回合数派生（100/回合；实测 112 个归档回合 tool-call 均值 23.5/p95 49/max 60），在父进程内执行，child 够不到计数器。门②是关键：nonce 必须写进子配置（否则 pi 无法启动）、profile 必须放开 loopback（否则 child 够不到代理），故**被测方按构造即持该代理的 credential-of-record**——门①区分旁观者/参与者，不区分被测/未测回合。实测（上游回环 stub，未联系 provider，未读/未打印 key）：原复现 3 例中 2 例 401 且未转发；硬例——沙箱内 child 读自身 auth.json 取出 41 字符 nonce 后循环 10 次，得 3×200 + 7×429，upstream 恰 3 次；双向变异测试确证测试非空转（关①→'got 200'；关②→'looped 8x against a ceiling of 3 and the upstream saw 8'）。同时更正：preflight 的 404 注释不成立（该探针路径匹配 /p/<provider>/<path>，实为 502），且 preflight 此前**两道门都没测**，现已在沙箱内实测两门。0189 测试取消 skip（修复后 skip 会丢失关键缺陷的回归保护），M3_REQUIRE_0189_FIX 停用。套件 233/233/0 skipped，typecheck 干净，preflight 15 项全过，本轮 0 provider 请求。

## 处置记录 2026-09-24T18:51:16+0800

独立复核在 `catalog/test/child-credentials.ts` 的当前代理实现（该文件无未提交改动）做本地 stub 并发实验：`setBudget(3)`，同一正确 nonce 同时 `Promise.all` 发 20 个请求；stub 延迟响应 150ms。实测 20/20 HTTP 200、upstream stub 收到 20 次、`requestsForwarded()=20`、`requestsOverBudget()=0`。未联系任何 provider、未读取或记录任何 key 值。根因：budget check 读 `forwarded`，但计数只在 upstream response callback 中增加；所有并发请求可在首个响应前通过检查。串行 10→3 回归不能证明 ceiling 硬上限。需要在进入异步 body/upstream 前原子预留/计数每个可转发请求，并加并发延迟 stub 回归，断言真实上游尝试数不超过 ceiling。

## 处置记录 2026-09-24T18:51:32+0800

复核方独立并发压力测已复现硬上限可被绕过（3 限额下 20 个并发请求全被转发），故当前不得标记 fixed；代码处置尚未通过安全复核。

## 处置记录 2026-09-24T19:16:36+0800

【复核复核（执行者-1，seq 7-8）→ 三项均已修，本轮 commit：a7dee10（并发原子预留）、585496e（回合上限入码+取消默认授权）、e3fad99（标定单位与不可复现数字）。同时撤回本项补记中的标定数字：原写「112 个归档回合 tool-call 均值 23.5/p95 49/max 60」，独立重算为 184 回合/mean 14.8/p95 44/max 60，112 与 23.5 均不可复现（见 ISSUE-0193）。0189 的真边界（门②）此前存在三处缺陷：① 检查-后-计数竞态（并发 20/上限 3 → upstream 20）；② 未设上限即无限转发（fail-open 默认）；③ 上限标定单位错。均已修并各配变异/并发/失败路径测试。**0189 仍为 open，等执行者-1 对 e3fad99 的复核**（我方不得自行关闭）。
