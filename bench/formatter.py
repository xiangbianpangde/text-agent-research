"""ResearchCTL-Bench internal conformance report formatters."""
from __future__ import annotations

import html
import json
from typing import Optional

from .evaluator import BenchmarkMetrics
from .scenarios import TRACKS, TRACK_NAMES


BENCHMARK_VERSION = "0.7.0"


def _pct(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value * 100.0:.1f}%"


def _score(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:.1f}"


def format_terminal_dashboard(metrics: BenchmarkMetrics) -> str:
    """Render a truthful terminal report for the internal conformance suite."""
    bold = "\033[1m"
    green = "\033[32m"
    red = "\033[31m"
    yellow = "\033[33m"
    cyan = "\033[36m"
    reset = "\033[0m"

    eligible_text = "YES" if metrics.certification_eligible else "NO"
    integrity_text = "PASS" if metrics.integrity_gate_passed else "FAIL / NOT MEASURED"
    overall_color = green if metrics.iqg_passed else (yellow if not metrics.certification_eligible else red)

    lines = [
        f"{bold}{cyan}{'=' * 88}{reset}",
        f"{bold}{cyan} ResearchCTL-Bench v{BENCHMARK_VERSION} · Internal Conformance Report{reset}",
        f"{bold}{cyan}{'=' * 88}{reset}",
        "",
        f"  {bold}Evaluation mode:{reset}       {metrics.evaluation_mode}",
        f"  {bold}Evaluation engine:{reset}     {metrics.evaluation_engine}",
        f"  {bold}P0.3 status:{reset}           {metrics.p0_3_status}",
        f"  {bold}Oracle coverage:{reset}       {len(metrics.oracle_compiled_scenario_ids)} / {metrics.oracle_required}",
        f"  {bold}SUT adapter:{reset}            {metrics.sut_metadata.get('adapter') or 'unknown'}",
        f"  {bold}SUT command digest:{reset}     {metrics.sut_metadata.get('command_digest') or 'unknown'}",
        f"  {bold}Formal Oracle score:{reset}   {_score(metrics.composite_score)} / 100.0",
        f"  {bold}Scenario coverage:{reset}     {len(metrics.covered_scenario_ids)} / "
        f"{len(metrics.covered_scenario_ids) + len(metrics.missing_scenario_ids)} "
        f"({metrics.coverage_rate * 100.0:.1f}%)",
        f"  {bold}Certification eligible:{reset} {eligible_text}",
        f"  {bold}Integrity gate:{reset}        {integrity_text}",
        f"  {bold}Result:{reset}                {overall_color}{bold}{metrics.tier_name}{reset}",
        "",
        f"{bold}── Coverage Gate ───────────────────────────────────────────────────────────────{reset}",
        f"  Covered tracks: {len(metrics.covered_tracks)} / {len(metrics.covered_tracks) + len(metrics.missing_tracks)}",
        f"  Missing tracks: {', '.join(metrics.missing_tracks) or 'none'}",
        f"  Missing scenarios: {', '.join(metrics.missing_scenario_ids) or 'none'}",
        f"  Ineligible reasons: {', '.join(metrics.ineligible_reasons) or 'none'}",
        "",
        f"{bold}── Integrity Metrics ──────────────────────────────────────────────────────────{reset}",
        f"  P_GEM={_pct(metrics.pgem)}  VLP={_pct(metrics.vlp)}  SF1={_pct(metrics.sf1)}  "
        f"IF1={_pct(metrics.if1)}  FCAA={_pct(metrics.fcaa)}  ZHR={_pct(metrics.zhr)}  CIV={metrics.civ}",
        "",
        f"{bold}── Track Diagnostics ───────────────────────────────────────────────────────────{reset}",
    ]

    for index, track in enumerate(TRACKS, 1):
        score = metrics.track_scores.get(track)
        lines.append(f"  [{index}] {TRACK_NAMES.get(track, track):<42} {_score(score):>6}")

    lines.extend([
        "",
        f"{bold}── Scenario Results ───────────────────────────────────────────────────────────{reset}",
    ])
    for result in metrics.scenario_results:
        status = f"{green}PASS{reset}" if result.passed else f"{red}FAIL{reset}"
        lines.append(f"  {result.scenario_id:<6} {status:<15} {result.name:<36} {result.detail}")

    lines.extend([
        "",
        f"{bold}{cyan}{'=' * 88}{reset}",
        (
            f"{bold}{yellow} NOT CERTIFIABLE — required P0 gates remain incomplete.{reset}"
            if not metrics.certification_eligible
            else (
                f"{bold}{green} INTERNAL CONFORMANCE PASS — not a public benchmark certification.{reset}"
                if metrics.iqg_passed
                else f"{bold}{red} INTERNAL CONFORMANCE FAIL.{reset}"
            )
        ),
        f"{bold}{cyan}{'=' * 88}{reset}",
    ])
    return "\n".join(lines)


def format_json_report(metrics: BenchmarkMetrics) -> str:
    """Return a machine-readable, coverage-aware conformance report."""
    payload = {
        "benchmark_name": "ResearchCTL-Bench",
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_status": metrics.benchmark_status,
        "evaluation_mode": metrics.evaluation_mode,
        "evaluation_engine": metrics.evaluation_engine,
        "score_provenance": metrics.score_provenance,
        "integrity_metrics_provenance": metrics.integrity_metrics_provenance,
        "p0_3_status": metrics.p0_3_status,
        "p0_4_status": metrics.p0_4_status,
        "p0_status": metrics.p0_status,
        "shadow_review_status": metrics.shadow_review_status,
        "sut": metrics.sut_metadata,
        "oracle": {
            "passed_scenarios": sum(1 for item in metrics.oracle_evaluations if item.get("passed")),
            "failed_scenarios": sum(1 for item in metrics.oracle_evaluations if not item.get("passed")),
            "coverage": {
                "required": metrics.oracle_required,
                "compiled": len(metrics.oracle_compiled_scenario_ids),
                "compiled_scenario_ids": metrics.oracle_compiled_scenario_ids,
                "missing_scenario_ids": metrics.oracle_missing_scenario_ids,
            },
            "evaluations": metrics.oracle_evaluations,
        },
        "legacy_diagnostic": metrics.legacy_diagnostic,
        "composite_score": metrics.composite_score,
        "passed_scenarios": metrics.passed_scenarios,
        "total_scenarios": metrics.total_scenarios,
        "tier": metrics.tier,
        "tier_name": metrics.tier_name,
        "certification_eligible": metrics.certification_eligible,
        "integrity_gate_passed": metrics.integrity_gate_passed,
        "iqg_passed": metrics.iqg_passed,
        "coverage": {
            "rate": metrics.coverage_rate,
            "covered_tracks": metrics.covered_tracks,
            "missing_tracks": metrics.missing_tracks,
            "covered_scenario_ids": metrics.covered_scenario_ids,
            "missing_scenario_ids": metrics.missing_scenario_ids,
            "unexpected_scenario_ids": metrics.unexpected_scenario_ids,
            "duplicate_scenario_ids": metrics.duplicate_scenario_ids,
            "ineligible_reasons": metrics.ineligible_reasons,
        },
        "metrics": {
            "pgem": metrics.pgem,
            "vlp": metrics.vlp,
            "sdp": metrics.sdp,
            "sdr": metrics.sdr,
            "sf1": metrics.sf1,
            "ip": metrics.ip,
            "ir": metrics.ir,
            "if1": metrics.if1,
            "fcaa": metrics.fcaa,
            "zhr": metrics.zhr,
            "civ": metrics.civ,
        },
        "track_scores": metrics.track_scores,
        "scenarios": None if metrics.evaluation_engine == "oracle_shadow" else [
            {
                "id": result.scenario_id,
                "track": result.track,
                "name": result.name,
                "passed": result.passed,
                "score": result.score,
                "detail": result.detail,
            }
            for result in metrics.scenario_results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_talk_report_html(metrics: BenchmarkMetrics) -> str:
    """Return a report-design-system fragment without public certification claims."""
    scenario_rows = "".join(
        "<tr>"
        f"<th scope=\"row\"><code>{html.escape(result.scenario_id)}</code></th>"
        f"<td>{'PASS' if result.passed else 'FAIL'}</td>"
        f"<td>{html.escape(result.name)}</td>"
        f"<td>{html.escape(result.detail)}</td>"
        "</tr>"
        for result in metrics.scenario_results
    )
    verdict = (
        "Not certifiable: required P0 gates remain incomplete, so no tier is available."
        if not metrics.certification_eligible
        else (
            "Internal conformance passed; this is not a public benchmark certification."
            if metrics.iqg_passed
            else "Internal conformance failed."
        )
    )
    return f"""
<section id="hero" class="hero" data-nav-title="摘要">
  <div class="tag-row"><span class="b-pill inf">INTERNAL CONFORMANCE</span></div>
  <h1>ResearchCTL-Bench 诊断报告</h1>
  <p class="sub">当前输出用于内部一致性与回归诊断，不代表公开 Research Benchmark 认证。</p>
  <div class="meta-row"><span>v{BENCHMARK_VERSION}</span><span>•</span><span>{html.escape(metrics.evaluation_mode)}</span><span>•</span><span>{html.escape(str(metrics.sut_metadata.get('adapter') or 'unknown'))}</span></div>
</section>
<section id="coverage" class="sec-head section-gap" data-nav-title="覆盖门">
  <div class="tag">01 · COVERAGE</div><h2>覆盖与资格</h2>
  <p>缺失证据显示为 N/A；部分运行永不授予 Tier。</p>
</section>
<div class="kpi-row">
  <div class="kpi"><div class="num">{_score(metrics.composite_score)}</div><div class="lbl">诊断分数</div></div>
  <div class="kpi"><div class="num">{metrics.coverage_rate * 100.0:.1f}%</div><div class="lbl">场景覆盖率</div></div>
  <div class="kpi"><div class="num">{'YES' if metrics.certification_eligible else 'NO'}</div><div class="lbl">具备资格</div></div>
</div>
<section id="details" class="sec-head section-gap" data-nav-title="场景明细">
  <div class="tag">02 · RESULTS</div><h2>场景执行结果</h2><p>逐项执行结果不替代独立 Gold。</p>
</section>
<div class="tbl-wrap"><table><caption>Internal conformance scenario results</caption>
<thead><tr><th scope="col">ID</th><th scope="col">状态</th><th scope="col">场景</th><th scope="col">明细</th></tr></thead>
<tbody>{scenario_rows}</tbody></table></div>
<div class="verdict"><div class="lbl">RESULT</div><h3>{html.escape(metrics.tier)}</h3><p>{html.escape(verdict)}</p></div>
"""
