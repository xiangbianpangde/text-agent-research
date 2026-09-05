"""Pure, implementation-independent Oracle state machine."""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, Iterable, List, Mapping, Set, Tuple

from .manifest import OracleManifest, digest_json


@dataclasses.dataclass(frozen=True)
class OracleState:
    objects: Mapping[str, Mapping[str, Any]]
    facts: tuple[Mapping[str, Any], ...]
    evidence_atoms: tuple[Mapping[str, Any], ...]
    relations: tuple[Mapping[str, Any], ...]
    external_sources: Mapping[str, Mapping[str, Any]]
    snapshots: Mapping[str, Mapping[str, Any]]
    clock: str
    invalid_refs: frozenset[str] = frozenset()
    stale_refs: frozenset[str] = frozenset()
    changed_refs: frozenset[str] = frozenset()
    transaction_stage: str | None = None

    @classmethod
    def from_manifest(cls, manifest: OracleManifest) -> "OracleState":
        doc = manifest.document
        objects = {row["ref"]: dict(row) for row in (*doc["entities"], *doc["artifacts"])}
        return cls(
            objects=objects,
            facts=tuple(dict(row) for row in doc["facts"]),
            evidence_atoms=tuple(dict(row) for row in doc["evidence_atoms"]),
            relations=tuple(dict(row) for row in doc["relations"]),
            external_sources={row["ref"]: dict(row) for row in doc["external_sources"]},
            snapshots={row["snapshot_id"]: dict(row) for row in doc["snapshots"]},
            clock=str(doc["clock"]),
        )

    def object_for(self, ref_or_id: str) -> Mapping[str, Any] | None:
        if ref_or_id in self.objects:
            return self.objects[ref_or_id]
        matches = [row for row in self.objects.values() if row["entity_id"] == ref_or_id or row.get("version_ref") == ref_or_id]
        return matches[0] if len(matches) == 1 else None

    def facts_for(self, subject: str, predicate: str | None = None) -> List[Mapping[str, Any]]:
        return [row for row in self.facts if row["subject"] == subject and (predicate is None or row["predicate"] == predicate)]

    def reverse_closure(self, root: str) -> Set[str]:
        """Return dependents because relation direction is source depends on target."""
        closure = {root}
        changed = True
        while changed:
            changed = False
            for edge in self.relations:
                if edge["target_ref"] in closure and edge["source_ref"] not in closure:
                    closure.add(edge["source_ref"])
                    changed = True
        return closure

    def dependency_subgraph(self, root: str) -> Dict[str, List[Mapping[str, Any]]]:
        nodes = {root}
        edges: List[Mapping[str, Any]] = []
        changed = True
        while changed:
            changed = False
            for edge in self.relations:
                if edge["source_ref"] in nodes and edge not in edges:
                    edges.append(edge)
                    if edge["target_ref"] not in nodes:
                        nodes.add(edge["target_ref"])
                        changed = True
        node_rows = [self.objects[ref] for ref in sorted(nodes) if ref in self.objects]
        edge_rows = sorted(edges, key=lambda row: (row["source_ref"], row["relation"], row["target_ref"]))
        return {"nodes": node_rows, "edges": edge_rows}

    def apply(self, action: Mapping[str, Any]) -> "OracleState":
        if action["action"] == "mutate":
            kind = action["type"]
            target = action["target"]
            if kind == "external_update":
                externals = {key: dict(value) for key, value in self.external_sources.items()}
                if target not in externals:
                    raise ValueError(f"unknown external source: {target}")
                externals[target]["latest_content_hash"] = action["content_hash"]
                externals[target]["latest_value"] = action.get("content")
                return dataclasses.replace(self, external_sources=externals, changed_refs=self.changed_refs | {target})
            if kind == "semantic_change":
                if self.object_for(target) is None:
                    raise ValueError(f"unknown semantic change target: {target}")
                return dataclasses.replace(self, changed_refs=self.changed_refs | {target})
            if kind == "raw_invalidation":
                if self.object_for(target) is None:
                    raise ValueError(f"unknown invalidation target: {target}")
                stale = self.reverse_closure(target) - {target}
                return dataclasses.replace(
                    self,
                    invalid_refs=self.invalid_refs | {target},
                    stale_refs=self.stale_refs | stale,
                    changed_refs=self.changed_refs | {target},
                )
        if action["action"] == "external_crash":
            return dataclasses.replace(self, transaction_stage=str(action["pause_at"]))
        return self

    def summary(self) -> Dict[str, Any]:
        value = {
            "clock": self.clock,
            "object_refs": sorted(self.objects),
            "invalid_refs": sorted(self.invalid_refs),
            "stale_refs": sorted(self.stale_refs),
            "changed_refs": sorted(self.changed_refs),
            "transaction_stage": self.transaction_stage,
        }
        value["state_digest"] = digest_json(value)
        return value
