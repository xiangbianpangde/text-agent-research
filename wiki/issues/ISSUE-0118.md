---
id: "ISSUE-0118"
title: "canonical trace CAS index accepts duplicate names and unreferenced non-regular entries"
status: "open"
severity: "high"
area: "bench"
discovered_at: "2026-09-22"
discovered_by: "agent"
tags: []
signals:
  - "both_halves_independently_reproduced_with_line_numbers_2026_09_22;cas_index_is_not_exact_closure_of_regular_frames"
  - "canonical_trace_cas_duplicate_entry,canonical_trace_cas_nonregular_unreferenced"
  - "independently_reproduced_by_me_duplicate_cas_name_accepted_silently"
evidence: "v77 archive 7de9414fa01dfac284c029bc37aad9f004bbc04f8b02578bd8c500294de20e04; /tmp/r62_v77_trace_cas_independent_probe.out; tools/canonical_trace.py:_verify_cas declared[name] overwrite and frame_path.is_file() continue"
related:
  - "ISSUE-0106"
fix_ref: null
summary: "_verify_cas does not enforce unique CAS entry names or regular-file type for entries with no record reference"
updated_at: "2026-09-22"
---

## 现象

On an internally valid v77 trace, append a duplicate raw_manifest entry for an existing frame, or add a declared unreferenced directory/dangling symlink under raw/ with a matching manifest entry; after rebinding raw_manifest_sha256, load_canonical_trace returns valid=True/problems=[] and verdict=INTERNALLY_VALID_UNBOUND.

## 复现

Copy review_v77; append an exact duplicate to raw_manifest.entries, or create raw/unreferenced_directory (directory) / raw/unreferenced_dangling (dangling symlink) and append name/sha256/size; recompute TRACE_MANIFEST.raw_manifest_sha256; call tools.canonical_trace.load_canonical_trace(root).

## 影响

The CAS index is not an exact closure of regular immutable frames: duplicate declarations are silently collapsed and special entries can be present without validation. A malformed or redirected unreferenced object can therefore remain in a trace that consumers accept as internally valid.

## 根因

（待定位）

## 处置

- [ ] 定位根因
- [ ] 修复（见 `fix_ref`）
- [ ] 回归验证（测试 / 实跑证据）

## 备注

（无）

## 处置记录 2026-09-22T21:42:09+0800

INDEPENDENT REPRODUCTION (mine, 2026-09-22), confirming the reviewer's HIGH finding. Setup: isolated copy of the archive with no reachable repo. I appended an EXACT DUPLICATE of the first entry to raw_manifest.json entries, then rebound TRACE_MANIFEST.raw_manifest_sha256 to the rewritten manifest so the trace remained internally consistent. Result: load_canonical_trace returns valid=True, verdict=INTERNALLY_VALID_UNBOUND, problems=[] -- the duplicate declaration is silently collapsed. Then restored both files and confirmed byte-exact restoration. Mechanism matches the issue text: tools/canonical_trace.py:_verify_cas uses declared[name] keyed by name (so a duplicate overwrites rather than conflicts) and frame_path.is_file() continues past unreferenced non-regular entries. This is a genuine evidence-closure defect: the CAS index is not an exact closure of regular immutable frames, so an internally valid trace can carry a malformed or redirected unreferenced object.

## 处置记录 2026-09-22T21:50:10+0800

R68 完整双半复现（见 RAW-20260922-006，探针副本 /private/tmp/cas_test 与 /private/tmp/cas_b）：

HALF A duplicate：raw_manifest.entries 追加现有帧精确副本（1072→1073），重绑 raw_manifest_sha256 后 load_canonical_trace('.') => found=True, valid=True, source_bound=False, verdict=INTERNALLY_VALID_UNBOUND, problems=[]。

HALF B unreferenced non-regular：raw/ 下新增 unref_dir/（目录）与 unref_dangling（悬空符号链接 → /nonexistent/target/outside），各追加伪造 sha256 的 name/sha256/size 条目（1072→1074），重绑后同样 => valid=True, problems=[]。

精确机制（tools/canonical_trace.py）：
  L563 declared[name] = (digest, size)        同名后写覆盖前写 => duplicate 静默折叠
  L566 if set(declared) != set(on_disk):      只比名字集合 => 目录/悬空链接名字在 iterdir() 中，集合仍相等
  L576 if not frame_path.is_file(): continue  注释称集合比较已报告，但集合不比类型 => 非 regular entry 跳过 digest/size/类型校验

结论：CAS 索引既非唯一名闭包，亦非 regular immutable frames 的精确闭包。修复需同时覆盖唯一名与 regular-file 类型两项回归。
