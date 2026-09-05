"""Generic compiled-Gold versus prediction evaluator."""
from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

from bench.dsl.executor import ExecutionRecord
from bench.dsl.loader import ScenarioContractError, validate_prediction
from bench.oracle.manifest import OracleManifest

from .graph import graph_exact_match
from .integrity import classify_civ, resolve_object
from .sets import set_confusion


RESULT_FIELDS = (
    "entity_id", "version_ref", "path", "content_hash", "git_commit", "status",
    "is_stale", "relation_type", "section", "is_available",
)
KNOWN_RESULT_FIELDS = frozenset({"ref", *RESULT_FIELDS})


def _canonical_rows(values: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(sorted(json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in values))


def _object_ref(
    row: Mapping[str, Any],
    manifest: OracleManifest,
    *,
    state_snapshot: Mapping[str, Any] | None = None,
) -> Optional[str]:
    if "ref" in row:
        if not isinstance(row["ref"], str):
            return None
        objects = state_snapshot.get("objects", {}) if state_snapshot else {}
        return str(row["ref"]) if not objects or row["ref"] in objects else None
    obj = resolve_object(row, manifest, state_snapshot=state_snapshot)
    return None if obj is None else str(obj["ref"])


def _predicted_refs(
    prediction: Mapping[str, Any],
    manifest: OracleManifest,
    *,
    stale_only: bool = False,
    state_snapshot: Mapping[str, Any] | None = None,
) -> Set[str]:
    refs = set()
    unresolved = 0
    for row in prediction.get("results") or []:
        if not isinstance(row, dict):
            unresolved += 1
            continue
        if stale_only and row.get("is_stale") is not True:
            continue
        ref = _object_ref(row, manifest, state_snapshot=state_snapshot)
        if ref:
            refs.add(ref)
        else:
            unresolved += 1
    refs.update(f"__unresolved_result_{index}" for index in range(unresolved))
    return refs


def _result_exact(
    predicted: Any,
    gold_rows: Iterable[Mapping[str, Any]],
    manifest: OracleManifest,
    *,
    state_snapshot: Mapping[str, Any] | None = None,
) -> bool:
    predicted_rows = predicted.get("results") or []
    if not isinstance(predicted_rows, list):
        return False
    expected_by_ref = {
        str(row["ref"]): {"ref": str(row["ref"]), **{field: row.get(field) for field in RESULT_FIELDS}}
        for row in gold_rows
    }
    actual_by_ref: Dict[str, Mapping[str, Any]] = {}
    for row in predicted_rows:
        if not isinstance(row, dict) or set(row) - KNOWN_RESULT_FIELDS:
            return False
        if any(field not in row for field in RESULT_FIELDS):
            return False
        ref = _object_ref(row, manifest, state_snapshot=state_snapshot)
        if ref is None or ref in actual_by_ref:
            return False
        actual_by_ref[ref] = {"ref": ref, **{field: row.get(field) for field in RESULT_FIELDS}}
    return actual_by_ref == expected_by_ref


@dataclasses.dataclass
class OracleScenarioEvaluation:
    scenario_id: str
    passed: bool
    score: float
    checks: List[Dict[str, Any]]
    civ_count: int
    civ_violations: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    impact_tp: int = 0
    impact_fp: int = 0
    impact_fn: int = 0
    stale_tp: int = 0
    stale_fp: int = 0
    stale_fn: int = 0
    version_correct: Optional[bool] = None
    graph_exact_match: Optional[bool] = None
    fail_closed_expected: bool = False
    fail_closed_satisfied: bool = False
    gold_digest: str = ""
    execution_errors: List[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def evaluate_scenario(
    gold: Mapping[str, Any],
    execution: ExecutionRecord,
    manifest: OracleManifest,
) -> OracleScenarioEvaluation:
    """Compute every score/metric from sealed Gold and captured execution."""
    checks: List[Dict[str, Any]] = []
    civ_violations: List[Dict[str, Any]] = []
    impact_totals = {"tp": 0, "fp": 0, "fn": 0}
    stale_totals = {"tp": 0, "fp": 0, "fn": 0}
    version_checks: List[bool] = []
    graph_checks: List[bool] = []
    fail_expected = False
    fail_checks: List[bool] = []

    def add(kind: str, passed: bool, **detail: Any) -> None:
        checks.append({"kind": kind, "passed": bool(passed), **detail})

    for checkpoint in gold["checkpoints"]:
        capture_id = checkpoint["capture_id"]
        expected_observation = checkpoint.get("expected_observation")
        if expected_observation is not None:
            observed = execution.observations.get(capture_id)
            add("observation_present", observed is not None, capture_id=capture_id)
            if observed is None:
                continue
            for key in (
                "external_termination", "signal", "tx_residue_empty", "index_present",
                "session_id", "process_restarted",
            ):
                if key in expected_observation:
                    add(key, observed.get(key) == expected_observation[key], capture_id=capture_id)
            equal_to = expected_observation.get("equals_capture")
            if equal_to:
                baseline = execution.observations.get(equal_to)
                if "cle_digest" in observed:
                    exact = baseline is not None and observed.get("cle_digest") == baseline.get("cle_digest")
                    add("canonical_index_exact", exact, capture_id=capture_id, equals_capture=equal_to)
                else:
                    exact = baseline is not None and observed.get("canonical_digest") == baseline.get("canonical_digest")
                    add("canonical_state_exact", exact, capture_id=capture_id, equals_capture=equal_to)
            continue

        prediction = execution.predictions.get(capture_id)
        add("prediction_present", prediction is not None, capture_id=capture_id)
        if prediction is None:
            continue
        try:
            prediction = validate_prediction(prediction, capture_id=capture_id)
        except ScenarioContractError as exc:
            add("prediction_contract", False, capture_id=capture_id, error=str(exc))
            continue
        condition = checkpoint["expected_condition"]
        condition_ok = prediction["status"] == condition["status"] and prediction["error_semantic"] == condition["error_semantic"]
        if condition["behavior"] == "fail_closed":
            fail_expected = True
            condition_ok = condition_ok and not (prediction.get("results") or [])
            if prediction.get("asserted_facts") or prediction.get("evidence") or prediction.get("provenance_graph"):
                condition_ok = False
            fail_checks.append(condition_ok)
        add("expected_condition", condition_ok, capture_id=capture_id)

        if "results" in checkpoint:
            state_snapshot = checkpoint.get("oracle_state")
            exact = _result_exact(
                prediction,
                checkpoint["results"],
                manifest,
                state_snapshot=state_snapshot,
            )
            pred_refs = _predicted_refs(
                prediction,
                manifest,
                state_snapshot=state_snapshot,
            )
            gold_refs = {row["ref"] for row in checkpoint["results"]}
            confusion = set_confusion(pred_refs, gold_refs)
            add("result_set_exact", exact, capture_id=capture_id, **confusion)

        if "version_bindings" in checkpoint:
            expected = {(row["subject"], str(row["value"])) for row in checkpoint["version_bindings"]}
            actual = {
                (str(row.get("subject")), str(row.get("value")))
                for row in prediction.get("asserted_facts") or []
                if isinstance(row, dict) and row.get("predicate") == "bound_version"
            }
            correct = actual == expected
            version_checks.append(correct)
            add("version_binding_exact", correct, capture_id=capture_id)

        if "asserted_facts" in checkpoint:
            exact = _canonical_rows(prediction.get("asserted_facts") or []) == _canonical_rows(checkpoint["asserted_facts"])
            add("asserted_facts_exact", exact, capture_id=capture_id)

        if "lineage" in checkpoint:
            actual = sorted(
                str(row.get("version_ref"))
                for row in prediction.get("results") or []
                if isinstance(row, dict) and row.get("version_ref")
            )
            add("lineage_exact", actual == checkpoint["lineage"], capture_id=capture_id)

        if "evidence" in checkpoint:
            exact = _canonical_rows(prediction.get("evidence") or []) == _canonical_rows(checkpoint["evidence"])
            add("evidence_exact", exact, capture_id=capture_id)

        if "provenance_graph" in checkpoint:
            exact = graph_exact_match(prediction.get("provenance_graph"), checkpoint["provenance_graph"])
            graph_checks.append(exact)
            add("provenance_graph_exact", exact, capture_id=capture_id)

        if "route_sequence" in checkpoint:
            add("routing_policy", prediction.get("route_sequence") == checkpoint["route_sequence"], capture_id=capture_id)
        if "ranking_authority" in checkpoint and condition["behavior"] != "fail_closed":
            add("ranking_authority", prediction.get("ranking_authority") == checkpoint["ranking_authority"], capture_id=capture_id)

        if "integrity_issues" in checkpoint:
            actual_issues = []
            for row in [*(prediction.get("warnings") or []), *(prediction.get("errors") or [])]:
                if isinstance(row, dict) and isinstance(row.get("code"), str):
                    actual_issues.append({"code": row["code"], "ref": row.get("ref")})
            add("integrity_issues_exact", _canonical_rows(actual_issues) == _canonical_rows(checkpoint["integrity_issues"]), capture_id=capture_id)

        if "historical_bindings" in checkpoint:
            actual = []
            for row in prediction.get("results") or []:
                if isinstance(row, dict):
                    obj = resolve_object(row, manifest)
                    if obj is not None:
                        actual.append({"ref": obj["ref"], "content_hash": row.get("content_hash"), "git_commit": row.get("git_commit")})
            expected = [{"ref": row["ref"], "content_hash": row.get("content_hash"), "git_commit": row.get("git_commit")} for row in checkpoint["historical_bindings"]]
            add("historical_binding_exact", _canonical_rows(actual) == _canonical_rows(expected), capture_id=capture_id)

        if "as_of" in checkpoint:
            add("as_of_exact", prediction.get("as_of") == checkpoint["as_of"], capture_id=capture_id)

        if "state_assertions" in checkpoint:
            actual = []
            for row in prediction.get("results") or []:
                if not isinstance(row, dict):
                    continue
                ref = _object_ref(row, manifest, state_snapshot=checkpoint.get("oracle_state"))
                if ref:
                    actual.append({"ref": ref, "is_stale": row.get("is_stale") is True})
            add("state_exact", _canonical_rows(actual) == _canonical_rows(checkpoint["state_assertions"]), capture_id=capture_id)

        if "impact_set" in checkpoint:
            confusion = set_confusion(
                _predicted_refs(prediction, manifest, state_snapshot=checkpoint.get("oracle_state")),
                checkpoint["impact_set"],
            )
            for key in impact_totals:
                impact_totals[key] += int(confusion[key])
            add("impact_set_exact", bool(confusion["exact"]), capture_id=capture_id, **confusion)

        if "stale_set" in checkpoint:
            confusion = set_confusion(
                _predicted_refs(
                    prediction,
                    manifest,
                    stale_only=True,
                    state_snapshot=checkpoint.get("oracle_state"),
                ),
                checkpoint["stale_set"],
            )
            for key in stale_totals:
                stale_totals[key] += int(confusion[key])
            add("stale_set_exact", bool(confusion["exact"]), capture_id=capture_id, **confusion)

        civ_violations.extend(classify_civ(prediction, checkpoint, manifest, state_snapshot=checkpoint.get("oracle_state")))

    if execution.errors:
        add("execution_errors", False, errors=list(execution.errors))
    passed = bool(checks) and all(row["passed"] for row in checks) and not civ_violations
    return OracleScenarioEvaluation(
        scenario_id=str(gold["scenario_id"]), passed=passed, score=1.0 if passed else 0.0,
        checks=checks, civ_count=len(civ_violations), civ_violations=civ_violations,
        impact_tp=impact_totals["tp"], impact_fp=impact_totals["fp"], impact_fn=impact_totals["fn"],
        stale_tp=stale_totals["tp"], stale_fp=stale_totals["fp"], stale_fn=stale_totals["fn"],
        version_correct=(all(version_checks) if version_checks else None),
        graph_exact_match=(all(graph_checks) if graph_checks else None),
        fail_closed_expected=fail_expected, fail_closed_satisfied=(all(fail_checks) if fail_checks else False),
        gold_digest=str(gold["gold_digest"]), execution_errors=list(execution.errors),
    )
