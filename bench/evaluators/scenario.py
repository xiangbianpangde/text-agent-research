"""Generic compiled-Gold versus prediction evaluator."""
from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

from bench.dsl.executor import ExecutionRecord
from bench.oracle.manifest import OracleManifest

from .graph import graph_exact_match
from .sets import set_confusion


def _canonical_rows(values: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(sorted(json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in values))


def _object_ref(row: Mapping[str, Any], manifest: OracleManifest) -> Optional[str]:
    if isinstance(row.get("ref"), str):
        return str(row["ref"])
    objects = (*manifest.document["entities"], *manifest.document["artifacts"])
    for obj in objects:
        same_entity = isinstance(row.get("entity_id"), str) and row.get("entity_id") == obj["entity_id"]
        same_path = isinstance(row.get("path"), str) and bool(row.get("path")) and row.get("path") == obj.get("path")
        if same_entity or same_path:
            return str(obj["ref"])
    return None


def _predicted_refs(prediction: Mapping[str, Any], manifest: OracleManifest, *, stale_only: bool = False) -> Set[str]:
    refs = set()
    for row in prediction.get("results") or []:
        if not isinstance(row, dict):
            continue
        if stale_only and row.get("is_stale") is not True:
            continue
        ref = _object_ref(row, manifest)
        if ref:
            refs.add(ref)
    return refs


@dataclasses.dataclass
class OracleScenarioEvaluation:
    scenario_id: str
    passed: bool
    score: float
    checks: List[Dict[str, Any]]
    civ_count: int
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
    civ = 0
    impact_totals = {"tp": 0, "fp": 0, "fn": 0}
    stale_totals = {"tp": 0, "fp": 0, "fn": 0}
    version_checks: List[bool] = []
    graph_checks: List[bool] = []
    fail_expected = False
    fail_checks: List[bool] = []
    known_refs = set(manifest.refs)
    gold_edges = {
        (edge["source_ref"], edge["relation"], edge["target_ref"])
        for edge in manifest.document["relations"]
    }

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
            for key in ("external_termination", "signal", "tx_residue_empty", "index_present"):
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
        condition = checkpoint["expected_condition"]
        condition_ok = prediction["status"] == condition["status"] and prediction["error_semantic"] == condition["error_semantic"]
        if condition["behavior"] == "fail_closed":
            fail_expected = True
            condition_ok = condition_ok and not (prediction.get("results") or [])
            fail_checks.append(condition_ok)
        add("expected_condition", condition_ok, capture_id=capture_id)
        if condition["behavior"] == "fail_closed":
            continue

        if "results" in checkpoint and checkpoint["results"]:
            gold_refs = {row["ref"] for row in checkpoint["results"]}
            pred_refs = _predicted_refs(prediction, manifest)
            confusion = set_confusion(pred_refs, gold_refs)
            add("result_set_exact", bool(confusion["exact"]), capture_id=capture_id, **confusion)

        if "version_bindings" in checkpoint and checkpoint["version_bindings"]:
            expected = {
                (row["subject"], str(row["value"])) for row in checkpoint["version_bindings"]
            }
            actual = set()
            for row in prediction.get("asserted_facts") or []:
                if isinstance(row, dict) and row.get("predicate") == "bound_version":
                    actual.add((str(row.get("subject")), str(row.get("value"))))
            correct = actual == expected
            version_checks.append(correct)
            add("version_binding_exact", correct, capture_id=capture_id)

        if "asserted_facts" in checkpoint:
            exact = _canonical_rows(prediction.get("asserted_facts") or []) == _canonical_rows(checkpoint["asserted_facts"])
            add("asserted_facts_exact", exact, capture_id=capture_id)

        if "lineage" in checkpoint:
            actual = sorted(
                str(row.get("version_ref")) for row in prediction.get("results") or []
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

        if "required_routing" in checkpoint:
            actual_route = prediction.get("retrieval_mode")
            route_ok = actual_route in checkpoint["required_routing"]
            if actual_route in checkpoint.get("forbidden_routing", []):
                route_ok = False
            add("routing_policy", route_ok, capture_id=capture_id)
        if "ranking_authority" in checkpoint:
            add(
                "ranking_authority",
                prediction.get("ranking_authority") == checkpoint["ranking_authority"],
                capture_id=capture_id,
            )

        if "integrity_issues" in checkpoint:
            actual_issues = []
            for row in [*(prediction.get("warnings") or []), *(prediction.get("errors") or [])]:
                if isinstance(row, dict) and isinstance(row.get("code"), str):
                    actual_issues.append({"code": row["code"], "ref": row.get("ref")})
            expected_codes = sorted(row["code"] for row in checkpoint["integrity_issues"])
            actual_codes = sorted(row["code"] for row in actual_issues)
            add("integrity_issues_exact", actual_codes == expected_codes, capture_id=capture_id)

        if "impact_set" in checkpoint:
            confusion = set_confusion(_predicted_refs(prediction, manifest), checkpoint["impact_set"])
            for key in impact_totals:
                impact_totals[key] += int(confusion[key])
            add("impact_set_exact", bool(confusion["exact"]), capture_id=capture_id, **confusion)

        if "stale_set" in checkpoint:
            confusion = set_confusion(_predicted_refs(prediction, manifest, stale_only=True), checkpoint["stale_set"])
            for key in stale_totals:
                stale_totals[key] += int(confusion[key])
            add("stale_set_exact", bool(confusion["exact"]), capture_id=capture_id, **confusion)

        if prediction.get("ranking_authority") == "authoritative":
            for row in prediction.get("results") or []:
                if isinstance(row, dict):
                    ref = _object_ref(row, manifest)
                    if ref is None:
                        civ += 1
        graph = prediction.get("provenance_graph")
        if isinstance(graph, dict):
            for edge in graph.get("edges", []):
                if isinstance(edge, dict):
                    key = (edge.get("source_ref"), edge.get("relation"), edge.get("target_ref"))
                    if key not in gold_edges:
                        civ += 1

    if execution.errors:
        add("execution_errors", False, errors=list(execution.errors))
    passed = bool(checks) and all(row["passed"] for row in checks) and civ == 0
    return OracleScenarioEvaluation(
        scenario_id=str(gold["scenario_id"]),
        passed=passed,
        score=1.0 if passed else 0.0,
        checks=checks,
        civ_count=civ,
        impact_tp=impact_totals["tp"], impact_fp=impact_totals["fp"], impact_fn=impact_totals["fn"],
        stale_tp=stale_totals["tp"], stale_fp=stale_totals["fp"], stale_fn=stale_totals["fn"],
        version_correct=(all(version_checks) if version_checks else None),
        graph_exact_match=(all(graph_checks) if graph_checks else None),
        fail_closed_expected=fail_expected,
        fail_closed_satisfied=(all(fail_checks) if fail_checks else False),
        gold_digest=str(gold["gold_digest"]),
        execution_errors=list(execution.errors),
    )
