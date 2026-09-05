# P0.4 Negative Controls

P0.4 validates the benchmark harness itself. Each control is a real `sut-adapter/v1` participant and is evaluated by the same 33-scenario Oracle-only runner used for ResearchCTL.

Controls:

- `always-pass`
- `always-abstain`
- `universal-stale`
- `universal-impact`
- `random`
- `gold-reader`

Acceptance does not depend on the control name. Every control must fail formal scenarios or the integrity gate, remain `certification_eligible=false`, keep Tier `N/A`, and never obtain a passing conclusion. Random runs twice with identical evaluation bytes. The official ResearchCTL adapter also runs twice with identical evaluation bytes. Gold-Reader runs under an OS filesystem sandbox and must report `gold_read_blocked=true`.

`attestation.json` binds:

- Oracle manifest digest;
- source/fixture hashes;
- pack registry and all 33 action files;
- control, adapter, executor, evaluator and Oracle implementation digest;
- each control evaluation digest;
- Random retry digest;
- official participant command and retry digest.

The default CLI validates this attestation fail-closed. A missing, stale or modified attestation sets P0.4 back to pending. P0 harness completion does not certify the official participant: the current ResearchCTL formal result remains 6/33 with Tier N/A.
