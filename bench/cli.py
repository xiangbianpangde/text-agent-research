"""ResearchCTL-Bench CLI 命令行入口。"""
from __future__ import annotations

import argparse
import os
import sys

from .evaluator import evaluate_benchmark
from .formatter import format_terminal_dashboard, format_json_report, format_talk_report_html
from .runner import BenchmarkSandbox, SCENARIO_RUNNERS


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="researchctl-bench",
        description="ResearchCTL-Bench: 超长程实验检索系统专业基准评测套件",
    )
    parser.add_argument("--fixture", default="fixture", help="基础 fixture 模板目录（默认 fixture）")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON 格式评测结果")
    parser.add_argument("--save-json", metavar="PATH", help="将评测结果保存至指定 JSON 文件")
    parser.add_argument("--talk", action="store_true", help="尝试向 /talk 前端渲染可视化交互报告")
    parser.add_argument("--track", help="仅运行指定 Track（如 Track1_DefinitionProvenance）")
    parser.add_argument("--scenario", help="仅运行指定场景 ID（如 S01, S19）")

    args = parser.parse_args(argv)

    runners_to_run = SCENARIO_RUNNERS
    if args.scenario:
        runners_to_run = [fn for fn in SCENARIO_RUNNERS if args.scenario.lower() in fn.__name__.lower()]
        if not runners_to_run:
            print(f"错误: 未找到匹配场景 ID: {args.scenario}", file=sys.stderr)
            return 1

    if not args.json:
        print("========================================================================================")
        print("正在启动 ResearchCTL-Bench 专业基准评测 (32 类规范场景)...")
        print("========================================================================================")

    results = []
    for idx, fn in enumerate(runners_to_run, 1):
        with BenchmarkSandbox(args.fixture) as sb:
            res = fn(sb)
            results.append(res)
            if not args.json:
                icon = "✔ PASS" if res.passed else "✖ FAIL"
                print(f"  [{idx:02d}/{len(runners_to_run):02d}] {res.scenario_id:<6} {icon:<8} {res.name:<32} {res.detail[:40]}")

    metrics = evaluate_benchmark(results)

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

    return 0 if metrics.iqg_passed else 1


if __name__ == "__main__":
    sys.exit(main())
