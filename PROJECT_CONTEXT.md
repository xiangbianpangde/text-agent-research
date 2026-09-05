---
schema_version: 1
project_id: researchctl
authority: working_projection
context_revision: 10
checkpoint_id: CP-0010
source_session_id: 01a06a96-0a23-7359-9ce9-3f9d1adacb7f
covered_through_entry_id: 01a06a96-0a23-7359-9ce9-3f9d1adacb7f:2026-09-05T16:05
git_branch: main
git_head: c47e3b549cd95e15865e215e4994c38b7e311241
base_context_sha256: 9a03c8db68131e45c5ff0a77d916984013da4f16b689a999deaacb0d6183f52b
generated_at: 2026-09-05T14:04:01.202Z
negative_constraints_relaxation:
  checkpoint_id: CP-0010
  timestamp: 2026-09-05T14:04:01.202Z
  actor: 01a06a96-0a23-7359-9ce9-3f9d1adacb7f
  previous_context_sha256: 9a03c8db68131e45c5ff0a77d916984013da4f16b689a999deaacb0d6183f52b
  reason: 逐条解除已满足的旧约束：1) “do not begin p0.3c on the current no-go candidate”和2)“do
    not begin p0.3c before fresh sol pass”已由第六次 Sol 作业 7402609a 的明确 PASS 满足；3)旧
    28 FAIL 向量已被修复后正式 6/27 Oracle-only 向量取代；4)“do not treat repaired 6/27 as
    certified until review”已由该 Sol PASS 与后续 P0.3C/P0.4
    机器验收满足。解除仅因里程碑已达成，并以更严格的新约束“P0 Harness 完成不等于 ResearchCTL 认证，P1/P2
    必须获得用户新批准”替代。
  removed_constraints:
    - do not begin p0.3c on the current no-go candidate
    - do not treat the current 28 fail vector as independently certified until
      the harness blockers are repaired
    - do not begin p0.3c before fresh sol pass on repaired p0.3b
    - do not treat the repaired 6/27 vector as independently certified until
      fresh sol review
---

# ResearchCTL-Bench Working Context

## Current Objective

P0 Harness Construction is complete through P0.4. Do not start P1/P2 automatically; the frozen decision requires new user approval after P0 exit. Current ResearchCTL is not qualified by the formal Oracle benchmark.

## Authority And Git

- Authority: `ResearchCTL-Bench-P0-Contract.md` and `超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench).md`.
- Reports: `benchmark_report.json`, `benchmark_report.md`, `benchmark_report.pdf`.
- Commits: `9c3209f` P0.1/P0.2/P0.3A; `0d20baa` P0.3B candidate; `be62ec1` accepted P0.3B repairs; `c47e3b5` P0.3C.
- P0.4 uncommitted. Main four commits ahead of origin, not pushed. Audit staging/session HTML excluded.

## P0.3 And P0.4

- Sixth Sol audit `7402609a-bfa8-4db5-a0af-231ef2e21c62`: `PASS — P0.3B repair accepted; P0.3C may begin`.
- Default path is pack-owned Oracle-only; legacy requires `--legacy-diagnostic` and cannot alter formal fields.
- Six controls use the same 33-scenario Oracle path: Always-Pass, Always-Abstain, Universal-Stale, Universal-Impact, Random, Gold-Reader.
- All controls: certification=false, Tier N/A, passing conclusion=false. Formal passes: 1,2,0,0,0,1. Universal Stale/Impact CIV=6; Random CIV=4.
- Random retry deterministic. Gold-Reader file read blocked by macOS sandbox-exec. Official ResearchCTL double-run digest matches: `sha256:a0a8d65261fbb267759eee3ee5b432051a88707768274f3840377ca851217cfd`.
- Bound attestation valid: `sha256:80b13cfa04bdce5e32ca4df0d00ec7dd44060304196bc32a6f5f441311424617`; binds manifest, source/fixture, actions, controls, adapter, executor, evaluator and Oracle; tampering fails.

## Current Machine State

- v0.7.0; `oracle_only`; P0.3C complete; P0.4 complete; `p0_status=complete_harness`.
- Official ResearchCTL: 6 PASS / 27 FAIL; composite 20.8; CIV 0; integrity gate false; certification=false; Tier N/A; reasons FORMAL_SCENARIOS_FAILED and INTEGRITY_GATE_FAILED.
- Harness 56/56; ResearchCTL regressions 443/443; coverage 33/33; trust imports 0; self-award fields 0; report audit 0/0.
- Source/fixture digest `sha256:205483526cf17db0066b55c0f097a99043443a79ed0c5fa919805537b73eea01`; root fingerprint `sha256:50aef045b805311de1e1111945f1397db6fa69bb1e93b3634a6380cb3c9fc2eb`.

## Next Gate

P1/P2 remain inactive: dynamic Universe, hidden split, real B1/B2/B3, multi-model statistics, remote OCI and leaderboard governance. Require explicit user approval and a separate P1 contract before implementation.

## Negative Constraints / Do Not Assume

- Oracle coverage is not pass rate.
- Never advertise current output as a public benchmark certification.
- Do not weaken Gold to retain legacy 33/33.
- Do not compile Gold after SUT start or derive it from SUT output/SQLite.
- Generic runner/Oracle/DSL/evaluators must not import `researchctl.*`.
- P0.3 is not complete until default `run_sXX()` self-scoring is cut off and formal metrics are Oracle-only.
- P0 is not complete until P0.4 six negative controls pass.
- P0 Harness completion is not ResearchCTL certification.
- Do not enter P1/P2 without explicit user approval after reviewing this P0 result.

## Next Action

1. Commit P0.4 controls/attestation/tests/reports/context.
2. Present P0 completion separately from ResearchCTL formal failure.
3. Wait for explicit P1 scope approval; if approved, write a separate P1 contract first.
