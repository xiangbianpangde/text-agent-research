---
schema_version: 1
project_id: researchctl
authority: working_projection
context_revision: 14
checkpoint_id: CP-0014
source_session_id: 01a07599-1af8-7d45-8c21-a93984c08d31
covered_through_entry_id: 01a07599-1af8-7d45-8c21-a93984c08d31:2026-09-06T14:20
git_branch: main
git_head: df3d456cf70fcb8d2f39ea627c7943c91abf4737
base_context_sha256: 7a9ad1c7deb64fb24cf8d830b0c54c5e59b7d95e86951b510937f634ff8ff03a
generated_at: 2026-09-06T14:20:51.031Z
---

# ResearchCTL-Bench Working Context

## Current Objective

P1A complete (G01–G08 all PASS, report at `bench/reports/p1a-gates.json`, status `candidate_p1a`, allowed claim "Dynamic B1 benchmark candidate"). P1B in progress: campaign lifecycle + T0–T3 runner + participant binding done (137 tests). Remaining P1B: hidden-validity canaries (§19.5.4), B1 runner + same-runner evaluation, independent filegraph baseline, S01–S07/B01–B06 gate suite.

## Authority And Git

- Authority: P0 Contract, P1 Contract (Frozen, Sol PASS aad0919c-e9c2-4368-9959-845745e162bc), Benchmark 方案.
- Commits: `c9d8a37` P1 freeze; `01f208a` P1A foundations; `6d7a10e` P1A generator+root; `39e8082` CP-0013; `32ec1bc` G-gates; `617175d` gate runner + frozen source-tree closure + regenerated root; `a9ba0e6` campaign state machine; `df3d456` campaign runner T0–T3 + tar binding.
- Main 11 ahead of origin, unpushed. Unrelated: `.pi/sol-staging/`, `.mimosa/`, root session HTML.

## Key Design Facts

- Source-tree closure frozen in `bench/generator/instance.py SOURCE_TREE_FILES` (bench/dsl/cjson+loader, generator pipeline, oracle compiler/conditions/manifest/model/time, v2 schema). Editing any listed file churns all instance digests; gates.py/__main__.py/release.py excluded (verification/CLI only).
- Public root `bench/packs/p1_public_v1` regenerated under frozen closure; verify-public byte-identical from foreign cwd.
- `bench/campaign/state.py`: campaign-manifest/v1 (17 fields, 9-state nullability matrix), 9 transitions T0–T8, immutability, event hash chain + verify_event_chain, all §19.5.3 formulas (campaign_id/digest, root commitments, commitment, materialization evidence, evidence bundle, disclosure).
- `bench/campaign/runner.py`: build_release (144 instances + release identity, b1_api_digest verified against contract frozen value e8cf1488...), build_root_tree (participant-visible fixtures ONLY — no gold/manifest/actions in roots), create_campaign T0–T3 with materialization + opening verification (fail-closed, cleans up on error).
- `bench/campaign/artifacts.py`: participant-artifact/v1, tar safety (reject absolute/.., symlink/hardlink, device, AppleDouble, PAX), exact tar SHA-256, entrypoint containment, seed_mode enum.
- Ephemeral test secrets only; repo never stores private/hidden secrets (S02).

## Tests (bench/tests, 137 total)

- P1A: cjson 6, kdf 5, tree 6, models 13, instance 9, release 4, gates 9 (thin over generator.gates), p0 suites 56.
- P1B: campaign 13 (transitions, immutability, opening verification, event chain), runner 14 (tar safety, binding, T0–T3, no-gold-in-roots, S01 match committed root, fail-closed secrets, tamper detection).

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
- Hidden roots contain only participant-visible fixtures; Oracle/Gold/seed packs stay evaluator-held.

## Next Action

1. Implement hidden-validity/v1 + 16 canaries (§19.5.4) with fail-closed evaluation gating (S05/S06).
2. Implement B1 runner: same-runner evaluation of participants via sut-adapter/v1 with run_seed per invoke; b1-kernel/v1 capability declaration (§9).
3. Implement independent-filegraph-v1 baseline (§11, §19.7) — full B1 surface, zero benchmark imports.
4. Build S01–S07 / B01–B06 gate suite; declare `candidate_p1b` only after all pass.
