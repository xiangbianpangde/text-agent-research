#!/usr/bin/env python3
"""ResearchCTL-Bench 一键基准评测运行脚本。

用法：
    python3 run_benchmark.py
    python3 run_benchmark.py --json
    python3 run_benchmark.py --save-json benchmark_results.json
"""
import sys
from bench.cli import main

if __name__ == "__main__":
    sys.exit(main())
