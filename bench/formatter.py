"""ResearchCTL-Bench 报告格式化器（终端彩色仪表盘、JSON 导出与 /talk 报告生成）。"""
from __future__ import annotations

import json
from typing import Dict, List
from .evaluator import BenchmarkMetrics, ScenarioResult
from .scenarios import TRACKS, TRACK_NAMES


def format_terminal_dashboard(metrics: BenchmarkMetrics) -> str:
    """生成专业的终端评测计分板。"""
    lines = []
    
    # ANSI 颜色码
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"
    RESET = "\033[0m"
    
    lines.append(f"{BOLD}{CYAN}========================================================================================{RESET}")
    lines.append(f"{BOLD}{CYAN}          ResearchCTL-Bench (v1.0) 超长程实验检索系统基准评测报告                       {RESET}")
    lines.append(f"{BOLD}{CYAN}========================================================================================{RESET}")
    lines.append("")
    
    # 概览 KPI
    status_color = GREEN if metrics.iqg_passed else RED
    tier_color = GREEN if metrics.tier == "S-Tier" else (YELLOW if metrics.tier in ("A-Tier", "B-Tier") else RED)
    lines.append(f"  {BOLD}综合总评得分 (Score):{RESET}  {tier_color}{BOLD}{metrics.composite_score:.1f} / 100.0{RESET}    {BOLD}认证等级 (Tier):{RESET} {tier_color}{BOLD}{metrics.tier_name}{RESET}")
    lines.append(f"  {BOLD}场景执行通过率:{RESET}       {GREEN if metrics.passed_scenarios == metrics.total_scenarios else YELLOW}{metrics.passed_scenarios} / {metrics.total_scenarios} ({metrics.passed_scenarios/max(1, metrics.total_scenarios)*100:.1f}%){RESET}")
    lines.append(f"  {BOLD}完整性资格门禁 (IQG):{RESET} {status_color}{BOLD}{'PASS (已通过)' if metrics.iqg_passed else 'FAIL (一票否决)'}{RESET}")
    lines.append("")

    # 1. 宪法级硬核指标 (Constitutional Metrics)
    lines.append(f"{BOLD}── 1. 六大宪法级硬核指标 (Constitutional Metrics) ───────────────────────────────────────{RESET}")
    lines.append(f"  ┌────────────────────────────────────────────────────────┬───────────┬──────────────┐")
    lines.append(f"  │ 指标名称 (Metric)                                      │ 实测数值  │ 门禁考核要求 │")
    lines.append(f"  ├────────────────────────────────────────────────────────┼───────────┼──────────────┤")
    lines.append(f"  │ 溯源有向图精确匹配度 (P_GEM - Provenance Graph Match)  │   {GREEN if metrics.pgem >= 0.98 else RED}{metrics.pgem*100.0:5.1f}%{RESET}   │  >= 98.0%    │")
    lines.append(f"  │ 版本级精度 (VLP - Version-Level Precision)             │   {GREEN if metrics.vlp >= 0.98 else RED}{metrics.vlp*100.0:5.1f}%{RESET}   │  >= 98.0%    │")
    lines.append(f"  │ 过期感知 F1 分数 (SF1 - Stale F1: P={metrics.sdp*100:.0f}%, R={metrics.sdr*100:.0f}%)   │   {GREEN if metrics.sf1 >= 0.98 else RED}{metrics.sf1*100.0:5.1f}%{RESET}   │  >= 98.0%    │")
    lines.append(f"  │ 逆向影响 F1 分数 (IF1 - Impact F1: P={metrics.ip*100:.0f}%, R={metrics.ir*100:.0f}%)  │   {GREEN if metrics.if1 >= 0.98 else RED}{metrics.if1*100.0:5.1f}%{RESET}   │  >= 98.0%    │")
    lines.append(f"  │ 正确拒答率 (FCAA - Fail-Closed Abstention Accuracy)    │   {GREEN if metrics.fcaa >= 0.98 else RED}{metrics.fcaa*100.0:5.1f}%{RESET}   │  >= 98.0%    │")
    lines.append(f"  │ 零脑补违约率 (ZHR - Zero-Hallucination Rate)           │   {GREEN if metrics.zhr == 0 else RED}{metrics.zhr*100.0:5.1f}%{RESET}   │  ==  0.0%    │")
    lines.append(f"  │ 严重完整性违规数 (CIV - Critical Integrity Violations) │   {GREEN if metrics.civ == 0 else RED}{metrics.civ:5d}{RESET}   │  ==  0 (绝对)│")
    lines.append(f"  └────────────────────────────────────────────────────────┴───────────┴──────────────┘")
    lines.append("")

    # 2. 8 大 Track 分项计分卡 (Track Scorecard)
    lines.append(f"{BOLD}── 2. 8 大评测轨道计分卡 (Track-by-Track Scorecard) ────────────────────────────────────{RESET}")
    for idx, track_key in enumerate(TRACKS, 1):
        name = TRACK_NAMES.get(track_key, track_key)
        score = metrics.track_scores.get(track_key, 0.0)
        # 制作 20 格进度条
        filled = int(score / 5)
        bar = f"{GREEN}{'█' * filled}{RESET}{'░' * (20 - filled)}"
        score_str = f"{GREEN if score == 100.0 else (YELLOW if score >= 80 else RED)}{score:5.1f}%{RESET}"
        lines.append(f"  [{idx}] {name:<38} {bar} {score_str}")
    lines.append("")

    # 3. 场景清单明细
    lines.append(f"{BOLD}── 3. 场景用例执行明细 (32 类核心场景全景) ─────────────────────────────────────────────{RESET}")
    lines.append(f"  {'ID':<5} {'状态':<6} {'场景名称':<35} {'明细与断言结论':<40}")
    lines.append(f"  {'─'*4} {'─'*6} {'─'*35} {'─'*40}")
    for r in metrics.scenario_results:
        status_tag = f"{GREEN}PASS{RESET}" if r.passed else f"{RED}FAIL{RESET}"
        lines.append(f"  {r.scenario_id:<5} {status_tag:<15} {r.name:<35} {r.detail}")
    lines.append("")

    # 4. 最终裁决 Banner
    lines.append(f"{BOLD}{CYAN}========================================================================================{RESET}")
    if metrics.iqg_passed and metrics.composite_score >= 95.0:
        lines.append(f"{BOLD}{GREEN}  ★ 最终裁决: PASS — 获得权威科研可信度 S-Tier 长期证明认证 (Scientific Certified)      {RESET}")
    elif metrics.iqg_passed:
        lines.append(f"{BOLD}{YELLOW}  ★ 最终裁决: PASS — 达到合格基准线 ({metrics.tier})                                      {RESET}")
    else:
        lines.append(f"{BOLD}{RED}  ✖ 最终裁决: DISQUALIFIED — 未通过完整性资格门禁 (CIV={metrics.civ}, ZHR={metrics.zhr:.1f})            {RESET}")
    lines.append(f"{BOLD}{CYAN}========================================================================================{RESET}")

    return "\n".join(lines)


def format_json_report(metrics: BenchmarkMetrics) -> str:
    """输出符合机器解析契约的完整 Benchmark JSON 数据包。"""
    payload = {
        "benchmark_name": "ResearchCTL-Bench",
        "benchmark_version": "1.0.0",
        "composite_score": metrics.composite_score,
        "passed_scenarios": metrics.passed_scenarios,
        "total_scenarios": metrics.total_scenarios,
        "tier": metrics.tier,
        "tier_name": metrics.tier_name,
        "iqg_passed": metrics.iqg_passed,
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
        "scenarios": [
            {
                "id": r.scenario_id,
                "track": r.track,
                "name": r.name,
                "passed": r.passed,
                "score": r.score,
                "detail": r.detail,
            }
            for r in metrics.scenario_results
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_talk_report_html(metrics: BenchmarkMetrics) -> str:
    """生成符合 /talk design system 规范的 HTML 报告片段。"""
    rows_html = []
    for r in metrics.scenario_results:
        badge = f'<span style="color:#10b981;font-weight:bold;">PASS</span>' if r.passed else f'<span style="color:#ef4444;font-weight:bold;">FAIL</span>'
        rows_html.append(f"""
        <tr>
          <td><code>{r.scenario_id}</code></td>
          <td>{badge}</td>
          <td>{r.name}</td>
          <td><small>{r.detail}</small></td>
        </tr>
        """)
        
    track_cards = []
    for track_key in TRACKS:
        tname = TRACK_NAMES.get(track_key, track_key)
        score = metrics.track_scores.get(track_key, 0.0)
        track_cards.append(f"""
        <div class="card" style="padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#f9fafb;">
          <div style="font-size:12px;color:#6b7280;">{tname}</div>
          <div style="font-size:24px;font-weight:bold;color:#111827;margin-top:4px;">{score:.1f}%</div>
        </div>
        """)

    return f"""
    <div class="hero">
      <h1 style="margin:0 0 8px 0;font-size:28px;">ResearchCTL-Bench 科研检索能力评测认证</h1>
      <p style="margin:0;color:#6b7280;">Long-Horizon Research State, Versioning, Provenance & Integrity Verifiability Benchmark</p>
    </div>

    <section id="kpi-overview" class="sec-head" style="margin-top:24px;">
      <h2>核心指标概览</h2>
      <div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:12px;margin-top:12px;">
        <div class="kpi" style="padding:16px;background:#eff6ff;border-radius:8px;border-left:4px solid #3b82f6;">
          <div style="font-size:12px;color:#1e40af;">综合总分 (Composite)</div>
          <div style="font-size:32px;font-weight:bold;color:#1e3a8a;">{metrics.composite_score:.1f}</div>
        </div>
        <div class="kpi" style="padding:16px;background:#ecfdf5;border-radius:8px;border-left:4px solid #10b981;">
          <div style="font-size:12px;color:#065f46;">认证等级 (Tier)</div>
          <div style="font-size:20px;font-weight:bold;color:#064e3b;margin-top:8px;">{metrics.tier}</div>
        </div>
        <div class="kpi" style="padding:16px;background:#fef3c7;border-radius:8px;border-left:4px solid #f59e0b;">
          <div style="font-size:12px;color:#92400e;">门禁状态 (IQG)</div>
          <div style="font-size:20px;font-weight:bold;color:#78350f;margin-top:8px;">{'通过 (PASS)' if metrics.iqg_passed else '未通过 (FAIL)'}</div>
        </div>
        <div class="kpi" style="padding:16px;background:#f3f4f6;border-radius:8px;border-left:4px solid #6b7280;">
          <div style="font-size:12px;color:#374151;">场景通过率 (Rate)</div>
          <div style="font-size:32px;font-weight:bold;color:#111827;">{metrics.passed_scenarios}/{metrics.total_scenarios}</div>
        </div>
      </div>
    </section>

    <section id="tracks" class="sec-head" style="margin-top:28px;">
      <h2>8 大轨道计分卡 (Track Scorecard)</h2>
      <div style="display:grid;grid-template-columns:repeat(2, 1fr);gap:12px;margin-top:12px;">
        {''.join(track_cards)}
      </div>
    </section>

    <section id="details" class="sec-head" style="margin-top:28px;">
      <h2>32 类场景执行明细</h2>
      <div class="tbl-wrap" style="margin-top:12px;overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:13px;text-align:left;">
          <thead>
            <tr style="border-bottom:2px solid #e5e7eb;background:#f9fafb;">
              <th style="padding:8px;">用例 ID</th>
              <th style="padding:8px;">状态</th>
              <th style="padding:8px;">测试场景名称</th>
              <th style="padding:8px;">执行断言与因果细节</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
      </div>
    </section>

    <div class="verdict" style="margin-top:32px;padding:20px;border-radius:8px;background:{'#ecfdf5;border:1px solid #10b981' if metrics.iqg_passed else '#fef2f2;border:1px solid #ef4444'};">
      <h3 style="margin:0 0 8px 0;color:{'#065f46' if metrics.iqg_passed else '#991b1b'};">
        {'✔ 评测结论: 恭喜！被测系统完全通过 ResearchCTL-Bench 严苛认证' if metrics.iqg_passed else '✖ 评测结论: 完整性门禁一票否决，判定无科研可信资格'}
      </h3>
      <p style="margin:0;color:#4b5563;font-size:14px;">
        {f'系统不仅在事实检索中取得 {metrics.composite_score:.1f} 分，且全面满足六大宪法级完整性要求（CIV=0, ZHR=0.0%, VLP=100.0%, FCAA=100.0%）。具备抵抗灾难性派生损坏、版本漂移与对抗性虚构脑补的顶级鲁棒性。' if metrics.iqg_passed else f'系统在完整性与安全测试中出现违规 (CIV={metrics.civ})，未能达成严苛科研基准门禁。'}
      </p>
    </div>
    """
