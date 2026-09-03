"""
researchctl.semantic — P1-C Semantic Retrieval 模块
==================================================
依据 P1-C-Contract.md（已冻结 rev12，2026-09-03）。
零第三方依赖（仅 stdlib：sqlite3, hashlib, math, re, unicodedata, collections, uuid, time, os, sys）。
"""

import collections
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import time
import unicodedata
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from .hashing import file_hash
from .queries import _connect, current_fingerprint, get_watermark

# ---------------- 常量与冻结集合 ----------------

DEFAULT_DB = ".index/research.sqlite"
CORPUS_EXTENSIONS = frozenset([".md", ".yaml", ".yml", ".txt", ".csv", ".json", ".log"])

STOPWORDS = frozenset([
    "the", "a", "an", "of", "to", "in", "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "but", "if", "then", "than", "that", "this", "these", "those", "it", "its",
    "as", "at", "by", "for", "from", "on", "with", "without", "do", "does", "did", "not", "no",
    "yes", "can", "could", "will", "would", "should", "may", "might", "must", "have", "has", "had",
    "i", "you", "he", "she", "we", "they", "me", "him", "her", "us", "them", "your", "their",
    "my", "our", "what", "which", "who", "whom", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "only", "own", "same",
    "so", "too", "very", "s", "t", "just", "now",
    "的", "了", "和", "是", "在", "我", "有", "也", "就", "不", "人", "都", "一", "一个", "上",
])

FROZEN_TABLE_SCHEMAS = {
    "terms": {
        "columns": {
            "term": {"type": "TEXT", "notnull": 1, "pk": 1},
            "doc_id": {"type": "TEXT", "notnull": 1, "pk": 2},
            "tf": {"type": "REAL", "notnull": 1, "pk": 0},
        }
    },
    "ngrams": {
        "columns": {
            "ngram": {"type": "TEXT", "notnull": 1, "pk": 1},
            "doc_id": {"type": "TEXT", "notnull": 1, "pk": 2},
        }
    },
    "semantic_metadata": {
        "columns": {
            "key": {"type": "TEXT", "notnull": 1, "pk": 1},
            "value": {"type": "TEXT", "notnull": 0, "pk": 0},
        }
    },
}

REQUIRED_METADATA_KEYS = frozenset([
    "algorithm_version",
    "source_scan_fingerprint",
    "source_last_event_id",
    "source_index_built_at",
    "document_count",
    "build_complete",
])

RE_FINGERPRINT = re.compile(r"^sha256:[0-9a-f]{64}$")
RE_EVENT_ID = re.compile(r"^(?:EV-[0-9]{6}|none)$")
RE_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$")
RE_DOC_COUNT = re.compile(r"^(?:0|[1-9][0-9]*)$")


# ---------------- 辅助函数 ----------------

def _default_db(root: str) -> str:
    return os.path.join(root, DEFAULT_DB)


def normalize_event_id(x: Optional[str]) -> Optional[str]:
    """统一归一化函数（Sol rev11 P2-REV11-2 闭合）：
    null if (x is null or x == '' or x == 'none') else x
    """
    if x is None or x == "" or x == "none":
        return None
    return x


def max_committed_event_id(root: str) -> Optional[str]:
    """在 canonical events 中，按事件类型使用对应的 frozen receipt validator
    验证通过的 committed Event 的最大 event_id。若无任何 committed Event 返回 null。
    """
    try:
        from .tx.impact import _max_committed_event_id
        res = _max_committed_event_id(root)
        return res if res else None
    except Exception:
        return None


def base_index_fresh(root: str, db_path: Optional[str] = None) -> bool:
    """共享 base_index_fresh(root)（build 与 query 唯一共同前置，Sol rev3 P1 + rev11 P2-REV11-2 闭合）：
    base_index_fresh(root) iff:
      P0 index_metadata.index_complete == true
      AND P0 index_metadata.drift == false
      AND P0 index_metadata.scan_fingerprint == current_fingerprint(root)
      AND normalize_event_id(P0 index_metadata.last_event_id) ==
          max_event_id(valid canonical COMMITTED events)
    """
    actual_db = db_path or _default_db(root)
    if not os.path.isfile(actual_db):
        return False
    try:
        conn = _connect(actual_db)
        try:
            wm = get_watermark(conn)
            if not wm.get("index_complete"):
                return False
            curr_fp = current_fingerprint(root)
            if wm.get("drift") or (curr_fp != wm.get("scan_fingerprint")):
                return False
            p0_last_ev = normalize_event_id(wm.get("last_event_id"))
            max_ev = max_committed_event_id(root)
            if p0_last_ev != max_ev:
                return False
            return True
        finally:
            conn.close()
    except Exception:
        return False


def get_semantic_corpus(root: str, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """semantic_corpus(doc) 唯一 predicate（Sol rev4 P2-1 闭合）：
    doc ∈ P0 documents 表
    AND path 后缀 ∈ 冻结 allowlist (.md, .yaml, .yml, .txt, .csv, .json, .log)
    AND canonical bytes strict UTF-8 decode 成功
    """
    rows = conn.execute("SELECT id, doc_type, path, version, content_hash, git_commit, status FROM documents").fetchall()
    corpus = []
    for r in rows:
        doc_id, doc_type, doc_path, version, content_hash, git_commit, status = r
        if not doc_path:
            continue
        ext = os.path.splitext(doc_path)[1].lower()
        if ext not in CORPUS_EXTENSIONS:
            continue
        full_path = os.path.join(root, doc_path)
        if not os.path.isfile(full_path):
            continue
        try:
            with open(full_path, "rb") as f:
                raw_bytes = f.read()
            # strict UTF-8 decode
            content = raw_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        corpus.append({
            "id": doc_id,
            "doc_type": doc_type,
            "path": doc_path,
            "version": version,
            "content_hash": content_hash,
            "git_commit": git_commit,
            "status": status,
            "content": content,
        })
    return corpus


# ---------------- 确定性算法：Tokenizer & N-grams ----------------

def tokenize(text: str) -> List[str]:
    """tokenize(text) 步骤（保留重复，保留原始顺序）：
    1. Unicode NFKC 归一化
    2. 转小写（ASCII）
    3. 切分：按 [^a-z0-9_\u4e00-\u9fff]+ 切
    4. CJK 段：对连续 CJK 串生成全部相邻 2-char bigram（如 "长上下文" → 长上, 上下, 下文）
    5. 非 CJK token：长度 < 2 者丢弃
    6. 停用词过滤（精确匹配，大小写已归一）
    7. 输出 token sequence（保留重复，保留原始顺序）
    """
    if not text:
        return []
    norm = unicodedata.normalize("NFKC", text).lower()
    chunks = re.split(r"[^a-z0-9_\u4e00-\u9fff]+", norm)
    tokens: List[str] = []
    cjk_re = re.compile(r"^[\u4e00-\u9fff]+$")
    for chunk in chunks:
        if not chunk:
            continue
        sub_segments = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9_]+", chunk)
        for seg in sub_segments:
            if cjk_re.match(seg):
                if len(seg) >= 2:
                    for i in range(len(seg) - 1):
                        bg = seg[i:i+2]
                        if bg not in STOPWORDS:
                            tokens.append(bg)
            else:
                if len(seg) >= 2:
                    if seg not in STOPWORDS:
                        tokens.append(seg)
    return tokens


def query_unique_terms(tokens: List[str]) -> List[str]:
    """对 tokenize(text) 结果按首次出现顺序去重，用于 cosine 的 numerator 枚举。"""
    return list(dict.fromkeys(tokens))


def generate_ngrams(text: str) -> Set[str]:
    """generate_ngrams(text): document 与 query 共享的唯一函数（Sol rev2 P2-3 + rev3 P2-2 闭合）：
    1. 对原始文本（不经 tokenizer 变换）做 NFKC 归一化 + ASCII lowercase
    2. 按 [^a-z0-9_\u4e00-\u9fff]+ 切分
    3. 每个连续 CJK 串（长度 >= 2）：生成全部相邻 character 2-gram 与 3-gram
    4. 每个非 CJK token（长度 >= 2）：生成全部相邻 character 2-gram 与 3-gram
    5. 去重：同一 ngram 多次出现只保留一次
    6. 输出：去重后的 ngram 集合
    """
    if not text:
        return set()
    norm = unicodedata.normalize("NFKC", text).lower()
    chunks = re.split(r"[^a-z0-9_\u4e00-\u9fff]+", norm)
    ngrams: Set[str] = set()
    for chunk in chunks:
        if not chunk:
            continue
        sub_segments = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9_]+", chunk)
        for seg in sub_segments:
            if len(seg) >= 2:
                for i in range(len(seg) - 1):
                    ngrams.add(seg[i:i+2])
            if len(seg) >= 3:
                for i in range(len(seg) - 2):
                    ngrams.add(seg[i:i+3])
    return ngrams


# ---------------- 结构与 Schema 校验器 ----------------

def validate_schema_only(conn: sqlite3.Connection) -> Tuple[bool, str]:
    """schema-only 前置校验（Sol rev8 P1 + rev9 P2-NEW-2 + rev11 P2-REV11-1 闭合）：
    检查已有三表 schema 声明是否与 §2.4 冻结 schema 完全兼容：
    terms / ngrams / semantic_metadata 每张表均要求列集合精确相等，且每一列的
    name / declared type / NOT NULL / PRIMARY KEY 与冻结 DDL 精确一致；
    不允许额外列、缺失列或任何上述属性差异；不检查数据行值/metadata 内容。
    """
    try:
        for tbl, expected in FROZEN_TABLE_SCHEMAS.items():
            info = conn.execute(f"PRAGMA table_info({tbl})").fetchall()
            if not info:
                return False, f"table {tbl} does not exist"
            cols = {row[1]: {"type": row[2].upper(), "notnull": row[3], "pk": row[5]} for row in info}
            exp_cols = expected["columns"]
            if set(cols.keys()) != set(exp_cols.keys()):
                return False, f"table {tbl} column set mismatch: got {set(cols.keys())}, expected {set(exp_cols.keys())}"
            for cname, exp_attr in exp_cols.items():
                act_attr = cols[cname]
                if act_attr["type"] != exp_attr["type"]:
                    return False, f"table {tbl}.{cname} type mismatch: got {act_attr['type']}, expected {exp_attr['type']}"
                if act_attr["notnull"] != exp_attr["notnull"]:
                    return False, f"table {tbl}.{cname} notnull mismatch: got {act_attr['notnull']}, expected {exp_attr['notnull']}"
                if act_attr["pk"] != exp_attr["pk"]:
                    return False, f"table {tbl}.{cname} pk mismatch: got {act_attr['pk']}, expected {exp_attr['pk']}"
        return True, ""
    except Exception as e:
        return False, f"schema validation error: {e}"


def validate_semantic_generation_structure(conn: sqlite3.Connection) -> Tuple[bool, str]:
    """共享结构校验器（Sol rev7 P2-4 + rev8 P1 + rev10 P2-REV10-1/4 + rev11 P2-REV11-1/P3-REV11-1 闭合）：
    query 侧必调，build 侧 post-write 调用。
    任一失败统一映射 SEMANTIC_INDEX_CORRUPT。
    """
    try:
        # 1. 检查三张表是否存在
        master_tables = set(r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('terms', 'ngrams', 'semantic_metadata')"
        ).fetchall())
        if len(master_tables) != 3:
            return False, f"missing semantic tables: {set(FROZEN_TABLE_SCHEMAS.keys()) - master_tables}"

        # 2. schema 强校验
        ok, reason = validate_schema_only(conn)
        if not ok:
            return False, reason

        # 3. semantic_metadata 键集合与文法校验
        meta_rows = conn.execute("SELECT key, value FROM semantic_metadata").fetchall()
        meta_keys = set()
        for k, v in meta_rows:
            # key/value runtime type text
            t_k = conn.execute("SELECT typeof(?)", (k,)).fetchone()[0]
            t_v = conn.execute("SELECT typeof(?)", (v,)).fetchone()[0]
            if t_k != "text" or len(str(k)) == 0:
                return False, f"semantic_metadata invalid key type or empty: {k!r}"
            if t_v != "text":
                return False, f"semantic_metadata value for key {k!r} is not text: typeof={t_v}"
            meta_keys.add(k)

        if meta_keys != REQUIRED_METADATA_KEYS:
            return False, f"semantic_metadata keys mismatch: got {meta_keys}, expected {REQUIRED_METADATA_KEYS}"

        meta_dict = dict(meta_rows)
        # algorithm_version
        if meta_dict["algorithm_version"] != "semantic-tfidf/v1":
            return False, f"algorithm_version mismatch: {meta_dict['algorithm_version']!r}"
        # source_scan_fingerprint
        if not RE_FINGERPRINT.fullmatch(meta_dict["source_scan_fingerprint"]):
            return False, f"source_scan_fingerprint malformed: {meta_dict['source_scan_fingerprint']!r}"
        # source_last_event_id
        if not RE_EVENT_ID.fullmatch(meta_dict["source_last_event_id"]):
            return False, f"source_last_event_id malformed: {meta_dict['source_last_event_id']!r}"
        # source_index_built_at
        if not RE_TIMESTAMP.fullmatch(meta_dict["source_index_built_at"]):
            return False, f"source_index_built_at malformed: {meta_dict['source_index_built_at']!r}"
        # document_count
        if not RE_DOC_COUNT.fullmatch(meta_dict["document_count"]):
            return False, f"document_count malformed: {meta_dict['document_count']!r}"
        # build_complete
        if meta_dict["build_complete"] != "1":
            return False, f"build_complete is not '1': {meta_dict['build_complete']!r}"

        # 4. terms 行值类型与重复校验
        # terms 表每一行：typeof(term) == 'text' ∧ length(term) > 0, typeof(doc_id) == 'text' ∧ length(doc_id) > 0,
        # typeof(tf) ∈ {"integer","real"} ∧ math.isfinite(tf) ∧ tf > 0
        bad_terms_type = conn.execute(
            "SELECT term, doc_id, tf FROM terms "
            "WHERE typeof(term) != 'text' OR length(term) == 0 "
            "   OR typeof(doc_id) != 'text' OR length(doc_id) == 0 "
            "   OR typeof(tf) NOT IN ('integer', 'real') OR tf <= 0 LIMIT 1"
        ).fetchone()
        if bad_terms_type:
            return False, f"terms table contains illegal row value: {bad_terms_type!r}"

        # 校验 tf 的 isfinite
        for (tf_val,) in conn.execute("SELECT tf FROM terms").fetchall():
            if not math.isfinite(tf_val):
                return False, f"terms table contains non-finite tf: {tf_val!r}"

        # 重复 terms
        dup_terms = conn.execute(
            "SELECT term, doc_id, COUNT(*) FROM terms GROUP BY term, doc_id HAVING COUNT(*) > 1 LIMIT 1"
        ).fetchone()
        if dup_terms:
            return False, f"duplicate (term, doc_id) in terms: {dup_terms!r}"

        # 5. ngrams 行值类型与重复校验
        # ngrams 表每一行：typeof(ngram) == 'text' ∧ length(ngram) > 0, typeof(doc_id) == 'text' ∧ length(doc_id) > 0
        bad_ngrams_type = conn.execute(
            "SELECT ngram, doc_id FROM ngrams "
            "WHERE typeof(ngram) != 'text' OR length(ngram) == 0 "
            "   OR typeof(doc_id) != 'text' OR length(doc_id) == 0 LIMIT 1"
        ).fetchone()
        if bad_ngrams_type:
            return False, f"ngrams table contains illegal row value: {bad_ngrams_type!r}"

        dup_ngrams = conn.execute(
            "SELECT ngram, doc_id, COUNT(*) FROM ngrams GROUP BY ngram, doc_id HAVING COUNT(*) > 1 LIMIT 1"
        ).fetchone()
        if dup_ngrams:
            return False, f"duplicate (ngram, doc_id) in ngrams: {dup_ngrams!r}"

        return True, ""
    except Exception as e:
        return False, f"structural validation exception: {e}"


def validate_generation_corpus_invariants(root: str, conn: sqlite3.Connection) -> Tuple[bool, str]:
    """仅当 generation fresh 后才校验（Sol rev6 P2-1/P2-4 闭合）：
    - document_count == |current semantic_corpus|
    - 每一 terms.doc_id ∈ current semantic_corpus
    - 每一 ngrams.doc_id ∈ current semantic_corpus
    任一不一致 → SEMANTIC_INDEX_CORRUPT
    """
    try:
        corpus = get_semantic_corpus(root, conn)
        corpus_ids = set(doc["id"] for doc in corpus)
        meta_count_str = conn.execute("SELECT value FROM semantic_metadata WHERE key='document_count'").fetchone()
        if not meta_count_str:
            return False, "document_count missing in metadata"
        doc_count = int(meta_count_str[0])
        if doc_count != len(corpus):
            return False, f"document_count invariant broken: stored={doc_count}, current={len(corpus)}"

        term_docs = set(r[0] for r in conn.execute("SELECT DISTINCT doc_id FROM terms").fetchall())
        if not term_docs.issubset(corpus_ids):
            return False, f"terms contains dangling doc_ids not in corpus: {term_docs - corpus_ids}"

        ngram_docs = set(r[0] for r in conn.execute("SELECT DISTINCT doc_id FROM ngrams").fetchall())
        if not ngram_docs.issubset(corpus_ids):
            return False, f"ngrams contains dangling doc_ids not in corpus: {ngram_docs - corpus_ids}"

        return True, ""
    except Exception as e:
        return False, f"corpus invariant exception: {e}"


# ---------------- 构建算法：build_semantic_index ----------------

def build_semantic_index(root: str, db_path: Optional[str] = None, crash_after: Optional[str] = None) -> Dict[str, Any]:
    """P1-C semantic 索引构建（原子全量重建，Sol rev1 P1-3 + rev3 P2-6 lock 继承）：
    必须在单个 SQLite transaction 内完成，且必须继承 P1-A 的全局 mutation lock。
    """
    from .tx.fs import freeze_lock, TxError
    actual_db = db_path or _default_db(root)

    try:
        with freeze_lock(root):
            conn = sqlite3.connect(actual_db)
            try:
                # 2. BEGIN IMMEDIATE
                conn.execute("BEGIN IMMEDIATE")

                # 3. 校验 base_index_fresh(root) == true
                # 不满足 → ROLLBACK → INDEX_STALE（build-time 固定复用 P0 码，零写入）
                if not base_index_fresh(root, actual_db):
                    conn.rollback()
                    return {
                        "query_id": uuid.uuid4().hex[:12],
                        "query_type": "reindex",
                        "status": "fail_closed",
                        "authority": "derived",
                        "source_watermark": {},
                        "results": None,
                        "warnings": [],
                        "errors": [{"code": "INDEX_STALE", "detail": "base index is not fresh"}],
                        "error_semantic": "INDEX_STALE",
                    }

                # 4-6. CREATE TABLE IF NOT EXISTS
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS terms ("
                    "term TEXT NOT NULL, doc_id TEXT NOT NULL, tf REAL NOT NULL, "
                    "PRIMARY KEY (term, doc_id))"
                )
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS ngrams ("
                    "ngram TEXT NOT NULL, doc_id TEXT NOT NULL, "
                    "PRIMARY KEY (ngram, doc_id))"
                )
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS semantic_metadata ("
                    "key TEXT NOT NULL PRIMARY KEY, value TEXT)"
                )

                # 7. schema-only 前置校验（Sol rev8 P1 + rev9 P2-NEW-2 + rev11 P2-REV11-1 闭合）
                ok_schema, schema_err = validate_schema_only(conn)
                if not ok_schema:
                    conn.rollback()
                    return {
                        "query_id": uuid.uuid4().hex[:12],
                        "query_type": "reindex",
                        "status": "fail_closed",
                        "authority": "derived",
                        "source_watermark": {},
                        "results": None,
                        "warnings": [],
                        "errors": [{"code": "SEMANTIC_INDEX_CORRUPT", "detail": f"schema-only preflight failed: {schema_err}"}],
                        "error_semantic": "SEMANTIC_INDEX_CORRUPT",
                    }

                # 8-10. DELETE FROM terms, ngrams, semantic_metadata
                conn.execute("DELETE FROM terms")
                conn.execute("DELETE FROM ngrams")
                conn.execute("DELETE FROM semantic_metadata")

                # 11-12. 从 documents 表读取全部 semantic_corpus，分词并插入 terms 与 ngrams
                corpus = get_semantic_corpus(root, conn)
                for doc in corpus:
                    doc_id = doc["id"]
                    text = doc["content"]
                    # Tokenize & terms
                    tokens = tokenize(text)
                    if tokens:
                        raw_tf_counts = collections.Counter(tokens)
                        for t, count in raw_tf_counts.items():
                            tf_val = 1.0 + math.log(count)
                            conn.execute(
                                "INSERT INTO terms (term, doc_id, tf) VALUES (?, ?, ?)",
                                (t, doc_id, tf_val)
                            )
                    # N-grams
                    ng_set = generate_ngrams(text)
                    for ng in ng_set:
                        conn.execute(
                            "INSERT INTO ngrams (ngram, doc_id) VALUES (?, ?)",
                            (ng, doc_id)
                        )

                if crash_after == "terms_and_ngrams":
                    raise RuntimeError("simulated crash after terms and ngrams inserted")

                # 13. 写 semantic_metadata（含 build_complete="1" 与 source watermark），最后一步
                p0_wm = get_watermark(conn)
                p0_last_ev = p0_wm.get("last_event_id")
                stored_last_ev = p0_last_ev if (p0_last_ev and p0_last_ev != "none") else "none"

                meta_kvs = [
                    ("algorithm_version", "semantic-tfidf/v1"),
                    ("source_scan_fingerprint", p0_wm.get("scan_fingerprint") or ""),
                    ("source_last_event_id", stored_last_ev),
                    ("source_index_built_at", p0_wm.get("index_built_at") or ""),
                    ("document_count", str(len(corpus))),
                    ("build_complete", "1"),
                ]
                for k, v in meta_kvs:
                    conn.execute("INSERT INTO semantic_metadata (key, value) VALUES (?, ?)", (k, v))

                if crash_after == "metadata":
                    raise RuntimeError("simulated crash after metadata inserted before commit")

                # 14. post-write 全量校验（Sol rev8 P1 闭合）
                ok_struct, struct_err = validate_semantic_generation_structure(conn)
                if not ok_struct:
                    conn.rollback()
                    return {
                        "query_id": uuid.uuid4().hex[:12],
                        "query_type": "reindex",
                        "status": "fail_closed",
                        "authority": "derived",
                        "source_watermark": {},
                        "results": None,
                        "warnings": [],
                        "errors": [{"code": "SEMANTIC_INDEX_CORRUPT", "detail": f"post-write validation failed: {struct_err}"}],
                        "error_semantic": "SEMANTIC_INDEX_CORRUPT",
                    }

                # 15. COMMIT
                conn.commit()

                # 构建成功返回 envelope
                return {
                    "query_id": uuid.uuid4().hex[:12],
                    "query_type": "reindex",
                    "status": "success",
                    "authority": "derived",
                    "source_watermark": {
                        "index_built_at": p0_wm.get("index_built_at"),
                        "last_event_id": p0_wm.get("last_event_id"),
                        "scan_fingerprint": p0_wm.get("scan_fingerprint"),
                        "index_complete": p0_wm.get("index_complete"),
                        "drift": p0_wm.get("drift"),
                        "semantic": {
                            "algorithm_version": "semantic-tfidf/v1",
                            "source_scan_fingerprint": p0_wm.get("scan_fingerprint") or "",
                            "source_last_event_id": None if stored_last_ev == "none" else stored_last_ev,
                            "source_index_built_at": p0_wm.get("index_built_at") or "",
                            "document_count": len(corpus),
                            "build_complete": True,
                        },
                    },
                    "results": [],
                    "warnings": [],
                    "errors": [],
                    "error_semantic": None,
                }
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
    except TxError as te:
        return {
            "query_id": uuid.uuid4().hex[:12],
            "query_type": "reindex",
            "status": "fail_closed",
            "authority": "derived",
            "source_watermark": {},
            "results": None,
            "warnings": [],
            "errors": [{"code": "TX_LOCKED", "detail": str(te)}],
            "error_semantic": "TX_LOCKED",
        }


# ---------------- 查询算法：query_semantic ----------------

def query_semantic(root: str, query_text: str, db_path: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """P1-C semantic 查询流程（§2.2 + §5，严格按单一定义链执行）：
    1. 三张 semantic 表全部不存在 → SEMANTIC_NOT_INDEXED
    2. validate_semantic_generation_structure() 任一失败 → SEMANTIC_INDEX_CORRUPT
    3. §2.5 查询前置校验任一不符 → SEMANTIC_INDEX_STALE
    4. fresh 后校验 current-corpus invariants 任一不符 → SEMANTIC_INDEX_CORRUPT
    5. 分词查询串
    6. 若 token 集为空 → SEMANTIC_EMPTY_QUERY 语义（results=[]）
    7. 计算 cosine(TF-IDF)
    8. 计算 n-gram ratio
    9. final_score = 0.7 * cosine + 0.3 * ngram_ratio
    10. 排序：按 score_q 降序 + entity_id/versioned_ref/path 真全序
    11. 全部 rank_score < 200_000_000 → SEMANTIC_LOW_CONFIDENCE warning
    12. 输出 envelope
    """
    actual_db = db_path or _default_db(root)
    query_id = uuid.uuid4().hex[:12]
    as_of = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    def _fail_closed(code: str, detail: str) -> Dict[str, Any]:
        return {
            "query_id": query_id,
            "query_type": "current",
            "as_of": as_of,
            "status": "fail_closed",
            "authority": "derived",
            "retrieval_mode": "semantic",
            "ranking_authority": "advisory",
            "source_watermark": {},
            "results": None,
            "warnings": [],
            "errors": [{"code": code, "detail": detail}],
            "error_semantic": code,
        }

    if not os.path.isfile(actual_db):
        return _fail_closed("SEMANTIC_NOT_INDEXED", "database file does not exist")

    conn = _connect(actual_db)
    try:
        # Step 1: 判定三张表全部不存在
        tbl_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('terms', 'ngrams', 'semantic_metadata')"
        ).fetchall()
        existing_tables = set(r[0] for r in tbl_rows)
        if len(existing_tables) == 0:
            return _fail_closed("SEMANTIC_NOT_INDEXED", "semantic tables not found, run index --semantic first")

        # Step 2: 结构校验器
        ok_struct, struct_err = validate_semantic_generation_structure(conn)
        if not ok_struct:
            return _fail_closed("SEMANTIC_INDEX_CORRUPT", f"semantic index corrupt: {struct_err}")

        # Step 3: §2.5 查询前置校验
        # base_index_fresh(root) == true
        # AND semantic_metadata.source_scan_fingerprint == P0 index_metadata.scan_fingerprint
        # AND normalize_event_id(semantic_metadata.source_last_event_id) == normalize_event_id(P0 index_metadata.last_event_id)
        # AND semantic_metadata.source_index_built_at == P0 index_metadata.index_built_at
        if not base_index_fresh(root, actual_db):
            return _fail_closed("SEMANTIC_INDEX_STALE", "base index is stale")

        p0_wm = get_watermark(conn)
        sm_rows = dict(conn.execute("SELECT key, value FROM semantic_metadata").fetchall())

        if sm_rows.get("source_scan_fingerprint") != p0_wm.get("scan_fingerprint"):
            return _fail_closed("SEMANTIC_INDEX_STALE", "source_scan_fingerprint does not match base index")

        p0_norm_ev = normalize_event_id(p0_wm.get("last_event_id"))
        sm_norm_ev = normalize_event_id(sm_rows.get("source_last_event_id"))
        if sm_norm_ev != p0_norm_ev:
            return _fail_closed("SEMANTIC_INDEX_STALE", "source_last_event_id does not match base index")

        if sm_rows.get("source_index_built_at") != p0_wm.get("index_built_at"):
            return _fail_closed("SEMANTIC_INDEX_STALE", "source_index_built_at does not match base index")

        # Step 4: 仅当 generation fresh 后才校验 current-corpus invariants
        ok_inv, inv_err = validate_generation_corpus_invariants(root, conn)
        if not ok_inv:
            return _fail_closed("SEMANTIC_INDEX_CORRUPT", f"corpus invariant broken: {inv_err}")

        # Step 5: 分词查询串
        q_tokens = tokenize(query_text)
        q_unique = query_unique_terms(q_tokens)
        q_ngrams = generate_ngrams(query_text)

        # 准备 source_watermark.semantic
        last_ev_val = sm_rows.get("source_last_event_id")
        out_last_ev = None if last_ev_val == "none" else last_ev_val
        semantic_wm = {
            "algorithm_version": sm_rows.get("algorithm_version", "semantic-tfidf/v1"),
            "source_scan_fingerprint": sm_rows.get("source_scan_fingerprint", ""),
            "source_last_event_id": out_last_ev,
            "source_index_built_at": sm_rows.get("source_index_built_at", ""),
            "document_count": int(sm_rows.get("document_count", 0)),
            "build_complete": sm_rows.get("build_complete") == "1",
        }
        envelope_wm = {
            "index_built_at": p0_wm.get("index_built_at"),
            "last_event_id": p0_wm.get("last_event_id"),
            "scan_fingerprint": p0_wm.get("scan_fingerprint"),
            "index_complete": p0_wm.get("index_complete"),
            "drift": p0_wm.get("drift"),
            "semantic": semantic_wm,
        }

        # Step 6: 若 token 集为空 → SEMANTIC_EMPTY_QUERY
        if not q_tokens:
            return {
                "query_id": query_id,
                "query_type": "current",
                "as_of": as_of,
                "status": "success",
                "authority": "derived",
                "retrieval_mode": "semantic",
                "ranking_authority": "advisory",
                "source_watermark": envelope_wm,
                "results": [],
                "warnings": [],
                "errors": [],
                "error_semantic": None,
            }

        # Step 7-10: 候选集、打分与排序
        # candidate set = { doc_id : 命中至少一个 query term } ∪ { doc_id : 命中至少一个 query ngram }
        candidate_docs: Set[str] = set()

        if q_unique:
            term_placeholders = ",".join("?" for _ in q_unique)
            c_rows = conn.execute(
                f"SELECT DISTINCT doc_id FROM terms WHERE term IN ({term_placeholders})",
                q_unique
            ).fetchall()
            for r in c_rows:
                candidate_docs.add(r[0])

        if q_ngrams:
            ng_list = list(q_ngrams)
            ng_placeholders = ",".join("?" for _ in ng_list)
            ng_rows = conn.execute(
                f"SELECT DISTINCT doc_id FROM ngrams WHERE ngram IN ({ng_placeholders})",
                ng_list
            ).fetchall()
            for r in ng_rows:
                candidate_docs.add(r[0])

        if not candidate_docs:
            return {
                "query_id": query_id,
                "query_type": "current",
                "as_of": as_of,
                "status": "success",
                "authority": "derived",
                "retrieval_mode": "semantic",
                "ranking_authority": "advisory",
                "source_watermark": envelope_wm,
                "results": [],
                "warnings": [],
                "errors": [],
                "error_semantic": None,
            }

        # 全语料 N 与 dfs
        N = int(sm_rows["document_count"])
        df_rows = conn.execute("SELECT term, COUNT(doc_id) FROM terms GROUP BY term").fetchall()
        dfs = dict(df_rows)

        # 计算 query vector w(t, q) 与 ||q||₂
        q_raw_counts = collections.Counter(q_tokens)
        w_q_dict: Dict[str, float] = {}
        for t in q_unique:
            raw_tf_q = q_raw_counts[t]
            tf_q = 1.0 + math.log(raw_tf_q)
            df_t = dfs.get(t, 0)
            idf_t = math.log((N + 1.0) / (df_t + 1.0)) + 1.0
            w_q_dict[t] = tf_q * idf_t

        norm_q = math.sqrt(math.fsum(w_q_dict[t] ** 2 for t in q_unique))

        # 加载 documents 表候选文档元数据
        cand_list = list(candidate_docs)
        cand_placeholders = ",".join("?" for _ in cand_list)
        doc_info_rows = conn.execute(
            f"SELECT id, path, version, content_hash, git_commit, status FROM documents WHERE id IN ({cand_placeholders})",
            cand_list
        ).fetchall()
        doc_info_map = {r[0]: r for r in doc_info_rows}

        scored_candidates = []
        for doc_id in cand_list:
            doc_meta = doc_info_map.get(doc_id)
            if not doc_meta:
                continue

            # 文档所有 terms（按 term 字节字典序排列）
            d_term_rows = conn.execute(
                "SELECT term, tf FROM terms WHERE doc_id = ? ORDER BY term",
                (doc_id,)
            ).fetchall()

            w_d_dict: Dict[str, float] = {}
            w_d_sq_list: List[float] = []
            for t, tf_val in d_term_rows:
                df_t = dfs.get(t, 0)
                idf_t = math.log((N + 1.0) / (df_t + 1.0)) + 1.0
                w_val = tf_val * idf_t
                w_d_dict[t] = w_val
                w_d_sq_list.append(w_val ** 2)

            norm_d = math.sqrt(math.fsum(w_d_sq_list))

            # cosine(q, d)
            if norm_q > 0 and norm_d > 0:
                dot_products = [w_q_dict[t] * w_d_dict.get(t, 0.0) for t in q_unique]
                cosine = math.fsum(dot_products) / (norm_q * norm_d)
            else:
                cosine = 0.0

            # ngram_ratio(q, d)
            if len(q_ngrams) > 0:
                doc_ng_rows = conn.execute("SELECT ngram FROM ngrams WHERE doc_id = ?", (doc_id,)).fetchall()
                doc_ng_set = set(r[0] for r in doc_ng_rows)
                ngram_ratio = len(q_ngrams.intersection(doc_ng_set)) / len(q_ngrams)
            else:
                ngram_ratio = 0.0

            # final_score = 0.7 * cosine + 0.3 * ngram_ratio
            final_score = 0.7 * cosine + 0.3 * ngram_ratio
            score_q = round(final_score * 1_000_000_000)

            # score_q == 0 的 candidate 不返回
            if score_q == 0:
                continue

            entity_id = str(doc_meta[0])
            path = str(doc_meta[1])
            version = doc_meta[2]
            versioned_ref = f"{entity_id}@{version}" if version else None
            content_hash = str(doc_meta[3]) if doc_meta[3] else None
            git_commit = str(doc_meta[4]) if doc_meta[4] else None

            # status 结构
            status_dict = {
                "lifecycle": None,
                "validity": None,
                "authority": None,
                "materialization": None,
                "research": None,
                "decision": None,
            }

            scored_candidates.append({
                "entity_id": entity_id,
                "versioned_ref": versioned_ref,
                "path": path,
                "content_hash": content_hash,
                "git_commit": git_commit,
                "section": None,
                "status": status_dict,
                "relation_type": None,
                "is_stale": False,
                "is_available": True,
                "rank_score": score_q,
                "score": score_q / 1_000_000_000,
            })

        # 排序键（真全序）：
        # 1. rank_score 降序
        # 2. entity_id 升序 (UTF-8 字节序)
        # 3. versioned_ref 升序 (UTF-8 字节序，缺省视为空串)
        # 4. path 升序 (UTF-8 字节序)
        def _sort_key(item):
            return (
                -item["rank_score"],
                item["entity_id"].encode("utf-8"),
                (item["versioned_ref"] or "").encode("utf-8"),
                item["path"].encode("utf-8"),
            )

        scored_candidates.sort(key=_sort_key)

        # 截断 limit
        results = scored_candidates[:limit]

        # Step 11: 置信阈值校验
        warnings = []
        if results and all(item["rank_score"] < 200_000_000 for item in results):
            warnings.append({
                "code": "SEMANTIC_LOW_CONFIDENCE",
                "detail": "all candidate scores below threshold 0.2",
            })

        # 清除内部 rank_score 字段，使每个 item 成为规范 ResultItem
        for item in results:
            del item["rank_score"]

        return {
            "query_id": query_id,
            "query_type": "current",
            "as_of": as_of,
            "status": "success",
            "authority": "derived",
            "retrieval_mode": "semantic",
            "ranking_authority": "advisory",
            "source_watermark": envelope_wm,
            "results": results,
            "warnings": warnings,
            "errors": [],
            "error_semantic": None,
        }
    finally:
        conn.close()
