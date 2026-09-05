"""Execute scenario actions through one SUT adapter and capture claims/observations only."""
from __future__ import annotations

import dataclasses
import hashlib
import os
import shutil
import signal
import time
from pathlib import Path
from typing import Any, Dict, Mapping

from bench.adapters import ProcessSUTAdapter
from bench.oracle.manifest import OracleManifest

from .command_codec import encode_operation
from .loader import ScenarioActions, ScenarioContractError, validate_prediction
from .mutations import apply_physical_mutation
from bench.evaluators.state import snapshot_paths, tx_residue_empty


@dataclasses.dataclass
class ExecutionRecord:
    scenario_id: str
    predictions: Dict[str, Mapping[str, Any]] = dataclasses.field(default_factory=dict)
    observations: Dict[str, Mapping[str, Any]] = dataclasses.field(default_factory=dict)
    errors: list[str] = dataclasses.field(default_factory=list)


def materialize_overlay(
    pack_root: str | Path,
    workspace: str,
    manifest: OracleManifest,
    actions: ScenarioActions,
) -> None:
    """Copy only physical objects reachable from refs named by the action DSL."""
    overlay = Path(pack_root) / "seed"
    if not overlay.exists():
        return
    objects = {
        row["ref"]: row for row in (*manifest.document["entities"], *manifest.document["artifacts"])
    }
    selected = set()
    for step in actions.steps:
        values = [step.get("target")]
        params = step.get("params", {})
        if isinstance(params, dict):
            values.extend(params.get(key) for key in ("ref", "definition_ref", "entity_ref"))
        selected.update(value for value in values if isinstance(value, str) and value in objects)
    changed = True
    while changed:
        changed = False
        for edge in manifest.document["relations"]:
            if edge["source_ref"] in selected and edge["target_ref"] not in selected:
                selected.add(edge["target_ref"])
                changed = True
    for ref in sorted(selected):
        relative = objects[ref].get("path")
        if not relative:
            continue
        source = overlay / relative
        if not source.exists():
            continue
        destination = Path(workspace) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)
            expected_hash = objects[ref].get("content_hash")
            if expected_hash:
                actual_hash = "sha256:" + hashlib.sha256(destination.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    raise ScenarioContractError(
                        f"seed materialization hash mismatch for {ref}: {actual_hash} != {expected_hash}"
                    )


def _snapshot_profile(manifest: OracleManifest) -> list[str]:
    for row in manifest.document["snapshots"]:
        if row["snapshot_id"] == "canonical":
            return list(row["paths"])
    raise ScenarioContractError("oracle manifest lacks canonical snapshot profile")


def _wait_for_file(path: Path, timeout_ms: int) -> bool:
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        if path.is_file():
            return True
        time.sleep(0.01)
    return False


def execute_actions(
    actions: ScenarioActions,
    manifest: OracleManifest,
    adapter: ProcessSUTAdapter,
    workspace: str,
) -> ExecutionRecord:
    """Execute without reading compiled Gold or deriving any expected answer."""
    record = ExecutionRecord(scenario_id=actions.scenario_id)
    snapshot_profile = _snapshot_profile(manifest)

    for step in actions.steps:
        action = step["action"]
        try:
            if action == "mutate":
                apply_physical_mutation(workspace, manifest, step)
                continue
            if action == "snapshot_state":
                observation = snapshot_paths(workspace, snapshot_profile)
                observation["tx_residue_empty"] = tx_residue_empty(workspace)
                record.observations[step["capture_id"]] = observation
                continue
            arguments = encode_operation(step["operation"], step["params"])
            timeout_ms = int(step.get("timeout_ms", 30_000))
            if action == "external_crash":
                barrier_rel = f".bench-control/{step['capture_id']}.json"
                barrier = Path(workspace) / barrier_rel
                adapter.begin_invoke(
                    arguments,
                    capture_id=step["capture_id"],
                    timeout_ms=timeout_ms,
                    test_control={"pause_at": step["pause_at"], "barrier_path": barrier_rel},
                )
                reached = _wait_for_file(barrier, timeout_ms)
                if not reached:
                    adapter.hard_kill_process_group()
                    record.errors.append(f"{step['capture_id']}: stage barrier timed out")
                    adapter.recover_after_hard_kill()
                    continue
                returncode = adapter.hard_kill_process_group()
                record.observations[step["capture_id"]] = {
                    "external_termination": returncode == -signal.SIGKILL if os.name == "posix" else returncode != 0,
                    "signal": "SIGKILL",
                    "returncode": returncode,
                    "barrier_reached": True,
                }
                adapter.recover_after_hard_kill()
                continue

            result = adapter.invoke(arguments, capture_id=step.get("capture_id", ""), timeout_ms=timeout_ms)
            if "capture_id" not in step:
                continue
            if not isinstance(result.payload, dict):
                record.errors.append(f"{step['capture_id']}: participant returned no prediction/v1 payload")
                continue
            record.predictions[step["capture_id"]] = validate_prediction(
                result.payload,
                capture_id=step["capture_id"],
            )
        except Exception as exc:
            record.errors.append(f"step {step['step']} {action}: {type(exc).__name__}: {exc}")
    return record
