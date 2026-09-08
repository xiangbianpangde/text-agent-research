"""Campaign runner: drive the lifecycle T0..T3 with real generated roots.

Deterministic given (participant digests, split secrets, attestation strings).
Roots contain the materialized participant-visible workspace fixtures only —
Oracle manifests, actions, Gold, and split secrets never enter a root tree.

T4+ (execution) is intentionally out of scope here; it lands with the B1
runner and baseline integration.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

from bench.campaign import state as cam
from bench.generator.identity import (
    build_release_identity,
    build_release_lockfile,
    lockfile_digest,
    release_digest,
)
from bench.generator.instance import generate_instance, quota_plan
from bench.generator.kdf import PUBLIC_SPLIT_SECRET
from bench.generator.models import build_family_identity
from bench.generator.families import all_families
from bench.generator.tree import (
    compute_bench_tree_digest_from_dir,
    compute_bench_tree_digest_from_entries,
)

SPLIT_SECRETS_REQUIRED = ("public", "private", "local-hidden")


class CampaignRunnerError(RuntimeError):
    pass


@dataclass
class CampaignMaterial:
    """Everything the evaluator holds for one campaign (never published raw)."""

    manifest: Dict[str, object]
    events: List[Dict[str, object]]
    release_identity: Dict[str, object]
    release: str
    instance_digests: Dict[Tuple[str, str, int], str]
    root_trees: Dict[str, Dict[str, Tuple[int, bytes]]]
    root_tree_digests: Dict[str, str]
    commitments: Dict[str, str]
    materialization_evidence_digest_value: Optional[str] = None


def build_release(secrets: Mapping[str, bytes]) -> Tuple[Dict[str, object], str, Dict[Tuple[str, str, int], str]]:
    """Generate all 144 instances and assemble the release identity chain."""
    missing = [s for s in SPLIT_SECRETS_REQUIRED if s not in secrets]
    if missing:
        raise CampaignRunnerError(f"missing split secrets: {missing}")
    for name in SPLIT_SECRETS_REQUIRED:
        if len(secrets[name]) != 32:
            raise CampaignRunnerError(f"split secret {name!r} must be 32 bytes")

    families = all_families()
    identities = [build_family_identity(f) for f in families]
    digests: Dict[Tuple[str, str, int], str] = {}
    entries = []
    for fid, split, ordinal in quota_plan():
        inst = generate_instance(family_id=fid, split=split, ordinal=ordinal, split_secret=secrets[split])
        digests[(fid, split, ordinal)] = inst.instance_digest
        entries.append({
            "family_id": fid,
            "split": split,
            "ordinal": ordinal,
            "instance_digest": inst.instance_digest,
        })
    lockfile = build_release_lockfile(entries)
    identity = build_release_identity(
        b1_api_digest=_b1_api_digest(),
        family_identities=identities,
        lockfile=lockfile,
    )
    return identity, release_digest(identity), digests


_B1_API_CACHE: Optional[str] = None


def _b1_api_digest() -> str:
    """SHA-256 over bench-cjson of the frozen b1-api/v1 object (§19.6.2)."""
    global _B1_API_CACHE
    if _B1_API_CACHE is None:
        import json

        from bench.dsl.cjson import bench_cjson_digest

        contract = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "ResearchCTL-Bench-P1-Contract.md"
        if not contract.exists():
            contract = Path(__file__).resolve().parents[2] / "ResearchCTL-Bench-P1-Contract.md"
        text = contract.read_text(encoding="utf-8")
        obj = None
        import re

        for m in re.finditer(r"```json\n(.*?)\n```", text, re.S):
            if '"kernel_version": "b1-kernel/v1"' in m.group(1):
                obj = json.loads(m.group(1))
                break
        if obj is None:
            raise CampaignRunnerError("b1-api/v1 object not found in frozen contract")
        digest = bench_cjson_digest(obj)
        expected = "sha256:e8cf1488cc32be80a53d8c8e803d9182c59623abd488c564ce504655741f8e1e"
        if digest != expected:
            raise CampaignRunnerError(
                f"b1-api/v1 digest mismatch: computed {digest}, contract freezes {expected}"
            )
        _B1_API_CACHE = digest
    return _B1_API_CACHE


def build_root_tree(split: str, secrets: Mapping[str, bytes]) -> Tuple[Dict[str, Tuple[int, bytes]], Dict[str, str]]:
    """Build one split's participant-visible root tree (fixtures only)."""
    files: Dict[str, Tuple[int, bytes]] = {}
    per_instance: Dict[str, str] = {}
    for fid, sp, ordinal in quota_plan():
        if sp != split:
            continue
        inst = generate_instance(family_id=fid, split=sp, ordinal=ordinal, split_secret=secrets[sp])
        prefix = inst.display
        per_instance[prefix] = inst.instance_digest
        for rel_path, (mode, data) in inst.fixture_files.items():
            files[f"{prefix}/{rel_path}"] = (mode, data)
    return files, per_instance


def create_campaign(
    *,
    participant_digests: List[str],
    secrets: Mapping[str, bytes],
    isolation_profile_digest: str,
    network_policy_digest: str,
    created_at_attestation: str,
    materialized_at_attestation: str,
    materialize_dir: Optional[Path] = None,
) -> CampaignMaterial:
    """Drive T0..T3: freeze artifacts, create roots, commit, materialize."""
    identity, rel_dg, instance_digests = build_release(secrets)

    manifest = cam.initial_manifest(
        release_digest=rel_dg,
        isolation_profile_digest=isolation_profile_digest,
        network_policy_digest=network_policy_digest,
        created_at_attestation=created_at_attestation,
    )
    events: List[Dict[str, object]] = []
    previous: Optional[str] = None
    seq = 0

    def advance(to_state: str, payload: Dict[str, object], event_payload: Dict[str, object]) -> Dict[str, object]:
        nonlocal previous, seq, manifest
        event = cam.build_event(
            manifest=manifest, to_state=to_state, payload=payload,
            seq=seq, previous_event_digest=previous, event_payload=event_payload,
        )
        event = cam.seal_event(event)
        events.append(event)
        previous = event["event_digest"]
        seq += 1
        manifest = cam.apply_transition(manifest, to_state=to_state, payload=payload)
        return manifest

    # T0: freeze participant artifacts
    parts_sorted = cam.sort_participant_digests(participant_digests)
    asets = cam.artifact_set_digest(parts_sorted)
    cid = cam.campaign_id(artifact_set=asets, created_at_attestation=created_at_attestation, release_digest=rel_dg)
    cident = cam.campaign_identity(
        artifact_set=asets, created_at_attestation=created_at_attestation,
        isolation_profile_digest=isolation_profile_digest,
        network_policy_digest=network_policy_digest, release_digest=rel_dg,
    )
    cdg = cam.campaign_digest(cident)
    t0_payload = {
        "artifact_set_digest": asets,
        "campaign_digest": cdg,
        "campaign_id": cid,
        "participant_artifact_digests_sorted": parts_sorted,
    }
    manifest = advance("ARTIFACTS_FROZEN", t0_payload, t0_payload)

    # T1: create private + hidden root trees and bind commitments
    root_trees: Dict[str, Dict[str, Tuple[int, bytes]]] = {}
    root_digests: Dict[str, str] = {}
    commitments: Dict[str, str] = {}
    for split, kind in (("private", "private"), ("local-hidden", "hidden")):
        tree, _per = build_root_tree(split, secrets)
        tree_dg = compute_bench_tree_digest_from_entries(tree)
        root_trees[split] = tree
        root_digests[split] = tree_dg
        commitments[kind] = cam.root_commitment(campaign=cid, root_kind=kind, root_tree_digest=tree_dg)
    t1_payload = {
        "private_root_commitment": commitments["private"],
        "hidden_root_commitment": commitments["hidden"],
    }
    manifest = advance("ROOTS_CREATED", t1_payload, t1_payload)

    # T2: commitment object
    cobj = cam.commitment_object(
        artifact_set=asets, campaign=cid,
        hidden_commitment=commitments["hidden"], private_commitment=commitments["private"],
    )
    cdig_obj = cam.commitment_digest(cobj)
    t2_payload = {"commitment_digest": cdig_obj}
    manifest = advance("COMMITTED", t2_payload, t2_payload)

    # T3: materialize + opening verification
    if materialize_dir is not None:
        materialize_dir = Path(materialize_dir)
        if materialize_dir.exists():
            raise CampaignRunnerError(f"materialize dir already exists: {materialize_dir}")
        try:
            for split, tree in root_trees.items():
                base = materialize_dir / split
                for rel, (mode, data) in sorted(tree.items()):
                    target = base / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    if mode == 0o755:
                        target.chmod(0o755)
            # opening verification: materialized bytes must re-derive commitments
            for split, kind in (("private", "private"), ("local-hidden", "hidden")):
                live_dg = compute_bench_tree_digest_from_dir(materialize_dir / split)
                if live_dg != root_digests[split]:
                    raise CampaignRunnerError(
                        f"opening verification failed for {kind} root: "
                        f"materialized {live_dg} != committed {root_digests[split]}"
                    )
                if not cam.verify_root_commitment(
                    campaign=cid, root_kind=kind,
                    root_tree_digest=live_dg, commitment=commitments[kind],
                ):
                    raise CampaignRunnerError(f"root commitment mismatch for {kind}")
            mev = cam.materialization_evidence(
                campaign=cid,
                hidden_root_digest=root_digests["local-hidden"],
                materialized_at_attestation=materialized_at_attestation,
                participant_digests_sorted=parts_sorted,
                private_root_digest=root_digests["private"],
                workspace_tree_digest=compute_bench_tree_digest_from_dir(materialize_dir),
            )
            mdig = cam.materialization_evidence_digest(mev)
            t3_payload = {"materialization_evidence_digest": mdig}
            manifest = advance("MATERIALIZED", t3_payload, t3_payload)
        except BaseException:
            shutil.rmtree(materialize_dir, ignore_errors=True)
            raise

    return CampaignMaterial(
        manifest=manifest,
        events=events,
        release_identity=identity,
        release=rel_dg,
        instance_digests=instance_digests,
        root_trees=root_trees,
        root_tree_digests=root_digests,
        commitments=commitments,
        materialization_evidence_digest_value=manifest.get("materialization_evidence_digest"),
    )
