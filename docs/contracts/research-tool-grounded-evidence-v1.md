# research-tool evidence and review reader contracts

Date: 2026-10-23. This reader adds capabilities; it does not certify clinical truth.

## Capability handshake

`python -m researchctl --layout research-tool --root ROOT capabilities` returns `retrieval-manifest/v1`, `report-review/v1`, `evidence-snapshot/v1`, and `issue-evaluation/v1`. An older reader or a legacy layout must not silently satisfy these contracts.

## Final manifest compatibility

- Canonical `run-record.json` remains unchanged. Its four final-file pins are a subset of runtime-committed final files.
- Current summary files must equal every runtime-committed final output and the actual final directory set, with identical hashes. No arbitrary extras are allowed.
- Old v1 citation records lacking title derive it from the pinned final source. Where the old graph also omits title, descriptive citation metadata is retained; title never determines source identity. Conflicting explicit titles fail.

## Pre-report evidence

The `evidence` action takes `--snapshot`, mandatory `--snapshot-hash`, `--view graph|body`, optional `--source-id`/exact `--text`, and explicit page offset/limit. It validates the actual committed graph envelope and all raw/clean dependencies, without requiring a successful report or creating SQLite.

The source snapshot is report-independent. It names only committed stage envelopes and exact clean/raw files. `body` searches whole clean bodies, not only report-selected facts, returning exact offsets, hashes and table/paragraph text. Page truncation, match count and the fact that unavailable supplements were not searched are explicit. Empty lookup is never an absence proof. Source/graph drift or unsafe paths fail closed. `graph` returns the full validated ledger, not a selected subset.

## Review and report adoption

Append-only `runs/<id>/reviews/*.json` records use `report-review/v1`. Each is bound to the run, report SHA and runtime-committed evidence SHA/path, and states `passed|rejected`, `agent_source_review`, reviewer, reason and UTC timestamp. Ordinary current/history queries preserve execution identity and expose review state separately. This mechanism cannot confer human clinical authorization.

`query --entity CURRENT --require-review agent_source_review` only adopts that exact current successful report when its latest unambiguous pinned review passed. Missing/rejected review or failed current execution cannot fall back to an earlier machine success. `human_clinical` does not match an Agent review.

## Cross-repository accepted scope (2026-10-23)

Companion producer branch `feat/researchctl-grounded-report-20261023` generated independent run `d672f7fb457b4d4eaa00ba4f8c60847a` using runtime19/source commit `6dcbd99`; resume stage projection was subsequently fixed by `eb9f232` without changing report bytes. The report SHA is `1952b47401b0b7113aaddaed9dea83531844097dd7d4c722b0bfc950660ce585`.

The frozen ten-public-fulltext acceptance covers 2070 ledger facts, 60 Chinese template observations plus 27 required original anchors, 147 report claims and 125 final-file hashes. An independent Agent source rereading record passed within explicit limits; current Agent adoption succeeds while human clinical adoption fails closed. All 107 unresolved findings and 28 limitations remain. This is not new-search coverage, latest systematic review or clinical validation. Previous machine successes rejected by source review remain rejected. Zero-model resume, index/trace/sources/reconcile and exact report hash were rechecked.

Local producer evidence stays in its ignored implementation output and the authorized medical workspace; no papers, private patients or credentials are part of either repository. Reader layout/body tests11 and legacy443checks pass; three existing benchmark attestation/public-root failures reproduce on the unchanged baseline and are not re-certified here.

## Explicit reviewed issue evaluation (I1–I4)

The companion producer keeps `disposition.policy=raw` by default without changing runtime19 input identity. Explicit reviewed consumption pins a single registry HEAD, the reader implementation/interpreter identity and `issue-evaluation/v1` capability before collection. No legacy/unknown reader fallback is permitted.

`final/issue-evaluation.json` is report-runtime committed and byte-equal to its envelope value. It embeds `issue-ledger-snapshot/v1` with the single content-addressed HEAD chain, state digest and exact hash-pinned original audit/graph artifact bytes. The reader verifies every revision/event hash, fully replays initialize/import/proposal/review/network/history transitions in a pure read-only projection, checks each intermediate state digest and recomputes effective required issues/counts from raw findings and children/canonical links. It never writes a second registry or lets SQLite become authority. Network/policy changes invalidate old approvals; current closure evidence cannot disappear merely because an inspection omits a finding.

Summary and per-run manifest required_contracts must exactly match the committed sidecar, including historical runs without a current summary. Raw manifests stay v1; explicit reviewed manifests use schema_version=2 so real pinned old v1 readers reject rather than silently ignoring added fields. Report review additionally pins issue-evaluation SHA, HEAD, network and policy digests. Unknown schema, changed proposal/state/counts, missing review version, symlink/hash/span failures fail closed. Raw verdicts and the four canonical final record fields are unchanged; extra final sidecars remain in the full committed file set.

Issue closure is an Agent decision, not medical truth: scientific_answered, administratively_disposed and new_scientific_evidence_added remain separate. Synonym grouping, same-register papers, secondary citations and context containment do not automatically create independent scientific evidence or close issues. The actual medical rehearsal imported107 findings +28 limitations, created135 classification proposals and238 mapping candidates without approving them;135 required issues remain unresolved and scientific/new-evidence counts are zero. Original173 run files remain unchanged.

Implementation checkpoint: reader `1602bd48bcefb921b0a20fc2614fd646429c1d6e` and producer `b1c25a58dc5e12f1c55a2d71fe1b4012a257ed79`, on non-main feature branches. Existing Pi /review replay/evidence and evaluation/projection scopes both approve0 after adverse-case fixes; actual producer pre-push1381 passed/3 skipped, reader11 and legacy443checks passed. No package version/tag/main change.

## Verification

Producer integration tests live in research-tool and execute its actual nine-stage pipeline with only external search/model I/O replaced. Reader-specific tests are `researchctl/tests/test_grounded_evidence_queries.py` and `test_research_tool_layout.py`. Full-source counterexamples, snapshot recovery and malicious numerical rewrites are exercised by the producer tests.

The prior benchmark attestation/public-root failures reproduce in the untouched base commit; no benchmark data, assertions or attestations are rewritten for these features. Use `-c pytest.ini` for pytest because the historical nested `researchctl/pyproject.toml` is JSON metadata, not a valid TOML test configuration. The legacy acceptance scripts are executable scripts with top-level SystemExit; run them directly with PYTHONPATH set to this checkout, not as pytest imports.
