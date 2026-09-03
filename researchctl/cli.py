"""researchctl CLI（P0-B 只读检索内核）。"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .indexer import build_index
from .queries import cmd_query, cmd_sources, cmd_trace, cmd_history, cmd_impact
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
    sp.add_argument("--semantic", action="store_true", help="P1-C: 原子全量重建 semantic 派生索引")
    sp.set_defaults(func=cmd_index)

    sp = sub.add_parser("query", help="结构化查询（SQLite）+ lexical 关键词检索")
    sp.add_argument("--entity", help="按 entity_id 查询")
    sp.add_argument("--doc-type", dest="doc_type", help="按 doc_type 查询（organized/raw/run_manifest/...）")
    sp.add_argument("--status", help="按状态查询（valid/invalid/completed/...）")
    sp.add_argument("--raw", action="store_true", help="列出所有 raw 实体")
    sp.add_argument("--text", help="lexical 关键词检索（匹配文件内容/路径/实体名）")
    sp.add_argument("--semantic", action="store_true", help="P1-C: semantic fallback 检索")
    sp.add_argument("--limit", type=int, default=50, help="限制返回结果数（默认 50）")
    sp.set_defaults(func=cmd_query)

    sp = sub.add_parser("sources", help="查询实体来源并校验（含精确版本）")
    sp.add_argument("owner", help="实体 ID：CURRENT / REPORT-001 / ORG-EXP017 / ...")
    sp.add_argument("--semantic", action="store_true", help="P1-C: 忽略该开关（closed table）")
    sp.set_defaults(func=cmd_sources)

    sp = sub.add_parser("trace", help="provenance 追踪链")
    sp.add_argument("entity", help="起点实体 ID")
    sp.add_argument("--semantic", action="store_true", help="P1-C: 忽略该开关（closed table）")
    sp.set_defaults(func=cmd_trace)

    sp = sub.add_parser("history", help="历史报告 / 结论演化")
    sp.add_argument("--semantic", action="store_true", help="P1-C: 忽略该开关（closed table）")
    sp.set_defaults(func=cmd_history)

    sp = sub.add_parser("impact", help="逆向依赖与下游影响链分析（方案 §19）")
    sp.add_argument("entity", help="目标实体 ID 或路径（如 R051, ORG-EXP017, H003@v1）")
    sp.add_argument("--change-type", help="可选：预演语义变更类型（如 contract_tightened），计算推演影响分类")
    sp.add_argument("--semantic", action="store_true", help="P1-C: 忽略该开关（closed table）")
    sp.set_defaults(func=cmd_impact)

    sp = sub.add_parser("reconcile", help="完整性检测（断链/hash/漂移/缺失/orphan）")
    sp.set_defaults(func=cmd_reconcile)

    # ---- P1-A Evented Freeze ----
    sp = sub.add_parser("freeze-report", help="P1-A: 冻结 CURRENT → REPORT-NNN + Event + receipt（单一事务）")
    sp.add_argument("--idempotency-key", dest="idempotency_key", required=True)
    sp.add_argument("--actor", required=True)
    sp.add_argument("--authorization-ref", dest="authorization_ref", required=True)
    sp.add_argument("--reason-refs", dest="reason_refs", default="")
    sp.add_argument("--crash-after", dest="crash_after", default=None,
                    help="故障注入点（测试用）：after-plan/after-staging/after-report-install/...")
    sp.set_defaults(func=cmd_freeze_report)

    sp = sub.add_parser("tx-reconcile", help="P1-A: 崩溃恢复 / 半提交判定 / canonical 重建")
    sp.set_defaults(func=cmd_tx_reconcile)

    sp = sub.add_parser("tx-status", help="P1-A: 列出事务目录状态（plan/state/marker/staging）")
    sp.set_defaults(func=cmd_tx_status)

    sp = sub.add_parser("tx-reset-guard", help="P1-A: 检查 .index reset 是否被 unresolved WAL 阻止")
    sp.set_defaults(func=cmd_tx_reset_guard)

    # ---- P1-B Definition Evolution ----
    sp = sub.add_parser("revise-definition", help="P1-B: 定义版本修订 H003@v1→v2 + DefinitionRevised Event + APPROVED pointer（单一事务）")
    sp.add_argument("--idempotency-key", dest="idempotency_key", required=True)
    sp.add_argument("--definition", required=True)
    sp.add_argument("--expected-previous", dest="expected_previous", required=True)
    sp.add_argument("--definition-input", dest="definition_input", required=True,
                    help="definition semantic payload 文件（body-only，禁止含 reserved identity key）")
    sp.add_argument("--change-type", dest="change_type", default="",
                    help="逗号分隔的受控 enum（scope_change/population_change/...）")
    sp.add_argument("--actor", required=True)
    sp.add_argument("--authorization-ref", dest="authorization_ref", required=True)
    sp.add_argument("--approval-ref", dest="approval_ref", required=True)
    sp.add_argument("--reason-refs", dest="reason_refs", default="")
    sp.add_argument("--crash-after", dest="crash_after", default=None,
                    help="故障注入点（测试用）：after-plan/after-staging/after-definition-install/...")
    sp.set_defaults(func=cmd_revise_definition)

    # ---- 方案 §12: 导航层 INDEX.md 生成 ----
    sp = sub.add_parser("generate-index", help="自动生成/刷新全局导航 index/INDEX.md（方案 §12）")
    sp.set_defaults(func=cmd_generate_index)

    # ---- 方案 §14: Raw Ingest Hook ----
    sp = sub.add_parser("ingest-raw", help="原始实验数据导入 Hook（分配 ID、计算 hash、写 manifest、刷索引，方案 §14）")
    sp.add_argument("--experiment", required=True, help="所属实验 ID（如 EXP-017）")
    sp.add_argument("--source", required=True, help="原始数据目录或文件路径")
    sp.add_argument("--run-id", dest="run_id", default=None, help="可选：显式指定 Run ID（缺省自动递增分配 Rxxx）")
    sp.add_argument("--experiment-ref", dest="experiment_ref", default=None, help="可选：引用的实验规格版本（如 EXP-017@v1）")
    sp.add_argument("--status", default="completed", help="运行状态（completed/invalid/failed）")
    sp.add_argument("--model", default=None, help="可选：模型名称")
    sp.add_argument("--context-length", dest="context_length", default=None, help="可选：上下文长度")
    sp.add_argument("--seed", type=int, default=None, help="可选：随机种子")
    sp.add_argument("--reason", default=None, help="可选：invalid 时的原因说明")
    sp.set_defaults(func=cmd_ingest_raw)

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
    if getattr(args, "semantic", False):
        from .semantic import build_semantic_index
        return build_semantic_index(args.root, args.db)
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


# ---- P1-A 命令 ----------------

def cmd_freeze_report(args):
    from .tx.freeze import freeze_report
    reason_refs = [r for r in args.reason_refs.split(",") if r] if args.reason_refs else []
    return freeze_report(
        root=args.root, db_path=args.db,
        idempotency_key=args.idempotency_key,
        actor=args.actor, authorization_ref=args.authorization_ref,
        reason_refs=reason_refs, crash_after=args.crash_after,
    )


def cmd_tx_reconcile(args):
    from .tx.recover import reconcile_tx
    return reconcile_tx(args.root, args.db)


def cmd_tx_status(args):
    import os as _os
    txdir = _os.path.join(args.root, ".index", "tx")
    entries = []
    if _os.path.isdir(txdir):
        for name in sorted(_os.listdir(txdir)):
            full = _os.path.join(txdir, name)
            entries.append({"name": name, "size": _os.path.getsize(full)})
    return {"query_id": "tx-status", "query_type": "tx-status", "status": "success",
            "authority": "derived", "source_watermark": {},
            "results": [{"tx_dir": txdir, "entries": entries}],
            "warnings": [], "errors": [], "error_semantic": None}


def cmd_tx_reset_guard(args):
    from .tx.recover import reset_index_guard
    return reset_index_guard(args.root, args.db)


# ---- P1-B 命令 ----------------

def cmd_revise_definition(args):
    from .tx.revise import revise_definition
    from .mini_yaml import load_file
    if not os.path.exists(args.definition_input):
        return {"status": "error", "error_semantic": "SOURCE_MISSING",
                "detail": f"definition-input 文件不存在: {args.definition_input}"}
    try:
        body = load_file(args.definition_input, strict=True) or {}
    except Exception as e:
        return {"status": "error", "error_semantic": "HASH_MISMATCH",
                "detail": f"definition-input 解析失败: {e}"}
    if not isinstance(body, dict):
        return {"status": "error", "error_semantic": "HASH_MISMATCH",
                "detail": "definition-input 必须是 YAML 映射"}
    change_types = [c.strip() for c in args.change_type.split(",") if c.strip()] if args.change_type else []
    reason_refs = [r for r in args.reason_refs.split(",") if r] if args.reason_refs else []
    return revise_definition(
        root=args.root, db_path=args.db,
        idempotency_key=args.idempotency_key,
        definition=args.definition,
        expected_previous=args.expected_previous,
        definition_input=body,
        change_type=change_types,
        actor=args.actor, authorization_ref=args.authorization_ref,
        approval_ref=args.approval_ref, reason_refs=reason_refs,
        crash_after=args.crash_after,
    )


def cmd_generate_index(args):
    import uuid
    from .navigator import generate_index_md
    content = generate_index_md(args.root, args.db, write_file=True)
    return {
        "query_id": uuid.uuid4().hex[:12],
        "query_type": "status",
        "status": "success",
        "authority": "derived",
        "results": [{"path": "index/INDEX.md", "bytes": len(content.encode("utf-8"))}],
        "warnings": [],
        "errors": [],
        "error_semantic": None,
    }


def cmd_ingest_raw(args):
    from .ingest import ingest_raw
    return ingest_raw(
        args.root,
        experiment=args.experiment,
        source_path=args.source,
        run_id=args.run_id,
        experiment_ref=args.experiment_ref,
        status=args.status,
        model=args.model,
        context_length=args.context_length,
        seed=args.seed,
        invalid_reason=args.reason,
        db_path=args.db,
    )


if __name__ == "__main__":
    sys.exit(main())
