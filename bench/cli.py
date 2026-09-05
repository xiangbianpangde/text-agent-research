"""ResearchCTL-Bench CLI 命令行入口。"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .adapters import default_researchctl_command
from .adapters.process import project_root
from .evaluator import evaluate_benchmark
from .formatter import format_terminal_dashboard, format_json_report
from .runner import (
    BenchmarkSandbox,
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

    selected = list(SCENARIO_REGISTRY)
    if args.track:
        selected = [registration for registration in selected if registration.track == args.track]
    if args.scenario:
        scenario_id = args.scenario.upper()
        selected = [registration for registration in selected if registration.scenario_id.upper() == scenario_id]
    if not selected:
        print("错误: 场景与 Track 过滤条件没有匹配结果", file=sys.stderr)
        return 1

    evaluation_mode = "diagnostic_partial" if args.scenario or args.track else "full"

    if not args.json:
        print("========================================================================================")
        print("正在启动 ResearchCTL-Bench 内部一致性评测 (33 个 conformance 场景)...")
        if evaluation_mode != "full":
            print("注意: 当前为部分诊断运行，不具备认证资格，也不会授予 Tier。")
        print("========================================================================================")

    results = []
    sut_metadata = {}
    for idx, registration in enumerate(selected, 1):
        with BenchmarkSandbox(
            args.fixture,
            sut_command=sut_command,
            sut_cwd=sut_cwd,
        ) as sb:
            if not sut_metadata:
                sut_metadata = dict(sb.sut_metadata)
            res = registration.runner(sb)
            results.append(res)
            if not args.json:
                icon = "✔ PASS" if res.passed else "✖ FAIL"
                print(f"  [{idx:02d}/{len(selected):02d}] {res.scenario_id:<6} {icon:<8} {res.name:<32} {res.detail[:40]}")

    oracle_evaluations = []
    for registration in selected:
        if registration.scenario_id not in ORACLE_SCENARIO_IDS:
            continue
        oracle_evaluation, oracle_metadata, _gold = run_oracle_scenario(
            registration.scenario_id,
            args.fixture,
            sut_command=sut_command,
            sut_cwd=sut_cwd,
        )
        oracle_evaluations.append(oracle_evaluation)
        if not sut_metadata:
            sut_metadata = oracle_metadata
        if not args.json:
            status = "PASS" if oracle_evaluation.passed else "FAIL"
            print(f"       ↳ Oracle shadow {status}: {registration.scenario_id} ({len(oracle_evaluation.checks)} checks)")

    metrics = evaluate_benchmark(
        results,
        evaluation_mode=evaluation_mode,
        required_tracks=TRACKS,
        required_scenario_ids=REQUIRED_SCENARIO_IDS,
        oracle_evaluations=oracle_evaluations,
    )
    metrics.sut_metadata = sut_metadata

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
    return 0 if metrics.iqg_passed else 1


if __name__ == "__main__":
    sys.exit(main())
