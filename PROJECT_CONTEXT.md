---
schema_version: 1
project_id: researchctl
authority: working_projection
context_revision: 9
checkpoint_id: CP-0009
source_session_id: 01a06a96-0a23-7359-9ce9-3f9d1adacb7f
covered_through_entry_id: 01a06a96-0a23-7359-9ce9-3f9d1adacb7f:2026-09-05T14:45
git_branch: main
git_head: be62ec1cbd3772f0a693ee23d09a1eee6cddcb4a
base_context_sha256: 91ae7f0800717a6836009f323ca41d8a8270b84c0186a2e757fe9084f8d83492
generated_at: 2026-09-05T13:36:17.450Z
---

# ResearchCTL-Bench Working Context

## Current Objective

P0.3B was accepted by sixth Sol audit `7402609a-bfa8-4db5-a0af-231ef2e21c62`. P0.3C Oracle-only cutover is implemented and locally verified. Commit P0.3C, then proceed only to P0.4 negative controls. P0 remains incomplete; do not enter P1/P2.

## Authority And Git

- Frozen authority: `ResearchCTL-Bench-P0-Contract.md`; benchmark/CLE spec: `超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench).md`.
- Commits: `9c3209f` P0.1/P0.2/P0.3A; `0d20baa` initial P0.3B; `be62ec1` accepted P0.3B trust repairs.
- P0.3C changes uncommitted. Main is three commits ahead of origin, not pushed.
- `.pi/sol-staging/` and root Pi session HTML are unrelated artifacts and excluded.

## P0.3B Acceptance

- Sixth Sol verdict: `PASS — P0.3B repair accepted; P0.3C may begin`.
- Fresh extracted self-contained bundle: Harness 50/50, root stored/fresh fingerprint exact, canonical fixture double rebuild exact, 0 AppleDouble.
- Query/Gold independence, RFC3339/UTC lifecycle, checkpoint-state CIV, complete ResultRow, fail-closed, source bindings, stale graph, session mechanics, reproducible source.tar, CLE and process cleanup all accepted.

## P0.3C Implementation

- Version v0.6.0.
- Default CLI scenario registry is pack-owned `bench/packs/p0_seed_v1/pack.json` plus action DSL.
- Default path does not access/call legacy `registration.runner` or `run_sXX()`.
- Formal aggregation accepts only `OracleScenarioEvaluation`; score, TP/FP/FN, CIV, VLP, PGEM, FCAA and IQG derive from independent Oracle results.
- `--legacy-diagnostic` is the only legacy execution path. Its values are nested under `legacy_diagnostic` and cannot change formal fields.
- P0.4 pending is an explicit eligibility reason and forces Tier N/A.

## Current Machine State

- `evaluation_engine=oracle_only`, `p0_3_status=complete_p0_3c`, `score_provenance=independent_oracle`.
- Coverage 33/33; formal 6 PASS / 27 FAIL; composite 20.8; CIV 0; integrity gate false.
- `certification_eligible=false`, Tier N/A; sole full-run reason `P0_4_NEGATIVE_CONTROLS_PENDING`.
- Default legacy namespace empty. Explicit S19 legacy diagnostic left formal result unchanged.
- S29 fixed-CLE incompatibility and S31 opaque reconcile result remain strict FAIL.
- Harness 53/53 PASS; ResearchCTL regressions 443/443 PASS; trust imports 0; action self-award 0; report audit 0/0; PDF refreshed.

## P0.4 Target

Implement and test six controls: Always-Pass, Always-Abstain, Universal-Stale, Universal-Impact, Random, Gold-Reader. Every control must remain ineligible and must not obtain a passing conclusion. Gold-Reader must be blocked by isolation boundaries. P0 completes only after all P0 exit conditions, including clean-environment determinism, pass.

## Negative Constraints / Do Not Assume

- Oracle coverage is not pass rate.
- Never advertise current output as a public benchmark certification.
- Do not weaken Gold to retain legacy 33/33.
- Do not compile Gold after SUT start or derive it from SUT output/SQLite.
- Generic runner/Oracle/DSL/evaluators must not import `researchctl.*`.
- P0.3 is not complete until default `run_sXX()` self-scoring is cut off and formal metrics are Oracle-only.
- P0 is not complete until P0.4 six negative controls pass.
- Do not begin P0.3C on the current NO-GO candidate.
- Do not treat the current 28 FAIL vector as independently certified until the harness blockers are repaired.
- Do not begin P0.3C before fresh Sol PASS on repaired P0.3B.
- Do not treat the repaired 6/27 vector as independently certified until fresh Sol review.

## Next Action

1. Commit P0.3C code/tests/reports/context excluding audit artifacts.
2. Implement P0.4 six negative controls and isolation tests.
3. Run Harness, 443 regressions, all controls, full Oracle report and clean-environment determinism.
4. Refresh context and obtain final review before declaring P0 complete.
