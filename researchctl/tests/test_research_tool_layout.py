"""Research-tool layout M2/M3 integration tests.

The fixture is self-contained and never reads the research-tool repository.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def run_cli(root: Path, *args: str) -> dict:
    command = [
        sys.executable,
        "-m",
        "researchctl",
        "--layout",
        "research-tool",
        "--root",
        str(root),
        *args,
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode != 0:
        raise AssertionError(f"CLI failed: {completed.args}\nstdout={completed.stdout}\nstderr={completed.stderr}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"CLI did not return JSON: {completed.stdout}") from exc


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_run(
    root: Path,
    topic_slug: str,
    topic: str,
    run_id: str,
    timestamp: str,
    *,
    verdict: str = "STOP_SUCCESS",
    pipeline_complete: bool = True,
) -> Path:
    topic_root = root / topic_slug
    run_root = topic_root / "runs" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    write_json(topic_root / "run-summary.json", {"topic": topic, "run_id": run_id})
    write_json(topic_root / "runtime-state.json", {"topic_slug": topic_slug, "run_id": run_id, "state": "complete"})

    raw_path = run_root / "raw" / f"{run_id}-source.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(f"# Source {run_id}\n\nEvidence for {topic} / {run_id}.\n", encoding="utf-8")

    report_path = run_root / "final" / "report.md"
    sources_path = run_root / "final" / "sources.json"
    graph_path = run_root / "final" / "tree" / "knowledge.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(f"# {topic}\n\nReport for {run_id}.\n", encoding="utf-8")
    write_json(sources_path, {"run_id": run_id, "sources": [f"raw/{run_id}-source.md"]})
    write_json(graph_path, {"topic": topic, "run_id": run_id, "nodes": [{"id": run_id}]})

    source_hash = sha256_file(raw_path)
    report_hash = sha256_file(report_path)
    sources_hash = sha256_file(sources_path)
    graph_hash = sha256_file(graph_path)
    manifest = {
        "topic": topic,
        "topic_slug": topic_slug,
        "run_id": run_id,
        "verdict": verdict,
        "pipeline_complete": pipeline_complete,
        "stages": {"collect": "complete" if pipeline_complete else "stopped"},
        "artifacts": {
            "report": "final/report.md",
            "sources": "final/sources.json",
            "knowledge": "final/tree/knowledge.json",
        },
        "artifact_hashes": {
            "report": report_hash,
            "sources": sources_hash,
            "knowledge": graph_hash,
        },
        "sources": [{
            "raw_path": f"raw/{run_id}-source.md",
            "body_sha256": source_hash,
            "artifact_sha256": source_hash,
            "evidence_kind": "retrieved_markdown",
        }],
        "completed_at": timestamp,
    }
    write_json(run_root / "retrieval-manifest.json", manifest)
    return raw_path


def create_fixture() -> Path:
    root = Path(tempfile.mkdtemp(prefix="researchctl-research-tool-"))
    create_run(root, "alpha", "Alpha Topic", "run-001", "2026-10-01T10:00:00Z")
    create_run(root, "alpha", "Alpha Topic", "run-002", "2026-10-02T10:00:00Z")
    create_run(root, "beta", "Beta Topic", "run-101", "2026-10-01T11:00:00Z")
    return root


class ResearchToolLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = create_fixture()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_index_queries_navigation_and_reconcile(self) -> None:
        indexed = run_cli(self.root, "index")
        self.assertEqual(indexed["status"], "success")
        self.assertEqual(indexed["source_watermark"]["layout"], "research-tool")

        current = run_cli(self.root, "query", "--doc-type", "report_current")
        self.assertEqual(current["status"], "success")
        self.assertEqual({item["entity_id"] for item in current["results"]}, {
            "report:alpha:run-002", "report:beta:run-101",
        })

        historical = run_cli(self.root, "query", "--doc-type", "report_historical")
        self.assertEqual(historical["status"], "success")
        self.assertEqual([item["entity_id"] for item in historical["results"]], ["report:alpha:run-001"])

        owner = "report:alpha:run-002"
        sources = run_cli(self.root, "sources", owner)
        self.assertEqual(sources["status"], "success")
        self.assertEqual(sources["authority"], "canonical")
        self.assertTrue(any(item["path"].endswith("knowledge.json") for item in sources["results"]))
        self.assertTrue(any(item["path"].endswith("run-002-source.md") for item in sources["results"]))

        trace = run_cli(self.root, "trace", owner)
        self.assertEqual(trace["status"], "success")
        trace_paths = {item["path"] for item in trace["results"]}
        self.assertTrue(any(path.endswith("knowledge.json") for path in trace_paths))
        self.assertTrue(any(path.endswith("run-002-source.md") for path in trace_paths))

        history = run_cli(self.root, "history")
        self.assertEqual(history["status"], "success")
        self.assertEqual({item["entity_id"] for item in history["results"]}, {
            "report:alpha:run-001", "report:alpha:run-002", "report:beta:run-101",
        })

        generated = run_cli(self.root, "generate-index")
        self.assertEqual(generated["status"], "success")
        self.assertTrue((self.root / "index" / "INDEX.md").is_file())
        # Derived navigation must not make the base index stale.
        self.assertEqual(run_cli(self.root, "query")["status"], "success")

        reconciled = run_cli(self.root, "reconcile")
        self.assertEqual(reconciled["status"], "success")
        self.assertEqual(reconciled["results"][0]["issue_count"], 0)

    def test_deleted_source_fails_closed(self) -> None:
        run_cli(self.root, "index")
        source = self.root / "alpha" / "runs" / "run-002" / "raw" / "run-002-source.md"
        source.unlink()
        # Reindex preserves the manifest-pinned source hash and makes the
        # missing canonical source observable as SOURCE_MISSING.
        run_cli(self.root, "index")
        result = run_cli(self.root, "sources", "report:alpha:run-002")
        self.assertEqual(result["status"], "fail_closed")
        self.assertEqual(result["error_semantic"], "SOURCE_MISSING")
        reconcile = run_cli(self.root, "reconcile")
        self.assertEqual(reconcile["status"], "fail_closed")
        self.assertIn("SOURCE_MISSING", {item["issue"] for item in reconcile["results"][0]["issues"]})

    def test_tampered_source_reports_hash_mismatch(self) -> None:
        run_cli(self.root, "index")
        source = self.root / "alpha" / "runs" / "run-002" / "raw" / "run-002-source.md"
        source.write_text(source.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
        run_cli(self.root, "index")
        result = run_cli(self.root, "sources", "report:alpha:run-002")
        self.assertEqual(result["status"], "fail_closed")
        self.assertEqual(result["error_semantic"], "HASH_MISMATCH")
        reconcile = run_cli(self.root, "reconcile")
        self.assertEqual(reconcile["status"], "fail_closed")
        self.assertIn("HASH_MISMATCH", {item["issue"] for item in reconcile["results"][0]["issues"]})

    def test_stop_success_is_current_but_budget_and_error_are_not(self) -> None:
        create_run(
            self.root,
            "gamma",
            "Gamma Topic",
            "run-budget",
            "2026-10-03T10:00:00Z",
            verdict="STOP_BUDGET",
            pipeline_complete=True,
        )
        create_run(
            self.root,
            "delta",
            "Delta Topic",
            "run-error",
            "2026-10-03T10:00:00Z",
            verdict="STOP_ERROR",
            pipeline_complete=True,
        )
        run_cli(self.root, "index")
        current = run_cli(self.root, "query", "--doc-type", "report_current")
        current_ids = {item["entity_id"] for item in current["results"]}
        self.assertIn("report:alpha:run-002", current_ids)
        self.assertIn("report:beta:run-101", current_ids)
        self.assertNotIn("report:gamma:run-budget", current_ids)
        self.assertNotIn("report:delta:run-error", current_ids)
        manifests = run_cli(self.root, "query", "--doc-type", "run_manifest")
        manifest_ids = {item["entity_id"] for item in manifests["results"]}
        self.assertIn("run:gamma:run-budget", manifest_ids)
        self.assertIn("run:delta:run-error", manifest_ids)
        with sqlite3.connect(self.root / ".index" / "research.sqlite") as conn:
            statuses = dict(conn.execute("SELECT id,status FROM documents WHERE doc_type='run_manifest'"))
        self.assertEqual(statuses["run:gamma:run-budget"], "STOP_BUDGET")
        self.assertEqual(statuses["run:delta:run-error"], "STOP_ERROR")

    def test_manifest_artifact_hashes_pin_each_final_artifact(self) -> None:
        run_cli(self.root, "index")
        final_files = {
            "report:alpha:run-002": "final/report.md",
            "sources:alpha:run-002": "final/sources.json",
            "graph:alpha:run-002": "final/tree/knowledge.json",
        }
        for relative in final_files.values():
            path = self.root / "alpha" / "runs" / "run-002" / relative
            path.write_text(path.read_text(encoding="utf-8") + "tampered artifact\n", encoding="utf-8")
        # Reindex must retain artifact_hashes from the manifest rather than
        # replacing them with the mutated file hashes.
        run_cli(self.root, "index")
        with sqlite3.connect(self.root / ".index" / "research.sqlite") as conn:
            pinned = {
                entity_id: conn.execute(
                    "SELECT content_hash FROM documents WHERE id=?", (entity_id,)
                ).fetchone()[0]
                for entity_id in final_files
            }
        for entity_id, relative in final_files.items():
            actual = sha256_file(self.root / "alpha" / "runs" / "run-002" / relative)
            self.assertNotEqual(pinned[entity_id], actual)
        reconcile = run_cli(self.root, "reconcile")
        self.assertEqual(reconcile["status"], "fail_closed")
        mismatches = {
            issue["ref"] for issue in reconcile["results"][0]["issues"]
            if issue["issue"] == "HASH_MISMATCH"
        }
        self.assertTrue(any(ref.endswith("final/report.md") for ref in mismatches))
        self.assertTrue(any(ref.endswith("final/sources.json") for ref in mismatches))
        self.assertTrue(any(ref.endswith("final/tree/knowledge.json") for ref in mismatches))

    def test_stale_index_never_returns_old_query_results(self) -> None:
        run_cli(self.root, "index")
        report = self.root / "alpha" / "runs" / "run-002" / "final" / "report.md"
        report.write_text(report.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
        result = run_cli(self.root, "query")
        self.assertEqual(result["status"], "fail_closed")
        self.assertEqual(result["error_semantic"], "INDEX_STALE")
        self.assertEqual(result["results"], [])
        for command in (("sources", "report:alpha:run-002"), ("trace", "report:alpha:run-002"), ("history",)):
            stale = run_cli(self.root, *command)
            self.assertEqual(stale["status"], "fail_closed")
            self.assertEqual(stale["error_semantic"], "INDEX_STALE")
            self.assertEqual(stale["results"], [])


if __name__ == "__main__":
    unittest.main()
