"""Participant artifact binding (§10): exact tar SHA-256 + safety rules.

A participant tar may contain only normalized relative regular files and
directories. Absolute paths, '..' components, symlinks, hardlinks, devices,
FIFOs, sockets, AppleDouble files, and PAX/xattr headers are rejected.
"""
from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Mapping


ADAPTER_PROTOCOL = "sut-adapter/v1"
B1_API_VERSION = "b1-kernel/v1"

ARTIFACT_TYPES = frozenset({"participant_tar"})


class ArtifactBindingError(ValueError):
    """Raised when a participant artifact violates §10 safety rules."""


def validate_tar_safety(tar_path: str | Path) -> List[str]:
    """Validate member safety of a participant tar; returns member names."""
    members: List[str] = []
    with tarfile.open(tar_path, "r") as tf:
        for member in tf.getmembers():
            name = member.name
            pax = getattr(member, "pax_headers", None)
            if pax:
                raise ArtifactBindingError(f"PAX headers forbidden: {name!r}: {sorted(pax)}")
            if name.startswith("/") or name.startswith("\\"):
                raise ArtifactBindingError(f"absolute path forbidden: {name!r}")
            parts = PurePosixPath(name).parts
            if not parts:
                raise ArtifactBindingError(f"empty member name: {name!r}")
            for part in parts:
                if part in ("..", "."):
                    raise ArtifactBindingError(f"path traversal forbidden: {name!r}")
                if part.startswith("._"):
                    raise ArtifactBindingError(f"AppleDouble file forbidden: {name!r}")
                if "\x00" in part:
                    raise ArtifactBindingError(f"NUL byte in member name: {name!r}")
            if member.issym() or member.islnk():
                raise ArtifactBindingError(f"link forbidden: {name!r}")
            if not (member.isreg() or member.isdir()):
                raise ArtifactBindingError(
                    f"only regular files/directories allowed: {name!r} (type={member.type!r})"
                )
            members.append(name)
    if not members:
        raise ArtifactBindingError("participant tar contains no members")
    return members


def tar_sha256(tar_path: str | Path) -> str:
    """Exact-byte SHA-256 of the participant tar (mandatory binding, §10)."""
    digest = hashlib.sha256()
    with open(tar_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def validate_entrypoint(entrypoint: str, unpacked_root: str | Path) -> Path:
    """Entrypoint must resolve strictly inside the unpacked artifact root."""
    if not entrypoint or entrypoint.startswith("/"):
        raise ArtifactBindingError(f"entrypoint must be relative: {entrypoint!r}")
    parts = PurePosixPath(entrypoint).parts
    if any(part in ("..", ".") for part in parts):
        raise ArtifactBindingError(f"entrypoint path traversal: {entrypoint!r}")
    root = Path(unpacked_root).resolve()
    target = (root / entrypoint).resolve()
    if root not in target.parents and target != root:
        raise ArtifactBindingError(f"entrypoint escapes artifact root: {entrypoint!r}")
    if not target.exists():
        raise ArtifactBindingError(f"entrypoint missing in unpacked root: {entrypoint!r}")
    return target


def build_participant_artifact(
    *,
    participant_id: str,
    participant_version: str,
    tar_path: str | Path,
    entrypoint: str,
    seed_mode: str,
    adapter_digest: str,
    declared_kernel_dependencies: List[str],
    source_commit: str | None = None,
    artifact_type: str = "participant_tar",
) -> Dict[str, Any]:
    """Build a participant-artifact/v1 binding object after full validation."""
    if artifact_type not in ARTIFACT_TYPES:
        raise ArtifactBindingError(f"unsupported artifact type: {artifact_type!r}")
    if not participant_id or not participant_version:
        raise ArtifactBindingError("participant id/version required")
    if seed_mode not in ("deterministic", "explicit_run_seed", "diagnostic"):
        raise ArtifactBindingError(f"invalid seed_mode: {seed_mode!r}")
    validate_tar_safety(tar_path)
    if not adapter_digest.startswith("sha256:") or len(adapter_digest) != 71:
        raise ArtifactBindingError("adapter_digest must be a sha256 digest")
    obj: Dict[str, Any] = {
        "adapter_digest": adapter_digest,
        "adapter_protocol": ADAPTER_PROTOCOL,
        "artifact_digest": tar_sha256(tar_path),
        "artifact_type": artifact_type,
        "b1_api_version": B1_API_VERSION,
        "declared_kernel_dependencies": sorted(declared_kernel_dependencies),
        "entrypoint": entrypoint,
        "participant_id": participant_id,
        "participant_version": participant_version,
        "schema_version": "participant-artifact/v1",
        "seed_mode": seed_mode,
    }
    if source_commit is not None:
        obj["source_commit"] = source_commit
    return obj
