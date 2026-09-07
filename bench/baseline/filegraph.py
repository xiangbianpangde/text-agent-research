"""independent-filegraph-v1 engine (§11, §19.7).

A fully independent B1 implementation built only on the materialized
workspace: BENCH frontmatter (§19.7.2), the facts/evidence/edge ledgers, and
plain files. Imports NOTHING from bench.* or researchctl.* — stdlib only.

Semantics mirror the sealed-Gold compiler's observable projections:
- exact entity lookup, current selection (one-current-or-fail)
- token-multiset-intersection lexical scoring (UCD L/N tokens)
- declared-edges BFS for trace/impact
- fail-closed on tamper (HASH_MISMATCH), missing (SOURCE_MISSING),
  ambiguity (AMBIGUOUS_VERSION), not-found (NOT_FOUND)
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Mapping, Optional, Tuple

BEGIN = b"@@BENCH-FRONTMATTER-BEGIN\n"
END = b"\n@@BENCH-FRONTMATTER-END\n"

BEGIN_LEN = len(BEGIN)
END_LEN = len(END)

SCHEMA_VERSION = "filegraph-frontmatter/v1"
FRONT_KEYS = frozenset({
    "content_hash", "current", "entity_id", "git_commit", "path",
    "relations", "schema_version", "status", "version",
})
RELATION_KEYS = frozenset({"depends_on", "derived_from", "evidence", "sources"})

_B1_RESULT_FIELDS = (
    "entity_id", "version_ref", "path", "content_hash", "git_commit", "status",
    "is_stale", "relation_type", "section", "is_available",
)


class FileGraphError(RuntimeError):
    """Raised with a B1 error_semantic for fail-closed outcomes."""

    def __init__(self, error_semantic: str, detail: str = "") -> None:
        super().__init__(detail or error_semantic)
        self.error_semantic = error_semantic


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _tokenize(text: str) -> List[str]:
    """UCD General_Category L*/N* tokens (approximated with Unicode categories)."""
    out: List[str] = []
    buf: List[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("N"):
            buf.append(ch.lower())
        else:
            if buf:
                out.append("".join(buf))
                buf = []
    if buf:
        out.append("".join(buf))
    return out


def _score(body_text: str, query_text: str) -> int:
    """Integer token multiset intersection (profile: score)."""
    body_tokens = _tokenize(body_text)
    query_tokens = _tokenize(query_text)
    body_multiset: Dict[str, int] = {}
    for tok in body_tokens:
        body_multiset[tok] = body_multiset.get(tok, 0) + 1
    score = 0
    for tok in query_tokens:
        if body_multiset.get(tok, 0) > 0:
            score += 1
            body_multiset[tok] -= 1
    return score


class FileGraph:
    """In-memory B1 state built from one materialized workspace."""

    def __init__(self, workspace: str) -> None:
        self.workspace = Path(workspace)
        self.nodes: Dict[str, Dict[str, Any]] = {}   # ref key: entity_id@version | path
        self.edges: List[Dict[str, str]] = []
        self.facts: List[Dict[str, Any]] = []
        self.evidence_atoms: List[Dict[str, Any]] = []
        self.graph_nodes: List[Dict[str, Any]] = []
        self._load()

    # --- loading -----------------------------------------------------------

    @staticmethod
    def _node_key(entity_id: str, version: str) -> str:
        """Node ref convention: id@version; version-less objects use the bare id
        when it carries an @-kind prefix (external:, raw:, binding:), else id
        with an empty version suffix stripped."""
        if not version:
            return entity_id
        return f"{entity_id}@{version}"

    def _load(self) -> None:
        root = self.workspace
        paths = sorted(
            p for p in root.rglob("*")
            if p.is_file() and not any(
                part.startswith(".") or part == "__pycache__"
                for part in p.relative_to(root).parts
            )
        )
        for path in paths:
            rel = path.relative_to(root).as_posix()
            try:
                data = path.read_bytes()
            except OSError as exc:
                raise FileGraphError("INVALID_UTF8", f"{rel}: {exc}")
            if data.startswith(BEGIN):
                self._load_frontmatter(rel, data)
        self._load_ledger("facts/asserted-facts.cjson", self.facts, expect="array")
        self._load_ledger("facts/graph-nodes.cjson", self.graph_nodes, expect="array")
        self._load_ledger("facts/evidence-atoms.cjson", self.evidence_atoms, expect="array")
        edge_list: List[Dict[str, str]] = []
        self._load_ledger("facts/provenance-edges.cjson", edge_list, expect="array")
        for edge in edge_list:
            if set(edge.keys()) != {"source_ref", "relation", "target_ref"}:
                raise FileGraphError("INVALID_FRONTMATTER", "edge keys mismatch")
            self.edges.append(dict(edge))
        # verify declared edges against known nodes/paths (UNVERIFIED_REF)
        known_refs = set(self.nodes.keys())

        def _known(target: str) -> bool:
            if target in known_refs:
                return True
            # manifest kind prefixes: definition:<id@version>
            if target.startswith("definition:"):
                return target.removeprefix("definition:") in known_refs
            # structural/logical ref kinds never appear as physical nodes
            if ":" in target:
                return True
            return (self.workspace / target).exists()

        for edge in self.edges:
            if not _known(edge["source_ref"]) or not _known(edge["target_ref"]):
                raise FileGraphError("UNVERIFIED_REF", f"edge {edge}")

    def _load_frontmatter(self, rel: str, data: bytes) -> None:
        if not data.startswith(BEGIN):
            return
        end = data.find(END)
        if end < 0:
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: missing end delimiter")
        head = data[BEGIN_LEN:end]
        try:
            front = json.loads(head.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: {exc}")
        if not isinstance(front, dict) or set(front.keys()) != FRONT_KEYS:
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: keys mismatch")
        if front["schema_version"] != SCHEMA_VERSION:
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: schema_version")
        if front["path"] != rel:
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: path mismatch")
        body = data[end + END_LEN:]
        actual_body_hash = "sha256:" + hashlib.sha256(body).hexdigest()
        if front["content_hash"] != actual_body_hash:
            raise FileGraphError("HASH_MISMATCH", f"{rel}: frontmatter body hash mismatch")
        relations = front["relations"]
        if not isinstance(relations, dict) or set(relations.keys()) != RELATION_KEYS:
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: relations keys")
        if front["status"] not in ("valid", "invalid", "stale", "deprecated"):
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: status")

        ref = self._node_key(front["entity_id"], front["version"])
        if ref in self.nodes:
            raise FileGraphError("AMBIGUOUS", f"duplicate node {ref}")
        self.nodes[ref] = {
            "entity_id": front["entity_id"],
            "version_ref": front["version"] or None,
            "path": rel,
            "content_hash": front["content_hash"],
            "git_commit": front["git_commit"],
            "status": front["status"],
            "current": bool(front["current"]),
            "relations": {k: list(v) for k, v in relations.items()},
        }

    def _load_ledger(self, rel: str, sink: List[Dict[str, Any]], *, expect: str) -> None:
        path = self.workspace / rel
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: {exc}")
        if not isinstance(data, list):
            raise FileGraphError("INVALID_FRONTMATTER", f"{rel}: expected {expect}")
        sink.extend(data)

    # --- lookups -----------------------------------------------------------

    def current_ref(self, entity_id: str) -> str:
        candidates = [ref for ref, node in self.nodes.items()
                      if node["entity_id"] == entity_id]
        if not candidates:
            raise FileGraphError("NOT_FOUND", f"entity {entity_id}")
        currents = [ref for ref in candidates if self.nodes[ref]["current"]]
        if len(currents) != 1:
            raise FileGraphError("AMBIGUOUS_VERSION", f"entity {entity_id} current selection")
        return currents[0]

    def resolve(self, target: str) -> str:
        """Exact id@version | id (current) | path lookup (profile: lookup)."""
        target = _nfc(target)
        if target in self.nodes:
            return target
        if target.startswith("definition:"):
            return self.resolve(target.removeprefix("definition:"))
        if (self.workspace / target).is_file():
            matches = [ref for ref, node in self.nodes.items() if node["path"] == target]
            if len(matches) == 1:
                return matches[0]
            raise FileGraphError("AMBIGUOUS", f"path {target}")
        if "@" in target:
            raise FileGraphError("NOT_FOUND", target)
        return self.current_ref(target)

    def node(self, ref: str) -> Dict[str, Any]:
        if ref not in self.nodes:
            raise FileGraphError("NOT_FOUND", ref)
        return self.nodes[ref]

    def result_for_ref_key(self, manifest_ref: str) -> Optional[str]:
        """Map a manifest ref (definition:E001@v1, external:basis-doc, raw:R001,
        artifact:..., organized:X000) to a FileGraph node ref, or None."""
        if manifest_ref in self.nodes:
            return manifest_ref
        if manifest_ref.startswith("definition:"):
            candidate = manifest_ref.removeprefix("definition:")
            return candidate if candidate in self.nodes else None
        # path-bearing kinds: entity_id == workspace path in the manifest rows
        for prefix in ("raw:", "artifact:", "binding:", "run:"):
            if manifest_ref.startswith(prefix):
                rest = manifest_ref.removeprefix(prefix)
                if rest in self.nodes:
                    return rest
                if (self.workspace / rest).exists():
                    return rest
        # organized/report/spec entities are named by bare entity_id
        tail = manifest_ref.split(":", 1)[1] if ":" in manifest_ref else manifest_ref
        if tail in self.nodes:
            return tail
        # last resort: strip a @version suffix
        if "@" in tail:
            base = tail.split("@", 1)[0]
            if base in self.nodes:
                return base
        return None

    def result_row(self, ref: str, *, relation_type: Optional[str] = None) -> Dict[str, Any]:
        node = self.nodes.get(ref)
        if node is None:
            # manifest ref → node key (definition:/raw:/artifact: prefixes)
            candidate = self.result_for_ref_key(ref)
            if candidate is None:
                raise FileGraphError("NOT_FOUND", ref)
            ref = candidate
            node = self.nodes[ref]
        is_stale = node["status"] == "stale"
        version_ref = (
            f"{node['entity_id']}@{node['version_ref']}" if node["version_ref"] else None
        )
        # Manifest ref convention so the evaluator's resolver binds the row:
        # versioned definitions carry the definition: prefix; other nodes use
        # their bare node key (external:, or entity id).
        if node["version_ref"] and node["path"].startswith("definitions/"):
            manifest_ref = f"definition:{version_ref}"
        elif node["path"].startswith("external/"):
            manifest_ref = node["entity_id"]
        elif node["version_ref"]:
            manifest_ref = f"definition:{version_ref}"
        else:
            manifest_ref = node["entity_id"]
        return {
            "ref": manifest_ref,
            "entity_id": node["entity_id"],
            "version_ref": version_ref,
            "path": node["path"],
            "content_hash": node["content_hash"],
            "git_commit": node["git_commit"],
            "status": None,
            "is_stale": is_stale,
            "relation_type": relation_type,
            "section": None,
            "is_available": (self.workspace / node["path"]).is_file(),
        }

    # --- graph traversal -----------------------------------------------------

    def bfs(self, root_ref: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Declared-edges BFS downstream from root_ref (edges + visited node rows)."""
        adjacency: Dict[str, List[Dict[str, str]]] = {}
        for edge in self.edges:
            adjacency.setdefault(edge["source_ref"], []).append(edge)
        visited = {root_ref}
        queue = [root_ref]
        edges_out: List[Dict[str, str]] = []
        while queue:
            current = queue.pop(0)
            for edge in sorted(
                adjacency.get(current, []),
                key=lambda e: (e["relation"], e["target_ref"]),
            ):
                edges_out.append(dict(edge))
                if edge["target_ref"] not in visited:
                    visited.add(edge["target_ref"])
                    queue.append(edge["target_ref"])
        # visited is in manifest-ref space; map back to node keys for rows
        manifest_to_node = {
            self._manifest_ref_for(key): key for key in self.nodes
        }
        node_by_ref = {row["ref"]: row for row in self.graph_nodes}
        node_rows = [
            dict(node_by_ref[ref])
            for ref in sorted(visited)
            if ref in node_by_ref
        ]
        edges_out.sort(key=lambda e: (e["source_ref"], e["relation"], e["target_ref"]))
        return node_rows, edges_out

    def reverse_closure(self, root_ref: str) -> List[str]:
        """Upstream closure (who depends on me) — reverse BFS."""
        reverse: Dict[str, List[str]] = {}
        for edge in self.edges:
            reverse.setdefault(edge["target_ref"], []).append(edge["source_ref"])
        visited = {root_ref}
        queue = [root_ref]
        while queue:
            current = queue.pop(0)
            for nxt in sorted(reverse.get(current, [])):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return sorted(visited)

    # --- B1 operations --------------------------------------------------------

    def op_query_entity(self, target: str) -> Dict[str, Any]:
        ref = self.resolve(target)
        node = self.node(ref)
        return {
            "results": [self.result_row(ref)],
            "provenance_graph": None,
            "route_sequence": ["current"],
            "version_bindings": [
                {"subject": f["subject"], "value": f["value"]}
                for f in self.facts
                if f["subject"] == ref and f["predicate"] == "bound_version"
            ],
        }

    def op_query_facts(self, target: str, predicates: List[str]) -> Dict[str, Any]:
        ref = self.resolve(target)
        rows = [
            dict(f) for f in self.facts
            if f["subject"] == ref
            and (not predicates or f["predicate"] in predicates)
        ]
        return {
            "asserted_facts": rows,
            "route_sequence": ["current"],
        }

    def op_query_lineage(self, target: str) -> Dict[str, Any]:
        ref = self.resolve(target)
        node = self.node(ref)
        entity_id = node["entity_id"]
        versions = sorted(
            (r for r, n in self.nodes.items() if n["entity_id"] == entity_id),
            key=lambda r: int(r.rsplit("v", 1)[1]) if r.rsplit("v", 1)[1].isdigit() else 0,
        )
        rows = [self.result_row(r) for r in versions]
        return {
            "results": rows,
            "lineage": [self.nodes[r]["version_ref"] for r in versions],
            "route_sequence": ["current"],
        }

    def op_query_state(self, target: str) -> Dict[str, Any]:
        ref = self.resolve(target)
        row = self.result_row(ref)
        return {
            "results": [row],
            "state_assertions": [{"ref": ref, "is_stale": row["is_stale"]}],
            "route_sequence": ["current"],
        }

    def op_query_external_basis(self, target: str) -> Dict[str, Any]:
        ref = self.resolve(target)
        pinned = [
            dict(f) for f in self.facts
            if f["subject"] == ref and f["predicate"] == "pinned_external_value"
        ]
        source_facts = [
            f for f in self.facts
            if f["subject"] == ref and f["predicate"] == "authority_source"
        ]
        evidence = [
            {"kind": "external_pin", "source_ref": f["value"],
             "content_hash": self._external_pin_hash(f["value"])}
            for f in source_facts
        ]
        return {
            "asserted_facts": pinned,
            "evidence": evidence,
            "route_sequence": ["current"],
        }

    def _external_pin_hash(self, source_ref: str) -> str:
        """Manifest-bound pin hash: the ledger row's content_hash (§19.7.2 body)."""
        row = next((r for r in self.graph_nodes if r["ref"] == source_ref), None)
        if row is not None and row.get("content_hash"):
            return row["content_hash"]
        node = self.nodes.get(source_ref)
        if node is not None:
            path = self.workspace / node["path"]
            if path.is_file():
                data = path.read_bytes()
                if data.startswith(BEGIN):
                    end = data.find(END)
                    body = data[end + END_LEN:]
                    return "sha256:" + hashlib.sha256(body).hexdigest()
                return "sha256:" + hashlib.sha256(data).hexdigest()
        raise FileGraphError("UNVERIFIED_REF", source_ref)

    @staticmethod
    def _manifest_ref(node_key: str) -> str:
        """Node key → manifest ref convention (definition: prefix for defs)."""
        node = None
        return node_key

    def _manifest_ref_for(self, node_key: str) -> str:
        node = self.nodes.get(node_key)
        if node is None:
            return node_key
        if node["version_ref"] and node["path"].startswith("definitions/"):
            return f"definition:{node['entity_id']}@{node['version_ref']}"
        return node_key

    def op_query_sources(self, target: str, relation_types: List[str]) -> Dict[str, Any]:
        ref = self.resolve(target)
        source_entity = self.node(ref)["entity_id"]
        manifest_ref = self._manifest_ref_for(ref)
        rows = []
        for edge in self.edges:
            if edge["source_ref"] != manifest_ref:
                continue
            if relation_types and edge["relation"] not in relation_types:
                continue
            if edge["target_ref"] in self.nodes:
                row = self.result_row(edge["target_ref"], relation_type="based_on")
                # Gold semantics: entity_id identifies the SOURCE object
                row["entity_id"] = source_entity
                row["version_ref"] = None
                rows.append(row)
        rows.sort(key=lambda r: (r["entity_id"], r["version_ref"] or ""))
        return {
            "results": rows,
            "route_sequence": ["sources"],
        }

    def op_trace(self, target: str, *, with_evidence: bool) -> Dict[str, Any]:
        ref = self.resolve(target)
        root_ref = self._manifest_ref_for(ref)
        node_rows, edge_rows = self.bfs(root_ref)
        graph = {"nodes": node_rows, "edges": edge_rows}
        out: Dict[str, Any] = {
            "provenance_graph": graph,
            "route_sequence": ["trace"],
        }
        if with_evidence:
            graph_refs = {row["ref"] for row in node_rows}
            out["evidence"] = [
                dict(atom) for atom in self.evidence_atoms
                if atom["artifact_ref"] in graph_refs
            ]
        return out

    def op_history(self, as_of: Optional[str], predicates: Optional[List[str]] = None, *,
                   as_of_mode: bool) -> Dict[str, Any]:
        rows = [
            dict(f) for f in self.facts
            if (not predicates or f["predicate"] in predicates)
            and (as_of is None or f["occurred_at"] <= as_of)
        ]
        node_by_ref = {row["ref"]: row for row in self.graph_nodes}
        if as_of is None:
            visible = sorted(node_by_ref.keys())
        else:
            visible = sorted(
                ref for ref, row in node_by_ref.items()
                if row["lifecycle_start"] <= as_of
            )
        results = []
        for ref in visible:
            src = node_by_ref[ref]
            results.append({
                "ref": ref,
                "entity_id": src["entity_id"],
                "version_ref": src["version_ref"],
                "path": src["path"],
                "content_hash": src["content_hash"],
                "git_commit": None if as_of_mode else src["git_commit"],
                "status": None,
                "is_stale": False,
                "relation_type": None,
                "section": None,
                "is_available": (
                    (self.workspace / src["path"]).exists() if src["path"] else True
                ),
            })
        return {
            "asserted_facts": rows,
            "results": results,
            "route_sequence": ["history"],
            "as_of": as_of,
        }

    def op_impact(self, target: str) -> Dict[str, Any]:
        ref = self.resolve(target)
        root_ref = self._manifest_ref_for(ref)
        closure = self.reverse_closure(root_ref)
        kind_by_ref = {row["ref"]: row["kind"] for row in self.graph_nodes}
        row_by_ref = {row["ref"]: row for row in self.graph_nodes}
        eligible_kinds = {"run", "organized_result", "organized_analysis", "report", "report_claim"}
        eligible = {
            r for r in closure
            if kind_by_ref.get(r) in eligible_kinds and r != ref
        }
        impact_set = sorted(eligible)
        # propagation subgraph (Gold semantics): nodes = root + dependents;
        # edges = ledger edges with BOTH endpoints inside that node set.
        node_set = {root_ref} | set(impact_set)
        node_by_ref = {row["ref"]: row for row in self.graph_nodes}
        node_rows = [dict(node_by_ref[r]) for r in sorted(node_set) if r in node_by_ref]
        edge_rows = sorted(
            (dict(e) for e in self.edges
             if e["source_ref"] in node_set and e["target_ref"] in node_set),
            key=lambda e: (e["source_ref"], e["relation"], e["target_ref"]),
        )
        results = []
        for ref_key in impact_set:
            row = dict(row_by_ref[ref_key])
            results.append({
                "ref": ref_key,
                "entity_id": row["entity_id"],
                "version_ref": row["version_ref"],
                "path": row["path"],
                "content_hash": row["content_hash"],
                "git_commit": row["git_commit"],
                "status": None,
                "is_stale": row["status"] == "stale",
                "relation_type": None,
                "section": None,
                "is_available": (self.workspace / row["path"]).is_file() if row["path"] else True,
            })
        return {
            "results": results,
            "stale_set": [],
            "provenance_graph": {"nodes": node_rows, "edges": edge_rows},
            "route_sequence": ["impact"],
            "_impact_set": impact_set,
        }

    def op_query_maximal(self, target: str) -> Dict[str, Any]:
        """Maximal B1 envelope for `query --entity` (§19.6.2 shares argv across
        query_entity/facts/lineage/state/external_basis; the evaluator picks
        the projected subset per operation)."""
        ref = self.resolve(target)
        node = self.node(ref)
        manifest_ref = self._manifest_ref_for(ref)
        # results: all versions of the entity (lineage-consistent)
        entity_id = node["entity_id"]
        versions = sorted(
            (r for r, n in self.nodes.items() if n["entity_id"] == entity_id),
            key=lambda r: (
                int(r.rsplit("@v", 1)[1]) if r.rsplit("@v", 1)[1].isdigit() else 0,
                r,
            ),
        )
        results = [self.result_row(r) for r in versions]
        # facts projection: all subject facts; external-kind targets project
        # their pinned value (the authority_source fact routes the pin evidence).
        subject_ref = manifest_ref
        if node["path"].startswith("external/"):
            facts = [
                dict(f) for f in self.facts
                if f["subject"] == subject_ref
                and f["predicate"] == "pinned_external_value"
            ]
        else:
            facts = [dict(f) for f in self.facts if f["subject"] == subject_ref]
        evidence = [
            {"kind": "external_pin", "source_ref": f["value"],
             "content_hash": self._external_pin_hash(f["value"])}
            for f in self.facts
            if f["subject"] == subject_ref and f["predicate"] == "authority_source"
        ]
        node_rows, edge_rows = self.bfs(manifest_ref)
        return {
            "results": results,
            "asserted_facts": facts,
            "evidence": evidence,
            "provenance_graph": {"nodes": node_rows, "edges": edge_rows},
            "route_sequence": ["current"],
            "as_of": None,
        }

    def op_lexical(self, text: str, semantic: bool) -> Dict[str, Any]:
        """Gold semantics: fact-value token containment (all query tokens must
        appear in the fact's value tokens); matching subjects → result rows."""
        tokens = set(re.findall(r"[a-z0-9]+", str(text or "").lower()))
        refs = set()
        for fact in self.facts:
            value_tokens = set(re.findall(r"[a-z0-9]+", str(fact["value"]).lower()))
            if tokens and tokens.issubset(value_tokens):
                refs.add(str(fact["subject"]))
        results = []
        for ref in sorted(refs):
            node_key = self.result_for_ref_key(ref) or (
                ref if ref in self.nodes else None)
            if node_key is None:
                continue
            results.append(self.result_row(node_key))
        return {
            "results": results,
            "retrieval_mode": "semantic" if semantic else "lexical",
            "route_sequence": ["semantic" if semantic else "query"],
        }
