"""Build the reproducible P0 fixture from one sealed canonical source archive."""
from __future__ import annotations

import os
import shutil
import tarfile
import tempfile
from pathlib import Path


def _reject_member(name: str) -> None:
    parts = Path(name).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"unsafe canonical source member: {name}")
    if any(part.startswith("._") for part in parts):
        raise ValueError(f"AppleDouble metadata is forbidden: {name}")


def _extract_archive(source: Path, destination: Path) -> None:
    with tarfile.open(source, "r") as archive:
        root = destination.resolve()
        for member in archive.getmembers():
            _reject_member(member.name)
            target = (root / member.name).resolve()
            if os.path.commonpath([str(root), str(target)]) != str(root) or member.issym() or member.islnk():
                raise ValueError(f"unsafe canonical source member: {member.name}")
        archive.extractall(destination, filter="data")


def _materialize_source(source: Path, destination: Path) -> None:
    if source.is_file():
        destination.mkdir()
        _extract_archive(source, destination)
        return
    if not source.is_dir():
        raise ValueError(f"canonical source does not exist: {source}")
    contaminated = [path for path in source.rglob("*") if path.name.startswith("._")]
    if contaminated:
        raise ValueError(f"AppleDouble metadata is forbidden: {contaminated[0].relative_to(source)}")
    metadata = source / "git-metadata.tar"
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("git-metadata.tar"))
    if metadata.is_file():
        git_root = destination / ".git"
        git_root.mkdir()
        _extract_archive(metadata, git_root)


def build_fixture_archive(source_root: str | Path, output_path: str | Path) -> str:
    """Create a deterministic USTAR archive and return its SHA-256 digest."""
    source = Path(source_root).resolve()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bench_pack_") as temporary:
        materialized = Path(temporary) / "universe"
        _materialize_source(source, materialized)
        with tarfile.open(output, "w", format=tarfile.USTAR_FORMAT) as archive:
            for path in sorted(p for p in materialized.rglob("*") if not p.is_symlink()):
                relative = path.relative_to(materialized).as_posix()
                _reject_member(relative)
                info = tarfile.TarInfo(relative)
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mtime = 0
                if path.is_dir():
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    archive.addfile(info)
                    continue
                if not path.is_file():
                    raise ValueError(f"unsupported fixture source entry: {relative}")
                info.size = path.stat().st_size
                info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
                with path.open("rb") as handle:
                    archive.addfile(info, handle)
    import hashlib
    return "sha256:" + hashlib.sha256(output.read_bytes()).hexdigest()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    print(build_fixture_archive(args.source, args.output))
