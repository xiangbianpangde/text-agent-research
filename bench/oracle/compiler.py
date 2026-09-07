"""Deterministic manifest + action compiler for compiled-gold/v1."""
from __future__ import annotations

import dataclasses
import re
from typing import Any, Dict, List, Mapping

from bench.dsl.loader import ScenarioActions

from .conditions import expected_condition
from .manifest import ManifestError, OracleManifest, digest_json
from .model import OracleState
from .time import at_or_before, parse_rfc3339


COMPILER_VERSION = "oracle-compiler/v1"


def _result_row(state: OracleState, obj: Mapping[str, Any], **overrides: Any) -> Dict[str, Any]:
    row = {
        "ref": obj["ref"],
        "entity_id": obj["entity_id"],
        "version_ref": obj.get("version_ref"),
        "path": obj.get("path"),
        "content_hash": obj.get("content_hash"),
        "git_commit": obj.get("git_commit"),
        "status": None,
        "is_stale": obj["ref"] in state.stale_refs,
        "relation_type": None,
        "section": None,
        "is_available": obj["ref"] not in state.missing_refs,
    }
    row.update(overrides)
    return row


def _entity_result(state: OracleState, target: str) -> List[Dict[str, Any]]:
    obj = state.object_for(target)
    return [] if obj is None else [_result_row(state, obj)]


def _binding_is_stale(state: OracleState, binding: Mapping[str, Any]) -> bool:
    resolved = [
        state.objects[edge["target_ref"]]
        for edge in state.relations
        if edge["source_ref"] == binding["ref"]
        and edge["relation"] == "resolves_to"
        and edge["target_ref"] in state.objects
    ]
    if not resolved and binding.get("path"):
        resolved = [
            obj for obj in state.objects.values()
            if obj["ref"] != binding["ref"]
            and obj["kind"] not in {"source_binding", "historical_source"}
            and obj.get("path") == binding.get("path")
        ]
    return bool(resolved) and any(
        binding.get("content_hash") != obj.get("content_hash") for obj in resolved
    )


def _facts(
    state: OracleState,
    subject: str,
    predicates: List[str] | None = None,
    as_of: str | None = None,
) -> List[Dict[str, Any]]:
    rows = state.facts_for(subject)
    if predicates:
        rows = [row for row in rows if row["predicate"] in predicates]
    if as_of is not None:
        rows = [row for row in rows if at_or_before(row["occurred_at"], as_of)]
    return [dict(row) for row in rows]


def _lineage(state: OracleState, target: str) -> List[str]:
    obj = state.object_for(target)
    if obj is None:
        return []
    candidates = {
        str(row["version_ref"]): row["ref"]
        for row in state.objects.values()
        if row["entity_id"] == obj["entity_id"] and row.get("version_ref")
    }
    previous = {}
    for version_ref, ref in candidates.items():
        values = state.facts_for(ref, "previous")
        previous[version_ref] = None if not values else str(values[0]["value"])
    roots = sorted(version for version, parent in previous.items() if parent is None or parent not in candidates)
    if len(roots) != 1:
        raise ManifestError(f"lineage must have exactly one root for {obj['entity_id']}")
    ordered = [roots[0]]
    while len(ordered) < len(candidates):
        children = sorted(version for version, parent in previous.items() if parent == ordered[-1])
        if len(children) != 1:
            raise ManifestError(f"lineage branch, gap, or cycle for {obj['entity_id']}")
        ordered.append(children[0])
    return ordered


def _semantic_results(state: OracleState, query: Mapping[str, Any]) -> List[Dict[str, Any]]:
    tokens = re.findall(r"[a-z0-9]+", str(query.get("text") or "").lower())
    predicates = set(query.get("predicates") or [])
    refs = set()
    for fact in state.facts:
        if predicates and fact["predicate"] not in predicates:
            continue
        value_tokens = set(re.findall(r"[a-z0-9]+", str(fact["value"]).lower()))
        if tokens and all(token in value_tokens for token in tokens):
            refs.add(str(fact["subject"]))
    results = []
    for ref in sorted(refs):
        results.extend(_entity_result(state, ref))
    return results


def _compile_invoke(
    state: OracleState,
    step: Mapping[str, Any],
    manifest: OracleManifest,
) -> Dict[str, Any]:
    operation = str(step["operation"])
    query = manifest.query(str(step["params"]["query_id"])) if "query_id" in step["params"] else None
    params: Dict[str, Any] = dict(query or step["params"])
    if step["action"] == "invoke_while_locked":
        params["lock_held"] = True
    if query is not None and query["operation"] != operation:
        raise ManifestError(f"query {query['query_id']} operation does not match action")

    condition = expected_condition(state, operation, params)
    checkpoint: Dict[str, Any] = {
        "capture_id": step["capture_id"],
        "step": step["step"],
        "query_id": None if query is None else query["query_id"],
        "expected_condition": condition,
        "oracle_state": state.snapshot(as_of=params.get("as_of")),
    }
    target = str(params.get("target_ref") or "")
    obj = state.object_for(target) if target else None
    locator = params.get("participant_locator")
    if obj is not None and locator is not None:
        aliases = {obj["ref"], obj["entity_id"], obj.get("version_ref"), obj.get("path")}
        if locator not in aliases:
            raise ManifestError(f"query {params.get('query_id')} locator does not identify compiled target")
    if query is not None and query["route_sequence"]:
        checkpoint["route_sequence"] = list(query["route_sequence"])
    if query is not None and query["ranking_authority"] is not None:
        checkpoint["ranking_authority"] = query["ranking_authority"]

    if operation == "query_entity":
        checkpoint["results"] = _entity_result(state, target)
        obj = state.object_for(target)
        checkpoint["version_bindings"] = [
            {"subject": fact["subject"], "value": fact["value"]}
            for fact in state.facts_for(obj["ref"] if obj else target, "bound_version")
        ]
    elif operation in ("query_facts", "query_lineage", "query_state"):
        obj = state.object_for(target)
        subject = obj["ref"] if obj else target
        checkpoint["asserted_facts"] = _facts(
            state,
            subject,
            list(params["predicates"]),
            params.get("as_of"),
        )
        if operation == "query_lineage":
            checkpoint["lineage"] = _lineage(state, target)
        if operation == "query_state":
            checkpoint["results"] = _entity_result(state, target)
            checkpoint["state_assertions"] = [{
                "ref": target,
                "is_stale": target in state.stale_refs,
            }]
    elif operation == "query_external_basis":
        obj = state.object_for(target)
        subject = obj["ref"] if obj else target
        checkpoint["asserted_facts"] = _facts(state, subject, ["pinned_external_value"])
        source_facts = state.facts_for(subject, "authority_source")
        checkpoint["evidence"] = [
            {
                "kind": "external_pin",
                "source_ref": fact["value"],
                "content_hash": state.external_sources[fact["value"]]["pinned_content_hash"],
            }
            for fact in source_facts if fact["value"] in state.external_sources
        ]
    elif operation in ("trace_evidence", "trace_graph"):
        graph = state.dependency_subgraph(target)
        graph_refs = {row["ref"] for row in graph["nodes"]}
        checkpoint["provenance_graph"] = graph
        checkpoint["evidence"] = [dict(atom) for atom in state.evidence_atoms if atom["artifact_ref"] in graph_refs]
    elif operation == "query_sources":
        obj = state.object_for(target)
        root = obj["ref"] if obj else target
        relation_types = set(params.get("relation_types") or [])
        source_edges = [
            row for row in state.relations
            if row["source_ref"] == root
            and row["target_ref"] in state.objects
            and (not relation_types or row["relation"] in relation_types)
        ]
        checkpoint["results"] = [
            _result_row(
                state,
                state.objects[row["target_ref"]],
                entity_id=obj["entity_id"] if obj else state.objects[row["target_ref"]]["entity_id"],
                version_ref=None,
                status=None,
                is_stale=_binding_is_stale(state, state.objects[row["target_ref"]]),
                relation_type="based_on",
            )
            for row in source_edges
        ]
        historical = [row for row in checkpoint["results"] if state.objects[row["ref"]]["kind"] == "historical_source"]
        if historical:
            checkpoint["historical_bindings"] = historical
    elif operation in ("query_history", "query_as_of_state"):
        predicates = list(params.get("predicates") or [])
        as_of = params.get("as_of")
        checkpoint["asserted_facts"] = [
            dict(row) for row in state.facts
            if (not predicates or row["predicate"] in predicates)
            and (as_of is None or at_or_before(row["occurred_at"], as_of))
        ]
        if operation == "query_history":
            visible_refs = {
                row["subject"] for row in state.facts
                if row["predicate"] == "as_of"
                and (as_of is None or at_or_before(row["occurred_at"], as_of))
            }
        else:
            visible_refs = state.visible_refs(as_of)
        checkpoint["results"] = [
            item for ref in sorted(visible_refs) for item in _entity_result(state, ref)
        ]
        if operation == "query_as_of_state":
            for item in checkpoint["results"]:
                item["git_commit"] = None
                item["status"] = None
        checkpoint["as_of"] = as_of
    elif operation == "query_project_current":
        checkpoint["results"] = _entity_result(state, target)
        checkpoint["asserted_facts"] = _facts(state, target, list(params["predicates"]))
    elif operation == "query_project_index":
        checkpoint["results"] = _entity_result(state, target)
    elif operation in ("query_text_semantic", "query_text_lexical"):
        checkpoint["results"] = _semantic_results(state, params)
    elif operation == "query_exact_routing":
        checkpoint["results"] = _entity_result(state, target)
    elif operation == "reconcile_integrity":
        issues = []
        if state.index_state == "stale":
            issues.append({"code": "DRIFT_DETECTED", "ref": ".index/research.sqlite"})
        issues.extend({"code": "SOURCE_MISSING", "ref": ref} for ref in sorted(state.missing_refs))
        issues.extend({"code": "HASH_MISMATCH", "ref": ref} for ref in sorted(state.hash_mismatch_refs))
        issues.extend({"code": "ORPHAN_ARTIFACT", "ref": ref} for ref in sorted(state.orphan_paths))
        issues.extend({"code": "CANONICAL_SEMANTIC_DRIFT", "ref": ref} for ref in sorted(state.semantic_tamper_refs))
        checkpoint["integrity_issues"] = issues
        checkpoint["results"] = []
    elif operation == "impact":
        checkpoint["impact_set"] = sorted(state.benchmark_dependents(target))
    elif operation == "stale_status":
        checkpoint["stale_set"] = sorted(state.stale_refs)
        checkpoint["provenance_graph"] = state.propagation_subgraph(target)
    elif operation == "tx_reconcile":
        checkpoint["results"] = []

    if condition["behavior"] == "fail_closed":
        # A refusal Gold must not also contain an answer which makes a correct
        # refusal fail or allows an answer-bearing refusal to pass.
        for key in (
            "results", "version_bindings", "asserted_facts", "lineage", "evidence",
            "provenance_graph", "impact_set", "stale_set", "state_assertions",
            "historical_bindings", "ranking_authority", "route_sequence",
        ):
            checkpoint.pop(key, None)
    return checkpoint


def compile_gold(manifest: OracleManifest, actions: ScenarioActions) -> Dict[str, Any]:
    """Compile Gold with no adapter, workspace, prediction, or SUT input."""
    if actions.document["initial_fixture"] != manifest.document["universe_id"]:
        raise ValueError("scenario initial_fixture does not match Oracle universe")
    state = OracleState.from_manifest(manifest)
    effective_clock = state.clock
    pre_state = state.summary()
    checkpoints: List[Dict[str, Any]] = []
    last_snapshot: str | None = None
    last_index_snapshot: str | None = None
    recovery_base: str | None = None

    for step in actions.steps:
        action = step["action"]
        if action in ("mutate", "advance_time", "context_reset", "restart_sut", "new_session", "external_crash"):
            if action == "external_crash":
                checkpoints.append({
                    "capture_id": step["capture_id"],
                    "step": step["step"],
                    "expected_observation": {"external_termination": True, "signal": "SIGKILL"},
                })
                recovery_base = last_snapshot
            state = state.apply(step)
            if action == "advance_time":
                effective_clock = str(step["new_timestamp"])
            if action == "new_session" and "capture_id" in step:
                checkpoints.append({
                    "capture_id": step["capture_id"],
                    "step": step["step"],
                    "expected_observation": {
                        "session_id": step["session_id"],
                        "process_restarted": True,
                    },
                })
        elif action in ("invoke", "invoke_while_locked"):
            if "capture_id" in step:
                query_id = step["params"].get("query_id")
                if query_id:
                    query = manifest.query(query_id)
                    if query.get("as_of") is not None and parse_rfc3339(query["as_of"]) != parse_rfc3339(effective_clock):
                        raise ManifestError(
                            f"query {query_id} cutoff does not match effective virtual clock"
                        )
                checkpoints.append(_compile_invoke(state, step, manifest))
            if step["operation"] == "index":
                state = dataclasses.replace(state, index_state="present")
        elif action == "snapshot_index":
            expected: Dict[str, Any] = {"index_present": state.index_state != "missing"}
            if last_index_snapshot:
                expected["equals_capture"] = last_index_snapshot
            checkpoints.append({
                "capture_id": step["capture_id"],
                "step": step["step"],
                "expected_observation": expected,
            })
            if last_index_snapshot is None:
                last_index_snapshot = step["capture_id"]
        elif action == "snapshot_state":
            expected = {"state_profile": "canonical"}
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
