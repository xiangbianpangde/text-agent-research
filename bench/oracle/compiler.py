"""Deterministic manifest + action compiler for compiled-gold/v1."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

from bench.dsl.loader import ScenarioActions

from .conditions import expected_condition
from .manifest import OracleManifest, digest_json
from .model import OracleState


COMPILER_VERSION = "oracle-compiler/v1"


def _entity_result(state: OracleState, target: str) -> List[Dict[str, Any]]:
    obj = state.object_for(target)
    if obj is None:
        return []
    return [{
        "ref": obj["ref"],
        "entity_id": obj["entity_id"],
        "version_ref": obj.get("version_ref"),
        "path": obj.get("path"),
        "status": obj.get("status"),
    }]


def _compile_invoke(state: OracleState, step: Mapping[str, Any]) -> Dict[str, Any]:
    operation = step["operation"]
    params = step["params"]
    checkpoint: Dict[str, Any] = {
        "capture_id": step["capture_id"],
        "step": step["step"],
        "expected_condition": expected_condition(state, operation, params),
    }
    target = str(params.get("ref") or params.get("entity_ref") or params.get("definition_ref") or params.get("entity") or "")

    if operation == "query_entity":
        checkpoint["results"] = _entity_result(state, target)
        obj = state.object_for(target)
        checkpoint["version_bindings"] = [
            {"subject": fact["subject"], "value": fact["value"]}
            for fact in state.facts_for(obj["ref"] if obj else target, "bound_version")
        ]
    elif operation == "query_external_basis":
        obj = state.object_for(target)
        subject = obj["ref"] if obj else target
        checkpoint["asserted_facts"] = [dict(row) for row in state.facts_for(subject, "pinned_external_value")]
        source_facts = state.facts_for(subject, "authority_source")
        checkpoint["evidence"] = [
            {
                "kind": "external_pin",
                "source_ref": fact["value"],
                "content_hash": state.external_sources[fact["value"]]["pinned_content_hash"],
            }
            for fact in source_facts if fact["value"] in state.external_sources
        ]
    elif operation == "trace_evidence":
        graph = state.dependency_subgraph(target)
        graph_refs = {row["ref"] for row in graph["nodes"]}
        checkpoint["provenance_graph"] = graph
        checkpoint["evidence"] = [dict(atom) for atom in state.evidence_atoms if atom["artifact_ref"] in graph_refs]
    elif operation == "impact":
        checkpoint["impact_set"] = sorted(state.reverse_closure(target) - {target})
    elif operation == "stale_status":
        checkpoint["stale_set"] = sorted(state.stale_refs)
        checkpoint["provenance_graph"] = state.dependency_subgraph(target)
    elif operation == "tx_reconcile":
        checkpoint["results"] = []
    return checkpoint


def compile_gold(manifest: OracleManifest, actions: ScenarioActions) -> Dict[str, Any]:
    """Compile Gold with no adapter, workspace, prediction, or SUT input."""
    if actions.document["initial_fixture"] != manifest.document["universe_id"]:
        raise ValueError("scenario initial_fixture does not match Oracle universe")
    state = OracleState.from_manifest(manifest)
    pre_state = state.summary()
    checkpoints: List[Dict[str, Any]] = []
    last_snapshot: str | None = None
    recovery_base: str | None = None

    for step in actions.steps:
        action = step["action"]
        if action in ("mutate", "external_crash"):
            if action == "external_crash":
                checkpoints.append({
                    "capture_id": step["capture_id"],
                    "step": step["step"],
                    "expected_observation": {"external_termination": True, "signal": "SIGKILL"},
                })
                recovery_base = last_snapshot
            state = state.apply(step)
        elif action == "invoke" and "capture_id" in step:
            checkpoints.append(_compile_invoke(state, step))
        elif action == "snapshot_state":
            expected: Dict[str, Any] = {"state_profile": "canonical"}
            if state.transaction_stage == "after-staging" and recovery_base:
                expected["equals_capture"] = recovery_base
            elif step.get("require_no_tx_residue") and recovery_base:
                expected["equals_capture"] = recovery_base
            if step.get("require_no_tx_residue"):
                expected["tx_residue_empty"] = True
            checkpoints.append({
                "capture_id": step["capture_id"],
                "step": step["step"],
                "expected_observation": expected,
            })
            last_snapshot = step["capture_id"]
            if step.get("require_no_tx_residue"):
                recovery_base = step["capture_id"]

    gold: Dict[str, Any] = {
        "schema_version": "compiled-gold/v1",
        "scenario_id": actions.scenario_id,
        "compiler_version": COMPILER_VERSION,
        "manifest_digest": manifest.digest,
        "action_digest": actions.digest,
        "pre_state": pre_state,
        "checkpoints": checkpoints,
        "post_state": state.summary(),
    }
    gold["gold_digest"] = digest_json(gold)
    return gold
