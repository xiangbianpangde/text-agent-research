---
schema_version: 1
project_id: researchctl
authority: working_projection
context_revision: 16
checkpoint_id: CP-0016
source_session_id: 01a079a1-7261-7605-8a92-f9b5af734d65
covered_through_entry_id: 01a07599-1af8-7d45-8c21-a93984c08d31:2026-09-06T16:30
git_branch: main
git_head: 1499ff0945abd7886188e5f7b7a987d7cc8dbb35
base_context_sha256: 0f1d406fb6031341dca648b36ec208065313c89a62ced68fa038572c6d31075c
generated_at: 2026-09-07T02:34:32.663Z
---

# ResearchCTL-Bench Working Context

## Current Objective

P1B ~85% done: independent-filegraph baseline implemented AND 48/48 public instances solvable at score 1.0 (152 bench tests green). Remaining: B04 artifact-binding wiring, S01–S07/B01–B06 gate suite, then `candidate_p1b`.

## Authority And Git

- P1 Contract Frozen (Sol PASS aad0919c). New commits: `1499ff0` baseline + ledgers (48/48 solvable). Main 15 ahead of origin.
- P0.4 attestation re-issued: `sha256:85884db9f1a0ae8792ea293315cf8a47f968ebb8aa51455eaabed91e216c7d0b` (p0_4_passed=true).

## Landed This Phase (baseline + solvability)

- `bench/baseline/filegraph.py` — independent-filegraph-v1 engine: BENCH frontmatter parsing (§19.7.2), facts/evidence/edges/graph-nodes ledgers, exact/current/path lookup, token-multiset lexical (fact-value semantics), declared-edges BFS, propagation subgraph (root+dependents, Gold semantics), fail-closed mapping (HASH_MISMATCH/SOURCE_MISSING/AMBIGUOUS_VERSION/NOT_FOUND). `bench/baseline/adapter.py` — sut-adapter/v1 loop (own wire handling).
- **B1 shared-argv decision (PM-DEC-0006)**: query_entity/facts/lineage/state/external_basis share argv `["query","--entity",loc]` (frozen §19.6.2); participants emit maximal envelope (all version rows + all subject facts + graph); evaluator checks only checkpoint-present fields. Solvability requires: single-version definitions at compile time; registry predicates=[] (compiler `_facts` truthy filter: [] = no filter — P0 compiler changed, S05 P0 test updated); external_basis excluded from sampled registry ops (pinned-only projection not derivable under shared argv); as_of visibility facts (predicate as_of per object); history rows: git_commit kept/status null for plain history, both null for as_of (--as-of presence distinguishes).
- Workspace ledgers: `facts/{asserted-facts,evidence-atoms,provenance-edges,graph-nodes}.cjson` — emitted AFTER hash finalization (emit_state_ledgers); fixture.source_hash recomputed to cover full tree.
- **Baseline scores 1.0 on 48/48 public instances** (engine `run_instance` + adapter subprocess). ResearchCTL adapter not yet aligned (still 0.0) — next: port the same projection semantics into researchctl/bench_adapter.
- Public root regenerated; verify-public byte-identical.

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
- P0.4 attestation binds harness bytes — re-issue via `PYTHONPATH=. python3 -m bench.controls.runner` whenever executor/adapters/controls/evaluators change. Current digest 85884db9....
- P0.4 attestation binds harness bytes: re-issue via documented runner, never silent patching.
- Shared-argv ops use maximal-envelope projections (PM-DEC-0006); changing that requires contract change, not implementation drift.

## Next Action

1. Port maximal-envelope projection semantics into researchctl/bench_adapter (participant update; make reference SUT solvable too).
2. B04 wiring: campaign runner re-checks participant artifact digest before/after execution.
3. S01–S07/B01–B06 gate suite (`bench/tests/test_p1b_gates.py`); declare `candidate_p1b` when green.
4. Then P1C (statistics, R=5 with 5-rep engine already in place, bootstrap, clean-room).
