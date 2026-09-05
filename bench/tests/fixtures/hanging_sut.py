"""Adapter fixture that spawns a child and never answers invoke requests."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time


VERSION = "sut-adapter/v1"
child = None


def emit(request, **fields):
    value = {
        "schema_version": VERSION,
        "request_id": request["request_id"],
        "operation": request["operation"],
        "status": "ok",
    }
    value.update(fields)
    print(json.dumps(value, sort_keys=True, separators=(",", ":")), flush=True)


for line in sys.stdin:
    request = json.loads(line)
    operation = request["operation"]
    if operation == "prepare":
        emit(request, details={"workspace_ready": True})
    elif operation == "health":
        emit(request, details={"adapter": "hanging-stub", "capabilities": [], "pid": os.getpid()})
    elif operation == "invoke":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        with open(os.environ["BENCH_CHILD_PID_FILE"], "w", encoding="utf-8") as handle:
            handle.write(str(child.pid))
            handle.flush()
            os.fsync(handle.fileno())
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            time.sleep(1)
    elif operation in ("restart", "shutdown"):
        emit(request, details={"done": True})
        raise SystemExit(0)
    else:
        emit(request, details={"done": True})
