# Independent Oracle — P0.3B

Status: **INCOMPLETE (`oracle_shadow`)**.

P0.3A froze four contracts:

- `oracle-manifest/v1`: objective initial universe;
- `scenario-actions/v1`: execution and world mutations only;
- `prediction/v1`: participant claims only;
- `compiled-gold/v1`: generated expectations and state transitions.

P0.3B migrates all 33 canonical scenario IDs onto that shadow path. This is full **Oracle coverage**, not a passing benchmark result and not the P0.3 trust-path cutover.

## Trust Path

```text
oracle manifest + action DSL ──compile before SUT start──> sealed Gold
                                                        ┌──────────────┐
action DSL ──execute through sut-adapter/v1────────────>│ prediction + │
                                                        │ observations │
sealed Gold + prediction/observations ──generic eval───>│ derived score│
                                                        └──────────────┘
```

`compile_gold(manifest, actions)` accepts no adapter, workspace, prediction or SUT input. `execute_actions(...)` receives no compiled Gold. Scenario files cannot contain `passed`, `score`, `expected_*`, `gold_*`, TP/FP/FN, CIV, version correctness or graph-match fields.

## P0.3B State

A full v0.5 run reports:

- `evaluation_engine: oracle_shadow`;
- `oracle.coverage.compiled: 33` of 33;
- `p0_3_status: incomplete_p0_3b`;
- `certification_eligible: false`;
- `tier: N/A`;
- `coverage.ineligible_reasons: ["P0_3_SHADOW_MODE"]`.

The official ResearchCTL adapter currently passes 5 strict Oracle scenarios and fails 28. Those failures expose missing `prediction/v1` facts, evidence, graph, exact condition, routing or frozen-CLE support. They must remain visible; legacy 33/33 values are diagnostic only and do not establish Oracle-scored quality.

## P0.3C Exit

P0.3 can be declared complete only after the default path stops calling all legacy `run_sXX()` self-scoring functions, formal metrics are aggregated only from Oracle evaluations, and no mixed legacy/Oracle score remains. P0 remains incomplete after that until P0.4 negative controls pass.
