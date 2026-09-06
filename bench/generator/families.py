"""Task family registry: the 8 versioned families F01–F08 (§7, §19.3.1).

Each family is a pure task-family/v1 object: no Gold, no expected results,
no TP/FP/FN, no scores, no participant-specific logic.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .models import validate_task_family

FAMILY_VERSION = "1.0.0"

START_TIME = "2026-08-01T00:00:00Z"


def _family(
    family_id: str,
    capability: str,
    p0_anchors: List[str],
    operation_allowlist: List[str],
    mutation_allowlist: List[str],
    subvariant_schedule: List[Dict[str, Any]],
    *,
    min_entities: int,
    max_entities: int,
    min_artifacts: int,
    max_artifacts: int,
    positive_requirements: List[str],
    negative_requirements: List[str],
    checkpoint_types: List[str],
    applicable_metrics: List[str],
    forbidden_conditions: List[str],
    generation_acceptance_predicates: List[str],
    allow_cycles: bool = False,
    max_depth: int = 4,
    object_kinds: List[str] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": "task-family/v1",
        "family_id": family_id,
        "family_version": FAMILY_VERSION,
        "capability": capability,
        "p0_anchors": p0_anchors,
        "object_kinds": object_kinds or ["entity", "artifact"],
        "operation_allowlist": operation_allowlist,
        "mutation_allowlist": mutation_allowlist,
        "subvariant_schedule": subvariant_schedule,
        "cardinality_constraints": {
            "min_entities": min_entities,
            "max_entities": max_entities,
            "min_artifacts": min_artifacts,
            "max_artifacts": max_artifacts,
        },
        "temporal_constraints": {"start_time": START_TIME, "tick_interval_seconds": 86400},
        "topology_constraints": {"allow_cycles": allow_cycles, "max_depth": max_depth},
        "positive_requirements": positive_requirements,
        "negative_requirements": negative_requirements,
        "checkpoint_types": checkpoint_types,
        "applicable_metrics": applicable_metrics,
        "forbidden_conditions": forbidden_conditions,
        "generation_acceptance_predicates": generation_acceptance_predicates,
    }


def _schedule(*entries: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(entries)


FAMILIES: Dict[str, Dict[str, Any]] = {
    # F01: Definition identity, authority, evolution (S01–S06)
    "F01": _family(
        "F01",
        "Definition identity, authority, and evolution",
        ["S01", "S02", "S03", "S04", "S05", "S06"],
        [
            "query_entity",
            "query_external_basis",
            "query_facts",
            "query_history",
            "query_lineage",
            "query_sources",
        ],
        ["create_version", "duplicate_version", "external_update"],
        _schedule(
            {"subvariant_id": "introduced-authority", "weight": 3, "parameters": {"max_depth": 2}},
            {"subvariant_id": "evolution-rationale", "weight": 3, "parameters": {"max_depth": 3}},
            {"subvariant_id": "lineage-ordering", "weight": 2, "parameters": {"max_depth": 4}},
        ),
        min_entities=3, max_entities=8, min_artifacts=1, max_artifacts=4,
        positive_requirements=["definition_origin_attributed", "authority_chain_resolved"],
        negative_requirements=["no_authority_fabrication", "no_unpinned_external_basis"],
        checkpoint_types=["provenance_graph", "asserted_facts"],
        applicable_metrics=["CIV", "PGEM", "SF1"],
        forbidden_conditions=["gold_after_sut", "participant_specific_gold"],
        generation_acceptance_predicates=["unique_entity_ids", "graph_acyclic", "authority_chain_complete"],
    ),
    # F02: Run/spec binding, runtime deviation (S07–S09)
    "F02": _family(
        "F02",
        "Run/spec binding and runtime deviation",
        ["S07", "S08", "S09"],
        ["query_entity", "query_lineage", "query_sources", "query_state"],
        ["create_file", "tamper_file", "runtime_deviation"],
        _schedule(
            {"subvariant_id": "binding-verification", "weight": 4, "parameters": {}},
            {"subvariant_id": "runtime-deviation", "weight": 4, "parameters": {"noise_rate_ppm": 0}},
        ),
        min_entities=3, max_entities=8, min_artifacts=2, max_artifacts=6,
        positive_requirements=["run_spec_binding_resolved", "deviation_detected"],
        negative_requirements=["no_unbound_run_accepted"],
        checkpoint_types=["results", "provenance_graph"],
        applicable_metrics=["CIV", "PGEM", "VLP"],
        forbidden_conditions=["gold_after_sut", "score_driven_rejection"],
        generation_acceptance_predicates=["unique_entity_ids", "binding_edges_present"],
    ),
    # F03: Provenance graph, evidence penetration (S10–S12)
    "F03": _family(
        "F03",
        "Provenance graph traversal and evidence penetration",
        ["S10", "S11", "S12"],
        ["query_facts", "query_lineage", "trace_evidence", "trace_graph"],
        [],
        _schedule(
            {"subvariant_id": "shallow-trace", "weight": 3, "parameters": {"max_depth": 2, "min_depth": 1}},
            {"subvariant_id": "deep-penetration", "weight": 3, "parameters": {"max_depth": 4, "min_depth": 2}},
        ),
        min_entities=4, max_entities=10, min_artifacts=3, max_artifacts=8,
        positive_requirements=["evidence_atoms_reachable", "graph_path_complete"],
        negative_requirements=["no_unsupported_evidence_claim"],
        checkpoint_types=["provenance_graph", "evidence"],
        applicable_metrics=["CIV", "IF1", "PGEM"],
        forbidden_conditions=["gold_after_sut", "oracle_derived_from_sut"],
        generation_acceptance_predicates=["unique_entity_ids", "graph_acyclic", "evidence_atoms_bound"],
        max_depth=4,
    ),
    # F04: Historical snapshot, as-of (S13–S15)
    "F04": _family(
        "F04",
        "Historical snapshot and as-of state reconstruction",
        ["S13", "S14", "S15"],
        ["query_as_of_state", "query_history", "query_project_current"],
        ["create_version"],
        _schedule(
            {"subvariant_id": "snapshot-current", "weight": 3, "parameters": {}},
            {"subvariant_id": "snapshot-as-of", "weight": 3, "parameters": {"max_depth": 3}},
        ),
        min_entities=3, max_entities=8, min_artifacts=2, max_artifacts=5,
        positive_requirements=["as_of_state_reconstructed", "historical_report_recoverable"],
        negative_requirements=["no_future_state_leak", "no_snapshot_fabrication"],
        checkpoint_types=["asserted_facts", "results"],
        applicable_metrics=["CIV", "VLP", "SF1"],
        forbidden_conditions=["gold_after_sut", "wall_time_dependence"],
        generation_acceptance_predicates=["unique_entity_ids", "snapshot_paths_consistent"],
    ),
    # F05: Stale propagation, reverse impact (S16–S18)
    "F05": _family(
        "F05",
        "Stale propagation and reverse impact analysis",
        ["S16", "S17", "S18"],
        ["impact", "query_lineage", "stale_status"],
        ["raw_invalidation", "external_update"],
        _schedule(
            {"subvariant_id": "single-hop-stale", "weight": 3, "parameters": {"max_depth": 1}},
            {"subvariant_id": "multi-hop-impact", "weight": 3, "parameters": {"max_depth": 3, "branching_factor": 2}},
        ),
        min_entities=4, max_entities=10, min_artifacts=2, max_artifacts=6,
        positive_requirements=["stale_set_complete", "impact_direction_correct"],
        negative_requirements=["no_false_stale", "no_missing_downstream"],
        checkpoint_types=["provenance_graph", "asserted_facts"],
        applicable_metrics=["CIV", "IF1", "FCAA"],
        forbidden_conditions=["gold_after_sut", "participant_output_dependence"],
        generation_acceptance_predicates=["unique_entity_ids", "graph_acyclic", "impact_closure_deterministic"],
        max_depth=3,
    ),
    # F06: Integrity, corruption, ambiguity, fail-closed (S19–S24, S32-B)
    "F06": _family(
        "F06",
        "Integrity verification, corruption and ambiguity handling, fail-closed behavior",
        ["S19", "S20", "S21", "S22", "S23", "S24", "S32-B"],
        ["query_entity", "query_sources", "reconcile_integrity", "stale_status"],
        ["delete_file", "tamper_file", "corrupt_index", "semantic_tamper", "create_file", "delete_tree"],
        _schedule(
            {"subvariant_id": "content-tamper", "weight": 3, "parameters": {"redundancy_factor": 0}},
            {"subvariant_id": "missing-source", "weight": 3, "parameters": {"redundancy_factor": 1}},
            {"subvariant_id": "ambiguous-version", "weight": 2, "parameters": {"branching_factor": 2}},
        ),
        min_entities=3, max_entities=8, min_artifacts=2, max_artifacts=6,
        positive_requirements=["corruption_detected", "fail_closed_not_fail_open"],
        negative_requirements=["no_silent_recovery", "no_unverified_acceptance"],
        checkpoint_types=["results", "evidence"],
        applicable_metrics=["CIV", "ZHR", "FCAA"],
        forbidden_conditions=["gold_after_sut", "fail_open_recovery"],
        generation_acceptance_predicates=["unique_entity_ids", "corruption_sites_deterministic"],
    ),
    # F07: Explicit kernel retrieval modes (S25–S27)
    "F07": _family(
        "F07",
        "Explicit kernel retrieval routing modes",
        ["S25", "S26", "S27"],
        ["query_exact_routing", "query_project_index", "query_text_lexical", "query_text_semantic"],
        [],
        _schedule(
            {"subvariant_id": "exact-mode", "weight": 2, "parameters": {}},
            {"subvariant_id": "lexical-mode", "weight": 2, "parameters": {}},
            {"subvariant_id": "semantic-mode", "weight": 2, "parameters": {}},
        ),
        min_entities=4, max_entities=10, min_artifacts=3, max_artifacts=8,
        positive_requirements=["route_sequence_exact", "explicit_mode_honored"],
        negative_requirements=["no_route_substitution", "no_implicit_fallback"],
        checkpoint_types=["results", "provenance_graph"],
        applicable_metrics=["VLP", "SF1", "PGEM"],
        forbidden_conditions=["gold_after_sut", "implicit_routing"],
        generation_acceptance_predicates=["unique_entity_ids", "route_modes_disjoint"],
    ),
    # F08: Rebuild, transaction, crash/restart (S28–S31, S32-A)
    "F08": _family(
        "F08",
        "Rebuild, transaction, and crash/restart recovery",
        ["S28", "S29", "S30", "S31", "S32-A"],
        ["index", "query_project_current", "reconcile_integrity", "tx_reconcile"],
        ["delete_tree", "delete_file", "corrupt_index", "create_file"],
        _schedule(
            {"subvariant_id": "clean-rebuild", "weight": 3, "parameters": {}},
            {"subvariant_id": "crash-restart", "weight": 3, "parameters": {"redundancy_factor": 1}},
        ),
        min_entities=3, max_entities=8, min_artifacts=2, max_artifacts=6,
        positive_requirements=["rebuild_reproduces_state", "tx_recovery_atomic"],
        negative_requirements=["no_partial_commit", "no_wal_loss"],
        checkpoint_types=["results", "provenance_graph", "evidence"],
        applicable_metrics=["CIV", "FCAA", "ZHR"],
        forbidden_conditions=["gold_after_sut", "warm_cache_dependence"],
        generation_acceptance_predicates=["unique_entity_ids", "rebuild_deterministic"],
    ),
}


def all_families() -> List[Dict[str, Any]]:
    """Return the 8 validated family documents in F01..F08 order."""
    return [validate_task_family(FAMILIES[fid]) for fid in sorted(FAMILIES)]


def get_family(family_id: str) -> Dict[str, Any]:
    """Return a validated copy of one family document."""
    if family_id not in FAMILIES:
        raise KeyError(f"unknown family: {family_id}")
    return validate_task_family(FAMILIES[family_id])
