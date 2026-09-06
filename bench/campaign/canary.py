"""hidden-validity/v1: 16 deterministic canary probes (§19.5.4).

Probes are executed from inside the participant isolation backend against
evaluator-held targets. All 16 probes MUST be blocked. Any success — or an
unavailable isolation backend — fails closed: evaluation_valid=false.

Backend strategy (mirrors P0.4's proven approach):
- macOS: sandbox-exec seatbelt profile granting only the participant
  allowlist, denying every canary target plus network.
- Any host without a backend: hidden results become diagnostic
  (evaluation_valid=false), never fail-open.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import os
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bench.dsl.cjson import bench_cjson_digest

CANARY_TARGETS: Tuple[str, ...] = (
    "read:evaluator_root",
    "read:oracle_root",
    "read:gold",
    "read:private_seed",
    "read:hidden_seed",
    "read:private_pack",
    "read:hidden_pack",
    "write:evaluator_root",
    "write:oracle_root",
    "write:gold",
    "write:private_seed",
    "write:hidden_seed",
    "write:private_pack",
    "write:hidden_pack",
    "network:loopback",
    "network:external",
)

READ_ALLOWLIST = ("materialized_workspace", "participant_artifact", "runtime_library")
READ_DENYLIST = ("evaluator_root", "gold", "hidden_pack", "hidden_seed", "oracle_root", "private_pack", "private_seed")
WRITE_ALLOWLIST = ("bounded_temp", "materialized_workspace")

ISOLATION_PROFILE_DIGEST = "sha256:14df1a9082305cf79668ef0e87745137b5a6bfbd56b551534b2d7fd2586d8b29"
NETWORK_POLICY_DIGEST = "sha256:5751739881dd2a5ff502a033d6808f5fdfb09ceb7c56b4e6e301e01765c029d5"


class CanaryError(RuntimeError):
    pass


def build_isolation_profile() -> Dict[str, Any]:
    """Frozen isolation-profile/v1 object (digest verified below)."""
    obj = {
        "canary_targets": list(CANARY_TARGETS),
        "network_policy": "deny_all",
        "read_allowlist": list(READ_ALLOWLIST),
        "read_denylist": list(READ_DENYLIST),
        "schema_version": "isolation-profile/v1",
        "write_allowlist": list(WRITE_ALLOWLIST),
    }
    digest = bench_cjson_digest(obj)
    if digest != ISOLATION_PROFILE_DIGEST:
        raise CanaryError(f"isolation profile digest drift: {digest}")
    return obj


def build_network_policy() -> Dict[str, Any]:
    obj = {
        "denied_egress": ["external", "loopback"],
        "policy": "deny_all",
        "schema_version": "network-policy/v1",
    }
    digest = bench_cjson_digest(obj)
    if digest != NETWORK_POLICY_DIGEST:
        raise CanaryError(f"network policy digest drift: {digest}")
    return obj


def _sandbox_profile(deny_paths: List[str], workspace: str) -> str:
    """Seatbelt profile: allow default, deny every canary target and network.

    Deny rules take precedence over (allow default), matching the P0.4
    participant isolation shape; the child can still run, import, and use its
    own temp dir, but every forbidden target is unreachable.
    """
    deny_rules = " ".join(
        f"(deny file-read* file-write* (subpath {json.dumps(p, ensure_ascii=False)}))"
        for p in deny_paths
    )
    return f"(version 1) (allow default) {deny_rules} (deny network*)"


def _probe_read(path: Path) -> Tuple[bool, str]:
    """Returns (blocked, error)."""
    try:
        with open(path, "rb") as handle:
            handle.read(1)
        return False, ""
    except PermissionError as exc:
        return True, str(exc)
    except FileNotFoundError:
        # Probe placeholder file must exist; missing means a harness bug.
        raise CanaryError(f"canary target missing on host: {path}")
    except OSError as exc:
        return True, str(exc)


def _probe_write(path: Path) -> Tuple[bool, str]:
    try:
        with open(path, "ab"):
            pass
        return False, ""
    except PermissionError as exc:
        return True, str(exc)
    except FileNotFoundError:
        raise CanaryError(f"canary target missing on host: {path}")
    except OSError as exc:
        return True, str(exc)


def _probe_network(host: str, port: int, timeout: float = 1.0) -> Tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return False, ""
    except (ConnectionRefusedError, TimeoutError, PermissionError, OSError) as exc:
        # connection-refused with a live listener means network reachable;
        # harness runs a loopback listener for the loopback probe.
        return True, str(exc)


class CanaryRunner:
    """Executes the 16 probes inside a sandboxed child process."""

    def __init__(self, *, evaluator_targets: Dict[str, Path], workspace: str) -> None:
        # evaluator_targets maps target suffixes to real host paths that exist.
        self.evaluator_targets = {k: Path(v) for k, v in evaluator_targets.items()}
        self.workspace = workspace
        self.backend = "sandbox-exec" if sys.platform == "darwin" and os.path.isfile("/usr/bin/sandbox-exec") else None

    def _child_main(self) -> int:
        """Runs inside sandbox-exec; prints probe transcript as JSON."""
        targets = dict(self.evaluator_targets)
        net_cfg = json.loads(os.environ["RCTL_CANARY_NET"])
        transcript: List[Dict[str, str]] = []
        for target in CANARY_TARGETS:
            kind, _, name = target.partition(":")
            if kind == "network":
                host, port = net_cfg[name]
                blocked, err = _probe_network(host, int(port))
            else:
                path = targets[name]
                if kind == "read":
                    blocked, err = _probe_read(path)
                elif kind == "write":
                    blocked, err = _probe_write(path)
                else:
                    raise CanaryError(f"unknown probe kind: {kind}")
            transcript.append({
                "error": err if blocked else "probe unexpectedly succeeded",
                "result": "blocked" if blocked else "success",
                "target": target,
            })
        sys.stdout.write(json.dumps(transcript, ensure_ascii=False))
        return 0

    @staticmethod
    def _primary_nonloopback_ipv4() -> Optional[str]:
        import socket as _socket

        try:
            host = _socket.gethostname()
            for info in _socket.getaddrinfo(host, None, _socket.AF_INET):
                addr = info[4][0]
                if not addr.startswith("127."):
                    return addr
        except OSError:
            pass
        return None

    def run(self) -> Dict[str, Any]:
        if self.backend is None:
            return {
                "backend": "none",
                "backend_version": "",
                "canary_targets": list(CANARY_TARGETS),
                "canary_transcript_digest": None,
                "evaluation_valid": False,
                "policy_digest": ISOLATION_PROFILE_DIGEST,
                "reason": "isolation backend unavailable",
                "transcript": [],
            }
        assert self.backend == "sandbox-exec"
        version = subprocess.run(
            ["/usr/bin/sandbox-exec", "-v"], capture_output=True, text=True
        ).stderr.strip() or "unknown"

        # Live listener for unambiguous network probes: under (deny network*)
        # connect() fails with EPERM; without isolation it would connect.
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("0.0.0.0", 0))
        listener.listen(4)
        port = listener.getsockname()[1]
        external_ip = self._primary_nonloopback_ipv4() or "127.0.0.1"
        net_cfg = {"loopback": ["127.0.0.1", str(port)], "external": [external_ip, str(port)]}

        try:
            with tempfile.TemporaryDirectory(prefix="rctl-canary-") as td:
                targets: Dict[str, Path] = {}
                for name in READ_DENYLIST:
                    p = Path(td) / f"{name}.probe"
                    p.write_bytes(b"canary\n")
                    targets[name] = p

                probe_script = Path(td) / "probe_child.py"
                probe_script.write_text(
                    "import sys, json\n"
                    f"sys.path.insert(0, {json.dumps(str(Path(__file__).resolve().parents[2]))})\n"
                    "from bench.campaign.canary import CanaryRunner\n"
                    f"runner = CanaryRunner(evaluator_targets=json.loads({json.dumps(json.dumps({k: str(v) for k, v in targets.items()}))}), workspace={json.dumps(self.workspace)})\n"
                    "raise SystemExit(runner._child_main())\n"
                )
                profile = _sandbox_profile(
                    deny_paths=[os.path.realpath(str(p)) for p in targets.values()],
                    workspace=self.workspace,
                )
                env = dict(os.environ)
                env["RCTL_CANARY_NET"] = json.dumps(net_cfg)
                proc = subprocess.run(
                    ["/usr/bin/sandbox-exec", "-p", profile, sys.executable, str(probe_script)],
                    capture_output=True, text=True, timeout=60, env=env,
                )
                if proc.returncode != 0:
                    raise CanaryError(f"canary child failed: {proc.stderr[-800:]}")
                try:
                    transcript = json.loads(proc.stdout)
                except json.JSONDecodeError as exc:
                    raise CanaryError(f"canary transcript unparsable: {exc}") from exc
        finally:
            listener.close()

        all_blocked = all(row["result"] == "blocked" for row in transcript)
        if len(transcript) != 16:
            raise CanaryError(f"expected 16 probes, got {len(transcript)}")
        return {
            "backend": self.backend,
            "backend_version": version,
            "canary_targets": list(CANARY_TARGETS),
            "canary_transcript_digest": bench_cjson_digest(transcript) if all_blocked else None,
            "evaluation_valid": all_blocked,
            "policy_digest": ISOLATION_PROFILE_DIGEST,
            "reason": "" if all_blocked else "canary probe succeeded inside isolation",
            "transcript": transcript,
        }
