"""Release identity chain (§19.3): generator config/profile, instance
descriptors, release lockfile, and release identity.

Pure computation over frozen inputs; no filesystem access, no RNG, no clock.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from bench.dsl.cjson import bench_cjson_digest

RELEASE_ID = "RCTL-P1-B1-2026-01"
GENERATOR_VERSION = "universe-generator/v1"

QUOTA_PROFILE_DIGEST = "sha256:6c26fb4ce20da8030fdef949292925115441c73471562b93275c4a83fe65dbb6"
METRIC_PROFILE_DIGEST = "sha256:2e998c351aa12f82595feb1c935b359bbd1e677a44a2c159c878455ef0fb69be"
STATISTICS_PROFILE_DIGEST = "sha256:bd08e958ec639020396e8446c076bccd047989765ea7969bdae97a9ef9761eab"

ATTEMPT_LIMIT = 64
DOMAIN_ORDER = ("objects", "relations", "content", "timestamps", "mutation", "actions", "query")
SPLIT_ORDER = ("public", "private", "local-hidden")


def build_generator_config() -> Dict[str, Any]:
    return {
        "attempt_limit": ATTEMPT_LIMIT,
        "domain_order": list(DOMAIN_ORDER),
        "generator_version": GENERATOR_VERSION,
        "metric_profile_digest": METRIC_PROFILE_DIGEST,
        "quota_profile_digest": QUOTA_PROFILE_DIGEST,
        "schema_version": "generator-config/v1",
        "split_order": list(SPLIT_ORDER),
    }


def generator_config_digest() -> str:
    return bench_cjson_digest(build_generator_config())


def build_generator_profile(source_tree_digest: str) -> Dict[str, Any]:
    return {
        "domain_order": list(DOMAIN_ORDER),
        "generator_config_digest": generator_config_digest(),
        "generator_version": GENERATOR_VERSION,
        "schema_version": "generator-profile/v1",
        "source_tree_digest": source_tree_digest,
    }


def generator_profile_digest(source_tree_digest: str) -> str:
    return bench_cjson_digest(build_generator_profile(source_tree_digest))


def build_generator_identity(source_tree_digest: str) -> Dict[str, str]:
    return {
        "generator_profile_digest": generator_profile_digest(source_tree_digest),
        "generator_version": GENERATOR_VERSION,
        "schema_version": "generator/v1",
        "source_tree_digest": source_tree_digest,
    }


def generator_identity_digest(source_tree_digest: str) -> str:
    return bench_cjson_digest(build_generator_identity(source_tree_digest))


def build_instance_descriptor(
    *,
    attempt: int,
    family_digest: str,
    family_id: str,
    family_version: str,
    fixture_tree_digest: str,
    oracle_manifest_digest: str,
    ordinal: int,
    query_registry_digest: str,
    scenario_action_digest: str,
    source_tree_digest: str,
    split: str,
) -> Dict[str, Any]:
    if split not in SPLIT_ORDER:
        raise ValueError(f"invalid split: {split!r}")
    return {
        "attempt": attempt,
        "family_digest": family_digest,
        "family_id": family_id,
        "family_version": family_version,
        "fixture_tree_digest": fixture_tree_digest,
        "generator_version": GENERATOR_VERSION,
        "oracle_manifest_digest": oracle_manifest_digest,
        "ordinal": ordinal,
        "query_registry_digest": query_registry_digest,
        "release_id": RELEASE_ID,
        "scenario_action_digest": scenario_action_digest,
        "schema_version": "instance-descriptor/v1",
        "source_tree_digest": source_tree_digest,
        "split": split,
    }


def instance_digest(descriptor: Mapping[str, Any]) -> str:
    return bench_cjson_digest(descriptor)


def display_id(descriptor: Mapping[str, Any]) -> str:
    """Display ID: RCTL1-<family_id>-<split>-<ordinal>-<first24hex>.

    Human-readable label only; never a machine authority.
    """
    digest = instance_digest(descriptor)
    hex24 = digest.removeprefix("sha256:")[:24]
    return f"RCTL1-{descriptor['family_id']}-{descriptor['split']}-{descriptor['ordinal']}-{hex24}"


def build_release_lockfile(entries: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build release-lockfile/v1 from 144 instance entries.

    Each entry must provide family_id, split, ordinal, instance_digest.
    Ordering: family_id ascending, split in fixed order, ordinal ascending.
    """
    normalized: List[Tuple[str, str, int, str]] = []
    for e in entries:
        normalized.append((e["family_id"], e["split"], e["ordinal"], e["instance_digest"]))
    if len(normalized) != 144:
        raise ValueError(f"release lockfile requires exactly 144 entries, got {len(normalized)}")
    split_rank = {s: i for i, s in enumerate(SPLIT_ORDER)}
    normalized.sort(key=lambda t: (t[0], split_rank[t[1]], t[2]))
    seen = set()
    for fid, split, ordinal, _ in normalized:
        key = (fid, split, ordinal)
        if key in seen:
            raise ValueError(f"duplicate lockfile entry: {key}")
        seen.add(key)
    return {
        "entries": [
            {"family_id": fid, "instance_digest": dg, "ordinal": ordinal, "split": split}
            for fid, split, ordinal, dg in normalized
        ],
        "generator_version": GENERATOR_VERSION,
        "release_id": RELEASE_ID,
        "schema_version": "release-lockfile/v1",
    }


def lockfile_digest(lockfile: Mapping[str, Any]) -> str:
    return bench_cjson_digest(lockfile)


def build_release_identity(
    *,
    b1_api_digest: str,
    family_identities: Sequence[Mapping[str, Any]],
    lockfile: Mapping[str, Any],
) -> Dict[str, Any]:
    if len(family_identities) != 8:
        raise ValueError("release identity requires exactly 8 family identities")
    ids = [dict(f) for f in family_identities]
    if [f["family_id"] for f in ids] != [f"F{i:02d}" for i in range(1, 9)]:
        raise ValueError("family identities must be ordered F01..F08")
    return {
        "b1_api_digest": b1_api_digest,
        "family_identities": ids,
        "generator_version": GENERATOR_VERSION,
        "lockfile_digest": lockfile_digest(lockfile),
        "metric_profile_digest": METRIC_PROFILE_DIGEST,
        "quota_profile_digest": QUOTA_PROFILE_DIGEST,
        "release_id": RELEASE_ID,
        "release_schema_version": "release-identity/v1",
        "schema_version": "release-identity/v1",
        "statistics_profile_digest": STATISTICS_PROFILE_DIGEST,
    }


def release_digest(release_identity: Mapping[str, Any]) -> str:
    return bench_cjson_digest(release_identity)
