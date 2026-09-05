"""Canonical provenance-graph equality with no subset credit."""
from __future__ import annotations

import json
from typing import Any, Iterable, Mapping, Tuple


def _rows(values: Iterable[Mapping[str, Any]]) -> Tuple[str, ...]:
    return tuple(sorted(json.dumps(dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in values))


def canonical_graph(graph: Mapping[str, Any] | None) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    if graph is None:
        return (), ()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ("<invalid>",), ("<invalid>",)
    return _rows(nodes), _rows(edges)


def graph_exact_match(predicted: Mapping[str, Any] | None, gold: Mapping[str, Any]) -> bool:
    return canonical_graph(predicted) == canonical_graph(gold)
