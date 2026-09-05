"""P0.2 tests for the generic process-level SUT adapter."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bench.adapters import ProcessSUTAdapter
from bench.adapters.process import project_root
from bench.adapters.protocol import AdapterProtocolError, make_request, validate_response
from bench.runner import BenchmarkSandbox


STUB_COMMAND = [sys.executable, "-m", "bench.tests.fixtures.stub_sut"]


class ProtocolContractTests(unittest.TestCase):
    def test_all_required_lifecycle_operations_are_valid(self) -> None:
        for operation in ("prepare", "invoke", "reset_context", "restart", "health", "shutdown"):
            fields = {}
            if operation == "prepare":
                fields["workspace"] = "/tmp/workspace"
            if operation == "invoke":
                fields["arguments"] = ["query", "--entity", "EXP-017"]
            request = make_request(f"req-{operation}", operation, **fields)
            self.assertEqual(request["operation"], operation)

    def test_response_request_id_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(AdapterProtocolError, "request_id mismatch"):
            validate_response(
                {
                    "schema_version": "sut-adapter/v1",
                    "request_id": "other",
                    "operation": "health",
                    "status": "ok",
                },
                expected_request_id="expected",
                expected_operation="health",
            )


class DeterministicFingerprintTests(unittest.TestCase):
    def test_directory_creation_order_does_not_change_fingerprint(self) -> None:
        from researchctl.queries import current_fingerprint

        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            for root, order in ((Path(first), ("z", "a")), (Path(second), ("a", "z"))):
                for name in order:
                    directory = root / name
                    directory.mkdir()
                    (directory / "value.txt").write_text(name, encoding="utf-8")
            self.assertEqual(current_fingerprint(first), current_fingerprint(second))


class AdapterLifecycleTests(unittest.TestCase):
    def test_official_researchctl_runs_out_of_process_without_pythonpath(self) -> None:
        with BenchmarkSandbox("fixture") as sandbox:
            health = sandbox.adapter.health()
            code, payload = sandbox.run_json(["query", "--entity", "EXP-017"])

            self.assertEqual(health["adapter"], "researchctl")
            self.assertFalse(health["pythonpath_present"])
            self.assertEqual(code, 0)
            self.assertEqual(payload["status"], "success")
            self.assertEqual(sandbox.sut_metadata["protocol"], "sut-adapter/v1")
            self.assertTrue(str(sandbox.sut_metadata["command_digest"]).startswith("sha256:"))

    def test_restart_replaces_process_and_reprepares_workspace(self) -> None:
        with BenchmarkSandbox("fixture") as sandbox:
            first = sandbox.adapter.health()
            sandbox.adapter.reset_context()
            sandbox.adapter.restart()
            second = sandbox.adapter.health()
            code, payload = sandbox.run_json(["query", "--entity", "EXP-017"])

            self.assertNotEqual(first["pid"], second["pid"])
            self.assertTrue(second["workspace_prepared"])
            self.assertEqual(code, 0)
            self.assertEqual(payload["status"], "success")

    def test_independent_stub_implements_same_protocol(self) -> None:
        with ProcessSUTAdapter(STUB_COMMAND, cwd=project_root()) as adapter:
            adapter.prepare("fixture")
            health = adapter.health()
            result = adapter.invoke(["query", "--entity", "EXP-017"])

            self.assertEqual(health["adapter"], "independent-stub")
            self.assertFalse(health["pythonpath_present"])
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(result.payload["error_semantic"], "BASELINE_UNSUPPORTED")

    def test_cli_measures_independent_stub_with_same_runner(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "bench",
                "--scenario",
                "S25",
                "--sut-command-json",
                json.dumps(STUB_COMMAND),
                "--sut-cwd",
                project_root(),
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        report = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(report["sut"]["adapter"], "independent-stub")
        self.assertEqual(report["total_scenarios"], 1)
        self.assertIsNone(report["passed_scenarios"])
        self.assertEqual(report["legacy_diagnostic"]["passed_scenarios"], 0)
        self.assertEqual(report["tier"], "N/A")
        self.assertFalse(report["certification_eligible"])


if __name__ == "__main__":
    unittest.main()
