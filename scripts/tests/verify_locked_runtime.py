#!/usr/bin/env python3
"""Verify that the active Conda environment exactly matches the explicit lock."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "evidence"))

from environment_lock import validate as validate_lock  # noqa: E402


SKIP_EXIT = 77


def package_record_from_url(url: str) -> tuple[str, str, str]:
    filename = Path(unquote(urlparse(url).path)).name
    if filename.endswith(".tar.bz2"):
        stem = filename[:-8]
    elif filename.endswith(".conda"):
        stem = filename[:-6]
    else:
        raise ValueError(f"unsupported package archive in lockfile: {filename}")
    try:
        name, version, build = stem.rsplit("-", 2)
    except ValueError as exc:
        raise ValueError(f"invalid package filename in lockfile: {filename}") from exc
    return name, version, build


def locked_packages(lockfile: Path) -> dict[str, tuple[str, str]]:
    packages: dict[str, tuple[str, str]] = {}
    for line in lockfile.read_text(encoding="utf-8", errors="strict").splitlines():
        if not line.startswith(("http://", "https://")):
            continue
        name, version, build = package_record_from_url(line.split("#", 1)[0])
        if name in packages:
            raise ValueError(f"duplicate package in lockfile: {name}")
        packages[name] = (version, build)
    if not packages:
        raise ValueError("lockfile contains no package records")
    return packages


def installed_packages(prefix: Path) -> dict[str, tuple[str, str]]:
    metadata_dir = prefix / "conda-meta"
    if not metadata_dir.is_dir():
        raise FileNotFoundError(f"active environment has no conda-meta directory: {prefix}")
    packages: dict[str, tuple[str, str]] = {}
    for record_path in sorted(metadata_dir.glob("*.json")):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8", errors="strict"))
            name = str(record["name"])
            packages[name] = (str(record["version"]), str(record["build"]))
        except (KeyError, OSError, json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError(f"invalid Conda package record: {record_path}") from exc
    if not packages:
        raise ValueError(f"active environment has no package records: {prefix}")
    return packages


def verify(
    lockfile: Path,
    manifest: Path,
    prefix: Path,
    python_executable: Path | None = None,
) -> dict:
    lock_report = validate_lock(lockfile, manifest)
    expected = locked_packages(lockfile)
    installed = installed_packages(prefix)
    effective_python = (python_executable or Path(sys.executable)).resolve()
    try:
        effective_python.relative_to(prefix.resolve())
    except ValueError as exc:
        raise ValueError(
            f"ACTIVE_PYTHON_OUTSIDE_LOCKED_ENV: {effective_python}"
        ) from exc
    missing = sorted(set(expected) - set(installed))
    extra = sorted(set(installed) - set(expected))
    mismatched = {
        name: {"expected": expected[name], "installed": installed[name]}
        for name in sorted(set(expected) & set(installed))
        if expected[name] != installed[name]
    }
    if missing or extra or mismatched:
        detail = {
            "missing": missing,
            "extra": extra,
            "mismatched": mismatched,
        }
        raise ValueError("ACTIVE_ENVIRONMENT_LOCK_MISMATCH " + json.dumps(detail, sort_keys=True))
    return {
        "status": "LOCK_QUALIFIED",
        "prefix": str(prefix.resolve()),
        "python": str(effective_python),
        "lock_sha256": lock_report["sha256"],
        "package_entries": len(expected),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Require the active Conda environment to match conda-linux-64.lock exactly"
    )
    parser.add_argument("--lockfile", type=Path, default=ROOT / "conda-linux-64.lock")
    parser.add_argument("--manifest", type=Path, default=ROOT / "config" / "environment_lock.json")
    parser.add_argument("--prefix", type=Path, default=None)
    args = parser.parse_args()
    raw_prefix = args.prefix or (Path(os.environ["CONDA_PREFIX"]) if os.environ.get("CONDA_PREFIX") else None)
    if raw_prefix is None:
        print("[SKIP] CONDA_PREFIX is not active; runtime is not lock-qualified", file=sys.stderr)
        return SKIP_EXIT
    try:
        report = verify(args.lockfile, args.manifest, raw_prefix)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
