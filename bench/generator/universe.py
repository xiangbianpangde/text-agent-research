"""Deterministic synthetic universe construction (P1A).

Builds a self-consistent oracle-manifest/v1 document, a scenario-actions/v2
action stream, a query-registry/v1, and a physical fixture file map for one
instance — entirely from the family spec and the KDF domain streams.

No floats, no wall clock, no locale, no filesystem order, no RNG beyond the
HMAC counter streams. All ordering is by UTF-8 byte lexical sort.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from bench.generator.kdf import PRNGStream

TICK = 86400  # family temporal tick (seconds); rendered via fixed-format arithmetic


def _ts(base_day: int, day_offset: int) -> str:
    """Render an RFC3339 UTC timestamp from a fixed epoch day + offset.

    base_day counts days since 1970-01-01; conversion is pure integer
    arithmetic with a fixed civil-from-days algorithm (no locale/timezone).
    """
    total = base_day + day_offset
    # days -> civil date (Howard Hinnant's algorithm)
    z = total + 719468
    era = (z if z >= 0 else z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    y = y + (1 if m <= 2 else 0)
    return f"{y:04d}-{m:02d}-{d:02d}T00:00:00Z"


EPOCH_DAY_FOR_2026_08_01 = 20666  # fixed constant: 2026-08-01


def _pad(n: int, width: int = 3) -> str:
    return str(n).zfill(width)


class UniverseBuildError(ValueError):
    """Raised when a candidate universe violates a generator validity rule."""


def build_universe_document(
    *,
    family: Mapping[str, Any],
    ordinal: int,
    streams: Mapping[str, PRNGStream],
    universe_id: str,
) -> Dict[str, Any]:
    """Construct the manifest body (entities/artifacts/facts/relations/queries)."""
    family_id = family["family_id"]
    card = family["cardinality_constraints"]
    objects_stream = streams["objects"]
    n_entities = card["min_entities"] + objects_stream.uniform(
        card["max_entities"] - card["min_entities"] + 1
    )
    n_artifacts = card["min_artifacts"] + objects_stream.uniform(
        card["max_artifacts"] - card["min_artifacts"] + 1
    )

    base_day = EPOCH_DAY_FOR_2026_08_01 + ordinal * 3  # instance-unique calendar window
    clock = _ts(base_day, 4)

    entities: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    facts: List[Dict[str, Any]] = []
    evidence_atoms: List[Dict[str, Any]] = []

    entity_paths: List[str] = []

    def _sha_hex(data: bytes) -> str:
        import hashlib
        return "sha256:" + hashlib.sha256(data).hexdigest()

    # --- definitions ------------------------------------------------------
    definition_ids: List[str] = []
    definition_version_refs: List[str] = []
    for i in range(n_entities):
        entity_id = f"E{_pad(i + 1)}"
        version_count = 1 + objects_stream.uniform(2)
        chosen_version = None
        for v in range(1, version_count + 1):
            version_ref = f"{entity_id}@v{v}"
            path = f"definitions/{entity_id}/{version_ref}.yaml"
            entity_paths.append(path)
            if chosen_version is None or v == version_count:
                chosen_version = (entity_id, version_ref, path)
        assert chosen_version is not None
        eid, vref, vpath = chosen_version
        definition_ids.append(eid)
        definition_version_refs.append(vref)
        entities.append({
            "ref": f"definition:{vref}",
            "kind": "definition",
            "entity_id": eid,
            "version_ref": vref,
            "path": vpath,
            "status": "valid",
            "content_hash": None,  # filled after fixture bytes are built
            "lifecycle_start": _ts(base_day, 0),
            "git_commit": None,
        })
        facts.append({
            "fact_id": f"fact:{vref}:introduced-by",
            "subject": f"definition:{vref}",
            "predicate": "introduced_by",
            "value": "human:generator",
            "occurred_at": _ts(base_day, 0),
        })

    # --- external source --------------------------------------------------
    external_ref = "external:basis-doc"
    external_path = "external/basis-doc.txt"
    entity_paths.append(external_path)
    external_hash = _sha_hex(b"PINNED_BASIS_VALUE\n")
    entities.append({
        "ref": external_ref,
        "kind": "external_source",
        "entity_id": "external:basis-doc",
        "version_ref": None,
        "path": external_path,
        "status": "valid",
        "content_hash": external_hash,
        "lifecycle_start": _ts(base_day, 0),
        "git_commit": None,
    })
    # authority edge from first definition to external source
    first_def_ref = f"definition:{definition_version_refs[0]}"
    relations.append({
        "source_ref": first_def_ref,
        "target_ref": external_ref,
        "relation": "authorized_by",
    })
    facts.append({
        "fact_id": f"fact:{definition_version_refs[0]}:pinned-external-value",
        "subject": external_ref,
        "predicate": "pinned_external_value",
        "value": "PINNED_BASIS_VALUE",
        "occurred_at": _ts(base_day, 0),
    })
    facts.append({
        "fact_id": f"fact:{definition_version_refs[0]}:authority-source",
        "subject": external_ref,
        "predicate": "authority_source",
        "value": external_ref,
        "occurred_at": _ts(base_day, 0),
    })

    # --- spec + runs ------------------------------------------------------
    spec_id = f"X{ordinal:03d}"
    spec_ref = f"spec:{spec_id}@v1"
    spec_path = f"experiments/{spec_id}/spec.yaml"
    entity_paths.append(spec_path)
    entities.append({
        "ref": spec_ref,
        "kind": "experiment_spec",
        "entity_id": spec_id,
        "version_ref": f"{spec_id}@v1",
        "path": spec_path,
        "status": "valid",
        "content_hash": None,
        "lifecycle_start": _ts(base_day, 1),
        "git_commit": None,
    })

    run_ids = [f"R{_pad(i + 1)}" for i in range(2)]
    for i, run_id in enumerate(run_ids):
        run_ref = f"run:{run_id}"
        run_path = f"runs/{run_id}/manifest.yaml"
        entity_paths.append(run_path)
        entities.append({
            "ref": run_ref,
            "kind": "run",
            "entity_id": run_id,
            "version_ref": None,
            "path": run_path,
            "status": "valid",
            "content_hash": None,
            "lifecycle_start": _ts(base_day, 2 + i),
            "git_commit": None,
        })
        relations.append({"source_ref": run_ref, "target_ref": spec_ref, "relation": "bound_to"})

        raw_dir = f"raw/{spec_id}/{run_id}"
        metrics_rel = f"{raw_dir}/metrics.csv"
        artifacts.append({
            "ref": f"artifact:{run_id}:metrics",
            "kind": "metrics_csv",
            "entity_id": metrics_rel,
            "version_ref": None,
            "path": metrics_rel,
            "status": "valid",
            "content_hash": None,
            "lifecycle_start": _ts(base_day, 2 + i),
            "git_commit": None,
        })
        entities.append({
            "ref": f"raw:{run_id}",
            "kind": "raw_run",
            "entity_id": raw_dir,
            "version_ref": None,
            "path": raw_dir,
            "status": "valid",
            "content_hash": None,
            "lifecycle_start": _ts(base_day, 2 + i),
            "git_commit": None,
        })
        # metric evidence atom
        metric_value = f"0.{objects_stream.uniform(900) + 100}"
        evidence_atoms.append({
            "atom_id": f"metric:{run_id}:accuracy",
            "kind": "metric_cell",
            "artifact_ref": f"artifact:{run_id}:metrics",
            "row_key": [{"column": "step", "value": "100"}],
            "column": "accuracy",
            "value_type": "decimal",
            "value": metric_value,
            "argv": None,
        })
        binding_ref = f"binding:ORG:{run_id}"
        entities.append({
            "ref": binding_ref,
            "kind": "source_binding",
            "entity_id": binding_ref,
            "version_ref": None,
            "path": raw_dir,
            "status": "valid",
            "content_hash": None,
            "lifecycle_start": _ts(base_day, 2 + i),
            "git_commit": None,
        })
        relations.append({
            "source_ref": binding_ref,
            "target_ref": f"raw:{run_id}",
            "relation": "resolves_to",
        })

    # --- organized result + report ---------------------------------------
    result_ref = f"organized:{spec_id}"
    result_path = f"organized/{spec_id}/result.md"
    entity_paths.append(result_path)
    entities.append({
        "ref": result_ref,
        "kind": "organized_result",
        "entity_id": spec_id,
        "version_ref": None,
        "path": result_path,
        "status": "valid",
        "content_hash": None,
        "lifecycle_start": _ts(base_day, 4),
        "git_commit": None,
    })
    relations.append({"source_ref": result_ref, "target_ref": first_def_ref, "relation": "based_on"})
    for run_id in run_ids:
        relations.append({
            "source_ref": f"binding:ORG:{run_id}",
            "target_ref": result_ref,
            "relation": "cites",
        })

    report_ref = "report:CURRENT"
    report_path = "reports/CURRENT.md"
    entity_paths.append(report_path)
    entities.append({
        "ref": report_ref,
        "kind": "report",
        "entity_id": "CURRENT",
        "version_ref": None,
        "path": report_path,
        "status": "valid",
        "content_hash": None,
        "lifecycle_start": clock,
        "git_commit": None,
    })

    # additional relations chain for F05-style impact depth
    if len(definition_ids) >= 3:
        version_refs = [row["version_ref"] for row in entities if row["kind"] == "definition"]
        for a, b in zip(version_refs, version_refs[1:]):
            relations.append({
                "source_ref": f"definition:{b}",
                "target_ref": f"definition:{a}",
                "relation": "derived_from",
            })

    # --- artifact content (metrics csv / execution log / run manifest) ----
    content_stream = streams["content"]
    for run_id in run_ids:
        raw_dir = f"raw/{spec_id}/{run_id}"
        acc = f"0.{content_stream.uniform(900) + 100}"
        loss = f"0.{content_stream.uniform(300) + 50}"
        artifacts.append({
            "ref": f"artifact:{run_id}:execution-log",
            "kind": "execution_log",
            "entity_id": f"{raw_dir}/execution.log",
            "version_ref": None,
            "path": f"{raw_dir}/execution.log",
            "status": "valid",
            "content_hash": None,
            "lifecycle_start": _ts(base_day, 2),
            "git_commit": None,
        })

    # --- queries from the family's operation allowlist ---------------------
    query_stream = streams["query"]
    queries: List[Dict[str, Any]] = []
    # non-query operations (index/freeze_report/tx_reconcile etc.) are invoked
    # directly by the action stream, not via the query registry
    registry_ops = frozenset({
        "query_as_of_state", "query_entity", "query_exact_routing",
        "query_external_basis", "query_facts", "query_history", "query_lineage",
        "query_project_current", "query_project_index", "query_sources",
        "query_state", "query_text_lexical", "query_text_semantic",
        "impact", "stale_status", "trace_evidence", "trace_graph",
    })
    op_list = [op for op in family["operation_allowlist"] if op in registry_ops]
    if not op_list:
        op_list = ["query_entity", "query_sources"]
    n_queries = max(2, min(len(op_list), 2 + query_stream.uniform(3)))
    available = list(op_list)
    chosen_ops: List[str] = []
    while len(chosen_ops) < n_queries and available:
        pick = available[query_stream.uniform(len(available))]
        chosen_ops.append(pick)
        available.remove(pick)
    seen_ops: set = set()
    idx = 0
    for op in chosen_ops:
        if op in seen_ops:
            continue
        seen_ops.add(op)
        idx += 1
        qid = f"Q{_pad(idx)}"
        if op in ("query_text_lexical", "query_text_semantic"):
            queries.append({
                "query_id": qid,
                "operation": op,
                "target_ref": None,
                "text": f"{spec_id} accuracy result",
                "as_of": None,
                "participant_locator": None,
                "predicates": [],
                "relation_types": [],
                "route_sequence": ["current"],
                "ranking_authority": None,
            })
        elif op == "query_as_of_state":
            queries.append({
                "query_id": qid,
                "operation": op,
                "target_ref": None,
                "text": None,
                "as_of": _ts(base_day, 2),
                "participant_locator": None,
                "predicates": [],
                "relation_types": [],
                "route_sequence": ["current"],
                "ranking_authority": None,
            })
        elif op in ("impact", "stale_status"):
            queries.append({
                "query_id": qid,
                "operation": op,
                "target_ref": first_def_ref,
                "text": None,
                "as_of": None,
                "participant_locator": definition_ids[0],
                "predicates": [],
                "relation_types": [],
                "route_sequence": ["current"],
                "ranking_authority": None,
                "change_type": "definition_revised",
            })
        else:
            target = first_def_ref
            queries.append({
                "query_id": qid,
                "operation": op,
                "target_ref": target,
                "text": None,
                "as_of": None,
                "participant_locator": definition_ids[0],
                "predicates": ["introduced_by"] if op == "query_facts" else [],
                "relation_types": [],
                "route_sequence": ["current"],
                "ranking_authority": None,
            })
    queries.sort(key=lambda q: q["query_id"])

    document: Dict[str, Any] = {
        "schema_version": "oracle-manifest/v1",
        "universe_id": universe_id,
        "clock": clock,
        "fixture": {
            "source_archive": "source.tar",
            "source_hash": None,  # filled by caller
            "archive": "fixture.tar",
            "format": "tar",
            "content_hash": None,  # filled by caller
        },
        "event_ids": [f"EV-{_pad(i + 1)}" for i in range(1)],
        "queries": queries,
        "entities": entities,
        "artifacts": artifacts,
        "facts": facts,
        "evidence_atoms": evidence_atoms,
        "relations": relations,
        "snapshots": [{"snapshot_id": "canonical", "as_of": clock, "paths": ["reports", "events"]}],
        "external_sources": [{
            "ref": external_ref,
            "pinned_content_hash": None,
            "pinned_value": "PINNED_BASIS_VALUE",
            "latest_content_hash": None,
            "latest_value": "PINNED_BASIS_VALUE",
        }],
    }
    return document


def build_action_stream(
    *,
    family: Mapping[str, Any],
    universe: Mapping[str, Any],
    streams: Mapping[str, PRNGStream],
    scenario_id: str,
) -> Dict[str, Any]:
    """Build a scenario-actions/v2 document exercising the family's allowlist."""
    actions_stream = streams["actions"]
    steps: List[Dict[str, Any]] = []
    step_no = 1

    steps.append({"step": step_no, "action": "invoke", "operation": "index", "params": {}})
    step_no += 1

    for query in universe["queries"]:
        # as_of queries require the virtual clock to equal the cutoff (P0 compiler rule)
        if query.get("as_of") is not None:
            steps.append({
                "step": step_no, "action": "advance_time", "new_timestamp": query["as_of"],
            })
            step_no += 1
        steps.append({
            "step": step_no,
            "action": "invoke",
            "capture_id": f"cap-{query['query_id'].lower()}",
            "operation": query["operation"],
            "params": {"query_id": query["query_id"]},
        })
        step_no += 1

    # family-specific mutation: deterministic pick from mutation_allowlist
    mut_allow = list(family["mutation_allowlist"])
    if mut_allow:
        mut = mut_allow[actions_stream.uniform(len(mut_allow))]
        artifacts = universe["artifacts"]
        entities = universe["entities"]
        if mut in ("tamper_file", "delete_file"):
            target = next(a["ref"] for a in artifacts if a["kind"] == "metrics_csv")
            steps.append({"step": step_no, "action": "mutate", "type": mut, "target": target})
            step_no += 1
        elif mut in ("corrupt_index", "touch_file"):
            steps.append({"step": step_no, "action": "mutate", "type": mut, "target": ".index"})
            step_no += 1
        elif mut == "create_file":
            steps.append({
                "step": step_no, "action": "mutate", "type": "create_file",
                "target": "organized/UNTRACKED_NOTE.md", "content": "# untracked\n",
            })
            step_no += 1
        elif mut == "delete_tree":
            steps.append({"step": step_no, "action": "mutate", "type": "delete_tree", "target": ".index"})
            step_no += 1
        elif mut == "external_update":
            target = universe["external_sources"][0]["ref"]
            import hashlib
            revised_hash = "sha256:" + hashlib.sha256(b"REVISED_BASIS_VALUE\n").hexdigest()
            steps.append({
                "step": step_no, "action": "mutate", "type": "external_update",
                "target": target, "content_hash": revised_hash, "content": "REVISED_BASIS_VALUE",
            })
            step_no += 1
        elif mut == "raw_invalidation":
            target = next(e["ref"] for e in entities if e["kind"] == "raw_run")
            steps.append({"step": step_no, "action": "mutate", "type": "raw_invalidation", "target": target})
            step_no += 1
        elif mut in ("create_version", "duplicate_version"):
            defs = [e for e in entities if e["kind"] == "definition"]
            base = defs[0]
            base_version_num = int(base["version_ref"].rsplit("v", 1)[1])
            next_version = f"{base['entity_id']}@v{base_version_num + 1}"
            if mut == "create_version":
                steps.append({
                    "step": step_no, "action": "mutate", "type": "create_version",
                    "target": f"definition:{base['version_ref']}",
                    "new_ref": f"definition:{next_version}",
                    "entity_id": base["entity_id"],
                    "version_ref": next_version,
                    "path": f"definitions/{base['entity_id']}/{next_version}.yaml",
                    "properties": {"rationale": "generator-created revision"},
                })
            else:
                steps.append({
                    "step": step_no, "action": "mutate", "type": "duplicate_version",
                    "target": f"definition:{base['version_ref']}",
                    "new_ref": f"definition:{next_version}-duplicate",
                    "entity_id": base["entity_id"],
                    "version_ref": next_version,
                    "path": f"definitions/{base['entity_id']}/{next_version}-duplicate.yaml",
                    "properties": {"body": "forged"},
                })
            step_no += 1
        elif mut == "semantic_tamper":
            target = next(e["ref"] for e in entities if e["kind"] == "organized_result")
            steps.append({"step": step_no, "action": "mutate", "type": "semantic_tamper", "target": target})
            step_no += 1
        elif mut == "runtime_deviation":
            target = next(e["ref"] for e in entities if e["kind"] == "run")
            steps.append({"step": step_no, "action": "mutate", "type": "runtime_deviation", "target": target})
            step_no += 1

    return {
        "schema_version": "scenario-actions/v2",
        "scenario_id": scenario_id,
        "track": f"P1_{family['family_id']}",
        "name": f"P1 instance {scenario_id}",
        "initial_fixture": universe["universe_id"],
        "steps": steps,
    }


def build_query_registry(universe: Mapping[str, Any]) -> Dict[str, Any]:
    """Derive query-registry/v1 from the manifest queries (§19.6.1)."""
    records = []
    for q in universe["queries"]:
        records.append({
            "as_of": q.get("as_of"),
            "change_type": q.get("change_type"),
            "participant_locator": q.get("participant_locator"),
            "query_id": q["query_id"],
            "text": q.get("text"),
        })
    records.sort(key=lambda r: r["query_id"])
    return {"records": records, "schema_version": "query-registry/v1"}


def finalize_manifest_filler_hashes(
    universe: Mapping[str, Any],
    files: Mapping[str, Tuple[int, bytes]],
) -> None:
    """Fill content_hash / fixture digests in the manifest from built fixture bytes.

    Mutates the manifest document in place. All digests derive from the exact
    fixture bytes, so the manifest and the physical tree always agree.
    """
    import hashlib

    def _sha_hex(data: bytes) -> str:
        return "sha256:" + hashlib.sha256(data).hexdigest()

    for row in (*universe["entities"], *universe["artifacts"]):
        path = row.get("path")
        if row["kind"] in ("metrics_csv", "execution_log"):
            row["content_hash"] = _sha_hex(files[path][1])
        elif row["kind"] in ("definition", "experiment_spec", "run", "organized_result", "report"):
            if path in files:
                row["content_hash"] = _sha_hex(files[path][1])
        elif row["kind"] == "raw_run":
            index_data = files.get(f"{path}/INDEX.yaml")
            if index_data is not None:
                row["content_hash"] = _sha_hex(index_data[1])

    fixture_blob = b"".join(files[p][1] for p in sorted(files))
    universe["fixture"]["source_hash"] = _sha_hex(fixture_blob)
    universe["fixture"]["content_hash"] = _sha_hex(fixture_blob)
    for ext in universe["external_sources"]:
        if ext.get("pinned_content_hash") is None:
            ext["pinned_content_hash"] = _sha_hex(b"PINNED_BASIS_VALUE\n")
        if ext.get("latest_content_hash") is None:
            ext["latest_content_hash"] = ext["pinned_content_hash"]


def build_fixture_files(
    *,
    universe: Mapping[str, Any],
    streams: Mapping[str, PRNGStream],
) -> Dict[str, Tuple[int, bytes]]:
    """Build the physical fixture file map {rel_path: (mode, bytes)}.

    File bodies are canonical bench-cjson documents; every file path and body
    is a deterministic function of the streams and universe structure.
    """
    files: Dict[str, Tuple[int, bytes]] = {}
    content_stream = streams["content"]

    def put(path: str, obj: Any) -> None:
        from bench.dsl.cjson import bench_cjson_bytes
        data = bench_cjson_bytes(obj) + b"\n"
        files[path] = (0o644, data)

    for row in universe["entities"]:
        if row["kind"] in ("definition", "experiment_spec"):
            put(row["path"], {
                "entity_id": row["entity_id"],
                "version_ref": row["version_ref"],
                "status": row["status"],
                "created_at": row["lifecycle_start"],
            })
        elif row["kind"] == "run":
            put(row["path"], {
                "run_id": row["entity_id"],
                "status": row["status"],
                "started_at": row["lifecycle_start"],
            })
        elif row["kind"] == "raw_run":
            # directory-like entry in P0; emit a marker file per raw run dir
            put(f"{row['path']}/INDEX.yaml", {"raw_run": row["entity_id"]})
        elif row["kind"] == "organized_result":
            put(row["path"], {
                "result": row["entity_id"],
                "summary": "GENERATED_RESULT_BODY",
            })
        elif row["kind"] == "report":
            put(row["path"], {
                "report": row["entity_id"],
                "generated_at": row["lifecycle_start"],
            })
        elif row["kind"] == "external_source":
            put(row["path"], universe["external_sources"][0]["pinned_value"] + "\n")

    for row in universe["artifacts"]:
        if row["kind"] == "metrics_csv":
            acc = next(
                atom["value"] for atom in universe["evidence_atoms"]
                if atom["artifact_ref"] == row["ref"]
            )
            body = (
                "step,accuracy,loss\n"
                f"100,{acc},0.3\n"
            ).encode("utf-8")
            files[row["path"]] = (0o644, body)
        elif row["kind"] == "execution_log":
            body = "run completed\n".encode("utf-8")
            files[row["path"]] = (0o644, body)

    return files
