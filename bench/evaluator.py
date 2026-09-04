"""ResearchCTL-Bench 评测指标与门禁裁决引擎。"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Any


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
    composite_score: float = 0.0  # 0.0 ~ 100.0
    
    # 宪法级硬核指标
    pgem: float = 0.0   # Provenance Graph Exact-Match
    vlp: float = 0.0    # Version-Level Precision
    sdp: float = 0.0    # Stale Detection Precision
    sdr: float = 0.0    # Stale Detection Recall
    sf1: float = 0.0    # Stale F1
    ip: float = 0.0     # Impact Precision
    ir: float = 0.0     # Impact Recall
    if1: float = 0.0    # Impact F1
    fcaa: float = 0.0   # Fail-Closed Abstention Accuracy
    zhr: float = 0.0    # Zero-Hallucination Rate (Target: 0.0%)
    civ: int = 0        # Critical Integrity Violations (Target: 0)
    iqg_passed: bool = False  # Integrity Qualification Gate
    
    # 8 大 Track 分项得分 (0 ~ 100)
    track_scores: Dict[str, float] = dataclasses.field(default_factory=dict)
    
    # 科研可信度认证等级 (S-Tier / A-Tier / B-Tier / DISQUALIFIED)
    tier: str = "DISQUALIFIED"
    tier_name: str = "无科研可信资格 (Disqualified)"
    
    # 场景结果列表
    scenario_results: List[ScenarioResult] = dataclasses.field(default_factory=list)


def evaluate_benchmark(results: List[ScenarioResult]) -> BenchmarkMetrics:
    """基于 §5 核心量化指标体系与 §5.4 完整性资格门禁进行综合评定。"""
    metrics = BenchmarkMetrics()
    metrics.scenario_results = results
    metrics.total_scenarios = len(results)
    metrics.passed_scenarios = sum(1 for r in results if r.passed)
    
    # Track 场景映射
    track_results: Dict[str, List[ScenarioResult]] = {}
    for r in results:
        track_results.setdefault(r.track, []).append(r)
        
    for track, s_list in track_results.items():
        if s_list:
            avg_score = sum(s.score for s in s_list) / len(s_list)
            metrics.track_scores[track] = round(avg_score * 100.0, 1)
        else:
            metrics.track_scores[track] = 0.0
            
    # 1. Provenance Graph Exact-Match (P_GEM)
    pgem_cases = [r for r in results if r.graph_exact_match is not None]
    if pgem_cases:
        metrics.pgem = sum(1.0 for r in pgem_cases if r.graph_exact_match) / len(pgem_cases)
    else:
        metrics.pgem = 1.0
        
    # 2. Version-Level Precision (VLP)
    vlp_cases = [r for r in results if r.version_correct is not None]
    if vlp_cases:
        metrics.vlp = sum(1.0 for r in vlp_cases if r.version_correct) / len(vlp_cases)
    else:
        metrics.vlp = 1.0

    # 3. Stale Detection SDP, SDR, SF1
    total_stale_tp = sum(r.stale_tp for r in results)
    total_stale_fp = sum(r.stale_fp for r in results)
    total_stale_fn = sum(r.stale_fn for r in results)
    if total_stale_tp + total_stale_fp > 0:
        metrics.sdp = total_stale_tp / (total_stale_tp + total_stale_fp)
    else:
        metrics.sdp = 1.0
    if total_stale_tp + total_stale_fn > 0:
        metrics.sdr = total_stale_tp / (total_stale_tp + total_stale_fn)
    else:
        metrics.sdr = 1.0
    if metrics.sdp + metrics.sdr > 0:
        metrics.sf1 = (2.0 * metrics.sdp * metrics.sdr) / (metrics.sdp + metrics.sdr)
    else:
        metrics.sf1 = 1.0

    # 4. Impact Analysis IP, IR, IF1
    total_impact_tp = sum(r.impact_tp for r in results)
    total_impact_fp = sum(r.impact_fp for r in results)
    total_impact_fn = sum(r.impact_fn for r in results)
    if total_impact_tp + total_impact_fp > 0:
        metrics.ip = total_impact_tp / (total_impact_tp + total_impact_fp)
    else:
        metrics.ip = 1.0
    if total_impact_tp + total_impact_fn > 0:
        metrics.ir = total_impact_tp / (total_impact_tp + total_impact_fn)
    else:
        metrics.ir = 1.0
    if metrics.ip + metrics.ir > 0:
        metrics.if1 = (2.0 * metrics.ip * metrics.ir) / (metrics.ip + metrics.ir)
    else:
        metrics.if1 = 1.0

    # 5. Fail-Closed Abstention Accuracy (FCAA)
    fcaa_cases = [r for r in results if r.is_fail_closed_expected]
    if fcaa_cases:
        metrics.fcaa = sum(1.0 for r in fcaa_cases if r.fail_closed_satisfied) / len(fcaa_cases)
    else:
        metrics.fcaa = 1.0

    # 6. Zero-Hallucination Rate (ZHR)
    adv_cases = [r for r in results if r.is_fail_closed_expected or "Adversarial" in r.track]
    if adv_cases:
        metrics.zhr = sum(1.0 for r in adv_cases if r.is_hallucination) / len(adv_cases)
    else:
        metrics.zhr = 0.0

    # 7. Critical Integrity Violations (CIV)
    metrics.civ = sum(r.civ_count for r in results)

    # 8. Integrity Qualification Gate (IQG)
    # 门禁一票否决规则: CIV == 0 and ZHR == 0 and VLP >= 0.98 and SF1 >= 0.98 and IF1 >= 0.98 and FCAA >= 0.98
    metrics.iqg_passed = (
        metrics.civ == 0 and
        metrics.zhr == 0.0 and
        metrics.vlp >= 0.98 and
        metrics.sf1 >= 0.98 and
        metrics.if1 >= 0.98 and
        metrics.fcaa >= 0.98
    )

    # 综合复合得分 Composite Score (8 个 Track 等权或均值)
    if metrics.track_scores:
        metrics.composite_score = round(sum(metrics.track_scores.values()) / len(metrics.track_scores), 1)
    else:
        metrics.composite_score = 0.0

    # 判定科研可信度评级 Tier
    if not metrics.iqg_passed:
        metrics.tier = "DISQUALIFIED"
        metrics.tier_name = "无科研可信资格 (Disqualified - IQG Failed)"
    elif metrics.composite_score >= 95.0:
        metrics.tier = "S-Tier"
        metrics.tier_name = "S级: 长期科研级证明系统 (Enterprise Long-Horizon Proven)"
    elif metrics.composite_score >= 90.0:
        metrics.tier = "A-Tier"
        metrics.tier_name = "A级: 生产环境就绪 (Production Ready)"
    elif metrics.composite_score >= 80.0:
        metrics.tier = "B-Tier"
        metrics.tier_name = "B级: 带告警合格 (Qualified with Warnings)"
    else:
        metrics.tier = "DISQUALIFIED"
        metrics.tier_name = "未达到最低基准线 (Below 80.0 Score Baseline)"

    return metrics
