---
schema_version: 1
project_id: researchctl
authority: working_projection
context_revision: 12
checkpoint_id: CP-0012
source_session_id: 01a07599-1af8-7d45-8c21-a93984c08d31
covered_through_entry_id: 01a07599-1af8-7d45-8c21-a93984c08d31:2026-09-06T12:48
git_branch: main
git_head: 8c20d809a2c455cbd628ab6a2f0ccb2e9dd15699
base_context_sha256: a458c29ee5a54ce4f6365ab98c449d67b1e80df93a4fae361c141d5ca0c5cbef
generated_at: 2026-09-06T12:48:53.187Z
---

# ResearchCTL-Bench Working Context

## Current Objective

P1 Contract Frozen via independent Sol audit PASS (aad0919c-e9c2-4368-9959-845745e162bc). Beginning P1A Generator & Family implementation. P2 remains deferred.

## Authority And Git

- Authority: `ResearchCTL-Bench-P0-Contract.md`, `ResearchCTL-Bench-P1-Contract.md` (Frozen), and `超长程实验 Agent 检索系统 Benchmark 方案 (ResearchCTL-Bench).md`.
- Reports: `benchmark_report.json`, `benchmark_report.md`, `benchmark_report.pdf`.
- Commits: `9c3209f` P0.1/P0.2/P0.3A; `0d20baa` P0.3B candidate; `be62ec1` accepted P0.3B repairs; `c47e3b5` P0.3C; `2385e91` P0.4/P0 completion; `8c20d80` P0 completion checkpoint.
- Next commit: `docs: freeze ResearchCTL-Bench P1 contract after Sol audit PASS`.
- Main is six commits ahead of origin and has not been pushed.
- `.pi/sol-staging/` and root Pi session HTML are unrelated and excluded.

## P0 Completion Status

- Complete harness confirmed: 6 controls pass/rejected, bound attestation `sha256:80b13cfa04bdce5e32ca4df0d00ec7dd44060304196bc32a6f5f441311424617`.
- Official ResearchCTL baseline run: 6 PASS / 27 FAIL, certification=false, Tier N/A.

## P1 Contract Freeze Acceptance

- Twelfth Sol audit `aad0919c-e9c2-4368-9959-845745e162bc`: `PASS — freeze P1 contract; P1A implementation may begin`.
- FZ-01–FZ-08 mechanical appendix §19 completely closed and verified:
  - Quota: 8 families, 144 instances (48 public, 48 private, 48 local-hidden).
  - Quota digest `sha256:6c26fb4ce20da8030fdef949292925115441c73471562b93275c4a83fe65dbb6`.
  - Metric digest `sha256:2e998c351aa12f82595feb1c935b359bbd1e677a44a2c159c878455ef0fb69be`.
  - B1 API digest `sha256:e8cf1488cc32be80a53d8c8e803d9182c59623abd488c564ce504655741f8e1e`.
  - FileGraph profile digest `sha256:9df1b1509829995c465d5f50717cf31ace9448cd4a36f6b30a46abb71e27ffa6`.
  - Known-answer digest `sha256:a8bc8261ea3eb542241a145bc2ebf2e363ebd5d526c5977088f24b742298503a`.
  - Statistics profile digest `sha256:bd08e958ec639020396e8446c076bccd047989765ea7969bdae97a9ef9761eab`.
  - K_boot `f25bf832810e022df4c1a9ff893497c3e4fc83f844efeb0bee3221f7c03a96cf`.
  - 10,000 paired bootstrap reproduced exactly.
  - Crash-atomic replacement primitive and unique path invariant with single relative-path formula $T(path, seq)$ and reserved namespace.
  - prediction/v2 and scenario-actions/v2 deterministic deltas.

## Next Gate: P1A Implementation

- Implement P1A components under `bench/`:
  1. `bench/dsl/cjson.py` (bench-cjson/v1 serializer).
  2. `bench/generator/kdf.py` (HMAC counter stream, deterministic seeding).
  3. `bench/generator/models.py` & `bench/generator/schema.py` (task-family/v1 schema & models).
  4. 8 versioned task families (F01–F08).
  5. 144 instances generation & public split deterministic reconstruction.
  6. Pass G01–G08 exit conditions.

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
- Do not enter P2 without explicit user approval after P1 completion.
- P1A candidate status is `candidate_p1a`; do not advertise full Research Benchmark status before P1C completes.
- No participant-specific code in benchmark generator.
- No float in canonical digests or preimages.
- Temporary paths must strictly follow $T(path, seq)$ in same directory.

## Next Action

1. Commit `ResearchCTL-Bench-P1-Contract.md` and memory updates.
2. Implement `bench/dsl/cjson.py` following §19.1.1 spec with unit tests.
3. Implement `bench/generator/` (KDF, models, task families F01–F08) and public instance generation.
