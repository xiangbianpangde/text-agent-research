"""ResearchCTL-Bench conformance metrics and certification-safety gates.

P0.1 deliberately separates diagnostic scores from certification eligibility.
Missing evidence is represented as ``None`` (JSON ``null``), never as a perfect
score. The current suite remains an internal conformance suite until later P0
contracts introduce an independent SUT adapter and Oracle.
"""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, List, Optional, Sequence


MetricValue = Optional[float]


@dataclasses.dataclass
class ScenarioResult:
    scenario_id: str
    track: str
    name: str
    passed: bool
    score: float  # 0.0 ~ 1.0
    detail: str = ""
    error_semantic: Optional[str] = None
    envelope_status: Optional[str] = None
    expected_behavior: Optional[str] = None
    civ_count: int = 0
    is_hallucination: bool = False
    is_fail_closed_expected: bool = False
    fail_closed_satisfied: bool = False
    stale_tp: int = 0
    stale_fp: int = 0
    stale_fn: int = 0
    impact_tp: int = 0
    impact_fp: int = 0
    impact_fn: int = 0
    version_correct: Optional[bool] = None
    graph_exact_match: Optional[bool] = None


@dataclasses.dataclass
class BenchmarkMetrics:
    total_scenarios: int = 0
    passed_scenarios: int = 0
    composite_score: MetricValue = None

    # Evaluation/coverage contract
    evaluation_mode: str = "full"
    benchmark_status: str = "internal_conformance_only"
    sut_metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    evaluation_engine: str = "legacy_diagnostic"
    score_provenance: str = "legacy_self_scored_diagnostic"
    integrity_metrics_provenance: str = "legacy_self_scored_diagnostic"
    p0_3_status: str = "not_started"
    oracle_required: int = 0
    oracle_compiled_scenario_ids: List[str] = dataclasses.field(default_factory=list)
    oracle_missing_scenario_ids: List[str] = dataclasses.field(default_factory=list)
    oracle_evaluations: List[Dict[str, Any]] = dataclasses.field(default_factory=list)
    certification_eligible: bool = False
    coverage_rate: float = 0.0
    covered_tracks: List[str] = dataclasses.field(default_factory=list)
    missing_tracks: List[str] = dataclasses.field(default_factory=list)
    covered_scenario_ids: List[str] = dataclasses.field(default_factory=list)
    missing_scenario_ids: List[str] = dataclasses.field(default_factory=list)
    unexpected_scenario_ids: List[str] = dataclasses.field(default_factory=list)
    duplicate_scenario_ids: List[str] = dataclasses.field(default_factory=list)
    ineligible_reasons: List[str] = dataclasses.field(default_factory=list)

    # Integrity metrics. None means not measured, not perfect.
    pgem: MetricValue = None
    vlp: MetricValue = None
    sdp: MetricValue = None
    sdr: MetricValue = None
    sf1: MetricValue = None
    ip: MetricValue = None
    ir: MetricValue = None
    if1: MetricValue = None
    fcaa: MetricValue = None
    zhr: MetricValue = None
    civ: int = 0
    integrity_gate_passed: bool = False
    iqg_passed: bool = False  # Backward-compatible field; now also requires coverage.

    # Fixed required tracks; missing tracks stay None.
    track_scores: Dict[str, MetricValue] = dataclasses.field(default_factory=dict)

    # No public S/A/B certification during P0.
    tier: str = "N/A"
    tier_name: str = "不可认证 (Diagnostic / Incomplete)"

    scenario_results: List[ScenarioResult] = dataclasses.field(default_factory=list)


def _ratio(numerator: int, denominator: int) -> MetricValue:
    return numerator / denominator if denominator > 0 else None


def _f1(precision: MetricValue, recall: MetricValue) -> MetricValue:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return (2.0 * precision * recall) / (precision + recall)


def _duplicate_ids(ids: Sequence[str]) -> List[str]:
    seen = set()
    duplicates = set()
    for value in ids:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def evaluate_benchmark(
    results: List[ScenarioResult],
    *,
    evaluation_mode: str = "full",
    required_tracks: Optional[Sequence[str]] = None,
    required_scenario_ids: Optional[Sequence[str]] = None,
    oracle_evaluations: Optional[Sequence[Any]] = None,
) -> BenchmarkMetrics:
    """Evaluate conformance results without converting missing evidence to success.

    ``evaluation_mode`` is ``full`` only for an unfiltered canonical run. Any
    selected scenario/track run must use ``diagnostic_partial`` and can never
    receive a conformance verdict or tier.
    """
    if evaluation_mode not in ("full", "diagnostic_partial"):
        raise ValueError(f"unsupported evaluation_mode: {evaluation_mode}")

    if required_tracks is None or required_scenario_ids is None:
        # Deferred import avoids the evaluator <-> runner/scenarios import cycle.
        from .runner import REQUIRED_SCENARIO_IDS
        from .scenarios import TRACKS
        if required_tracks is None:
            required_tracks = TRACKS
        if required_scenario_ids is None:
            required_scenario_ids = REQUIRED_SCENARIO_IDS

    required_tracks = list(required_tracks)
    required_scenario_ids = list(required_scenario_ids)
    required_id_set = set(required_scenario_ids)

    metrics = BenchmarkMetrics(evaluation_mode=evaluation_mode)
    metrics.scenario_results = results
    metrics.total_scenarios = len(results)
    metrics.passed_scenarios = sum(1 for result in results if result.passed)

    observed_ids = [result.scenario_id for result in results]
    observed_id_set = set(observed_ids)
    metrics.covered_scenario_ids = [sid for sid in required_scenario_ids if sid in observed_id_set]
    metrics.missing_scenario_ids = [sid for sid in required_scenario_ids if sid not in observed_id_set]
    metrics.unexpected_scenario_ids = sorted(observed_id_set - required_id_set)
    metrics.duplicate_scenario_ids = _duplicate_ids(observed_ids)
    metrics.coverage_rate = (
        len(metrics.covered_scenario_ids) / len(required_scenario_ids)
        if required_scenario_ids
        else 0.0
    )

    track_results: Dict[str, List[ScenarioResult]] = {}
    for result in results:
        track_results.setdefault(result.track, []).append(result)

    metrics.covered_tracks = [track for track in required_tracks if track in track_results]
    metrics.missing_tracks = [track for track in required_tracks if track not in track_results]
    metrics.track_scores = {
        track: (
            round(sum(result.score for result in track_results[track]) / len(track_results[track]) * 100.0, 1)
            if track in track_results
            else None
        )
        for track in required_tracks
    }

    diagnostic_scores = [score for score in metrics.track_scores.values() if score is not None]
    metrics.composite_score = (
        round(sum(diagnostic_scores) / len(diagnostic_scores), 1)
        if diagnostic_scores
        else None
    )

    if evaluation_mode != "full":
        metrics.ineligible_reasons.append("PARTIAL_EVALUATION")
    if metrics.missing_tracks:
        metrics.ineligible_reasons.append("MISSING_REQUIRED_TRACKS")
    if metrics.missing_scenario_ids:
        metrics.ineligible_reasons.append("MISSING_REQUIRED_SCENARIOS")
    if metrics.unexpected_scenario_ids:
        metrics.ineligible_reasons.append("UNEXPECTED_SCENARIOS")
    if metrics.duplicate_scenario_ids:
        metrics.ineligible_reasons.append("DUPLICATE_SCENARIO_IDS")
    if not results:
        metrics.ineligible_reasons.append("NO_RESULTS")

    if oracle_evaluations is not None:
        metrics.evaluation_engine = "oracle_shadow"
        metrics.score_provenance = "legacy_diagnostic_only"
        metrics.integrity_metrics_provenance = "legacy_diagnostic_only"
        metrics.oracle_required = len(required_scenario_ids)
        by_id = {evaluation.scenario_id: evaluation for evaluation in oracle_evaluations}
        metrics.oracle_compiled_scenario_ids = [sid for sid in required_scenario_ids if sid in by_id]
        metrics.oracle_missing_scenario_ids = [sid for sid in required_scenario_ids if sid not in by_id]
        metrics.oracle_evaluations = [by_id[sid].to_dict() for sid in metrics.oracle_compiled_scenario_ids]
        metrics.p0_3_status = (
            "incomplete_p0_3b"
            if not metrics.oracle_missing_scenario_ids
            else "incomplete_p0_3a"
        )
        metrics.ineligible_reasons.append("P0_3_SHADOW_MODE")
        if metrics.oracle_missing_scenario_ids:
            metrics.ineligible_reasons.append("P0_3_ORACLE_COVERAGE_INCOMPLETE")

    metrics.certification_eligible = not metrics.ineligible_reasons

    pgem_cases = [result for result in results if result.graph_exact_match is not None]
    metrics.pgem = _ratio(
        sum(1 for result in pgem_cases if result.graph_exact_match),
        len(pgem_cases),
    )

    vlp_cases = [result for result in results if result.version_correct is not None]
    metrics.vlp = _ratio(
        sum(1 for result in vlp_cases if result.version_correct),
        len(vlp_cases),
    )

    stale_tp = sum(result.stale_tp for result in results)
    stale_fp = sum(result.stale_fp for result in results)
    stale_fn = sum(result.stale_fn for result in results)
    metrics.sdp = _ratio(stale_tp, stale_tp + stale_fp)
    metrics.sdr = _ratio(stale_tp, stale_tp + stale_fn)
    metrics.sf1 = _f1(metrics.sdp, metrics.sdr)

    impact_tp = sum(result.impact_tp for result in results)
    impact_fp = sum(result.impact_fp for result in results)
    impact_fn = sum(result.impact_fn for result in results)
    metrics.ip = _ratio(impact_tp, impact_tp + impact_fp)
    metrics.ir = _ratio(impact_tp, impact_tp + impact_fn)
    metrics.if1 = _f1(metrics.ip, metrics.ir)

    fcaa_cases = [result for result in results if result.is_fail_closed_expected]
    metrics.fcaa = _ratio(
        sum(1 for result in fcaa_cases if result.fail_closed_satisfied),
        len(fcaa_cases),
    )

    adversarial_cases = [
        result
        for result in results
        if result.is_fail_closed_expected or "Adversarial" in result.track
    ]
    metrics.zhr = _ratio(
        sum(1 for result in adversarial_cases if result.is_hallucination),
        len(adversarial_cases),
    )
    metrics.civ = sum(result.civ_count for result in results)

    required_integrity_metrics = (
        metrics.vlp,
        metrics.sf1,
        metrics.if1,
        metrics.fcaa,
        metrics.zhr,
    )
    metrics.integrity_gate_passed = (
        all(value is not None for value in required_integrity_metrics)
        and metrics.civ == 0
        and metrics.zhr == 0.0
        and metrics.vlp >= 0.98
        and metrics.sf1 >= 0.98
        and metrics.if1 >= 0.98
        and metrics.fcaa >= 0.98
    )
    metrics.iqg_passed = metrics.certification_eligible and metrics.integrity_gate_passed

    if not metrics.certification_eligible:
        metrics.tier = "N/A"
        metrics.tier_name = "诊断运行，不具备认证资格 (Diagnostic / Incomplete)"
    elif metrics.iqg_passed:
        metrics.tier = "CONFORMANCE-PASS"
        metrics.tier_name = "内部一致性套件通过 (Internal Conformance Only)"
    else:
        metrics.tier = "CONFORMANCE-FAIL"
        metrics.tier_name = "内部一致性套件未通过 (Internal Conformance Failed)"

    return metrics
