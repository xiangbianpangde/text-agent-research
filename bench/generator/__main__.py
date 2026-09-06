"""CLI: build / verify the P1A public root (clean-room rebuild support).

Usage:
    python3 -m bench.generator build-public <out_dir>
    python3 -m bench.generator verify-public <root_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _build_public(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python3 -m bench.generator build-public <out_dir>", file=sys.stderr)
        return 2
    out = Path(argv[0])
    if out.exists():
        print(f"refusing to overwrite existing path: {out}", file=sys.stderr)
        return 1
    from .release import write_public_root

    digests = write_public_root(out)
    summary = {
        "instances": len(digests),
        "root": str(out),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def _verify_public(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python3 -m bench.generator verify-public <root_dir>", file=sys.stderr)
        return 2
    root = Path(argv[0])
    from .release import verify_public_root

    result = verify_public_root(root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["byte_identical"] else 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    command, rest = args[0], args[1:]
    if command == "build-public":
        return _build_public(rest)
    if command == "verify-public":
        return _verify_public(rest)
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
