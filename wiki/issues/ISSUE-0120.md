---
id: "ISSUE-0120"
title: "M1_P4A 门禁工具 :sol/3/P0P1_CLOSURE_AUDIT.py 不在 reviewed/attested artifact 范围内；SHA256SUMS 不可重定位且部分过期"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "archive_package_closure_is_exact_1917_equals_1916_plus_reserved_self_path"
  - "independently_corroborated_by_reviewer_gate_mutation_invisible_to_package_attestation"
  - "root_cause_found_layout_migration_cf1851c;gate_retains_old_pilot_campaign_path_after_flat_results_migration"
  - "scorecard_check_paths_are_parent_and_results_pilot_campaign_candidates_but_archive_ships_results;reviewer_accepted_set_algebra_2026-09-22"
  - "sol_gate_instrument_unattested"
  - "sol_tracked_and_tamper_detected_by_git_silent_only_in_zip;sol_sums_stale_for_2_of_8_entries_not_tampered"
evidence: "review_v77.zip 1946 entries 全为 review_v77/ 前缀，:sol entries=0; attestations/M1_worker_protocol_attestation.json artifacts=1916 全为包内相对路径，无 :sol 键; git ls-tree -r adf16ffc902f --full-tree --name-only -- ':(literal):sol' = 54 files（同仓库、且在绑定 commit 内），门禁脚本 commit/worktree SHA-256 均为 ef5c7c2c47bb9c36...; SHA256SUMS 8/8 使用 /mnt/data 绝对路径，当前环境 shasum -c 不可读，按 basename 重定位后 5 MATCH / 2 DIFFER / 1 MISSING。"
related: []
fix_ref: null
summary: "M1_P4A 门禁工具 :sol/3/P0P1_CLOSURE_AUDIT.py 不在 reviewed/attested artifact 范围内；SHA256SUMS 不可重定位且部分过期"
updated_at: "2026-09-22"
---

## 现象

决定 M1_P4A 是否 GO 的门禁脚本由人工引入 `:sol/3/`，虽然在绑定 commit 内受 Git 跟踪且当前工作树与该 commit 逐字节一致，但它不在 `review_v77.zip` 或包 attestation 的 1916-artifact closure 中。因而 zip-only 消费者无法独立验证实际决定 GO/HOLD 的工具；实测仅改写该工具时包内 attestation 仍 rc=0。另有 8/8 校验和路径写死 `/mnt/data`，按 basename 重定位后仅 5/8 匹配、2/8 过期、1/8 缺失。

## 复现

环境：`/Users/xbpd/Projects/benchmark`（含 `:sol/`），绑定 commit `adf16ffc902f`。

```bash
# 1. 门禁工具存在于绑定 commit 且与工作树逐字节相同（未被篡改）
cd /Users/xbpd/Projects/benchmark
git cat-file -e 'adf16ffc902f::sol/3/P0P1_CLOSURE_AUDIT.py' && echo PRESENT
git show 'adf16ffc902f::sol/3/P0P1_CLOSURE_AUDIT.py' | shasum -a 256   # ef5c7c2c...
shasum -a 256 ':sol/3/P0P1_CLOSURE_AUDIT.py'                          # ef5c7c2c... 相同

# 2. 但它不在受审产物内：包 attestation 覆盖 0 个 :sol 路径
unzip -l /private/tmp/rev/review_v77.zip | grep -c ':sol'    # 0
cd research-retrieval-benchmark
python3 tools/attestation_policy.py --package-root .          # rc=0, 1916 paths

# 3. zip-only 消费者无法感知门禁被改写（本 issue 的核心风险）
head -c 200 /tmp/gate_orig.py > ':sol/3/P0P1_CLOSURE_AUDIT.py'   # 模拟改写
cd research-retrieval-benchmark && python3 tools/attestation_policy.py --package-root .
#   => rc=0 「0 stale」：包内 attestation 未察觉
# 对照：有 git 时该改写会被发现
cd /Users/xbpd/Projects/benchmark && git status --porcelain -- ':(literal):sol'
#   => " M :sol/3/P0P1_CLOSURE_AUDIT.py"

# 4. sums 文件不可重定位且对 2/8 条目已过期
grep -c '/mnt/data' ':sol/3/P0P1_REVIEW_SHA256SUMS.txt'   # 8  (8/8 全指向 /mnt/data)
wc -l < ':sol/3/P0P1_REVIEW_SHA256SUMS.txt'              # 8
# 按 basename 重定位后逐条比对：5 MATCH / 2 DIFFER / 1 MISSING
```

注意：pathspec `:(literal):sol` **相对 CWD 解析**；在 `research-retrieval-benchmark/` 内执行会静默返回 0，必须在仓库顶层执行。

## 影响

- **门禁不可被独立复核**：只拿到 zip 的复核者无法验证「判定 M1_P4A 是否 GO」的那个脚本本身，闭合链在交付物上断开。
- **规避路径真实存在**：zip-only 场景下改写门禁脚本不会触发任何 fail-closed（attestation 仍 rc=0）。
- **风险有界**：源仓库中该文件受 git 跟踪，任何非 zip-only 消费者都能用 `git status` 发现改动；且当前工作树版本与绑定 commit **逐字节相同**，未发现篡改。
- **workaround（消费者可用，已验证）**：不依赖包内 attestation，改用 `--expected-required-set-digest` 由外部固定摘要，并另行对 `:sol/3/` 做独立摘要比对。
- 本条**不可在受审包内修复**（`:sol/` 在包根之外），故登记而非打补丁。

## 根因

1. **作用域错配**：包 attestation 只闭合**包根相对路径**（1916 条，全部包内），而门禁工具存放在包根**之外**的 `:sol/3/`，天然落在闭合范围外。
2. **发布打包遗漏**：`review_v77.zip` 只打包 `research-retrieval-benchmark/`（1946 entries，全为 `review_v77/` 前缀），未包含 `:sol/`。
3. **校验和文件不可重定位**：`P0P1_REVIEW_SHA256SUMS.txt` 的 8 条路径全部写成 `/mnt/data/...` 绝对路径（另一个评审环境的路径），在仓库内 `shasum -c` 全面 `FAILED open or read`。
4. **校验和未随更新刷新**：其中两个文件在 sums 冻结**之后**被合法更新（`P0P1_CLOSURE_AUDIT.py` @b0a5ada 09-18 00:57 vs sums @b0910a5 09-09 08:57），因此 2/8 条目摘要已过期。

## 处置

- [x] 定位根因（上述 4 条，均有实测证据）
- [ ] 修复（见 `fix_ref`）—— **不在受审包内**，需在交付流程侧处理：把 `:sol/3/` 纳入打包/闭合范围，并把 sums 改为相对路径且随更新刷新
- [x] 回归验证：已验证工作树门禁脚本与绑定 commit 逐字节相同（未篡改）；zip-only 规避路径已复现；5/8 sums 条目在重定位后摘要吻合

## 备注

**已对原表述做收窄修正**（见 frontmatter `signals` 与 `--note`）：

- ~~“其 SHA256SUMS 指向不可达的 /mnt/data”~~ → 更准确的描述是：sums 文件**不可重定位**（8/8 绝对路径），且其中 **2/8 已过期**；重定位后 5/8 摘要吻合。
- ~~“可被静默改写”~~ → 仅在 **zip-only** 消费者处成立；有 git 时改写会被 `git status` 发现。
- 本 issue 的**核心缺陷仍然成立**：门禁工具不在受审/受证范围内，闭合链在交付物上断开。
- **方法学旁注（同类根因，归属 ISSUE-0092）**：`:(literal):sol` 等 pathspec 相对 CWD 解析。我在 `research-retrieval-benchmark/` 子目录内执行 `git ls-tree ... -- ':(literal):sol'` 得到**静默的 0**，一度误判 `:sol` 未受跟踪；在仓库顶层同一命令返回 54。与 ISSUE-0092（已 fixed）是同一类错误——包内已用 `--full-name` 修好了自己的扫描，但手工 git 调用仍会踩到。判读规则：git 的静默 0 只能读作「**此处**未找到」，不可读作「不存在」。

## 处置记录 2026-09-22T21:09:05+0800

NET REVISED STATEMENT OF THIS ISSUE: the confirmed defect is a DELIVERY-SCOPE gap — the instrument that gates M1_P4A (:sol/3/P0P1_CLOSURE_AUDIT.py, plus its evidence and sums) is present, git-tracked and intact in the source repository, but is NOT included in the reviewed/attested artifact, so a consumer holding only the zip cannot verify the thing that judged the milestone; and the sums file intended to make it verifiable is itself stale for 2 of its 8 entries and non-relocatable for all 8. Severity stays high for the delivery-scope gap (it is a genuine closure hole), but the 'silently rewritable / unreachable' wording is withdrawn. Scope note unchanged: none of this is fixable inside the reviewed package root, which is why it is reported rather than patched.

## 处置记录 2026-09-22T21:10:56+0800

INDEPENDENT CORROBORATION by reviewer 01a08b88 (probes under /private/tmp/r62_v77_sol_gate_*, 2026-09-22 20:55-20:56), read from their artifacts rather than from their prose. CONFIRMED BY BOTH PARTIES: (1) out-of-scope mutation is invisible to the package's own attestation -- r62_v77_sol_gate_live_mutation_probe.out shows mutated_gate_sha=5d0ea5f6b807a025066d2d7670afe795a5b82bd70b10ea96bbc8239f30d8045b while attestation_rc_during_mutation=0 'attestation verified: 1916 paths closed ... 0 stale'; (2) same on a second run -- r62_v77_sol_gate_scope_probe.out mutated_gate_sha_before=ef5c7c2c47bb9c36... -> after=22435a77f35d9107... with package_attestation_rc=0; (3) the sums file cannot be used as published -- r62_v77_sol_gate_checksum.out shows 8/8 'FAILED open or read' against /mnt/data paths, 'WARNING: 8 listed files could not be read'; (4) the live gate instrument is NOT tampered -- on-disk sha256 re-verified by me now as ef5c7c2c47bb9c361cf662d11e4e815f01c735df53e803f52477d268d8d79722, matching the bound-commit blob, so both of us mutated only COPIES (the reviewer's was a temp dir r62_v77_sol_gate.wWEZ6E containing ':sol/3/P0P1_CLOSURE_AUDIT.py', not a git checkout, which is exactly why the package attestation could not see it). STILL SINGLE-SOURCE (mine only, do NOT attribute to the reviewer): the path-rebased content comparison of the 8 sums entries -- 5 MATCH / 2 DIFFER / 1 MISSING, with the 2 DIFFERs explained as legitimate post-sums updates (gate script b0a5ada 09-18 00:57, review doc e74fe82 09-09 11:36, vs sums frozen at b0910a5 09-09 08:57). The reviewer's output establishes only that the entries are UNREADABLE as published; it does not independently confirm which entries would still match after rebasing. Treat the 5/2/1 breakdown as my measurement pending their separate check. NET: the delivery-scope gap and the conditional (zip-only / out-of-package) silence are now corroborated by two independent parties; the 'unreachable / untracked / tampered' wording stays withdrawn.

## 处置记录 2026-09-22T21:11:07+0800

独立复核（本审计者）2026-09-22：在仓库顶层以 git ls-tree -r --full-tree --name-only adf16ffc902f -- " :(literal):sol"（去掉命令中的展示空格）核得 54 个受跟踪文件；git cat-file -e adf16ffc902f::sol/3/P0P1_CLOSURE_AUDIT.py 成功，commit 与工作树 SHA-256 都为 ef5c7c2c47bb9c36...；review_v77.zip 为 1946 entries、:sol=0，包 attestation artifacts=1916 且无 :sol；既有 scope/live mutation probe 仍证明仅变更门禁工具时包 attestation rc=0。故接受收窄后的结论：这是 delivery-scope/independent-verifiability 缺口，不是“未跟踪”或有 git 时“任意静默改写”；8/8 sums 使用 /mnt/data，当前不可读，按 basename 重定位的 5/2/1 结果待交付流程修复。

## 处置记录 2026-09-22T21:12:39+0800

补充独立复核（本审计者）2026-09-22：按 basename 将 :sol/3/P0P1_REVIEW_SHA256SUMS.txt 的 8 条记录重定位到 :sol/3/，实际计数确为 MATCH=5、DIFFER=2、MISSING=1；DIFFER 为 P0P1_CLOSURE_AUDIT.py（sums 提交 b0910a5，文件更新 b0a5ada）与 P0P1_ORACLE_FIRST_INDEPENDENT_REVIEW.zh-CN.md（sums b0910a5，文件更新 e74fe82），MISSING 为 context-8c03b3e3-0bb3-465c-bca2-e4dffbdceaee.tar.zst。该层证据支持“不可重定位且部分过期”，不支持“当前文件被篡改”。

## 处置记录 2026-09-22T21:42:15+0800

SHARPEST CORRECTION OF MY OWN FRAMING, 2026-09-22, from set algebra over the archive rather than reasoning about counts. The reviewer's adjudication (and my own earlier notes) contrast '1,946 archive entries' with '1,916 attested paths' as if the archive contained unattested material. That contrast is misleading and I retract my use of it. Exact computation over review_v77.zip: zip entries INCLUDING directories = 1946; zip FILES after stripping the single top-level 'review_v77/' prefix = 1917; attestation artifact map = 1916. Set difference: IN ZIP BUT NOT ATTESTED = 1 -- and that one is attestations/M1_worker_protocol_attestation.json, the documented RESERVED SELF-PATH (attestation_policy.py:14, :38) deliberately excluded from the required set. ATTESTED BUT NOT IN ZIP = 0. The remaining 29 of the 30-count gap are DIRECTORY entries, not files. CONCLUSION: the archive's in-package closure is EXACT (1917 files = 1916 attested + 1 reserved self-path), not incomplete. The single genuine, still-open defect in this issue is the governance one: ':sol entries in zip: 0' -- I independently confirmed zero ':sol' entries in the archive, so the gate instrument that adjudicates the milestone is not part of the attested deliverable and a zip-only consumer cannot verify it. Keep this issue open on THAT basis only. Also note the adjacent scope mismatch I found: :sol/3/P0P1_CLOSURE_AUDIT.py:103-115 looks for PILOT_SCORECARD_REPORT.md at parent/ (repo root, OUTSIDE the package) and treats that copy as the input to p0_root_report_is_explicitly_non_comparative, whereas the archive ships the report at results/PILOT_SCORECARD_REPORT.md (2877 bytes, present). So the archive's 23/24 P0/P1 result is caused by the gate searching outside the package, not by the report being undelivered.

## 处置记录 2026-09-22T21:48:52+0800

复核者裁定（2026-09-22 13:48Z，intercom seq 12）接受第二节集合运算：review_v77.zip=1946 entries=1917 files+29 dirs；attestation artifacts=1916；ZIP−attestation 恰为保留自路径 attestations/M1_worker_protocol_attestation.json；attestation−ZIP=0。故不把 1,946/1,916 差额算作包内闭包缺陷。本 issue 收敛为 :sol/3/P0P1_CLOSURE_AUDIT.py 不在包内证明范围，且 scorecard 检查的作用域错配。

R68 补充精确根因（我本人复现，补足复核者概括）：:sol/3/P0P1_CLOSURE_AUDIT.py:103-112 只探测两条路径 —
  (1) parent / 'PILOT_SCORECARD_REPORT.md'                          （包外，root.parent）
  (2) root / 'results' / 'pilot_campaign' / 'PILOT_SCORECARD_REPORT.md'（包内）
而归档实际交付的是 review_v77/results/PILOT_SCORECARD_REPORT.md（2877B）——两者都不是。
实测：candidate(1) 不存在（zip-only 解包后 parent 即解包目录）；candidate(2) 不存在（无 pilot_campaign/ 层级）。
故不是『报告缺失』（报告确实随包，复核者亦已确认），而是门禁的路径契约与归档布局不一致 =>
治理/作用域错配，与 ISSUE-0122/0123 同族（reviewer-facing 可发现性缺口）。

## 处置记录 2026-09-22T22:12:34+0800

根因定位（R68，见 RAW-20260922-007）：这是布局迁移遗留，不是'门禁只认包外'。

门禁代码（:sol/3/P0P1_CLOSURE_AUDIT.py:103-112）探测四条候选路径：
  (1) parent/PILOT_SCORECARD_REPORT.md
  (2) root/results/pilot_campaign/PILOT_SCORECARD_REPORT.md
  (3) root/results/summary.md
  (4) root/results/summaries/scorecard.md

实测交付态（review_v77）：(1) 与 (2) 均不存在；归档实际携带 review_v77/results/PILOT_SCORECARD_REPORT.md (2877B)。

路径断裂原因：results/ 布局发生过迁移。旧布局为 results/pilot_campaign/...，在提交 cf1851c（'fix(bench): resolve Sol R23 M1_P4A review findings'）被删除；新布局改为 results/ 扁平化（468d9fc 下 results/ 直接含 PILOT_SCORECARD_REPORT.md、events.jsonl.RETIRED 等）。门禁保留了对旧路径 (2) 的探测，未随迁移更新。

对照证据：过期副本 /Users/xbpd/Projects/文字Agent检索系统/research-retrieval-benchmark/ 仍保留旧布局 results/pilot_campaign/PILOT_SCORECARD_REPORT.md（2789B，blob 508768501c39b0e6），该内容在 git 中完全不存在（git cat-file -e 失败）。新旧评分卡内容不同（旧 35d38945… ≠ 新 c4049b0e…），故非简单重命名。

修复方向：门禁应改为探测交付实际使用的 results/PILOT_SCORECARD_REPORT.md（或改为按内容特征发现评分卡，而非硬编码路径）。
