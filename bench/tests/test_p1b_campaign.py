"""Campaign lifecycle state machine tests (§19.5)."""
from __future__ import annotations

import unittest

from bench.campaign.state import (
    CampaignError,
    TRANSITIONS,
    apply_transition,
    artifact_set_digest,
    build_event,
    campaign_digest,
    campaign_id,
    campaign_identity,
    commitment_digest,
    commitment_object,
    disclosure_digest,
    disclosure_manifest,
    evidence_bundle,
    evidence_digest,
    find_transition,
    initial_manifest,
    materialization_evidence,
    materialization_evidence_digest,
    root_commitment,
    seal_event,
    sort_participant_digests,
    validate_manifest_state,
    verify_event_chain,
    verify_root_commitment,
)

ISO = "sha256:" + "a" * 64
NET = "sha256:" + "b" * 64
REL = "sha256:" + "c" * 64
AT0 = "2026-09-06T00:00:00Z"
PARTS = ["sha256:" + "f" * 64, "sha256:" + "e" * 64, "sha256:" + "0" * 63 + "1"]


def fresh_draft():
    return initial_manifest(
        release_digest=REL, isolation_profile_digest=ISO,
        network_policy_digest=NET, created_at_attestation=AT0,
    )


class TransitionGraphTests(unittest.TestCase):
    def test_nine_transitions(self) -> None:
        self.assertEqual(len(TRANSITIONS), 9)
        ids = [t[0] for t in TRANSITIONS]
        self.assertEqual(ids, [f"T{i}" for i in range(9)])

    def test_draft_emptiness_matrix(self) -> None:
        m = fresh_draft()
        for name in ("campaign_id", "artifact_set_digest", "retired_reason"):
            self.assertIsNone(m[name])
        for name in ("release_digest", "state", "created_at_attestation"):
            self.assertIsNotNone(m[name])

    def test_illegal_transition_rejected(self) -> None:
        with self.assertRaises(CampaignError):
            find_transition("DRAFT", "COMMITTED")
        with self.assertRaises(CampaignError):
            find_transition("COMPLETED_UNDISCLOSED", "EXECUTING")

    def test_unknown_field_rejected(self) -> None:
        m = fresh_draft()
        m["gold_score"] = 1
        with self.assertRaises(CampaignError):
            validate_manifest_state(m)


class LifecycleTests(unittest.TestCase):
    def drive_to_artifacts_frozen(self):
        m = fresh_draft()
        parts = sort_participant_digests(PARTS)
        asets = artifact_set_digest(parts)
        cid = campaign_id(artifact_set=asets, created_at_attestation=AT0, release_digest=REL)
        ident = campaign_identity(
            artifact_set=asets, created_at_attestation=AT0,
            isolation_profile_digest=ISO, network_policy_digest=NET, release_digest=REL,
        )
        cdig = campaign_digest(ident)
        m = apply_transition(
            m, to_state="ARTIFACTS_FROZEN",
            payload={
                "artifact_set_digest": asets,
                "campaign_digest": cdig,
                "campaign_id": cid,
                "participant_artifact_digests_sorted": parts,
            },
        )
        return m, parts, asets, cid

    def test_full_lifecycle_t0_to_t8(self) -> None:
        m, parts, asets, cid = self.drive_to_artifacts_frozen()
        self.assertEqual(m["state"], "ARTIFACTS_FROZEN")

        priv_root = "sha256:" + "1" * 64
        hid_root = "sha256:" + "2" * 64
        pc = root_commitment(campaign=cid, root_kind="private", root_tree_digest=priv_root)
        hc = root_commitment(campaign=cid, root_kind="hidden", root_tree_digest=hid_root)
        m = apply_transition(m, to_state="ROOTS_CREATED",
                             payload={"private_root_commitment": pc, "hidden_root_commitment": hc})
        cobj = commitment_object(artifact_set=asets, campaign=cid,
                                 hidden_commitment=hc, private_commitment=pc)
        m = apply_transition(m, to_state="COMMITTED",
                             payload={"commitment_digest": commitment_digest(cobj)})
        mev = materialization_evidence(
            campaign=cid, hidden_root_digest=hid_root,
            materialized_at_attestation=AT0, participant_digests_sorted=parts,
            private_root_digest=priv_root, workspace_tree_digest="sha256:" + "3" * 64,
        )
        mdig = materialization_evidence_digest(mev)
        m = apply_transition(m, to_state="MATERIALIZED",
                             payload={"materialization_evidence_digest": mdig})
        m = apply_transition(m, to_state="EXECUTING", payload={})
        eobj = evidence_bundle(
            campaign=cid, canary_transcript_digest="sha256:" + "4" * 64,
            frozen_at_attestation=AT0, materialization_evidence=mdig,
            series_digest="sha256:" + "5" * 64, statistics_digest="sha256:" + "6" * 64,
        )
        edig = evidence_digest(eobj)
        m = apply_transition(m, to_state="EVIDENCE_FROZEN", payload={"evidence_digest": edig})
        m = apply_transition(m, to_state="COMPLETED_UNDISCLOSED", payload={})
        dm = disclosure_manifest(campaign=cid, disclosed_at_attestation=AT0, evidence=edig,
                                 hidden_root_tree_digest=hid_root,
                                 retired_reason="clean_room_reproduction_disclosed")
        m = apply_transition(
            m, to_state="DISCLOSED_RETIRED",
            payload={"disclosure_digest": disclosure_digest(dm),
                     "retired_reason": "clean_room_reproduction_disclosed"},
        )
        self.assertEqual(m["state"], "DISCLOSED_RETIRED")

    def test_immutability_of_bound_fields(self) -> None:
        m, parts, asets, cid = self.drive_to_artifacts_frozen()
        with self.assertRaises(CampaignError):
            apply_transition(
                m, to_state="ROOTS_CREATED",
                payload={
                    "private_root_commitment": "sha256:" + "1" * 64,
                    "hidden_root_commitment": "sha256:" + "2" * 64,
                    "campaign_id": "sha256:" + "9" * 64,  # rebind attempt
                },
            )

    def test_missing_payload_rejected(self) -> None:
        m, _, _, _ = self.drive_to_artifacts_frozen()
        with self.assertRaises(CampaignError):
            apply_transition(m, to_state="ROOTS_CREATED",
                             payload={"private_root_commitment": "sha256:" + "1" * 64})

    def test_extra_payload_rejected(self) -> None:
        m, _, _, _ = self.drive_to_artifacts_frozen()
        with self.assertRaises(CampaignError):
            apply_transition(
                m, to_state="ROOTS_CREATED",
                payload={
                    "private_root_commitment": "sha256:" + "1" * 64,
                    "hidden_root_commitment": "sha256:" + "2" * 64,
                    "evidence_digest": "sha256:" + "3" * 64,
                },
            )

    def test_opening_verification(self) -> None:
        m, _, asets, cid = self.drive_to_artifacts_frozen()
        priv_root = "sha256:" + "1" * 64
        pc = root_commitment(campaign=cid, root_kind="private", root_tree_digest=priv_root)
        self.assertTrue(verify_root_commitment(campaign=cid, root_kind="private",
                                               root_tree_digest=priv_root, commitment=pc))
        self.assertFalse(verify_root_commitment(campaign=cid, root_kind="private",
                                                root_tree_digest="sha256:" + "9" * 64, commitment=pc))
        with self.assertRaises(CampaignError):
            root_commitment(campaign=cid, root_kind="public", root_tree_digest=priv_root)


class EventChainTests(unittest.TestCase):
    def test_hash_chain_and_seq(self) -> None:
        m = fresh_draft()
        parts = sort_participant_digests(PARTS)
        asets = artifact_set_digest(parts)
        cid = campaign_id(artifact_set=asets, created_at_attestation=AT0, release_digest=REL)
        cdig = campaign_digest(campaign_identity(
            artifact_set=asets, created_at_attestation=AT0,
            isolation_profile_digest=ISO, network_policy_digest=NET, release_digest=REL,
        ))
        t0_payload = {"artifact_set_digest": asets, "campaign_digest": cdig, "campaign_id": cid,
                      "participant_artifact_digests_sorted": parts}
        e0 = build_event(manifest=m, to_state="ARTIFACTS_FROZEN", payload=t0_payload,
                         seq=0, previous_event_digest=None, event_payload=t0_payload)
        self.assertIsNone(e0["campaign_id"])
        e0 = seal_event(e0)
        self.assertTrue(e0["event_digest"].startswith("sha256:"))
        m = apply_transition(m, to_state="ARTIFACTS_FROZEN", payload=t0_payload)

        pc = root_commitment(campaign=cid, root_kind="private", root_tree_digest="sha256:" + "1" * 64)
        hc = root_commitment(campaign=cid, root_kind="hidden", root_tree_digest="sha256:" + "2" * 64)
        t1_payload = {"private_root_commitment": pc, "hidden_root_commitment": hc}
        e1 = build_event(manifest=m, to_state="ROOTS_CREATED", payload=t1_payload,
                         seq=1, previous_event_digest=e0["event_digest"], event_payload=t1_payload)
        self.assertEqual(e1["campaign_id"], cid)
        e1 = seal_event(e1)
        # wrong previous digest rejected at seal-time? build allows; but mismatch must be caught here:
        e1_bad = dict(e1)
        e1_bad["previous_event_digest"] = "sha256:" + "0" * 64
        e1_bad["event_digest"] = "unsealed"
        # chain integrity is verified by verify_event_chain (not build): rebuild digest
        body = {k: v for k, v in e1.items() if k != "event_digest"}
        from bench.dsl.cjson import bench_cjson_digest
        self.assertEqual(seal_event(e1)["event_digest"], bench_cjson_digest(body))

        # honest chain verifies
        verify_event_chain([e0, e1])

        # broken previous_event_digest detected
        e1_bad2 = dict(e1)
        e1_bad2["previous_event_digest"] = "sha256:" + "0" * 64
        with self.assertRaises(CampaignError):
            verify_event_chain([e0, e1_bad2])

        # tampered payload detected by digest recomputation
        e1_tampered = dict(e1)
        e1_tampered["event_payload"] = dict(t1_payload, private_root_commitment="sha256:" + "9" * 64)
        with self.assertRaises(CampaignError):
            verify_event_chain([e0, e1_tampered])

        # seq skip detected
        e1_skip = dict(e1)
        e1_skip["seq"] = 5
        with self.assertRaises(CampaignError):
            verify_event_chain([e0, e1_skip])

    def test_seq0_requires_null_campaign_id(self) -> None:
        m = fresh_draft()
        parts = sort_participant_digests(PARTS)
        asets = artifact_set_digest(parts)
        with self.assertRaises(CampaignError):
            build_event(
                manifest={**m, "campaign_id": "sha256:" + "9" * 64},
                to_state="ARTIFACTS_FROZEN",
                payload={"artifact_set_digest": asets, "campaign_digest": "sha256:" + "8" * 64,
                         "campaign_id": "sha256:" + "9" * 64,
                         "participant_artifact_digests_sorted": parts},
                seq=0, previous_event_digest=None,
                event_payload={"artifact_set_digest": asets, "campaign_digest": "sha256:" + "8" * 64,
                               "campaign_id": "sha256:" + "9" * 64,
                               "participant_artifact_digests_sorted": parts},
            )


class SortingTests(unittest.TestCase):
    def test_sort_by_raw_bytes(self) -> None:
        a = "sha256:" + "00" * 32
        z = "sha256:" + "ff" * 32
        m = "sha256:" + "80" * 32
        out = sort_participant_digests([z, m, a])
        self.assertEqual(out, [a, m, z])

    def test_rejects_bad_digests(self) -> None:
        with self.assertRaises(CampaignError):
            sort_participant_digests(["not-a-digest"])
        with self.assertRaises(CampaignError):
            sort_participant_digests(["sha256:" + "00" * 32, "sha256:" + "00" * 32])


if __name__ == "__main__":
    unittest.main()
