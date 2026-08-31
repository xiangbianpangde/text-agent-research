"""researchctl CLI（P0-B 只读检索内核）。"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .indexer import build_index
from .queries import cmd_query, cmd_sources, cmd_trace, cmd_history
from .reconciler import run_reconcile


DEFAULT_DB = ".index/research.sqlite"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="researchctl",
        description="Text Agent 检索内核（P0-B）：只读检索，不写入 T0–T3。",
    )
    p.add_argument("--version", action="version", version=f"researchctl {__version__}")
    p.add_argument("--root", default="fixture", help="fixture 项目根目录（默认 fixture）")
    p.add_argument("--db", default=None, help="SQLite 派生索引路径（默认 <root>/.index/research.sqlite）")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("index", help="构建/重建派生 SQLite 索引")
    sp.add_argument("--commit", default="HEAD", help="git commit 引用（默认 HEAD）")
    sp.set_defaults(func=cmd_index)

    sp = sub.add_parser("query", help="结构化查询（SQLite）+ lexical 关键词检索")
    sp.add_argument("--entity", help="按 entity_id 查询")
    sp.add_argument("--doc-type", dest="doc_type", help="按 doc_type 查询（organized/raw/run_manifest/...）")
    sp.add_argument("--status", help="按状态查询（valid/invalid/completed/...）")
    sp.add_argument("--raw", action="store_true", help="列出所有 raw 实体")
    sp.add_argument("--text", help="lexical 关键词检索（匹配文件内容/路径/实体名）")
    sp.set_defaults(func=cmd_query)

    sp = sub.add_parser("sources", help="查询实体来源并校验（含精确版本）")
    sp.add_argument("owner", help="实体 ID：CURRENT / REPORT-001 / ORG-EXP017 / ...")
    sp.set_defaults(func=cmd_sources)

    sp = sub.add_parser("trace", help="provenance 追踪链")
    sp.add_argument("entity", help="起点实体 ID")
    sp.set_defaults(func=cmd_trace)

    sp = sub.add_parser("history", help="历史报告 / 结论演化")
    sp.set_defaults(func=cmd_history)

    sp = sub.add_parser("reconcile", help="完整性检测（断链/hash/漂移/缺失/orphan）")
    sp.set_defaults(func=cmd_reconcile)

    args = p.parse_args(argv)
    if args.db is None:
        args.db = os.path.join(args.root, DEFAULT_DB)
    args.gitdir = args.root

    if not os.path.isdir(args.root):
        print(f"error: 项目根目录不存在: {args.root}", file=sys.stderr)
        return 1

    try:
        out = args.func(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_index(args):
    wm = build_index(args.root, args.db, git_commit=args.commit)
    return {
        "query_id": "index",
        "query_type": "reindex",
        "status": "success",
        "authority": "derived",
        "source_watermark": wm,
        "results": [{"detail": f"派生索引已构建: {args.db}", "watermark": wm}],
        "warnings": [], "errors": [], "error_semantic": None,
    }


def cmd_reconcile(args):
    return run_reconcile(args.root, args.db, args.gitdir)


if __name__ == "__main__":
    sys.exit(main())
