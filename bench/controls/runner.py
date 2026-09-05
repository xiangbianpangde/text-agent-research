"""Run all P0.4 negative controls through the production Oracle-only path."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from bench.dsl.loader import load_scenario
from bench.evaluator import evaluate_oracle_benchmark
from bench.oracle.manifest import canonical_json_bytes, load_manifest
from bench.adapters import default_researchctl_command
from bench.adapters.protocol import command_digest
from bench.runner import DEFAULT_ORACLE_PACK, ORACLE_SCENARIO_IDS, REQUIRED_SCENARIO_IDS, run_oracle_scenario
from bench.scenarios import TRACKS

from . import CONTROL_MODES


ATTESTATION_SCHEMA = "negative-control-attestation/v1"


def _tree_digest(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _action_digest(pack_root: str) -> str:
    root = Path(pack_root)
    return _tree_digest([root / "pack.json", *(root / "scenarios").glob("*.json")])


def _harness_digest() -> str:
    bench_root = Path(__file__).resolve().parents[1]
    paths = [
        bench_root / "controls" / "control_sut.py",
        bench_root / "controls" / "runner.py",
        bench_root / "cli.py",
        bench_root / "adapters" / "process.py",
        bench_root / "dsl" / "executor.py",
        bench_root / "evaluator.py",
        bench_root / "evaluators" / "scenario.py",
        bench_root / "evaluators" / "integrity.py",
        bench_root / "oracle" / "compiler.py",
        bench_root / "oracle" / "model.py",
    ]
    return _tree_digest(paths)


def _scenario_metadata(pack_root: str) -> Dict[str, Dict[str, str]]:
    return {
        scenario_id: {
            "track": actions.document["track"],
            "name": actions.document["name"],
        }
        for scenario_id in ORACLE_SCENARIO_IDS
        for actions in [load_scenario(Path(pack_root) / "scenarios" / f"{scenario_id}.json")]
    }


def _evaluation_digest(evaluations: Iterable[Any]) -> str:
    payload = [evaluation.to_dict() for evaluation in evaluations]
    return "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def run_control(mode: str, *, pack_root: str = DEFAULT_ORACLE_PACK) -> Dict[str, Any]:
    if mode not in CONTROL_MODES:
        raise ValueError(f"unsupported control mode: {mode}")
    command = [sys.executable, "-m", "bench.controls.control_sut"]
    env = {"BENCH_CONTROL_MODE": mode}
    denied = []
    if mode == "gold-reader":
        probe = os.path.realpath(os.path.join(pack_root, "oracle-manifest.json"))
        env["BENCH_GOLD_PROBE"] = probe
        denied = [os.path.realpath(pack_root)]

    evaluations = []
    metadata: Dict[str, Any] = {}
    for scenario_id in ORACLE_SCENARIO_IDS:
        evaluation, scenario_metadata, _gold = run_oracle_scenario(
            scenario_id,
            sut_command=command,
            sut_cwd=str(Path(__file__).resolve().parents[2]),
            pack_root=pack_root,
            sut_env=env,
            denied_read_paths=denied,
        )
        evaluations.append(evaluation)
        if not metadata:
            metadata = scenario_metadata

    metrics = evaluate_oracle_benchmark(
        evaluations,
        evaluation_mode="full",
        scenario_metadata=_scenario_metadata(pack_root),
        required_tracks=TRACKS,
        required_scenario_ids=REQUIRED_SCENARIO_IDS,
        p0_4_complete=True,
    )
    passed_conclusion = bool(
        metrics.certification_eligible
        or metrics.tier != "N/A"
        or metrics.passed_scenarios == metrics.total_scenarios
        or metrics.iqg_passed
    )
    return {
        "mode": mode,
        "adapter": metadata.get("adapter"),
        "total_scenarios": metrics.total_scenarios,
        "passed_scenarios": metrics.passed_scenarios,
        "composite_score": metrics.composite_score,
        "civ": metrics.civ,
        "integrity_gate_passed": metrics.integrity_gate_passed,
        "iqg_passed": metrics.iqg_passed,
        "certification_eligible": metrics.certification_eligible,
        "tier": metrics.tier,
        "ineligible_reasons": metrics.ineligible_reasons,
        "passed_conclusion": passed_conclusion,
        "gold_read_blocked": metadata.get("gold_read_blocked"),
        "evaluation_digest": _evaluation_digest(evaluations),
    }


def run_official(*, pack_root: str = DEFAULT_ORACLE_PACK) -> Dict[str, Any]:
    evaluations = []
    metadata: Dict[str, Any] = {}
    for scenario_id in ORACLE_SCENARIO_IDS:
        evaluation, scenario_metadata, _gold = run_oracle_scenario(
            scenario_id,
            sut_command=default_researchctl_command(),
            sut_cwd=str(Path(__file__).resolve().parents[2]),
            pack_root=pack_root,
        )
        evaluations.append(evaluation)
        if not metadata:
            metadata = scenario_metadata
    return {
        "command_digest": command_digest(default_researchctl_command()),
        "adapter": metadata.get("adapter"),
        "evaluation_digest": _evaluation_digest(evaluations),
    }


def build_attestation(*, pack_root: str = DEFAULT_ORACLE_PACK) -> Dict[str, Any]:
    manifest = load_manifest(Path(pack_root) / "oracle-manifest.json")
    controls = [run_control(mode, pack_root=pack_root) for mode in CONTROL_MODES]
    random_retry = run_control("random", pack_root=pack_root)
    random_first = next(item for item in controls if item["mode"] == "random")
    random_deterministic = random_first["evaluation_digest"] == random_retry["evaluation_digest"]
    all_rejected = all(not item["passed_conclusion"] for item in controls)
    gold_reader = next(item for item in controls if item["mode"] == "gold-reader")
    official_first = run_official(pack_root=pack_root)
    official_second = run_official(pack_root=pack_root)
    official_deterministic = official_first == official_second
    payload: Dict[str, Any] = {
        "schema_version": ATTESTATION_SCHEMA,
        "pack_id": manifest.document["universe_id"],
        "manifest_digest": manifest.digest,
        "source_hash": manifest.document["fixture"]["source_hash"],
        "fixture_hash": manifest.document["fixture"]["content_hash"],
        "action_digest": _action_digest(pack_root),
        "harness_digest": _harness_digest(),
        "controls": controls,
        "random_retry_digest": random_retry["evaluation_digest"],
        "random_deterministic": random_deterministic,
        "gold_reader_blocked": gold_reader["gold_read_blocked"] is True,
        "all_controls_rejected": all_rejected,
        "official_run": official_first,
        "official_retry_digest": official_second["evaluation_digest"],
        "official_deterministic": official_deterministic,
    }
    payload["p0_4_passed"] = bool(
        all_rejected and random_deterministic and payload["gold_reader_blocked"] and official_deterministic
    )
    payload["attestation_digest"] = "sha256:" + hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return payload


def validate_attestation(value: Mapping[str, Any], *, pack_root: str = DEFAULT_ORACLE_PACK) -> bool:
    manifest = load_manifest(Path(pack_root) / "oracle-manifest.json")
    if value.get("schema_version") != ATTESTATION_SCHEMA:
        return False
    if value.get("manifest_digest") != manifest.digest:
        return False
    if value.get("source_hash") != manifest.document["fixture"]["source_hash"]:
        return False
    if value.get("fixture_hash") != manifest.document["fixture"]["content_hash"]:
        return False
    if value.get("action_digest") != _action_digest(pack_root):
        return False
    if value.get("harness_digest") != _harness_digest():
        return False
    controls = value.get("controls")
    if not isinstance(controls, list) or [item.get("mode") for item in controls] != list(CONTROL_MODES):
        return False
    if any(item.get("passed_conclusion") is not False for item in controls):
        return False
    if value.get("random_deterministic") is not True or value.get("gold_reader_blocked") is not True:
        return False
    if value.get("official_deterministic") is not True:
        return False
    official = value.get("official_run")
    if not isinstance(official, dict) or official.get("command_digest") != command_digest(default_researchctl_command()):
        return False
    if value.get("official_retry_digest") != official.get("evaluation_digest"):
        return False
    digest_payload = dict(value)
    claimed = digest_payload.pop("attestation_digest", None)
    actual = "sha256:" + hashlib.sha256(canonical_json_bytes(digest_payload)).hexdigest()
    return claimed == actual and value.get("p0_4_passed") is True


if __name__ == "__main__":
    print(json.dumps(build_attestation(), ensure_ascii=False, indent=2))
