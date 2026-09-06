---
schema_version: 1
project_id: researchctl
authority: working_projection
context_revision: 13
checkpoint_id: CP-0013
source_session_id: 01a07599-1af8-7d45-8c21-a93984c08d31
covered_through_entry_id: 01a07599-1af8-7d45-8c21-a93984c08d31:2026-09-06T13:35
git_branch: main
git_head: 6d7a10e148e7996b257d0ddf0c9933d090a2844d
base_context_sha256: bd2d3a5952f569441e716fae80052fc61ec15de47b32dabc441db0cff3796b4c
generated_at: 2026-09-06T13:32:26.147Z
---

# ResearchCTL-Bench Working Context

## Current Objective

P1A implementation complete: 100 bench tests pass; 48-instance public root at `bench/packs/p1_public_v1` with cross-environment byte-identical rebuild verified. Next: G01–G08 gate summary, then `candidate_p1a` declaration.

## Authority And Git

- Authority: P0 Contract, P1 Contract (Frozen via Sol PASS aad0919c-e9c2-4368-9959-845745e162bc), Benchmark 方案.
- Commits: `8c20d80` P0 done; `c9d8a37` P1 freeze; `01f208a` P1A foundations; `6d7a10e` P1A generator+quota+public root. Main 8 ahead of origin, unpushed.
- Unrelated: `.pi/sol-staging/`, `.mimosa/`, root session HTML.

## P1A Map (under bench/)

- `dsl/cjson.py` bench-cjson/v1; reproduces all 7 frozen digests.
- `generator/kdf.py`+`frame.py` HMAC streams (§19.9); public secret 0x00..0x1f; uniform+weighted_choice; run_seed.
- `generator/tree.py` bench-tree/v1 (reserved `.tmp`, NFC, prefix, empty dirs).
- `generator/models.py` task-family/v1 18-field closed set + FamilyIdentity.
- `generator/families.py` F01–F08 v1.0.0, closed allowlists, subvariant schedules.
- `generator/identity.py` config/profile/identity, Descriptor, Display ID, lockfile (144, strict order), ReleaseIdentity.
- `generator/schemas/scenario-actions-v2.schema.json` 3-delta from v1; scenario_action_digest sha256:f53a9f6de1eef4d6a3db4426d19b45d915ef5d181dbe8ccee58d2007f6bb97ab.
- `generator/universe.py` universe+fixture+query-registry; pure-int dates.
- `generator/scenario.py` v2 validator (adds freeze_report write params).
- `generator/instance.py` attempt loop (64), subvariant weighted pick, Gold pre-SUT, acyclicity, instance_digest, GENERATOR_REJECTION_EXHAUSTED.
- `generator/release.py` write/verify public root; `__main__.py` CLI build-public/verify-public.
- Public root: 48 instances, 1117 files, 5.9MB; verify passes from foreign cwd.

## Tests (bench/tests, 100 total)

- p1_cjson 6 (incl. 7 contract hashes); p1_kdf 5; p1_tree 6; p1_models 13 (families, lockfile, release); p1_instance 9 (quota 144=48/48/48, determinism, rejection, exhaustion, full release); p1_release 4 (committed-root rebuild G01/G02, tamper detect). P0 suites 56 still pass.

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
- Public root secret is a fixed constant; private/hidden secrets are evaluator-held and must never enter the public tree.

## Next Action

1. Produce P1A G-gate checklist run (G01–G08) as a verification report; commit.
2. Declare `candidate_p1a` with allowed claim "Dynamic B1 benchmark candidate" only after all gates pass.
3. Then plan P1B (held-out commitments, campaign lifecycle, artifact binding, real independent baseline, isolation gates) — requires its own acceptance tests S01–S07/B01–B06 before any held-out claims.
