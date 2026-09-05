"""Synchronous client for the frozen process-level SUT adapter protocol."""
from __future__ import annotations

import dataclasses
import json
import os
import select
import signal
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from .protocol import (
    AdapterProtocolError,
    command_digest,
    encode_message,
    make_request,
    validate_response,
)


class SUTAdapterError(RuntimeError):
    """Lifecycle, transport, timeout, or participant-reported adapter error."""


@dataclasses.dataclass(frozen=True)
class InvocationResult:
    exit_code: int
    stdout: str
    stderr: str
    payload: Optional[Any] = None


@dataclasses.dataclass(frozen=True)
class PendingRequest:
    request_id: str
    operation: str
    process_pid: int


class ProcessSUTAdapter:
    """Launch one SUT process and exchange request/response NDJSON messages."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        cwd: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
        request_timeout_ms: int = 30_000,
    ) -> None:
        if not command or any(not isinstance(part, str) or not part or "\x00" in part for part in command):
            raise ValueError("command must be a non-empty sequence of safe strings")
        if not 1 <= request_timeout_ms <= 600_000:
            raise ValueError("request_timeout_ms must be in [1, 600000]")
        self.command = tuple(command)
        self.cwd = os.path.abspath(cwd) if cwd else None
        self.extra_env = dict(env or {})
        self.request_timeout_ms = request_timeout_ms
        self._process: Optional[subprocess.Popen[str]] = None
        self._workspace: Optional[str] = None
        self._sequence = 0
        self._health: Dict[str, Any] = {}
        self._pending: Optional[PendingRequest] = None

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "protocol": "sut-adapter/v1",
            "transport": "stdio-ndjson",
            "command_digest": command_digest(self.command),
            "adapter": self._health.get("adapter"),
            "capabilities": self._health.get("capabilities", []),
        }

    def _start(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        env = dict(os.environ)
        # Participant discovery must not depend on the benchmark's PYTHONPATH.
        env.pop("PYTHONPATH", None)
        env.update(self.extra_env)
        self._process = subprocess.Popen(
            list(self.command),
            cwd=self.cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            start_new_session=(os.name == "posix"),
        )

    def _begin_request(self, operation: str, **fields: Any) -> PendingRequest:
        if self._pending is not None:
            raise SUTAdapterError("only one adapter request may be pending")
        self._start()
        process = self._process
        assert process is not None and process.stdin is not None

        self._sequence += 1
        request_id = f"req-{self._sequence:06d}-{uuid.uuid4().hex[:8]}"
        request = make_request(request_id, operation, **fields)
        try:
            process.stdin.write(encode_message(request))
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise SUTAdapterError(f"adapter pipe closed during {operation}: {exc}") from exc
        pending = PendingRequest(request_id=request_id, operation=operation, process_pid=process.pid)
        self._pending = pending
        return pending

    def _await_request(self, pending: PendingRequest, timeout_ms: int) -> Dict[str, Any]:
        if self._pending != pending:
            raise SUTAdapterError("pending request does not belong to this adapter")
        process = self._process
        if process is None or process.pid != pending.process_pid or process.stdout is None:
            self._pending = None
            raise SUTAdapterError("adapter process changed while request was pending")
        ready, _, _ = select.select([process.stdout], [], [], timeout_ms / 1000.0)
        if not ready:
            self._pending = None
            self._terminate()
            raise SUTAdapterError(f"adapter operation timed out: {pending.operation}")
        line = process.stdout.readline()
        self._pending = None
        if not line:
            stderr = self._read_stderr()
            self._terminate()
            raise SUTAdapterError(
                f"adapter exited before responding to {pending.operation}"
                + (f": {stderr.strip()}" if stderr.strip() else "")
            )
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AdapterProtocolError(f"adapter emitted non-JSON stdout: {line[:200]!r}") from exc
        return validate_response(
            response,
            expected_request_id=pending.request_id,
            expected_operation=pending.operation,
        )

    def _request(
        self,
        operation: str,
        *,
        response_timeout_ms: Optional[int] = None,
        **fields: Any,
    ) -> Dict[str, Any]:
        pending = self._begin_request(operation, **fields)
        wait_ms = response_timeout_ms if response_timeout_ms is not None else self.request_timeout_ms
        return self._await_request(pending, wait_ms)

    def prepare(self, workspace: str) -> Dict[str, Any]:
        workspace = os.path.abspath(workspace)
        response = self._request("prepare", workspace=workspace)
        self._require_ok(response)
        self._workspace = workspace
        return response

    def health(self) -> Dict[str, Any]:
        response = self._request("health")
        self._require_ok(response)
        details = response.get("details")
        self._health = details if isinstance(details, dict) else {}
        return self._health

    def begin_invoke(
        self,
        arguments: Sequence[str],
        *,
        capture_id: str = "",
        timeout_ms: int = 30_000,
        test_control: Optional[Mapping[str, Any]] = None,
        virtual_time: Optional[str] = None,
        query_id: Optional[str] = None,
    ) -> PendingRequest:
        if self._workspace is None:
            raise SUTAdapterError("prepare must succeed before invoke")
        fields: Dict[str, Any] = {
            "arguments": list(arguments),
            "timeout_ms": timeout_ms,
            "capture_id": capture_id,
        }
        if test_control is not None:
            fields["test_control"] = dict(test_control)
        if virtual_time is not None:
            fields["virtual_time"] = virtual_time
        if query_id is not None:
            fields["query_id"] = query_id
        return self._begin_request("invoke", **fields)

    def await_invoke(self, pending: PendingRequest, *, timeout_ms: int = 30_000) -> InvocationResult:
        response = self._await_request(pending, timeout_ms)
        if response["status"] == "error":
            error = response["error"]
            return InvocationResult(
                exit_code=70,
                stdout="",
                stderr=f"{error['code']}: {error['message']}",
            )
        return InvocationResult(
            exit_code=response["exit_code"],
            stdout=response["stdout"],
            stderr=response["stderr"],
            payload=response.get("payload"),
        )

    def invoke(
        self,
        arguments: Sequence[str],
        *,
        capture_id: str = "",
        timeout_ms: int = 30_000,
        test_control: Optional[Mapping[str, Any]] = None,
        virtual_time: Optional[str] = None,
        query_id: Optional[str] = None,
    ) -> InvocationResult:
        pending = self.begin_invoke(
            arguments,
            capture_id=capture_id,
            timeout_ms=timeout_ms,
            test_control=test_control,
            virtual_time=virtual_time,
            query_id=query_id,
        )
        return self.await_invoke(pending, timeout_ms=timeout_ms)

    def hard_kill_process_group(self) -> int:
        """Issue an external hard kill for crash-safety scenarios."""
        process = self._process
        if process is None or process.poll() is not None:
            raise SUTAdapterError("adapter is not running")
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        returncode = process.wait(timeout=5)
        self._close_pipes(process)
        self._process = None
        self._pending = None
        self._health = {}
        return returncode

    def recover_after_hard_kill(self) -> None:
        if self._workspace is None:
            raise SUTAdapterError("no prepared workspace to recover")
        workspace = self._workspace
        self._workspace = None
        self.prepare(workspace)
        self.health()

    def reset_context(self) -> None:
        response = self._request("reset_context")
        self._require_ok(response)

    def restart(self) -> None:
        if self._workspace is None:
            raise SUTAdapterError("prepare must succeed before restart")
        workspace = self._workspace
        response = self._request("restart")
        self._require_ok(response)
        process = self._process
        if process is not None:
            try:
                process.wait(timeout=5)
                self._close_pipes(process)
            except subprocess.TimeoutExpired:
                self._terminate()
        self._process = None
        self._workspace = None
        self._health = {}
        self.prepare(workspace)
        self.health()

    def shutdown(self) -> None:
        process = self._process
        if process is None:
            return
        if process.poll() is None:
            try:
                response = self._request("shutdown", response_timeout_ms=5_000)
                self._require_ok(response)
                process.wait(timeout=5)
                self._close_pipes(process)
            except (AdapterProtocolError, SUTAdapterError, subprocess.TimeoutExpired):
                self._terminate()
        self._process = None
        self._workspace = None
        self._health = {}

    def _require_ok(self, response: Dict[str, Any]) -> None:
        if response["status"] != "ok":
            error = response["error"]
            raise SUTAdapterError(f"{error['code']}: {error['message']}")

    def _read_stderr(self) -> str:
        process = self._process
        if process is None or process.stderr is None or process.poll() is None:
            return ""
        return process.stderr.read()

    def _terminate(self) -> None:
        process = self._process
        if process is None:
            self._pending = None
            return
        if process.poll() is None:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            else:
                process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
                process.wait(timeout=2)
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self._close_pipes(process)
        self._process = None
        self._pending = None

    @staticmethod
    def _close_pipes(process: subprocess.Popen[str]) -> None:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()

    def __enter__(self) -> "ProcessSUTAdapter":
        self._start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.shutdown()


def default_researchctl_command() -> Sequence[str]:
    """Return the official SUT-owned protocol server command.

    The module is discovered from an explicit launch cwd, not by injecting
    PYTHONPATH into participant processes.
    """
    return (sys.executable, "-m", "researchctl.bench_adapter")


def project_root() -> str:
    return str(Path(__file__).resolve().parents[2])
