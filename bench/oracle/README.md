# Independent Oracle — P0.3C

Status: **COMPLETE (`oracle_only`)**. P0 remains **INCOMPLETE** until P0.4 negative controls pass.

## Default Trust Path

```text
pack.json + oracle-manifest/v1 + scenario-actions/v1
  ├─ compile before participant start → compiled-gold/v1
  └─ execute through sut-adapter/v1 → prediction/v1 + observations

compiled Gold + prediction/observations → OracleScenarioEvaluation → formal metrics
```

The default CLI does not invoke legacy `run_sXX()` functions. The pack-owned `pack.json` registry and action files own scenario selection and metadata. Formal score, TP/FP/FN, CIV, version accuracy, graph exactness, refusal accuracy and integrity metrics derive only from Oracle evaluations.

Legacy scenarios remain available only through `--legacy-diagnostic`. Their values are nested under `legacy_diagnostic` and cannot alter formal Oracle fields.

## Machine Contracts

- `oracle-manifest/v1`: objective universe, lifecycle, facts, evidence, relations and query registry.
- `scenario-actions/v1`: execution and world mutations only; no expected results or scores.
- `prediction/v1`: closed participant output with complete typed ResultRow objects.
- `compiled-gold/v1`: deterministic pre-SUT state/checkpoints/digests.

## Current Official Participant

A full v0.6 run reports:

- `evaluation_engine: oracle_only`;
- `p0_3_status: complete_p0_3c`;
- Oracle coverage 33/33;
- formal 6 PASS / 27 FAIL, composite 20.8;
- CIV 0;
- legacy diagnostic absent by default;
- `certification_eligible: false`, Tier N/A;
- ineligible reason `P0_4_NEGATIVE_CONTROLS_PENDING`.

The 27 strict failures are preserved. In particular, S29 rejects the participant's schema-incompatible SQLite index under frozen CLE, and S31 rejects an extra opaque reconciliation result even though external SIGKILL/no-half-commit/fixed-point observations pass.

P0.4 must now prove that Always-Pass, Always-Abstain, Universal-Stale, Universal-Impact, Random and Gold-Reader controls cannot obtain eligibility or a passing conclusion.
