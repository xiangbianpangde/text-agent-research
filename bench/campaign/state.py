"""Campaign lifecycle state machine (§19.5).

campaign-manifest/v1: 17 strict fields; 9 states with a REQ/NULL emptiness
matrix; 9 monotone transitions (T0..T8); byte-immutability for every non-state
field once set; campaign-event/v1 hash chain with strict seq ordering.

Pure deterministic computation: the only non-deterministic inputs (attestation
timestamps) are caller-supplied strings.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from bench.dsl.cjson import bench_cjson_digest

CAMPAIGN_SCHEMA_VERSION = "campaign-manifest/v1"
EVENT_SCHEMA_VERSION = "campaign-event/v1"

STATES = (
    "DRAFT",
    "ARTIFACTS_FROZEN",
    "ROOTS_CREATED",
    "COMMITTED",
    "MATERIALIZED",
    "EXECUTING",
    "EVIDENCE_FROZEN",
    "COMPLETED_UNDISCLOSED",
    "DISCLOSED_RETIRED",
)

# (event_type, from_state, to_state, payload keys bound by the transition)
TRANSITIONS: Tuple[Tuple[str, str, str, Tuple[str, ...]], ...] = (
    ("T0", "DRAFT", "ARTIFACTS_FROZEN",
     ("artifact_set_digest", "campaign_digest", "campaign_id", "participant_artifact_digests_sorted")),
    ("T1", "ARTIFACTS_FROZEN", "ROOTS_CREATED",
     ("hidden_root_commitment", "private_root_commitment")),
    ("T2", "ROOTS_CREATED", "COMMITTED", ("commitment_digest",)),
    ("T3", "COMMITTED", "MATERIALIZED", ("materialization_evidence_digest",)),
    ("T4", "MATERIALIZED", "EXECUTING", ()),
    ("T5", "EXECUTING", "EVIDENCE_FROZEN", ("evidence_digest",)),
    ("T6", "EVIDENCE_FROZEN", "COMPLETED_UNDISCLOSED", ()),
    ("T7", "EVIDENCE_FROZEN", "DISCLOSED_RETIRED", ("disclosure_digest", "retired_reason")),
    ("T8", "COMPLETED_UNDISCLOSED", "DISCLOSED_RETIRED", ("disclosure_digest", "retired_reason")),
)

# Field indices (1-based per §19.5.1) required non-null per state
_REQUIRED_BY_STATE: Dict[str, Tuple[int, ...]] = {
    "DRAFT": (1, 3, 4, 5, 6, 7),
    "ARTIFACTS_FROZEN": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    "ROOTS_CREATED": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
    "COMMITTED": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13),
    "MATERIALIZED": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14),
    "EXECUTING": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14),
    "EVIDENCE_FROZEN": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    "COMPLETED_UNDISCLOSED": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
    "DISCLOSED_RETIRED": (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17),
}

FIELD_NAMES = (
    "campaign_schema_version",          # 1
    "campaign_id",                      # 2
    "release_digest",                   # 3
    "state",                            # 4
    "isolation_profile_digest",         # 5
    "network_policy_digest",            # 6
    "created_at_attestation",           # 7
    "participant_artifact_digests_sorted",  # 8
    "artifact_set_digest",              # 9
    "campaign_digest",                  # 10
    "private_root_commitment",          # 11
    "hidden_root_commitment",           # 12
    "commitment_digest",                # 13
    "materialization_evidence_digest",  # 14
    "evidence_digest",                  # 15
    "disclosure_digest",                # 16
    "retired_reason",                   # 17
)


class CampaignError(ValueError):
    """Any violation of the campaign state machine."""


def _field_index(name: str) -> int:
    try:
        return FIELD_NAMES.index(name) + 1
    except ValueError:
        raise CampaignError(f"unknown campaign field: {name!r}")


def initial_manifest(
    *,
    release_digest: str,
    isolation_profile_digest: str,
    network_policy_digest: str,
    created_at_attestation: str,
) -> Dict[str, Any]:
    """Create the DRAFT manifest (fields 2, 8..17 null)."""
    manifest: Dict[str, Any] = {name: None for name in FIELD_NAMES}
    manifest["campaign_schema_version"] = CAMPAIGN_SCHEMA_VERSION
    manifest["release_digest"] = release_digest
    manifest["state"] = "DRAFT"
    manifest["isolation_profile_digest"] = isolation_profile_digest
    manifest["network_policy_digest"] = network_policy_digest
    manifest["created_at_attestation"] = created_at_attestation
    validate_manifest_state(manifest)
    return manifest


def validate_manifest_state(manifest: Mapping[str, Any]) -> None:
    """Enforce the §19.5.1 emptiness matrix for the manifest's current state."""
    unknown = set(manifest.keys()) - set(FIELD_NAMES)
    if unknown:
        raise CampaignError(f"unknown manifest fields: {sorted(unknown)}")
    missing = set(FIELD_NAMES) - set(manifest.keys())
    if missing:
        raise CampaignError(f"missing manifest fields: {sorted(missing)}")
    if manifest["campaign_schema_version"] != CAMPAIGN_SCHEMA_VERSION:
        raise CampaignError("wrong campaign_schema_version")
    state = manifest["state"]
    if state not in STATES:
        raise CampaignError(f"unknown state: {state!r}")
    required = set(_REQUIRED_BY_STATE[state])
    for idx, name in enumerate(FIELD_NAMES, start=1):
        value = manifest[name]
        if idx in required:
            if value is None:
                raise CampaignError(f"state {state}: field {idx} ({name}) must be non-null")
        else:
            if value is not None:
                raise CampaignError(f"state {state}: field {idx} ({name}) must be null")


def find_transition(from_state: str, to_state: str) -> Tuple[str, str, str, Tuple[str, ...]]:
    for t in TRANSITIONS:
        if t[1] == from_state and t[2] == to_state:
            return t
    raise CampaignError(f"no legal transition {from_state} -> {to_state}")


def apply_transition(
    manifest: Mapping[str, Any],
    *,
    to_state: str,
    payload: Mapping[str, Any],
) -> Dict[str, Any]:
    """Atomically move the manifest along a legal edge, binding payload fields.

    Immutability: any already non-null field (other than `state`) whose new
    value differs byte-for-byte is a fatal violation.
    """
    from_state = manifest["state"]
    event_type, f_state, t_state, payload_keys = find_transition(from_state, to_state)
    if f_state != from_state or t_state != to_state:
        raise CampaignError("transition mismatch")

    updated = dict(manifest)
    # bind payload fields (must currently be null)
    for key in payload_keys:
        if key not in payload:
            raise CampaignError(f"transition {event_type}: missing payload field {key!r}")
        if updated.get(key) is not None:
            raise CampaignError(f"transition {event_type}: field {key!r} already bound")
        updated[key] = payload[key]
    extra = set(payload.keys()) - set(payload_keys)
    if extra:
        raise CampaignError(f"transition {event_type}: unexpected payload fields {sorted(extra)}")

    updated["state"] = to_state
    validate_manifest_state(updated)
    return updated


def build_event(
    *,
    manifest: Mapping[str, Any],
    to_state: str,
    payload: Mapping[str, Any],
    seq: int,
    previous_event_digest: Optional[str],
    event_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    """Construct a campaign-event/v1 (without event_digest; call seal_event)."""
    event_type, f_state, t_state, _keys = find_transition(manifest["state"], to_state)
    event: Dict[str, Any] = {
        "campaign_id": manifest.get("campaign_id"),
        "event_type": event_type,
        "event_payload": dict(event_payload),
        "from_state": f_state,
        "previous_event_digest": previous_event_digest,
        "schema_version": EVENT_SCHEMA_VERSION,
        "seq": seq,
        "to_state": t_state,
    }
    if seq == 0:
        if f_state != "DRAFT" or manifest.get("campaign_id") is not None:
            raise CampaignError("seq 0 must start from a DRAFT manifest without campaign_id")
        if event.get("campaign_id") is not None:
            raise CampaignError("seq 0 event campaign_id must be null (bound in payload)")
    else:
        if manifest.get("campaign_id") is None:
            raise CampaignError("non-initial events require a campaign_id on the manifest")
        if event["campaign_id"] != manifest["campaign_id"]:
            raise CampaignError("event campaign_id must equal manifest campaign_id")
        if previous_event_digest is None:
            raise CampaignError("non-initial events require previous_event_digest")
    # payload must carry exactly the newly-bound fields
    _, _, _, payload_keys = find_transition(manifest["state"], to_state)
    if set(event_payload.keys()) != set(payload_keys):
        raise CampaignError(
            f"event_payload must contain exactly {sorted(payload_keys)}, got {sorted(event_payload.keys())}"
        )
    return event


def seal_event(event: Mapping[str, Any]) -> Dict[str, Any]:
    """Compute event_digest over the event object excluding event_digest."""
    body = {k: v for k, v in event.items() if k != "event_digest"}
    sealed = dict(event)
    sealed["event_digest"] = bench_cjson_digest(body)
    return sealed


def verify_event_chain(events: List[Mapping[str, Any]]) -> None:
    """Verify a full campaign-event chain (§19.5.2).

    Enforces: closed field set; seq starting at 0 with strict monotone +1;
    hash-chain linkage; campaign_id consistency; from/to states following the
    transition graph; payload exactly matching the edge's bound fields; and
    event_digest recomputation over the digest-excluded body.
    """
    previous: Optional[Mapping[str, Any]] = None
    for idx, event in enumerate(events):
        unknown = set(event.keys()) - {
            "campaign_id", "event_digest", "event_payload", "event_type",
            "from_state", "previous_event_digest", "schema_version", "seq", "to_state",
        }
        if unknown:
            raise CampaignError(f"event {idx}: unknown fields {sorted(unknown)}")
        if event["schema_version"] != EVENT_SCHEMA_VERSION:
            raise CampaignError(f"event {idx}: wrong schema_version")
        if event["seq"] != idx:
            raise CampaignError(f"event {idx}: seq must be {idx}, got {event['seq']}")
        try:
            event_type, f_state, t_state, payload_keys = next(
                t for t in TRANSITIONS
                if t[1] == event["from_state"] and t[2] == event["to_state"]
            )
        except StopIteration:
            raise CampaignError(f"event {idx}: illegal transition edge")
        if event["event_type"] != event_type:
            raise CampaignError(f"event {idx}: event_type mismatch")
        if set(event["event_payload"].keys()) != set(payload_keys):
            raise CampaignError(f"event {idx}: payload must contain exactly {sorted(payload_keys)}")
        if previous is None:
            if event["seq"] != 0:
                raise CampaignError("first event must have seq 0")
            if event["from_state"] != "DRAFT" or event["campaign_id"] is not None:
                raise CampaignError("first event must start from DRAFT with null campaign_id")
            if event["previous_event_digest"] is not None:
                raise CampaignError("first event must have null previous_event_digest")
        else:
            if event["previous_event_digest"] != previous["event_digest"]:
                raise CampaignError(f"event {idx}: previous_event_digest chain broken")
            if event["from_state"] != previous["to_state"]:
                raise CampaignError(f"event {idx}: from_state must equal previous to_state")
            expected_cid = previous["event_payload"].get("campaign_id") or previous["campaign_id"]
            if expected_cid is not None and event["campaign_id"] != expected_cid:
                raise CampaignError(f"event {idx}: campaign_id must match the chain")
        body = {k: v for k, v in event.items() if k != "event_digest"}
        if event["event_digest"] != bench_cjson_digest(body):
            raise CampaignError(f"event {idx}: event_digest mismatch")
        previous = event


def sort_participant_digests(digests: List[str]) -> List[str]:
    """Sort full Digest strings by their decoded 32 raw bytes, deduplicated."""
    seen = set()
    out: List[Tuple[bytes, str]] = []
    for d in digests:
        if not isinstance(d, str) or not d.startswith("sha256:") or len(d) != 71:
            raise CampaignError(f"invalid participant digest: {d!r}")
        if d in seen:
            raise CampaignError(f"duplicate participant digest: {d!r}")
        seen.add(d)
        out.append((bytes.fromhex(d.removeprefix("sha256:")), d))
    out.sort(key=lambda t: t[0])
    return [d for _, d in out]


# --- §19.5.3 commitment/evidence objects -------------------------------------

def artifact_set_digest(participant_digests_sorted: List[str]) -> str:
    return bench_cjson_digest(participant_digests_sorted)


def campaign_identity(
    *,
    artifact_set: str,
    created_at_attestation: str,
    isolation_profile_digest: str,
    network_policy_digest: str,
    release_digest: str,
) -> Dict[str, str]:
    return {
        "artifact_set_digest": artifact_set,
        "created_at_attestation": created_at_attestation,
        "isolation_profile_digest": isolation_profile_digest,
        "network_policy_digest": network_policy_digest,
        "release_digest": release_digest,
        "schema_version": "campaign-identity/v1",
    }


def campaign_digest(identity: Mapping[str, str]) -> str:
    return bench_cjson_digest(identity)


def campaign_id(
    *,
    artifact_set: str,
    created_at_attestation: str,
    release_digest: str,
) -> str:
    return bench_cjson_digest({
        "artifact_set_digest": artifact_set,
        "created_at_attestation": created_at_attestation,
        "release_digest": release_digest,
    })


def root_commitment(
    *, campaign: str, root_kind: str, root_tree_digest: str
) -> str:
    if root_kind not in ("private", "hidden"):
        raise CampaignError(f"invalid root_kind: {root_kind!r}")
    return bench_cjson_digest({
        "campaign_id": campaign,
        "root_kind": root_kind,
        "root_tree_digest": root_tree_digest,
        "schema_version": "root-commitment/v1",
    })


def verify_root_commitment(
    *, campaign: str, root_kind: str, root_tree_digest: str, commitment: str
) -> bool:
    expected = root_commitment(campaign=campaign, root_kind=root_kind, root_tree_digest=root_tree_digest)
    return expected == commitment


def commitment_object(
    *,
    artifact_set: str,
    campaign: str,
    hidden_commitment: str,
    private_commitment: str,
) -> Dict[str, str]:
    return {
        "artifact_set_digest": artifact_set,
        "campaign_id": campaign,
        "hidden_root_commitment": hidden_commitment,
        "private_root_commitment": private_commitment,
        "schema_version": "commitment/v1",
    }


def commitment_digest(obj: Mapping[str, str]) -> str:
    return bench_cjson_digest(obj)


def materialization_evidence(
    *,
    campaign: str,
    hidden_root_digest: str,
    materialized_at_attestation: str,
    participant_digests_sorted: List[str],
    private_root_digest: str,
    workspace_tree_digest: str,
) -> Dict[str, Any]:
    return {
        "campaign_id": campaign,
        "hidden_root_digest": hidden_root_digest,
        "materialized_at_attestation": materialized_at_attestation,
        "participant_artifact_digests_sorted": participant_digests_sorted,
        "private_root_digest": private_root_digest,
        "schema_version": "materialization-evidence/v1",
        "workspace_tree_digest": workspace_tree_digest,
    }


def materialization_evidence_digest(obj: Mapping[str, Any]) -> str:
    return bench_cjson_digest(obj)


def evidence_bundle(
    *,
    campaign: str,
    canary_transcript_digest: str,
    frozen_at_attestation: str,
    materialization_evidence: str,
    series_digest: str,
    statistics_digest: str,
) -> Dict[str, str]:
    return {
        "campaign_id": campaign,
        "canary_transcript_digest": canary_transcript_digest,
        "frozen_at_attestation": frozen_at_attestation,
        "materialization_evidence_digest": materialization_evidence,
        "schema_version": "evidence-bundle/v1",
        "series_digest": series_digest,
        "statistics_digest": statistics_digest,
    }


def evidence_digest(obj: Mapping[str, str]) -> str:
    return bench_cjson_digest(obj)


def disclosure_manifest(
    *,
    campaign: str,
    disclosed_at_attestation: str,
    evidence: str,
    hidden_root_tree_digest: str,
    retired_reason: str,
) -> Dict[str, str]:
    return {
        "campaign_id": campaign,
        "disclosed_at_attestation": disclosed_at_attestation,
        "evidence_digest": evidence,
        "hidden_root_tree_digest": hidden_root_tree_digest,
        "retired_reason": retired_reason,
        "schema_version": "disclosure-manifest/v1",
    }


def disclosure_digest(obj: Mapping[str, str]) -> str:
    return bench_cjson_digest(obj)
