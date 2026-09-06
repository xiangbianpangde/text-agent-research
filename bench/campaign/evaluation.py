"""P1B evaluation engine: same-runner multi-repetition instance execution.

- prediction/v2 validation (v1 closed set + nullable result.ref, §19.3.3)
- deterministic run-seed schedule per (instance, repetition) via §19.9 KDF
- every repetition materializes a FRESH workspace (no warm cache, §14)
- missingness (§12.6): timeout/crash/protocol failure records a failed
  repetition; nothing is dropped or retried
- scoring reuses the sealed-Gold evaluator (bench/evaluators/scenario)
- zero participant-identity branches: participants differ only by adapter
  command + artifact binding (§9.2, B01/B03)
"""
from __future__ import annotations

import dataclasses
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from bench.adapters.process import ProcessSUTAdapter
from bench.dsl.executor import execute_actions
from bench.generator.kdf import derive_instance_key, derive_run_seed, build_instance_message
from bench.generator.identity import GENERATOR_VERSION, RELEASE_ID
from bench.generator.scenario import validate_scenario_v2
from bench.oracle.compiler import compile_gold
from bench.oracle.manifest import OracleManifest, validate_manifest


REPETITION_COUNT = 5
REPEITIONS = range(REPETITION_COUNT)


# --- prediction/v2 validation (deterministic delta over P0 v1 rules) ---------

def validate_prediction_v2(value: Any, *, capture_id: Optional[str] = None) -> Dict[str, Any]:
    from bench.dsl.loader import (
        PREDICTION_KEYS,
        PREDICTION_STATUSES,
        RESULT_KEYS,
        REQUIRED_RESULT_KEYS,
        ScenarioContractError,
        _assert_no_evaluation_fields,
        _strict_keys,
        _string,
    )

    _assert_no_evaluation_fields(value, "prediction")
    prediction = _strict_keys(value, PREDICTION_KEYS, PREDICTION_KEYS, "prediction")
    if prediction["schema_version"] != "prediction/v2":
        raise ScenarioContractError("unsupported prediction schema_version")
    _string(prediction["capture_id"], "prediction.capture_id", empty=True)
    if capture_id is not None and prediction["capture_id"] != capture_id:
        raise ScenarioContractError("prediction capture_id mismatch")
    if prediction["status"] not in PREDICTION_STATUSES:
        raise ScenarioContractError("unsupported prediction status")
    if prediction["error_semantic"] is not None and not isinstance(prediction["error_semantic"], str):
        raise ScenarioContractError("prediction.error_semantic must be string or null")
    for f in ("warnings", "errors", "asserted_facts", "evidence", "route_sequence"):
        if not isinstance(prediction[f], list):
            raise ScenarioContractError(f"prediction.{f} must be an array")
    if prediction["results"] is not None and not isinstance(prediction["results"], list):
        raise ScenarioContractError("prediction.results must be an array or null")
    for index, row in enumerate(prediction["results"] or []):
        result = _strict_keys(row, RESULT_KEYS, REQUIRED_RESULT_KEYS, f"prediction.results[{index}]")
        # v2 delta: ref may be a string OR null OR omitted (v1: string only)
        if "ref" in result and result["ref"] is not None and not isinstance(result["ref"], str):
            raise ScenarioContractError(f"prediction.results[{index}].ref must be string or null")
        for f in ("entity_id", "version_ref", "path", "content_hash", "git_commit", "status", "relation_type", "section"):
            if result[f] is not None and not isinstance(result[f], str):
                raise ScenarioContractError(f"prediction.results[{index}].{f} must be string or null")
        for f in ("is_stale", "is_available"):
            if not isinstance(result[f], bool):
                raise ScenarioContractError(f"prediction.results[{index}].{f} must be boolean")
    if prediction["provenance_graph"] is not None and not isinstance(prediction["provenance_graph"], dict):
        raise ScenarioContractError("prediction.provenance_graph must be object or null")
    for f in ("retrieval_mode", "ranking_authority", "as_of"):
        if prediction[f] is not None and not isinstance(prediction[f], str):
            raise ScenarioContractError(f"prediction.{f} must be string or null")
    return dict(prediction)


# --- instance material -------------------------------------------------------

@dataclass
class InstanceMaterial:
    family_id: str
    split: str
    ordinal: int
    manifest: OracleManifest
    actions: Dict[str, Any]
    gold: Dict[str, Any]
    fixture_files: Dict[str, Tuple[int, bytes]]
    split_secret: bytes

    @property
    def k_instance(self) -> bytes:
        message = build_instance_message(
            release_id=RELEASE_ID,
            generator_version=GENERATOR_VERSION,
            family_id=self.family_id,
            family_version="1.0.0",
            split=self.split,
            ordinal=self.ordinal,
            attempt=0,
        )
        return derive_instance_key(self.split_secret, message)

    def run_seed(self, repetition: int) -> str:
        return derive_run_seed(self.k_instance, repetition)

    def run_seed_schedule(self) -> List[str]:
        return [self.run_seed(r) for r in REPEITIONS]


@dataclass
class RepetitionOutcome:
    repetition: int
    run_seed: str
    failed: bool
    failure_reasons: List[str] = field(default_factory=list)
    evaluation: Optional[Any] = None
    prediction_count: int = 0
    observation_count: int = 0


def materialize_workspace(
    fixture_files: Mapping[str, Tuple[int, bytes]], workspace: Path
) -> None:
    """Write a fresh participant-visible workspace from the fixture file map."""
    if workspace.exists():
        raise FileExistsError(f"workspace already exists: {workspace}")
    for rel, (mode, data) in sorted(fixture_files.items()):
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if mode == 0o755:
            target.chmod(0o755)


def execute_repetition(
    *,
    material: InstanceMaterial,
    adapter_command: Sequence[str],
    adapter_cwd: str,
    repetition: int,
    workspaces_root: Path,
    denied_read_paths: Optional[Sequence[str]] = None,
    adapter_factory: Optional[Any] = None,
) -> RepetitionOutcome:
    """Run one repetition: fresh workspace → prepare → v2 stream → score."""
    seed = material.run_seed(repetition)
    outcome = RepetitionOutcome(repetition=repetition, run_seed=seed, failed=False)

    raw_actions = material.actions
    if hasattr(raw_actions, "document"):
        raw_actions = raw_actions.document
    actions = validate_scenario_v2(raw_actions)
    workspace = workspaces_root / f"rep{repetition}"
    materialize_workspace(material.fixture_files, workspace)
    adapter = None
    try:
        if adapter_factory is not None:
            adapter = adapter_factory()
        else:
            adapter = ProcessSUTAdapter(
                list(adapter_command),
                cwd=adapter_cwd,
                denied_read_paths=denied_read_paths,
            )
        adapter.prepare(str(workspace))
        record = execute_actions(actions, material.manifest, adapter, str(workspace), run_seed=seed)
        outcome.prediction_count = len(record.predictions)
        outcome.observation_count = len(record.observations)

        # §12.6 missingness: any recorded error is a failed repetition (kept).
        if record.errors:
            outcome.failed = True
            outcome.failure_reasons.extend(record.errors)

        # validate captured predictions as prediction/v2
        for cid, pred in list(record.predictions.items()):
            try:
                if pred.get("schema_version") == "prediction/v2":
                    record.predictions[cid] = validate_prediction_v2(pred, capture_id=cid)
            except Exception as exc:
                outcome.failed = True
                outcome.failure_reasons.append(f"{cid}: invalid prediction/v2: {exc}")

        from bench.evaluators.scenario import evaluate_scenario

        outcome.evaluation = evaluate_scenario(
            gold=material.gold,
            execution=record,
            manifest=material.manifest,
        )
    except Exception as exc:
        outcome.failed = True
        outcome.failure_reasons.append(f"{type(exc).__name__}: {exc}")
    finally:
        if adapter is not None:
            try:
                adapter.shutdown()
            except Exception:
                pass
        shutil.rmtree(workspace, ignore_errors=True)
    return outcome


def run_instance(
    *,
    material: InstanceMaterial,
    adapter_command: Sequence[str],
    adapter_cwd: str,
    workspaces_root: Path,
    repetitions: int = REPETITION_COUNT,
    denied_read_paths: Optional[Sequence[str]] = None,
    adapter_factory: Optional[Any] = None,
) -> List[RepetitionOutcome]:
    """Run every repetition of one instance with the same generic runner."""
    outcomes: List[RepetitionOutcome] = []
    for repetition in range(repetitions):
        outcomes.append(
            execute_repetition(
                material=material,
                adapter_command=adapter_command,
                adapter_cwd=adapter_cwd,
                repetition=repetition,
                workspaces_root=workspaces_root,
                denied_read_paths=denied_read_paths,
                adapter_factory=adapter_factory,
            )
        )
    return outcomes
