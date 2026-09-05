---
schema_version: 1
project_id: researchctl
authority: working_projection
context_revision: 8
checkpoint_id: CP-0008
source_session_id: 01a06a96-0a23-7359-9ce9-3f9d1adacb7f
covered_through_entry_id: 01a06a96-0a23-7359-9ce9-3f9d1adacb7f:2026-09-05T14:30
git_branch: main
git_head: 0d20baa61242d905bf9fe464b0dd244f3b62fbf3
base_context_sha256: 18eec4062b6c8b2ab980affacc06aac4ea9103d42d9d1c9041e894c281f5ed4c
generated_at: 2026-09-05T13:19:45.598Z
---

# ResearchCTL-Bench Working Context

## Current Objective

Sixth Sol audit `7402609a-bfa8-4db5-a0af-231ef2e21c62` returned `PASS — P0.3B repair accepted; P0.3C may begin`. Commit the accepted P0.3B repair checkpoint, then implement P0.3C Oracle-only default path. P0 remains incomplete; do not enter P1/P2.

## Authority And Git

- Frozen authority: `ResearchCTL-Bench-P0-Contract.md`; benchmark/CLE spec: `超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench).md`.
- Accepted machine report: `benchmark_report.json`, `shadow_review_status=PASS_P0_3B_ACCEPTED`.
- `9c3209f`: P0.1/P0.2/P0.3A; `0d20baa`: initial P0.3B. Accepted repair tree is uncommitted and must become the next checkpoint.
- Main two commits ahead of origin, not pushed. Root Pi session HTML and `.pi/sol-staging/` are excluded.

## Accepted P0.3B Evidence

- Six Sol review rounds; final gate checks passed: exact audit bundle hash, 0 AppleDouble, fresh extraction 50/50 Harness, root fixture stored/fresh fingerprint exact, source.tar double rebuild exact, all prior trust checks closed.
- Final Sol verdict: `PASS — P0.3B repair accepted; P0.3C may begin`.
- Query registry and structured mutations close hidden Gold channels.
- Strict RFC3339/UTC, explicit object lifecycle, full as-of state and virtual-clock binding.
- Eight CIV classes use checkpoint compiled state; dynamic versions and cutoff facts covered.
- Complete typed ResultRow, optional string ref only, evaluator revalidation, full-row exactness.
- Fail-closed Gold suppresses positive channels; attached answers fail.
- Historical binding, downstream stale graph, unrelated freshness and session CURRENT/INDEX mechanics accepted.
- Canonical `source.tar` has 306 members, no AppleDouble/links/traversal; source/fixture hash `sha256:205483526cf17db0066b55c0f097a99043443a79ed0c5fa919805537b73eea01`; deterministic builder.
- CLE fixed schema/order/normalization and explicit transaction; process-group cleanup closed.
- Deterministic root scan sorts os.walk subdirs/files; root fingerprint `sha256:50aef045b805311de1e1111945f1397db6fa69bb1e93b3634a6380cb3c9fc2eb` stored=fresh after extraction.

## Current Machine State

- v0.5.0 `oracle_shadow`, P0.3B accepted, coverage 33/33.
- Strict vector 6 PASS (`S10`,`S11`,`S14`,`S19`,`S26`,`S30`) / 27 FAIL; CIV 0.
- S29 fixed-CLE incompatibility and S31 opaque reconcile result remain strict FAIL.
- Formal score/passed/integrity/IQG null; Tier N/A; certification false. Legacy diagnostic isolated.
- Harness 50/50 PASS; ResearchCTL regressions 443/443 PASS; trust imports 0; action self-award fields 0.
- Accepted report audit: 0 errors / 0 warnings; PDF refreshed.

## P0.3C Target

- Default CLI/runner executes only the 33 Oracle action scenarios; no active call to legacy `run_sXX()`.
- Formal metrics aggregate only from `OracleScenarioEvaluation` and compiled Gold.
- Legacy path remains available only behind an explicit diagnostic flag and is nested as diagnostic output.
- Full and partial Oracle modes retain coverage/eligibility safety. P0.3 completion must not imply P0 completion or public certification.

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

1. Git commit accepted P0.3B repair tree excluding audit staging/session HTML.
2. Implement P0.3C Oracle-only orchestration and aggregation with explicit legacy diagnostic flag.
3. Add no-active-run_sXX and no-mixed-metrics regressions; run full Harness/443/shadow.
4. Refresh context after P0.3C checkpoint; P0 then proceeds only to P0.4.
