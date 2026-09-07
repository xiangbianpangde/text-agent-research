"""Deterministic mini-YAML emitter for P1 synthetic workspaces.

Emits the exact YAML subset researchctl's mini_yaml parser accepts:
nested maps, lists of maps, lists of scalars, plain/quoted scalars.
Key order is the caller's insertion order (deterministic by construction).
"""
from __future__ import annotations

import re
from typing import Any, List, Mapping, Sequence

_PLAIN_SAFE = re.compile(r"^[A-Za-z0-9_./@\-]+$")


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        text = value
        if text != "" and _PLAIN_SAFE.fullmatch(text) and not text.endswith(":"):
            return text
        # single-quoted; escape internal single quotes by doubling
        return "'" + text.replace("'", "''") + "'"
    raise TypeError(f"unsupported scalar for mini-YAML: {type(value).__name__}")


def _emit_mapping(mapping: Mapping[str, Any], indent: int, out: List[str]) -> None:
    pad = " " * indent
    for key, value in mapping.items():
        if isinstance(value, Mapping) and value:
            out.append(f"{pad}{key}:")
            _emit_mapping(value, indent + 2, out)
        elif isinstance(value, Mapping):
            out.append(f"{pad}{key}: {{}}")
        elif isinstance(value, (list, tuple)):
            if not value:
                out.append(f"{pad}{key}: []")
            else:
                out.append(f"{pad}{key}:")
                _emit_list(value, indent + 2, out)
        else:
            out.append(f"{pad}{key}: {_scalar(value)}")


def _emit_list(items: Sequence[Any], indent: int, out: List[str]) -> None:
    pad = " " * indent
    for item in items:
        if isinstance(item, Mapping) and item:
            first = True
            sub: List[str] = []
            _emit_mapping(item, indent + 2, sub)
            for i, line in enumerate(sub):
                if i == 0:
                    out.append(f"{pad}- {line.strip()}")
                else:
                    out.append(f"{pad}  {line.strip()}")
            first = False
        elif isinstance(item, Mapping):
            out.append(f"{pad}- {{}}")
        elif isinstance(item, (list, tuple)):
            raise TypeError("nested lists are not part of the mini-YAML subset")
        else:
            out.append(f"{pad}- {_scalar(item)}")


def dumps(document: Mapping[str, Any]) -> str:
    out: List[str] = []
    _emit_mapping(document, 0, out)
    return "\n".join(out) + "\n"


def dumps_frontmatter(document: Mapping[str, Any], body: str) -> str:
    """Emit `---\\n<yaml>\\n---\\n<body>` markdown files."""
    yaml_text = dumps(document)
    return f"---\n{yaml_text}---\n{body}"
