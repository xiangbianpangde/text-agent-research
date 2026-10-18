"""Acceptance tests for the strict research-tool manifest v1 layout.

The fixture is generated locally and does not read the producer repository.
Every round is retained below the requested acceptance output directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE = Path(
    "/Users/xbpd/Projects/research-tool/research-output/"
    "researchctl-integration-acceptance/engine-tests"
)
RUN_ID_1 = "1" * 32
RUN_ID_2 = "2" * 32
RUN_ID_3 = "3" * 32
RUN_ID_4 = "4" * 32
RUN_ID_5 = "5" * 32


def bare_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prefixed(data: bytes) -> str:
    return "sha256:" + bare_hash(data)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def write_json(path: Path, value: object) -> bytes:
    data = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def write_text(path: Path, value: str) -> bytes:
    data = value.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def run_cli(root: Path, *args: str, expect: int = 0) -> tuple[dict, subprocess.CompletedProcess[str]]:
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
    if completed.returncode != expect:
        raise AssertionError(
            f"unexpected CLI exit {completed.returncode} != {expect}: {command}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    try:
        return json.loads(completed.stdout), completed
    except json.JSONDecodeError as exc:
        raise AssertionError(f"CLI did not return JSON: {completed.stdout}") from exc


def new_round(name: str) -> Path:
    ACCEPTANCE.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{name}-", dir=ACCEPTANCE))


def source_payload(locator: str, text: str, *, evidence_kind: str = "body") -> tuple[str, dict, dict]:
    source_id = bare_hash(locator.encode())[:16]
    body = f"<!-- source: {locator} -->\n<!-- title: Primary source -->\n<!-- evidence_kind: {evidence_kind} -->\n\n{text}"
    raw = body.encode()
    raw_path = f"raw/{source_id}.md"
    clean_path = f"clean/{source_id}.md"
    clean = f"<!-- source: {locator} -->\n<!-- title: Primary source -->\n<!-- evidence_kind: body -->\n\n{text}"
    clean_bytes = clean.encode()
    source = {
        "source_id": source_id,
        "locator": locator,
        "title": "Primary source",
        "source_engine": "fixture",
        "fetched_at": "2026-10-18T00:00:00Z",
        "evidence_kind": evidence_kind,
        "source_tier": "official",
        "raw_path": raw_path,
        "artifact_sha256": prefixed(raw),
        "body_sha256": prefixed(text.encode()),
    }
    citation = {
        "clean_path": clean_path,
        "clean_artifact_sha256": prefixed(clean_bytes),
        "body_sha256": prefixed(text.encode()),
        "source_id": source_id,
        "locator": locator,
        "title": "Primary source",
        "raw_path": raw_path,
    }
    return body, source, citation


def make_run(
    root: Path,
    slug: str,
    topic: str,
    run_id: str,
    finished: str,
    *,
    verdict: str = "STOP_SUCCESS",
    completed: list[str] | None = None,
    skipped: list[str] | None = None,
    failed_stage: str | None = None,
    include_final: bool = True,
    source_kind: str = "body",
) -> dict:
    """Write one canonical v1 run and return its record."""
    topic_root = root / slug
    run_root = topic_root / "runs" / run_id
    artifact_root = topic_root / "artifacts" / run_id
    completed = list(completed) if completed is not None else [
        "collect", "clean", "extract", "knowledge", "inspect", "targeted", "merge", "qgate", "report"
    ]
    skipped = list(skipped) if skipped is not None else []
    stages = ["collect", "clean", "extract", "knowledge", "inspect", "targeted", "merge", "qgate", "report"]
    pipeline_complete = verdict == "STOP_SUCCESS" and include_final
    input_fingerprint = bare_hash(f"{slug}:{run_id}".encode())
    started = finished.replace("10:00:00", "09:00:00")
    topic_prefix = f"{slug}/" if slug else ""
    committed_keys = []
    files: dict[str, str] = {}
    envelopes: dict[str, dict] = {}

    raw_body, source, citation = source_payload(
        f"https://example.test/{slug}/{run_id}",
        f"Evidence body for {topic} in run {run_id}.",
        evidence_kind=source_kind,
    )
    raw_path = run_root / source["raw_path"]
    clean_path = run_root / citation["clean_path"]
    raw_bytes = write_text(raw_path, raw_body)
    clean_bytes = write_text(clean_path, raw_body if source_kind == "body" else raw_body.replace(source_kind, "body"))
    raw_rel = f"runs/{run_id}/{source['raw_path']}"
    clean_rel = f"runs/{run_id}/{citation['clean_path']}"
    source["raw_path"] = raw_rel
    citation["raw_path"] = raw_rel
    citation["clean_path"] = clean_rel

    citation_span_text = f"Evidence body for {topic} in run {run_id}."
    start = 0
    end = len(citation_span_text)
    source_graph = {
        "source_id": source["source_id"],
        "locator": source["locator"],
        "text": citation_span_text,
        "content_sha256": bare_hash(citation_span_text.encode()),
        "path": f"/legacy/research-tool/{slug}/{run_id}/clean/{source['source_id']}.md",
    }
    span = {
        "source_id": source["source_id"],
        "locator": source["locator"],
        "content_sha256": source_graph["content_sha256"],
        "start_offset": start,
        "end_offset": end,
        "text": citation_span_text,
    }
    claim = {"claim_id": f"claim:{run_id}:1", "text": citation_span_text, "citations": [span]}
    node = {"node_id": f"topic:{slug}", "title": topic, "claim_ids": [claim["claim_id"]]}
    graph = {
        "nodes": [node],
        "facts": [claim],
        "sources": [source_graph],
        "counts": {"nodes": 1, "facts": 1, "sources": 1},
    }
    report_markdown = f"# {topic}\n\n## Evidence\n\n{citation_span_text}\n"
    report_result = {
        "markdown": report_markdown,
        "claims": [{"text": citation_span_text, "claim_ids": [claim["claim_id"]], "citations": [span]}],
        "headings": [{"text": "Evidence", "claim_ids": [claim["claim_id"]]}],
    }
    final_paths: dict[str, bytes] = {}
    if include_final:
        report_bytes = write_text(run_root / "final" / "report.md", report_markdown)
        sources_bytes = write_json(run_root / "final" / "sources.json", [source_graph])
        main_table_bytes = write_text(run_root / "final" / "tree" / "00-主表.md", f"# {topic}\n")
        knowledge_bytes = write_json(run_root / "final" / "tree" / "knowledge.json", graph)
        final_paths = {
            f"runs/{run_id}/final/report.md": report_bytes,
            f"runs/{run_id}/final/sources.json": sources_bytes,
            f"runs/{run_id}/final/tree/00-主表.md": main_table_bytes,
            f"runs/{run_id}/final/tree/knowledge.json": knowledge_bytes,
        }

    def stage_result(key: str) -> dict:
        if key == "report":
            return report_result
        if key == "knowledge":
            return {"graph": graph}
        if key == "collect":
            return {"output_files": [raw_rel]}
        if key == "clean":
            return {"output_files": [clean_rel]}
        return {}

    for stage in completed:
        key = stage if stage not in {"inspect", "targeted", "merge", "qgate"} else f"{stage}:0"
        # A failed/stopped run may have only a prefix of stages.
        if stage == "report" and not include_final:
            continue
        result = stage_result(stage)
        output_files: dict[str, str] = {}
        for path in result.get("output_files", []):
            output_files[path] = bare_hash((topic_root / path).read_bytes())
        if stage == "knowledge" and include_final:
            output_files.update({path: bare_hash(data) for path, data in final_paths.items() if "knowledge.json" in path})
        if stage == "report" and include_final:
            output_files.update({path: bare_hash(data) for path, data in final_paths.items()})
        envelope = {
            "v": 1,
            "run_id": run_id,
            "stage": stage,
            "request_id": key,
            "idempotency_key": bare_hash(f"{input_fingerprint}:{key}".encode()),
            "budget_lease": {"wall_s_max": 60},
            "result": result,
            "error": None,
            "files": output_files,
        }
        envelope_path = artifact_root / (key.replace(":", "-") + ".json")
        envelope_bytes = write_json(envelope_path, envelope)
        envelope_rel = f"artifacts/{run_id}/{key.replace(':', '-')}.json"
        digest = bare_hash(envelope_bytes)
        envelopes[key] = envelope
        committed_keys.append(key)
        runtime_digest = digest
        files[envelope_rel] = digest
        files.update(output_files)

    runtime = {
        "version": 1,
        "run_id": run_id,
        "input_fingerprint": input_fingerprint,
        "round": 0,
        "completed_stages": {
            key: {
                "artifact_path": f"artifacts/{run_id}/{key.replace(':', '-')}.json",
                "artifact_digest": bare_hash(json_bytes(envelopes[key])),
            }
            for key in committed_keys
        },
        "latest_digest": runtime_digest if committed_keys else None,
    }
    final_files = {path: bare_hash(data) for path, data in final_paths.items()}
    record = {
        "version": 1,
        "run_id": run_id,
        "topic": topic,
        "topic_slug": slug,
        "verdict": verdict,
        "pipeline_complete": pipeline_complete,
        "started_at": started,
        "finished_at": finished,
        "input_fingerprint": input_fingerprint,
        "output_contract": "nine-stage",
        "stages": stages,
        "stages_completed": completed,
        "stages_skipped": skipped,
        "failed_stage": failed_stage,
        "files": final_files,
        "runtime": runtime,
    }
    record_bytes = write_json(run_root / "run-record.json", record)
    record_rel = f"runs/{run_id}/run-record.json"
    files[record_rel] = bare_hash(record_bytes)
    statuses = {stage: "completed" if stage in completed else "skipped" if stage in skipped else "not_completed" for stage in stages}
    artifacts = {}
    artifact_hashes = {}
    if include_final:
        artifacts = {
            "report": f"runs/{run_id}/final/report.md",
            "sources": f"runs/{run_id}/final/sources.json",
            "main_table": f"runs/{run_id}/final/tree/00-主表.md",
            "knowledge": f"runs/{run_id}/final/tree/knowledge.json",
        }
        artifact_hashes = {
            name: "sha256:" + final_files[path]
            for name, path in artifacts.items()
        }
    manifest = {
        "schema_version": 1,
        "producer": "research-tool",
        "topic": topic,
        "topic_slug": slug,
        "run_id": run_id,
        "verdict": verdict,
        "pipeline_complete": pipeline_complete,
        "started_at": started,
        "finished_at": finished,
        "input_fingerprint": input_fingerprint,
        "stages": statuses,
        "failed_stage": failed_stage,
        "artifacts": artifacts,
        "artifact_hashes": artifact_hashes,
        "record_path": record_rel,
        "record_sha256": "sha256:" + bare_hash(record_bytes),
        "files": {path: "sha256:" + digest for path, digest in files.items()},
        "sources": [source],
        "citation_sources": [citation] if pipeline_complete else [],
    }
    write_json(run_root / "retrieval-manifest.json", manifest)
    return record


def write_current(root: Path, slug: str, record: dict) -> None:
    """Publish only a view of the canonical current run-record.

    The helper never reconstructs runtime from a summary; it reloads the
    canonical run-record and copies its exact runtime snapshot.
    """
    topic_root = root / slug
    run_id = record.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise AssertionError("current publication requires run-record run_id")
    canonical_path = topic_root / "runs" / run_id / "run-record.json"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    if canonical.get("run_id") != run_id or "runtime" not in canonical:
        raise AssertionError("current publication must read a canonical run-record runtime")
    summary = {key: value for key, value in canonical.items() if key != "runtime"}
    write_json(topic_root / "run-summary.json", summary)
    write_json(topic_root / "runtime-state.json", canonical["runtime"])


def create_fixture(*, two_topics: bool = True, include_failures: bool = True) -> Path:
    root = new_round("fixture")
    alpha_old = make_run(root, "alpha", "Alpha Topic", RUN_ID_1, "2026-10-01T10:00:00Z")
    alpha_current = make_run(root, "alpha", "Alpha Topic", RUN_ID_2, "2026-10-02T10:00:00Z")
    write_current(root, "alpha", alpha_current)
    if two_topics:
        beta_current = make_run(root, "beta", "Beta Topic", RUN_ID_3, "2026-10-01T11:00:00Z")
        write_current(root, "beta", beta_current)
    if include_failures:
        budget = make_run(root, "gamma", "Gamma Topic", RUN_ID_4, "2026-10-03T10:00:00Z",
                          verdict="STOP_BUDGET", completed=["collect"], skipped=[], failed_stage="clean", include_final=False)
        write_current(root, "gamma", budget)
        error = make_run(root, "delta", "Delta Topic", RUN_ID_5, "2026-10-03T11:00:00Z",
                         verdict="STOP_ERROR", completed=["collect"], skipped=[], failed_stage="extract", include_final=False)
        write_current(root, "delta", error)
    return root


class ResearchToolLayoutTests(unittest.TestCase):
    def test_success_multi_topic_index_query_and_history(self) -> None:
        root = create_fixture()
        indexed, _ = run_cli(root, "index")
        self.assertEqual(indexed["status"], "success")
        self.assertEqual(indexed["source_watermark"]["layout"], "research-tool")
        self.assertEqual(run_cli(root, "query", "--doc-type", "report_current")[0]["status"], "success")
        current, _ = run_cli(root, "query", "--doc-type", "report_current")
        self.assertEqual({item["run_id"] for item in current["results"]}, {RUN_ID_2, RUN_ID_3})
        historical, _ = run_cli(root, "query", "--doc-type", "report_historical", "--topic", "alpha")
        self.assertEqual([item["run_id"] for item in historical["results"]], [RUN_ID_1])
        ambiguous, _ = run_cli(root, "query", "--entity", "CURRENT", expect=1)
        self.assertEqual(ambiguous["error_semantic"], "AMBIGUOUS_VERSION")
        selected, _ = run_cli(root, "query", "--entity", "CURRENT", "--topic", "alpha")
        self.assertEqual(selected["status"], "success")
        self.assertEqual(selected["results"][0]["run_id"], RUN_ID_2)
        history, _ = run_cli(root, "history")
        self.assertEqual({item["run_id"] for item in history["results"]}, {RUN_ID_1, RUN_ID_2, RUN_ID_3, RUN_ID_4, RUN_ID_5})
        as_of, _ = run_cli(root, "history", "--as-of", "2026-10-01T23:00:00Z", "--topic", "alpha")
        self.assertEqual([item["run_id"] for item in as_of["results"]], [RUN_ID_1])

    def test_sources_trace_and_raw_separate_discovery(self) -> None:
        root = create_fixture(include_failures=False)
        run_cli(root, "index")
        owner = f"report:alpha:{RUN_ID_2}"
        sources, _ = run_cli(root, "sources", owner)
        self.assertEqual(sources["status"], "success")
        self.assertEqual(len(sources["results"]), 1)
        self.assertEqual(sources["results"][0]["evidence_kind"], "body")
        trace, _ = run_cli(root, "trace", owner)
        self.assertEqual(trace["status"], "success")
        self.assertTrue(any(item.get("relation_type") == "supported_by" for item in trace["results"]))
        raw, _ = run_cli(root, "query", "--raw", "--topic", "alpha")
        self.assertTrue(raw["results"])
        self.assertTrue(all(item["entity_id"].startswith("raw:") for item in raw["results"]))

    def test_budget_error_cancelled_have_no_final_and_are_visible(self) -> None:
        root = create_fixture(include_failures=True)
        # Add a cancellation-only run under a separate topic.
        cancelled = make_run(root, "epsilon", "Epsilon Topic", "e" * 32, "2026-10-03T12:00:00Z",
                             verdict="STOP_CANCELLED", completed=[], skipped=[], failed_stage="collect", include_final=False)
        write_current(root, "epsilon", cancelled)
        indexed, _ = run_cli(root, "index")
        self.assertEqual(indexed["status"], "success")
        manifests, _ = run_cli(root, "query", "--doc-type", "run_manifest")
        self.assertEqual({item["run_id"] for item in manifests["results"]}, {RUN_ID_1, RUN_ID_2, RUN_ID_3, RUN_ID_4, RUN_ID_5, "e" * 32})
        failed_current, _ = run_cli(root, "query", "--entity", "CURRENT", "--topic", "gamma", expect=1)
        self.assertEqual(failed_current["error_semantic"], "SOURCE_UNAVAILABLE")
        current, _ = run_cli(root, "query", "--doc-type", "report_current")
        self.assertNotIn("gamma", {item["topic_slug"] for item in current["results"]})

    def test_tamper_stale_reindex_rejected_and_no_db_query_side_effect(self) -> None:
        root = create_fixture(include_failures=False)
        missing_db = root / ".index" / "research.sqlite"
        before = set((root / ".index").glob("*") if (root / ".index").exists() else [])
        missing, _ = run_cli(root, "query", expect=1)
        self.assertEqual(missing["error_semantic"], "INDEX_STALE")
        after = set((root / ".index").glob("*") if (root / ".index").exists() else [])
        self.assertEqual(before, after)
        run_cli(root, "index")
        report = root / "alpha" / "runs" / RUN_ID_2 / "final" / "report.md"
        report.write_text(report.read_text() + "tampered\n", encoding="utf-8")
        stale, _ = run_cli(root, "query", "--topic", "alpha", expect=1)
        self.assertEqual(stale["error_semantic"], "INDEX_STALE")
        self.assertEqual(stale["results"], [])
        bad_index, _ = run_cli(root, "index", expect=1)
        self.assertEqual(bad_index["error_semantic"], "HASH_MISMATCH")
        self.assertTrue(missing_db.is_file())

    def test_paths_symlink_and_hash_contract(self) -> None:
        root = create_fixture(include_failures=False)
        run_cli(root, "index")
        source = root / "alpha" / "runs" / RUN_ID_2 / "raw"
        link = root / "alpha" / "runs" / RUN_ID_2 / "raw-link"
        try:
            link.symlink_to(source, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        rejected, _ = run_cli(root, "query", "--topic", "alpha", expect=1)
        self.assertEqual(rejected["error_semantic"], "UNSAFE_PATH")

        link.unlink()
        manifest = root / "alpha" / "runs" / RUN_ID_2 / "retrieval-manifest.json"
        payload = json.loads(manifest.read_text())
        payload["record_path"] = "../escape/run-record.json"
        manifest.write_bytes(json_bytes(payload))
        rejected, _ = run_cli(root, "index", expect=1)
        self.assertIn(rejected["error_semantic"], {"UNSAFE_PATH", "PROVENANCE_BROKEN"})

    def test_equal_finished_timestamp_is_ambiguous_and_legacy_manifest_is_unavailable(self) -> None:
        root = create_fixture(two_topics=False, include_failures=False)
        make_run(root, "alpha", "Alpha Topic", "a" * 32, "2026-10-02T10:00:00Z")
        # Keep summary/runtime pointing to the first current run; equal timestamps still fail closed.
        current = json.loads((root / "alpha" / "runs" / RUN_ID_2 / "run-record.json").read_text())
        write_current(root, "alpha", current)
        ambiguous, _ = run_cli(root, "index", expect=1)
        self.assertEqual(ambiguous["error_semantic"], "AMBIGUOUS_VERSION")

        legacy = new_round("legacy")
        topic = legacy / "alpha"
        (topic / "runs" / RUN_ID_1).mkdir(parents=True)
        write_json(topic / "runs" / RUN_ID_1 / "retrieval-manifest.json", {"schema_version": 1})
        unavailable, _ = run_cli(legacy, "index", expect=1)
        self.assertEqual(unavailable["error_semantic"], "SOURCE_UNAVAILABLE")
        self.assertIn("重建", unavailable["errors"][0]["detail"])

    def test_cli_forbids_mutation_and_semantic(self) -> None:
        root = create_fixture(include_failures=False)
        prohibited, _ = run_cli(root, "ingest-raw", "--experiment", "x", "--source", str(root), expect=1)
        self.assertEqual(prohibited["error_semantic"], "UNSUPPORTED_OPERATION")
        semantic, _ = run_cli(root, "query", "--semantic", "--text", "x", expect=1)
        self.assertEqual(semantic["error_semantic"], "UNSUPPORTED_OPERATION")


if __name__ == "__main__":
    unittest.main()
