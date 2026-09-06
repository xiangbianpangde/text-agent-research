---
schema_version: 1
project_id: researchctl
authority: working_projection
context_revision: 15
checkpoint_id: CP-0015
source_session_id: 01a07599-1af8-7d45-8c21-a93984c08d31
covered_through_entry_id: 01a07599-1af8-7d45-8c21-a93984c08d31:2026-09-06T15:05
git_branch: main
git_head: 0c78ae119b2fcab1a5936613623225a55f2160ae
base_context_sha256: eabf6d576d498f497883dcb2a3edd1511edf361f5148480c41e0a401ba2a9af9
generated_at: 2026-09-06T15:28:14.470Z
---

# ResearchCTL-Bench Working Context

## Current Objective

P1B ~70% done: canaries + evaluation engine landed (152 tests green). Remaining: independent-filegraph baseline (B05/B06), S01–S07/B01–B06 gate suite, B1 semantic alignment (instance solvability), then `candidate_p1b`.

## Authority And Git

- P1 Contract Frozen (Sol PASS aad0919c). Commits: `617175d` gates+closure+root; `a9ba0e6` campaign state; `df3d456` campaign runner; `737aa7b` canaries; `926e704` evaluation engine; `0c78ae1` P0.4 attestation re-issue (new digest 25a07a30acb207ac430a79709de39a7b82954c7163bd8d5b22f10c6554abbf30) + run_seed transport. Main 14 ahead of origin.

## Landed This Phase

- Gate runner `bench/generator/gates.py` G01–G08 all PASS; report `bench/reports/p1a-gates.json`; status `candidate_p1a`.
- SOURCE_TREE_FILES frozen (17 files incl. yamlemit.py; gates/__main__/release excluded). Listed-file edits churn instance digests by design.
- Fixture format rewritten to mini-research-repo (`bench/generator/yamlemit.py`): definitions w/ previous chains + APPROVED, events, spec, runs w/ dir-manifest hash raw_ref, organized frontmatter sources, CURRENT.{md,sources.yaml}, .auth, synthetic 40-hex commit. Manifest declares ALL versions + previous facts; raw_run hash = dir-manifest; objects git_commit = synthetic commit.
- Public root regenerated; cross-cwd byte-identical.
- campaign/state.py + runner.py T0–T3 (opening verification fail-closed); artifacts.py tar binding.
- canary.py: iso digest 14df1a90..., net digest 57517398...; 16 probes via sandbox-exec child (realpath paths! /var→/private/var), live-listener network probes (EPERM), no backend → evaluation_valid=false (S06). 16/16 blocked.
- evaluation.py: prediction/v2 (ref nullable), run_seed_schedule (KDF), fresh workspace per rep, missingness recorded, sealed-Gold scoring. Live smoke vs reference SUT: score 0.0, failed=False (legitimate low score).

## Known Open Items

1. **B1 semantic alignment / solvability**: SUT scores 0.0 — its envelopes don't project Gold rows (route_sequence/status/commit semantics from universe). Benchmark must be solvable: define B1 workspace semantics, implement baseline (§11) first, then update ResearchCTL adapter as participant.
2. B04 (artifact byte-change → invalid) needs campaign-level wiring.
3. P0.4 attestation binds harness bytes — re-issue via `PYTHONPATH=. python3 -m bench.controls.runner` whenever executor/adapters/controls/evaluators change. Current digest 25a07a30....

## Tests (bench/tests, 152)

- P1A 43 (cjson6/kdf5/tree6/models13/instance9/release4); gates 9; P0 56+3.
- P1B: campaign 13, runner 14, canary 6, evaluation 9 (v2, seed schedule, T02 pairing, workspace freshness, neutrality).

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
- P0.4 attestation binds harness bytes: re-issue via documented runner, never silent patching.

## Next Action

1. Implement `bench/baseline/` independent-filegraph-v1 (§11, §19.7): zero benchmark imports, full B1 surface, fail-closed; defines B1 workspace reading rules.
2. Align Gold projections with B1 semantics so instances are solvable; update ResearchCTL bench_adapter as participant.
3. B04 wiring: artifact digest re-check before/after execution in campaign runner.
4. S01–S07/B01–B06 gate suite (`bench/tests/test_p1b_gates.py`); declare `candidate_p1b` when green.
