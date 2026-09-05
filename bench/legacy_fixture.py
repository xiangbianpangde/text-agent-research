"""Benchmark-owned helpers for the current public toy fixture.

These helpers intentionally do not import the SUT. They exist only to keep the
legacy conformance scenarios operational until P0.3 replaces them with the DSL
and an independently compiled Oracle state.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import subprocess
from typing import Iterator


BOOTSTRAP_V1 = """schema_version: 1
entity_id: H003
version_ref: H003@v1
previous: null
body:
  kind: Hypothesis
  population: text_agent_long_context
  outcome: retrieval_recall
  threshold: 0.9
  method: index_scan
"""

BOOTSTRAP_APPROVED = """definition: H003
ref: H003@v1
approved_at: 2026-08-01T00:00:00+08:00
basis_git_commit: bootstrap
"""

DEFAULT_BODY = {
    "kind": "Hypothesis",
    "population": "text_agent_long_context",
    "outcome": "retrieval_recall",
    "threshold": 0.95,
    "method": "hybrid_scan",
}


def _canonical_json(value) -> str:
    if isinstance(value, dict):
        parts = []
        for key in sorted(value, key=lambda item: item.encode("utf-8")):
            item = value[key]
            if item is None:
                continue
            parts.append(f"{json.dumps(key)}:{_canonical_json(item)}")
        return "{" + ",".join(parts) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_canonical_json(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _definition_hash(entity: str, previous: str, body: dict) -> str:
    version = int(previous.rsplit("@v", 1)[1]) + 1
    wrapped = {
        "schema_version": 1,
        "entity_id": entity,
        "version_ref": f"{entity}@v{version}",
        "previous": previous,
        "body": body,
    }
    digest = hashlib.sha256(_canonical_json(wrapped).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def dump_mapping(mapping: dict, indent: int = 0) -> str:
    """Serialize the small mapping/list/scalar subset used by the toy fixture."""
    lines = []
    prefix = "  " * indent
    for key, value in mapping.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(dump_mapping(value, indent + 1).rstrip("\n"))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                lines.append(f"{prefix}  - {item}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines) + "\n"


def write_bootstrap(root: str) -> None:
    """Create the legacy H003 bootstrap without importing participant code."""
    definition_dir = os.path.join(root, "definitions", "H003")
    os.makedirs(definition_dir, exist_ok=True)
    with open(os.path.join(definition_dir, "H003@v1.yaml"), "w", encoding="utf-8") as handle:
        handle.write(BOOTSTRAP_V1)
    with open(os.path.join(definition_dir, "APPROVED.yaml"), "w", encoding="utf-8") as handle:
        handle.write(BOOTSTRAP_APPROVED)
    with open(os.path.join(definition_dir, "BOOTSTRAP.yaml"), "w", encoding="utf-8") as handle:
        handle.write(
            "schema_version: 1\nentity: H003\nrole: bootstrap-metadata\n"
            "created_by: external-controlled-bootstrap\n"
        )

    approval_dir = os.path.join(root, ".auth", "approvals")
    os.makedirs(approval_dir, exist_ok=True)
    approval = {
        "approval_id": "APR-000001",
        "definition": "H003",
        "previous": "H003@v1",
        "proposed_definition_hash": _definition_hash("H003", "H003@v1", DEFAULT_BODY),
        "change_type": ["scope_change"],
        "approved_by": "scientist-1",
        "valid": True,
    }
    with open(os.path.join(approval_dir, "APR-000001.yaml"), "w", encoding="utf-8") as handle:
        handle.write(dump_mapping(approval))

    registry_path = os.path.join(root, ".auth", "registry.yaml")
    with open(registry_path, encoding="utf-8") as handle:
        registry = handle.read()
    if "AUTH-0002" not in registry:
        registry += (
            "\n  - ref: AUTH-0002\n"
            "    grantee: text-agent\n"
            "    scope: revise-definition\n"
            "    valid: true\n"
        )
        with open(registry_path, "w", encoding="utf-8") as handle:
            handle.write(registry)

    subprocess.run(["git", "-C", root, "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", root, "commit", "-m", "benchmark bootstrap"],
        check=True,
        capture_output=True,
    )
    head = subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip()
    pin_path = os.path.join(os.path.dirname(os.path.abspath(root)), "bootstrap-pin.yaml")
    with open(pin_path, "w", encoding="utf-8") as handle:
        handle.write(f"schema_version: 1\nbootstrap_git_commit: {head}\n")


@contextlib.contextmanager
def hold_freeze_lock(root: str) -> Iterator[None]:
    """Hold the public lock path so a participant process observes contention."""
    lock_dir = os.path.join(root, ".researchctl", "locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, "freeze.lock")
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
