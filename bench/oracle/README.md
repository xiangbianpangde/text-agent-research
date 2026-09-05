# Independent Oracle — P0.3A

Status: **INCOMPLETE (`oracle_shadow`)**.

P0.3A freezes four contracts:

- `oracle-manifest/v1`: objective initial universe;
- `scenario-actions/v1`: execution and world mutations only;
- `prediction/v1`: participant claims only;
- `compiled-gold/v1`: generated expectations and state transitions.

The trust path is:

```text
oracle manifest + action DSL ──compile before SUT start──> sealed Gold
                                                        ┌──────────────┐
action DSL ──execute through sut-adapter/v1────────────>│ prediction + │
                                                        │ observations │
sealed Gold + prediction/observations ──generic eval───>│ derived score│
                                                        └──────────────┘
```

`compile_gold(manifest, actions)` accepts no adapter, workspace, prediction or SUT input. `execute_actions(...)` receives no compiled Gold. Scenario files cannot contain `passed`, `score`, `expected_*`, `gold_*`, TP/FP/FN, CIV, version correctness or graph-match fields.

## P0.3A anchors

The first seven migrated scenarios are S03, S07, S12, S16, S17, S24 and S31. They span pinned external truth, exact version binding, exact scientific evidence, impact/stale set difference, fail-closed/CIV behavior and externally killed transaction recovery.

A full v0.4 run therefore reports:

- `evaluation_engine: oracle_shadow`;
- `oracle.coverage.compiled: 7` of 33;
- `p0_3_status: incomplete_p0_3a`;
- `certification_eligible: false`;
- `tier: N/A`.

Legacy 33-scenario results remain visible only as diagnostics and do not establish Oracle-scored benchmark quality. P0.3 can be declared complete only after P0.3C cuts the active path over to 33/33 independently compiled Gold scenarios.
