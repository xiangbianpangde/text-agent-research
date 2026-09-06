"""P1B campaign runner + participant artifact binding tests (§5, §8, §10, §19.5)."""
from __future__ import annotations

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from bench.campaign.artifacts import (
    ArtifactBindingError,
    build_participant_artifact,
    tar_sha256,
    validate_entrypoint,
    validate_tar_safety,
)
from bench.campaign.runner import build_release, build_root_tree, create_campaign
from bench.generator.kdf import PUBLIC_SPLIT_SECRET
from bench.generator.release import public_plan

SECRETS = {
    "public": PUBLIC_SPLIT_SECRET,
    "private": bytes(range(32, 64)),
    "local-hidden": bytes(range(64, 96)),
}
PARTS = ["sha256:" + "aa" * 32, "sha256:" + "bb" * 32]
COMMITTED_ROOT = Path(__file__).resolve().parents[2] / "bench" / "packs" / "p1_public_v1"


def make_tar(entries: list[tuple[str, bytes | None]]) -> Path:
    """entries: (name, data) for files; (name, None) for dirs."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, data in entries:
            if data is None:
                info = tarfile.TarInfo(name)
                info.type = tarfile.DIRTYPE
                tf.addfile(info)
            else:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
    out = Path(tempfile.mkdtemp()) / "artifact.tar"
    out.write_bytes(buf.getvalue())
    return out


class TarSafetyTests(unittest.TestCase):
    def test_safe_tar_accepted(self) -> None:
        tar = make_tar([
            ("participant/", None),
            ("participant/main.py", b"print('ok')\n"),
            ("participant/lib/util.py", b"x = 1\n"),
        ])
        members = validate_tar_safety(tar)
        self.assertEqual(len(members), 3)
        digest = tar_sha256(tar)
        self.assertTrue(digest.startswith("sha256:"))
        self.assertEqual(tar_sha256(tar), digest)

    def test_absolute_path_rejected(self) -> None:
        tar = make_tar([("/etc/passwd", b"x")])
        with self.assertRaises(ArtifactBindingError):
            validate_tar_safety(tar)

    def test_traversal_rejected(self) -> None:
        tar = make_tar([("../evil.txt", b"x")])
        with self.assertRaises(ArtifactBindingError):
            validate_tar_safety(tar)

    def test_symlink_rejected(self) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tf:
            info = tarfile.TarInfo("link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tf.addfile(info)
        tar = Path(tempfile.mkdtemp()) / "s.tar"
        tar.write_bytes(buf.getvalue())
        with self.assertRaises(ArtifactBindingError):
            validate_tar_safety(tar)

    def test_appledouble_rejected(self) -> None:
        tar = make_tar([("._main.py", b"x")])
        with self.assertRaises(ArtifactBindingError):
            validate_tar_safety(tar)

    def test_empty_tar_rejected(self) -> None:
        tar = make_tar([])
        with self.assertRaises(ArtifactBindingError):
            validate_tar_safety(tar)

    def test_binding_object(self) -> None:
        tar = make_tar([("main.py", b"print('ok')\n")])
        obj = build_participant_artifact(
            participant_id="researchctl",
            participant_version="0.8.0",
            tar_path=tar,
            entrypoint="main.py",
            seed_mode="explicit_run_seed",
            adapter_digest="sha256:" + "cd" * 32,
            declared_kernel_dependencies=["kernel-core"],
        )
        self.assertEqual(obj["schema_version"], "participant-artifact/v1")
        self.assertEqual(obj["b1_api_version"], "b1-kernel/v1")
        self.assertEqual(obj["adapter_protocol"], "sut-adapter/v1")
        self.assertEqual(obj["artifact_digest"], tar_sha256(tar))
        self.assertEqual(obj["declared_kernel_dependencies"], ["kernel-core"])

    def test_entrypoint_containment(self) -> None:
        tar = make_tar([("bin/run.py", b"x")])
        with tempfile.TemporaryDirectory() as td:
            extract_root = Path(td) / "root"
            extract_root.mkdir()
            (extract_root / "bin").mkdir()
            (extract_root / "bin" / "run.py").write_bytes(b"x")
            validate_entrypoint("bin/run.py", extract_root)
            with self.assertRaises(ArtifactBindingError):
                validate_entrypoint("../outside.py", extract_root)
            with self.assertRaises(ArtifactBindingError):
                validate_entrypoint("/abs/path.py", extract_root)
            with self.assertRaises(ArtifactBindingError):
                validate_entrypoint("missing.py", extract_root)


class CampaignRunnerTests(unittest.TestCase):
    def test_t0_to_t3_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mat = create_campaign(
                participant_digests=PARTS,
                secrets=SECRETS,
                isolation_profile_digest="sha256:" + "a" * 32,
                network_policy_digest="sha256:" + "b" * 32,
                created_at_attestation="2026-09-06T00:00:00Z",
                materialized_at_attestation="2026-09-06T00:05:00Z",
                materialize_dir=Path(td) / "materialized",
            )
            self.assertEqual(mat.manifest["state"], "MATERIALIZED")
            self.assertEqual(len(mat.events), 4)
            self.assertTrue(mat.manifest["campaign_id"])
            self.assertTrue(mat.manifest["commitment_digest"])
            self.assertTrue(mat.manifest["materialization_evidence_digest"])

            # materialized trees exist for both held splits
            base = Path(td) / "materialized"
            self.assertEqual({p.name for p in base.iterdir()}, {"private", "local-hidden"})

    def test_roots_contain_no_gold_or_oracle_material(self) -> None:
        """S05-adjacent structural check: workspace roots hold fixtures only."""
        for split in ("private", "local-hidden"):
            tree, _ = build_root_tree(split, SECRETS)
            for rel in tree:
                self.assertFalse(rel.endswith(("gold.json", "manifest.json", "actions.json")), rel)
                self.assertFalse("oracle" in rel.lower(), rel)
                self.assertFalse(".tmp." in rel or rel.endswith(".tmp"), rel)

    def test_public_instances_match_committed_root(self) -> None:
        """S01: campaign-regenerated public instances equal the committed pack."""
        identity, rel_dg, digests = build_release(SECRETS)
        for fid, split, ordinal in public_plan():
            inst_dir = None
            for p in (COMMITTED_ROOT / "instances" / "public").iterdir():
                if p.name.startswith(f"RCTL1-{fid}-public-{ordinal}-"):
                    inst_dir = p
                    break
            self.assertIsNotNone(inst_dir, f"{fid}/{ordinal}")
            desc = __import__("json").loads((inst_dir / "descriptor.json").read_text())
            from bench.dsl.cjson import bench_cjson_digest
            self.assertEqual(
                bench_cjson_digest(desc), digests[(fid, split, ordinal)],
                f"committed instance digest mismatch for {fid}/{ordinal}",
            )
        # release identity chain is fully bound
        self.assertTrue(rel_dg.startswith("sha256:"))
        self.assertEqual(len(identity["family_identities"]), 8)

    def test_missing_secret_fails_closed(self) -> None:
        with self.assertRaises(Exception):
            build_release({"public": PUBLIC_SPLIT_SECRET})
        with self.assertRaises(Exception):
            build_release({"public": b"short", "private": SECRETS["private"],
                           "local-hidden": SECRETS["local-hidden"]})

    def test_materialize_refuses_existing_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            occupied = Path(td) / "occupied"
            occupied.mkdir()
            with self.assertRaises(Exception):
                create_campaign(
                    participant_digests=PARTS,
                    secrets=SECRETS,
                    isolation_profile_digest="sha256:" + "a" * 32,
                    network_policy_digest="sha256:" + "b" * 32,
                    created_at_attestation="2026-09-06T00:00:00Z",
                    materialized_at_attestation="2026-09-06T00:05:00Z",
                    materialize_dir=occupied,
                )

    def test_tampered_materialization_fails_verification(self) -> None:
        """B04-adjacent: any byte change in materialized root breaks commitments."""
        from bench.generator.tree import compute_bench_tree_digest_from_dir
        from bench.campaign.runner import build_root_tree
        from bench.generator.tree import compute_bench_tree_digest_from_entries

        with tempfile.TemporaryDirectory() as td:
            tree, _ = build_root_tree("private", SECRETS)
            base = Path(td) / "private"
            for rel, (mode, data) in tree.items():
                target = base / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            committed = compute_bench_tree_digest_from_entries(tree)
            # tamper one byte
            victim = next(p for p in base.rglob("*.yaml"))
            victim.write_bytes(victim.read_bytes() + b"# tampered\n")
            live = compute_bench_tree_digest_from_dir(base)
            self.assertNotEqual(live, committed)


if __name__ == "__main__":
    unittest.main()
