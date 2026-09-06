"""Public root materialization & byte-identical rebuild (P1A, G01/G02).

The public root contains: 8 family specs, the generator identity, and the 48
public instance directories (descriptor/manifest/actions/query-registry/gold +
physical fixture). Private/hidden plaintext never enters this tree.

Rebuild: re-running the generator in a clean environment must reproduce every
file byte-identically from the public root secret (a fixed 32-byte constant).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

from bench.dsl.cjson import bench_cjson_bytes
from bench.generator.families import all_families
from bench.generator.identity import (
    build_generator_identity,
    generator_identity_digest,
)
from bench.generator.instance import GeneratedInstance, generate_instance, quota_plan
from bench.generator.kdf import PUBLIC_SPLIT_SECRET
from bench.generator.tree import compute_bench_tree_digest_from_dir

PUBLIC_DIRNAME = "public"
INSTANCE_FILENAME_MAP = {
    "descriptor": "descriptor.json",
    "manifest": "manifest.json",
    "actions": "actions.json",
    "registry": "query-registry.json",
    "gold": "gold.json",
}


def _canon_file(obj: Mapping[str, any]) -> bytes:  # type: ignore[name-defined]
    return bench_cjson_bytes(obj) + b"\n"


def instance_dir_name(instance: GeneratedInstance) -> str:
    return instance.display


def write_instance_dir(base: Path, instance: GeneratedInstance) -> None:
    out = base / instance_dir_name(instance)
    out.mkdir(parents=True, exist_ok=False)
    (out / INSTANCE_FILENAME_MAP["descriptor"]).write_bytes(_canon_file(instance.descriptor))
    (out / INSTANCE_FILENAME_MAP["manifest"]).write_bytes(_canon_file(instance.manifest.document))
    (out / INSTANCE_FILENAME_MAP["actions"]).write_bytes(_canon_file(instance.actions))
    (out / INSTANCE_FILENAME_MAP["registry"]).write_bytes(_canon_file(instance.registry))
    (out / INSTANCE_FILENAME_MAP["gold"]).write_bytes(_canon_file(instance.gold))
    fixture_dir = out / "fixture"
    for rel_path, (mode, data) in sorted(instance.fixture_files.items()):
        target = fixture_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if mode == 0o755:
            target.chmod(0o755)


def public_plan() -> List[Tuple[str, str, int]]:
    return [(f, s, o) for f, s, o in quota_plan() if s == "public"]


def write_public_root(root: Path) -> Dict[str, str]:
    """Materialize the 48-instance public root. Returns {display_id: instance_digest}."""
    root = Path(root)
    if root.exists():
        raise FileExistsError(f"public root already exists: {root}")
    (root / "families").mkdir(parents=True)
    (root / "generator").mkdir(parents=True)
    (root / "instances" / PUBLIC_DIRNAME).mkdir(parents=True)

    digests: Dict[str, str] = {}
    for fid, split, ordinal in public_plan():
        instance = generate_instance(
            family_id=fid, split=split, ordinal=ordinal,
            split_secret=PUBLIC_SPLIT_SECRET,
        )
        write_instance_dir(root / "instances" / PUBLIC_DIRNAME, instance)
        digests[instance.display] = instance.instance_digest

    for family in all_families():
        fid = family["family_id"]
        (root / "families" / f"{fid}.json").write_bytes(_canon_file(family))

    source_tree_digest = compute_bench_tree_digest_from_dir(Path(__file__).parent)
    identity = build_generator_identity(source_tree_digest)
    (root / "generator" / "identity.json").write_bytes(_canon_file(identity))

    return digests


def verify_public_root(root: Path) -> Dict[str, object]:
    """Clean-room rebuild check: regenerate every public instance and compare bytes.

    Returns a summary {instances, byte_identical, failures[]}.
    """
    root = Path(root)
    instances_root = root / "instances" / PUBLIC_DIRNAME
    failures: List[str] = []
    checked = 0

    for fid, split, ordinal in public_plan():
        instance = generate_instance(
            family_id=fid, split=split, ordinal=ordinal,
            split_secret=PUBLIC_SPLIT_SECRET,
        )
        live_dir = instances_root / instance_dir_name(instance)
        if not live_dir.is_dir():
            failures.append(f"missing instance dir: {live_dir.name}")
            continue
        checked += 1

        pairs = [
            (INSTANCE_FILENAME_MAP["descriptor"], _canon_file(instance.descriptor)),
            (INSTANCE_FILENAME_MAP["manifest"], _canon_file(instance.manifest.document)),
            (INSTANCE_FILENAME_MAP["actions"], _canon_file(instance.actions)),
            (INSTANCE_FILENAME_MAP["registry"], _canon_file(instance.registry)),
            (INSTANCE_FILENAME_MAP["gold"], _canon_file(instance.gold)),
        ]
        for name, expected_bytes in pairs:
            live = live_dir / name
            if not live.exists() or live.read_bytes() != expected_bytes:
                failures.append(f"{instance.display}/{name}: byte mismatch")

        for rel_path, (mode, data) in sorted(instance.fixture_files.items()):
            live = live_dir / "fixture" / rel_path
            if not live.exists() or live.read_bytes() != data:
                failures.append(f"{instance.display}/fixture/{rel_path}: byte mismatch")

    # family specs byte-identical
    for family in all_families():
        fid = family["family_id"]
        live = root / "families" / f"{fid}.json"
        if not live.exists() or live.read_bytes() != _canon_file(family):
            failures.append(f"families/{fid}.json: byte mismatch")

    return {
        "instances": checked,
        "byte_identical": not failures,
        "failures": failures,
    }
