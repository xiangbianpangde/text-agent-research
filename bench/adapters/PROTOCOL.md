# ResearchCTL-Bench SUT Adapter Protocol v1

> P0.2 implementation contract. The executable contract is enforced by `protocol.py` and `bench/tests/test_p0_2_adapter.py`.

## Transport

The harness starts one participant process and communicates over UTF-8 stdio NDJSON:

- stdin: exactly one request JSON object per line;
- stdout: exactly one response JSON object per request line;
- stderr: participant diagnostics only;
- unsolicited or non-JSON stdout is a protocol violation;
- every message uses `schema_version: "sut-adapter/v1"`;
- every response must echo the request's `request_id` and `operation`.

The generic harness removes `PYTHONPATH` before process launch. A participant must be discoverable through its explicit command and launch directory.

## Request envelope

```json
{
  "schema_version": "sut-adapter/v1",
  "request_id": "req-000001-ab12cd34",
  "operation": "health"
}
```

Operations form a closed set:

- `prepare`
- `invoke`
- `reset_context`
- `restart`
- `health`
- `shutdown`

### prepare

```json
{
  "schema_version": "sut-adapter/v1",
  "request_id": "req-prepare",
  "operation": "prepare",
  "workspace": "/absolute/sandbox/workspace"
}
```

The participant must bind subsequent invocations to this workspace. Missing or invalid workspaces return an error response.

### invoke

```json
{
  "schema_version": "sut-adapter/v1",
  "request_id": "req-invoke",
  "operation": "invoke",
  "arguments": ["query", "--entity", "EXP-017"],
  "timeout_ms": 30000
}
```

`arguments` is a string array interpreted by the participant. It is not a host shell command. `timeout_ms` is an integer in `[1, 600000]`; the harness terminates a participant that misses the response deadline. P0.3 adds the optional string `capture_id`, used only to bind a `prediction/v1` payload to an execution checkpoint.

Crash-safety cases may add an optional test-control object:

```json
{
  "capture_id": "after-staging-kill",
  "test_control": {
    "pause_at": "after-staging",
    "barrier_path": ".bench-control/after-staging-kill.json"
  }
}
```

A participant supporting this control writes the workspace-confined barrier and blocks; it must not terminate itself. The harness then issues the external hard kill. The operation remains `invoke`; this optional instrumentation does not add a lifecycle operation.

### reset_context

Clears participant session/model context while preserving the prepared workspace. Stateless B1 adapters may acknowledge it as a no-op.

### restart

The participant acknowledges the request and exits successfully. The harness launches a new process, repeats `prepare` for the same workspace, and performs `health` again.

### health

Returns adapter identity, supported operations, process identity and readiness details. The report binds the participant through a stable command digest rather than exposing host-specific command paths.

### shutdown

The participant acknowledges the request and exits. The harness forcibly terminates it if graceful shutdown does not complete within the bounded timeout.

## Response envelopes

Success:

```json
{
  "schema_version": "sut-adapter/v1",
  "request_id": "req-health",
  "operation": "health",
  "status": "ok",
  "details": {
    "adapter": "researchctl",
    "capabilities": ["prepare", "invoke", "reset_context", "restart", "health", "shutdown"]
  }
}
```

Error:

```json
{
  "schema_version": "sut-adapter/v1",
  "request_id": "req-prepare",
  "operation": "prepare",
  "status": "error",
  "error": {
    "code": "WORKSPACE_NOT_FOUND",
    "message": "/missing/workspace"
  }
}
```

A successful `invoke` additionally requires:

```json
{
  "exit_code": 0,
  "stdout": "{...}",
  "stderr": "",
  "payload": {}
}
```

`payload` is a strict `prediction/v1` object for P0.3 execution. It contains claims, result sets, evidence and routing declarations, but cannot contain `passed`, `score`, TP/FP/FN, CIV, version correctness or graph-match fields. Benchmark semantics are compared with sealed independent Gold; participants cannot self-award scores.

## Harness CLI

Default official participant:

```bash
python3 -m bench --scenario S25 --json
```

Explicit third-party participant:

```bash
python3 -m bench \
  --scenario S25 \
  --sut-command-json '["/absolute/path/to/participant-adapter"]' \
  --sut-cwd /absolute/participant/root \
  --json
```

A partial run remains diagnostic and cannot receive a Tier, regardless of participant output.

## P0.2 boundary

Completed here:

- process-level transport and lifecycle;
- official ResearchCTL participant adapter;
- custom participant command selection;
- no benchmark-side `researchctl` imports;
- no `PYTHONPATH` injection;
- command digest and adapter identity in machine reports;
- independent weak stub measured through the same runner.

Not claimed here:

- independent Gold or semantic scoring (P0.3);
- hostile filesystem/container isolation and Gold-reader defense (P0.4);
- OCI submission or remote leaderboard operation (P2).
