#!/usr/bin/env python3
"""P1-C Semantic Retrieval 验收测试（P1-C-Contract rev12 冻结）。

运行（零第三方依赖）：
  python3 researchctl/tests/test_p1c.py

覆盖：V1–V23 全部场景（测试矩阵 §6）与退出条件（§7）。
所有故障注入在临时 fixture 副本中进行；fixture 原始工作树不变。
退出码：0=全部通过，1=有失败。
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE = os.path.join(ROOT, "fixture")

PASS = 0
FAIL = 0
FAILURES = []


def check(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAIL += 1
        FAILURES.append(name)
        print(f"  FAIL {name}" + (f"  ({detail})" if detail else ""))


def make_copy():
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "f")
    shutil.copytree(FIXTURE, dst, symlinks=False,
                    ignore=shutil.ignore_patterns(".index", "*.sqlite", "__pycache__"))
    return tmp, dst


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)


def run_cmd(*args, root):
    cmd = [sys.executable, "-m", "researchctl", "--root", root] + list(args)
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"status": "error", "cli_returncode": p.returncode,
                "stderr": p.stderr[:500], "stdout": p.stdout[:500]}


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def snapshot_hashes(root):
    hashes = {}
    for dirpath, _, fnames in os.walk(root):
        for fn in sorted(fnames):
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            if rel.startswith(".index") or rel.startswith(".researchctl") or rel.startswith(".git"):
                continue
            hashes[rel] = file_hash(os.path.join(dirpath, fn))
    return hashes


def main():
    print("=" * 62)
    print("P1-C Semantic Retrieval 验收测试 (V1–V23)")
    print("=" * 62)

    # -------------------------------------------------------------------------
    # [V1] clean-state 首次构建
    # fixture 中 semantic 三表全部不存在 → index --semantic → success → 查询已知主题词
    # -------------------------------------------------------------------------
    print("\n[V1] clean-state 首次构建")
    tmp, dst = make_copy()
    try:
        # P0 index
        run_cmd("index", root=dst)
        db_path = os.path.join(dst, ".index/research.sqlite")
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        check("V1-1 clean fixture 无 semantic 表",
              not any(t in tables for t in ('terms', 'ngrams', 'semantic_metadata')))

        res = run_cmd("index", "--semantic", root=dst)
        check("V1-2 index --semantic 成功", res.get("status") == "success", str(res.get("status")))
        check("V1-3 authority=derived", res.get("authority") == "derived")

        q = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        check("V1-4 query --semantic 成功", q.get("status") == "success")
        check("V1-5 返回结果非空", len(q.get("results") or []) > 0)
        top_score = q["results"][0].get("score")
        check("V1-6 top score ∈ [0, 1]", 0.0 <= top_score <= 1.0, f"score={top_score}")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V2] 未建索引即 --semantic
    # SEMANTIC_NOT_INDEXED，status="fail_closed"，results=null
    # -------------------------------------------------------------------------
    print("\n[V2] 未建索引即 --semantic")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)  # 仅建 P0
        q = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        check("V2-1 status=fail_closed", q.get("status") == "fail_closed")
        check("V2-2 results=null", q.get("results") is None)
        check("V2-3 error_semantic=SEMANTIC_NOT_INDEXED", q.get("error_semantic") == "SEMANTIC_NOT_INDEXED")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V3] --entity 带 --semantic
    # 忽略 semantic，走结构化路径，authority 不变
    # -------------------------------------------------------------------------
    print("\n[V3] --entity 带 --semantic")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        q = run_cmd("query", "--entity", "EXP-017", "--semantic", root=dst)
        check("V3-1 走结构化路径成功", q.get("status") == "success")
        check("V3-2 无 retrieval_mode 字段（非 semantic 查询）", "retrieval_mode" not in q)
        check("V3-3 authority=derived", q.get("authority") == "derived")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V4] 拼写/断词偏差（n-gram 召回）
    # -------------------------------------------------------------------------
    print("\n[V4] 拼写/断词偏差（n-gram 召回）")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        # "executio" 拼写偏差（少了个 n）
        q = run_cmd("query", "--text", "executio", "--semantic", root=dst)
        check("V4-1 拼写偏差查询成功", q.get("status") == "success")
        hit_paths = [r["path"] for r in q.get("results") or []]
        check("V4-2 n-gram 召回包含 execution 的文档",
              any("execution.log" in p or "manifest.yaml" in p for p in hit_paths))
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V5] 全低相关查询
    # 结果返回 + SEMANTIC_LOW_CONFIDENCE warning
    # -------------------------------------------------------------------------
    print("\n[V5] 全低相关查询")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        # 查询一个低相关词（仅产生微小 n-gram 命中，所有 score < 0.2）
        q = run_cmd("query", "--text", "xyzabcdefghijk execution", "--semantic", root=dst)
        check("V5-1 查询成功返回", q.get("status") == "success")
        check("V5-2 产生 SEMANTIC_LOW_CONFIDENCE warning",
              any(w.get("code") == "SEMANTIC_LOW_CONFIDENCE" for w in q.get("warnings") or []))
        if q.get("results"):
            check("V5-3 所有候选 score < 0.2", all(r["score"] < 0.2 for r in q["results"]))
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V6] 删 .index/ 后重建
    # 排名与 tie order 完全一致（幂等）
    # -------------------------------------------------------------------------
    print("\n[V6] 删 .index/ 后重建（幂等性）")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        q1 = run_cmd("query", "--text", "temperature", "--semantic", root=dst)
        payload1 = [(r["entity_id"], r["versioned_ref"], r["path"], round(r["score"] * 1e9)) for r in q1.get("results") or []]

        shutil.rmtree(os.path.join(dst, ".index"))
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        q2 = run_cmd("query", "--text", "temperature", "--semantic", root=dst)
        payload2 = [(r["entity_id"], r["versioned_ref"], r["path"], round(r["score"] * 1e9)) for r in q2.get("results") or []]

        check("V6-1 重建后 ranked semantic payload 逐项完全一致", payload1 == payload2, f"count={len(payload1)}")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V7] 空/纯停用词查询
    # SEMANTIC_EMPTY_QUERY 语义：空 results，success，无 error/warning
    # -------------------------------------------------------------------------
    print("\n[V7] 空/纯停用词查询")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        # 纯停用词
        q = run_cmd("query", "--text", "the in of to and", "--semantic", root=dst)
        check("V7-1 status=success", q.get("status") == "success")
        check("V7-2 results=[]", q.get("results") == [])
        check("V7-3 无 warning", len(q.get("warnings") or []) == 0)
        check("V7-4 无 error", len(q.get("errors") or []) == 0)
        check("V7-5 error_semantic=null", q.get("error_semantic") is None)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V8] canonical hash assertion
    # index --semantic 前后对全量 canonical 文件逐文件 hash 完全不变
    # -------------------------------------------------------------------------
    print("\n[V8] canonical hash assertion（零写入）")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        before = snapshot_hashes(dst)
        run_cmd("index", "--semantic", root=dst)
        after = snapshot_hashes(dst)
        check("V8-1 canonical 文件集合不变", set(before.keys()) == set(after.keys()))
        check("V8-2 逐文件 hash 严格相等", before == after)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V9] stale 洗白反例
    # 改 canonical → 不 reindex → index --semantic → 构建被拒（INDEX_STALE）
    # -------------------------------------------------------------------------
    print("\n[V9] stale 洗白反例")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        # 修改 canonical 文件
        curr = os.path.join(dst, "reports/CURRENT.md")
        with open(curr, "a") as f:
            f.write("\nnew line to cause drift\n")

        res = run_cmd("index", "--semantic", root=dst)
        check("V9-1 构建被拒 fail_closed", res.get("status") == "fail_closed")
        check("V9-2 错误码为 P0 的 INDEX_STALE", res.get("error_semantic") == "INDEX_STALE")
        check("V9-3 results=null", res.get("results") is None)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V10] 查询期 stale
    # 建好 semantic 索引后改 canonical 并 reindex P0 → query --semantic 报 SEMANTIC_INDEX_STALE
    # -------------------------------------------------------------------------
    print("\n[V10] 查询期 stale")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        # 修改 canonical 并仅 reindex P0
        curr = os.path.join(dst, "reports/CURRENT.md")
        with open(curr, "a") as f:
            f.write("\nmodification for stale test\n")
        run_cmd("index", root=dst)  # 仅 P0 reindex

        q = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        check("V10-1 query fail_closed", q.get("status") == "fail_closed")
        check("V10-2 error_semantic=SEMANTIC_INDEX_STALE", q.get("error_semantic") == "SEMANTIC_INDEX_STALE")
        check("V10-3 results=null", q.get("results") is None)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V11] partial rebuild 不可见
    # 构建中途注入失败（模拟 crash）→ ROLLBACK；查询只见完整旧 generation
    # -------------------------------------------------------------------------
    print("\n[V11] partial rebuild 不可见")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        q_before = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        top_before = q_before["results"][0]["entity_id"]

        # 使用 build_semantic_index 的 crash_after 注入失败
        from researchctl.semantic import build_semantic_index
        crashed = False
        try:
            build_semantic_index(dst, crash_after="terms_and_ngrams")
        except RuntimeError:
            crashed = True
        check("V11-1 模拟构建中途 crash 生效", crashed)

        # 再次查询，只见完整旧代，绝不暴露半代
        q_after = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        check("V11-2 crash 后查询仍然成功（回滚到旧代）", q_after.get("status") == "success")
        check("V11-3 top 实体与 crash 前一致", q_after["results"][0]["entity_id"] == top_before)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V12] 删除文档无残留
    # 删一个文档 → 重建 → 查其独有 n-gram 不再命中
    # -------------------------------------------------------------------------
    print("\n[V12] 删除文档无残留")
    tmp, dst = make_copy()
    try:
        # 新增一个具有独有特征词的文档
        doc_path = os.path.join(dst, "reports/history/REPORT-999.md")
        with open(doc_path, "w") as f:
            f.write("# Unique doc with token zzzunique123\n")
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)

        q1 = run_cmd("query", "--text", "zzzunique123", "--semantic", root=dst)
        check("V12-1 新文档可被查到", any("REPORT-999" in r["path"] for r in q1.get("results") or []))

        # 删除该文档并重建
        os.remove(doc_path)
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)

        q2 = run_cmd("query", "--text", "zzzunique123", "--semantic", root=dst)
        check("V12-2 删除并重建后不再命中", not any("REPORT-999" in r["path"] for r in q2.get("results") or []))

        # 检查 terms 和 ngrams 表无残留行
        conn = sqlite3.connect(os.path.join(dst, ".index/research.sqlite"))
        cnt_t = conn.execute("SELECT COUNT(*) FROM terms WHERE doc_id='REPORT-999'").fetchone()[0]
        cnt_ng = conn.execute("SELECT COUNT(*) FROM ngrams WHERE doc_id='REPORT-999'").fetchone()[0]
        conn.close()
        check("V12-3 terms 表无残留行", cnt_t == 0)
        check("V12-4 ngrams 表无残留行", cnt_ng == 0)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V13] determinism
    # 同一 corpus 重复构建 + 重复查询 → ranked semantic payload 逐字节/逐值一致
    # -------------------------------------------------------------------------
    print("\n[V13] determinism（确定性 payload）")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        q1 = run_cmd("query", "--text", "temperature measurement", "--semantic", root=dst)
        p1 = [(r["entity_id"], r["versioned_ref"], r["path"], round(r["score"] * 1e9)) for r in q1.get("results") or []]

        run_cmd("index", "--semantic", root=dst)
        q2 = run_cmd("query", "--text", "temperature measurement", "--semantic", root=dst)
        p2 = [(r["entity_id"], r["versioned_ref"], r["path"], round(r["score"] * 1e9)) for r in q2.get("results") or []]

        check("V13-1 ranked semantic payload 逐字节/逐值完全一致", p1 == p2, f"len={len(p1)}")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V14] tokenizer determinism
    # Unicode NFKC / 中文 bigram / 大小写 / 停用词
    # -------------------------------------------------------------------------
    print("\n[V14] tokenizer determinism")
    from researchctl.semantic import tokenize
    # 全角转半角、大写转小写、中文 bigram、停用词过滤
    t1 = tokenize("Ｈｅｌｌｏ，世界！超长程实验在进行中。")
    t2 = tokenize("Ｈｅｌｌｏ，世界！超长程实验在进行中。")
    check("V14-1 tokenizer 输出确定一致", t1 == t2)
    check("V14-2 包含归一化 hello", "hello" in t1)
    check("V14-3 包含中文 bigram '世界'", "世界" in t1)
    check("V14-4 包含中文 bigram '超长'", "超长" in t1)
    check("V14-5 停用词 '在' 被过滤", "在" not in t1)

    # -------------------------------------------------------------------------
    # [V15] corrupt index (V15a–V15h)
    # 覆盖所有结构破坏维度 → 全部 SEMANTIC_INDEX_CORRUPT, fail_closed, results=null
    # -------------------------------------------------------------------------
    print("\n[V15] corrupt index (V15a–V15h)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        db_path = os.path.join(dst, ".index/research.sqlite")

        # 辅助测试破坏函数
        def test_corrupt_scenario(name, mutate_sql):
            # 重建基线
            run_cmd("index", "--semantic", root=dst)
            conn = sqlite3.connect(db_path)
            mutate_sql(conn)
            conn.close()
            q = run_cmd("query", "--text", "execution", "--semantic", root=dst)
            ok = (q.get("status") == "fail_closed" and
                  q.get("results") is None and
                  q.get("error_semantic") == "SEMANTIC_INDEX_CORRUPT")
            check(name, ok, f"status={q.get('status')}, code={q.get('error_semantic')}")

        # V15a: 缺列
        def corrupt_missing_col(c):
            c.execute("DROP TABLE terms")
            c.execute("CREATE TABLE terms (term TEXT NOT NULL, doc_id TEXT NOT NULL, PRIMARY KEY (term, doc_id))")
        test_corrupt_scenario("V15a 缺列 (terms 缺 tf)", corrupt_missing_col)

        # V15b: 多列
        def corrupt_extra_col(c):
            c.execute("DROP TABLE ngrams")
            c.execute("CREATE TABLE ngrams (ngram TEXT NOT NULL, doc_id TEXT NOT NULL, extra TEXT, PRIMARY KEY (ngram, doc_id))")
        test_corrupt_scenario("V15b 多列 (ngrams 多 extra)", corrupt_extra_col)

        # V15c: declared type 不符
        def corrupt_type_mismatch(c):
            c.execute("DROP TABLE ngrams")
            c.execute("CREATE TABLE ngrams (ngram BLOB NOT NULL, doc_id TEXT NOT NULL, PRIMARY KEY (ngram, doc_id))")
        test_corrupt_scenario("V15c declared type 不符 (ngram BLOB)", corrupt_type_mismatch)

        # V15d: NOT NULL 不符
        def corrupt_notnull(c):
            c.execute("DROP TABLE terms")
            c.execute("CREATE TABLE terms (term TEXT, doc_id TEXT NOT NULL, tf REAL NOT NULL, PRIMARY KEY (term, doc_id))")
        test_corrupt_scenario("V15d NOT NULL 不符 (term nullable)", corrupt_notnull)

        # V15e: PRIMARY KEY 不符
        def corrupt_pk(c):
            c.execute("DROP TABLE terms")
            c.execute("CREATE TABLE terms (term TEXT NOT NULL PRIMARY KEY, doc_id TEXT NOT NULL, tf REAL NOT NULL)")
        test_corrupt_scenario("V15e PRIMARY KEY 不符 (terms 仅 term 为 PK)", corrupt_pk)

        # V15f: 空字符串字段
        def corrupt_empty_str(c):
            c.execute("INSERT INTO terms (term, doc_id, tf) VALUES ('', 'doc1', 1.0)")
        test_corrupt_scenario("V15f 空字符串字段 (term='')", corrupt_empty_str)

        # V15g: 缺失必含键
        def corrupt_missing_key(c):
            c.execute("DELETE FROM semantic_metadata WHERE key='build_complete'")
        test_corrupt_scenario("V15g 缺失必含键 (缺 build_complete)", corrupt_missing_key)

        # V15h: 存在额外键
        def corrupt_extra_key(c):
            c.execute("INSERT INTO semantic_metadata (key, value) VALUES ('extra_unapproved_key', '1')")
        test_corrupt_scenario("V15h 存在额外键", corrupt_extra_key)

        # 非法 tf (tf <= 0)
        def corrupt_illegal_tf(c):
            c.execute("UPDATE terms SET tf = -1.0 WHERE rowid = 1")
        test_corrupt_scenario("V15-tf 非法 tf (tf <= 0)", corrupt_illegal_tf)

        # 非文本类型行值 (插入 blob)
        def corrupt_blob_value(c):
            c.execute("INSERT INTO ngrams (ngram, doc_id) VALUES (X'DEADBEEF', 'doc1')")
        test_corrupt_scenario("V15-blob 非文本行值 (typeof!=text)", corrupt_blob_value)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V16] sources / trace / history 加 --semantic
    # 全部忽略 semantic（closed table）
    # -------------------------------------------------------------------------
    print("\n[V16] sources / trace / history 加 --semantic (closed table)")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)

        s = run_cmd("sources", "CURRENT", "--semantic", root=dst)
        check("V16-1 sources 忽略 --semantic", s.get("status") == "success" and "retrieval_mode" not in s)

        t = run_cmd("trace", "R051", "--semantic", root=dst)
        check("V16-2 trace 忽略 --semantic", t.get("status") in ("success", "warning") and "retrieval_mode" not in t)

        h = run_cmd("history", "--semantic", root=dst)
        check("V16-3 history 忽略 --semantic", h.get("status") == "success" and "retrieval_mode" not in h)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V17] 向后兼容：非 semantic 查询 envelope
    # 与 P0 完全一致，无新增字段出现
    # -------------------------------------------------------------------------
    print("\n[V17] 向后兼容（非 semantic 查询 envelope 干净）")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        q = run_cmd("query", "--text", "execution", root=dst)
        check("V17-1 查询成功", q.get("status") == "success")
        check("V17-2 无 retrieval_mode 字段", "retrieval_mode" not in q)
        check("V17-3 无 ranking_authority 字段", "ranking_authority" not in q)
        check("V17-4 watermark 无 semantic 字段", "semantic" not in q.get("source_watermark", {}))
        if q.get("results"):
            check("V17-5 ResultItem 无 score 字段", "score" not in q["results"][0])
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V18] score 边界
    # 全部 ∈ [0, 1]
    # -------------------------------------------------------------------------
    print("\n[V18] score 边界 (全部 ∈ [0, 1])")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        for term in ("temperature", "execution", "EXP-017", "analysis"):
            q = run_cmd("query", "--text", term, "--semantic", root=dst)
            for r in q.get("results") or []:
                sc = r["score"]
                check(f"V18 score ∈ [0, 1] for '{term}'", 0.0 <= sc <= 1.0, f"score={sc}")
                break
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V19] lexical 与 semantic authority 区分
    # -------------------------------------------------------------------------
    print("\n[V19] lexical 与 semantic authority 区分")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)
        q_lex = run_cmd("query", "--text", "execution", root=dst)
        q_sem = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        check("V19-1 lexical authority=derived", q_lex.get("authority") == "derived")
        check("V19-2 semantic authority=derived", q_sem.get("authority") == "derived")
        check("V19-3 semantic 含 ranking_authority=advisory", q_sem.get("ranking_authority") == "advisory")
        check("V19-4 semantic 含 retrieval_mode=semantic", q_sem.get("retrieval_mode") == "semantic")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V20] P0/P1-A/P1-B 回归
    # -------------------------------------------------------------------------
    print("\n[V20] P0/P1-A/P1-B 基线回归")
    p0b = subprocess.run([sys.executable, "researchctl/tests/test_p0b.py"], capture_output=True, text=True, cwd=ROOT)
    check("V20-1 test_p0b PASS", p0b.returncode == 0)

    p0c = subprocess.run([sys.executable, "researchctl/tests/test_p0c.py"], capture_output=True, text=True, cwd=ROOT)
    check("V20-2 test_p0c PASS", p0c.returncode == 0)

    p1a = subprocess.run([sys.executable, "researchctl/tests/test_p1a.py"], capture_output=True, text=True, cwd=ROOT)
    check("V20-3 test_p1a PASS", p1a.returncode == 0)

    p1b = subprocess.run([sys.executable, "researchctl/tests/test_p1b.py"], capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, PYTHONPATH="."))
    check("V20-4 test_p1b PASS", p1b.returncode == 0)

    # -------------------------------------------------------------------------
    # [V21] event frontier lag 反例
    # P0 materialize 到 EV-10，EV-11 canonical COMMITTED 但未 materialize → query 报 SEMANTIC_INDEX_STALE
    # -------------------------------------------------------------------------
    print("\n[V21] event frontier lag 反例")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)

        # 模拟 canonical event 提交但 P0 索引落后（未 materialize）
        # 创建一个有效的 committed Event EV-000001
        from researchctl.tx.freeze import freeze_report
        res = freeze_report(
            root=dst, db_path=os.path.join(dst, ".index/research.sqlite"),
            idempotency_key="v21-test-key", actor="text-agent",
            authorization_ref="AUTH-0001",
        )
        check("V21-1 freeze 产生 canonical event", res.get("status") == "success")

        # 人为把 P0 index_metadata.last_event_id 改旧（模拟 materialize lag）
        conn = sqlite3.connect(os.path.join(dst, ".index/research.sqlite"))
        conn.execute("UPDATE index_metadata SET value='' WHERE key='last_event_id'")
        conn.commit()
        conn.close()

        q = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        check("V21-2 query 检出 frontier lag fail_closed", q.get("status") == "fail_closed")
        check("V21-3 error_semantic=SEMANTIC_INDEX_STALE", q.get("error_semantic") == "SEMANTIC_INDEX_STALE")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V22] drift-only 反例
    # filesystem 未变，P0 reconcile 把 drift=true → query 报 SEMANTIC_INDEX_STALE
    # -------------------------------------------------------------------------
    print("\n[V22] drift-only 反例")
    tmp, dst = make_copy()
    try:
        run_cmd("index", root=dst)
        run_cmd("index", "--semantic", root=dst)

        # 人工在 P0 index_metadata 设置 drift=1
        conn = sqlite3.connect(os.path.join(dst, ".index/research.sqlite"))
        conn.execute("UPDATE index_metadata SET value='1' WHERE key='drift'")
        conn.commit()
        conn.close()

        q = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        check("V22-1 drift=true 导致 query fail_closed", q.get("status") == "fail_closed")
        check("V22-2 error_semantic=SEMANTIC_INDEX_STALE", q.get("error_semantic") == "SEMANTIC_INDEX_STALE")
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # [V23] no-event end-to-end
    # 无 committed Event 环境（P0 last_event_id 为 null 或 ""）→ index 存 "none" →
    # query base fresh 通过 → JSON envelope source_last_event_id 输出 null
    # -------------------------------------------------------------------------
    print("\n[V23] no-event end-to-end")
    tmp, dst = make_copy()
    try:
        # 全新环境，无任何 events
        run_cmd("index", root=dst)
        conn = sqlite3.connect(os.path.join(dst, ".index/research.sqlite"))
        p0_last_ev = conn.execute("SELECT value FROM index_metadata WHERE key='last_event_id'").fetchone()[0]
        check("V23-1 P0 SQLite last_event_id 为空串", p0_last_ev == "")

        res = run_cmd("index", "--semantic", root=dst)
        check("V23-2 index --semantic 成功", res.get("status") == "success")

        # 检查 SQLite semantic_metadata 存储值为 "none"
        sm_ev = conn.execute("SELECT value FROM semantic_metadata WHERE key='source_last_event_id'").fetchone()[0]
        check("V23-3 semantic_metadata 存储为 'none' 哨兵", sm_ev == "none")
        conn.close()

        q = run_cmd("query", "--text", "execution", "--semantic", root=dst)
        check("V23-4 query --semantic 成功返回", q.get("status") == "success")
        sem_wm = q.get("source_watermark", {}).get("semantic", {})
        check("V23-5 JSON envelope source_last_event_id 转换为 null", sem_wm.get("source_last_event_id") is None)
    finally:
        cleanup(tmp)

    # -------------------------------------------------------------------------
    # 汇总
    # -------------------------------------------------------------------------
    print("\n" + "=" * 62)
    print(f"结果: {PASS} PASS / {FAIL} FAIL")
    if FAIL:
        print(f"失败项: {FAILURES}")
        sys.exit(1)
    else:
        print("P1-C 全部测试通过！✅")
        sys.exit(0)


if __name__ == "__main__":
    main()
