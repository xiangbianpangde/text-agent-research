"""ResearchCTL-Bench CLI 命令行入口。"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .adapters import default_researchctl_command
from .adapters.process import project_root
from .evaluator import evaluate_benchmark, evaluate_oracle_benchmark, legacy_diagnostic_payload
from .formatter import format_terminal_dashboard, format_json_report
from .dsl.loader import load_scenario
from .runner import (
    BenchmarkSandbox,
    DEFAULT_ORACLE_PACK,
    ORACLE_SCENARIO_IDS,
    REQUIRED_SCENARIO_IDS,
    SCENARIO_REGISTRY,
    run_oracle_scenario,
)
from .scenarios import TRACKS


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="researchctl-bench",
        description="ResearchCTL-Bench: 内部一致性评测套件（P0 harness construction）",
    )
    parser.add_argument("--fixture", default="fixture", help="基础 fixture 模板目录（默认 fixture）")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON 格式评测结果")
    parser.add_argument("--save-json", metavar="PATH", help="将评测结果保存至指定 JSON 文件")
    parser.add_argument("--talk", action="store_true", help="尝试向 /talk 前端渲染可视化交互报告")
    parser.add_argument(
        "--legacy-diagnostic",
        action="store_true",
        help="额外运行旧 run_sXX 自评分诊断；不影响 Oracle-only 正式指标",
    )
    parser.add_argument("--track", choices=TRACKS, help="仅运行指定 Track（诊断模式，不授予 Tier）")
    parser.add_argument("--scenario", help="仅运行指定场景 ID（如 S01, S19）")
    parser.add_argument(
        "--sut-command-json",
        help="SUT adapter 启动命令的 JSON string array；缺省使用官方 ResearchCTL adapter",
    )
    parser.add_argument(
        "--sut-cwd",
        help="SUT adapter 启动目录；缺省为当前项目根目录",
    )

    args = parser.parse_args(argv)

    sut_command = list(default_researchctl_command())
    if args.sut_command_json:
        try:
            candidate = json.loads(args.sut_command_json)
        except json.JSONDecodeError as exc:
            parser.error(f"--sut-command-json 不是合法 JSON: {exc}")
        if not isinstance(candidate, list) or not candidate or any(
            not isinstance(part, str) or not part for part in candidate
        ):
            parser.error("--sut-command-json 必须是非空 string array")
        sut_command = candidate
    sut_cwd = os.path.abspath(args.sut_cwd) if args.sut_cwd else project_root()

    oracle_scenarios = {
        scenario_id: load_scenario(os.path.join(DEFAULT_ORACLE_PACK, "scenarios", f"{scenario_id}.json"))
        for scenario_id in ORACLE_SCENARIO_IDS
    }
    selected_ids = list(ORACLE_SCENARIO_IDS)
    if args.track:
        selected_ids = [sid for sid in selected_ids if oracle_scenarios[sid].document["track"] == args.track]
    if args.scenario:
        scenario_id = args.scenario.upper()
        selected_ids = [sid for sid in selected_ids if sid.upper() == scenario_id]
    if not selected_ids:
        print("错误: 场景与 Track 过滤条件没有匹配结果", file=sys.stderr)
        return 1

    evaluation_mode = "diagnostic_partial" if args.scenario or args.track else "full"

    if not args.json:
        print("========================================================================================")
        print("正在启动 ResearchCTL-Bench 内部一致性评测 (33 个 conformance 场景)...")
        if evaluation_mode != "full":
            print("注意: 当前为部分诊断运行，不具备认证资格，也不会授予 Tier。")
        print("========================================================================================")

    legacy_results = []
    sut_metadata = {}
    if args.legacy_diagnostic:
        legacy_by_id = {registration.scenario_id: registration for registration in SCENARIO_REGISTRY}
        for idx, scenario_id in enumerate(selected_ids, 1):
            registration = legacy_by_id[scenario_id]
            with BenchmarkSandbox(
                args.fixture,
                sut_command=sut_command,
                sut_cwd=sut_cwd,
            ) as sb:
                if not sut_metadata:
                    sut_metadata = dict(sb.sut_metadata)
                result = registration.runner(sb)
                legacy_results.append(result)
                if not args.json:
                    icon = "✔ PASS" if result.passed else "✖ FAIL"
                    print(f"  [legacy {idx:02d}/{len(selected_ids):02d}] {result.scenario_id:<6} {icon:<8} {result.name:<32}")

    oracle_evaluations = []
    oracle_metadata = {}
    for scenario_id in selected_ids:
        oracle_evaluation, oracle_metadata, _gold = run_oracle_scenario(
            scenario_id,
            args.fixture,
            sut_command=sut_command,
            sut_cwd=sut_cwd,
        )
        oracle_evaluations.append(oracle_evaluation)
        if not sut_metadata:
            sut_metadata = oracle_metadata
        if not args.json:
            status = "PASS" if oracle_evaluation.passed else "FAIL"
            print(f"       ↳ Oracle {status}: {scenario_id} ({len(oracle_evaluation.checks)} checks)")

    scenario_metadata = {
        scenario_id: {
            "track": actions.document["track"],
            "name": actions.document["name"],
        }
        for scenario_id, actions in oracle_scenarios.items()
    }
    metrics = evaluate_oracle_benchmark(
        oracle_evaluations,
        evaluation_mode=evaluation_mode,
        scenario_metadata=scenario_metadata,
        required_tracks=TRACKS,
        required_scenario_ids=REQUIRED_SCENARIO_IDS,
    )
    metrics.sut_metadata = sut_metadata or oracle_metadata
    if args.legacy_diagnostic:
        legacy_metrics = evaluate_benchmark(
            legacy_results,
            evaluation_mode=evaluation_mode,
            required_tracks=TRACKS,
            required_scenario_ids=REQUIRED_SCENARIO_IDS,
        )
        metrics.legacy_diagnostic = legacy_diagnostic_payload(legacy_metrics)

    if args.json:
        print(format_json_report(metrics))
    else:
        print("")
        print(format_terminal_dashboard(metrics))

    if args.save_json:
        with open(args.save_json, "w", encoding="utf-8") as f:
            f.write(format_json_report(metrics))
        if not args.json:
            print(f"\n评测完整数据包已保存至: {args.save_json}")

    if metrics.evaluation_mode == "diagnostic_partial":
        return 0 if metrics.total_scenarios > 0 and metrics.passed_scenarios == metrics.total_scenarios else 1
    return 0 if metrics.passed_scenarios == metrics.total_scenarios and metrics.integrity_gate_passed else 1


if __name__ == "__main__":
    sys.exit(main())
