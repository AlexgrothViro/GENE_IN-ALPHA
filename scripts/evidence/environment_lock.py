#!/usr/bin/env python3
"""Validate and record the immutable Linux environment lock used by Evidence V2."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .common import sha256_file, write_json_atomic
except ImportError:
    from common import sha256_file, write_json_atomic


def validate(lockfile: Path, manifest_path: Path) -> dict:
    if not lockfile.is_file() or lockfile.stat().st_size == 0:
        raise ValueError(f"lockfile missing or empty: {lockfile}")
    if not manifest_path.is_file():
        raise ValueError(f"lockfile manifest missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid lockfile manifest: {exc}") from exc
    text = lockfile.read_text(encoding="utf-8", errors="strict")
    entries = [line for line in text.splitlines() if line.startswith(("http://", "https://"))]
    if not entries or any("#" not in item for item in entries):
        raise ValueError("lockfile must be explicit and contain package hashes")
    actual = sha256_file(lockfile)
    if manifest.get("schema_version") != "1.0":
        raise ValueError("unsupported lockfile manifest schema")
    if manifest.get("lockfile") != lockfile.name or manifest.get("sha256") != actual:
        raise ValueError("LOCKFILE_HASH_MISMATCH")
    if manifest.get("package_entries") != len(entries):
        raise ValueError("LOCKFILE_ENTRY_COUNT_MISMATCH")
    return {"path": str(lockfile.resolve()), "sha256": actual, "package_entries": len(entries)}


def record(lockfile: Path, manifest_path: Path) -> dict:
    if not lockfile.is_file() or lockfile.stat().st_size == 0:
        raise ValueError(f"lockfile missing or empty: {lockfile}")
    text = lockfile.read_text(encoding="utf-8", errors="strict")
    entries = [line for line in text.splitlines() if line.startswith(("http://", "https://"))]
    if not entries or any("#" not in item for item in entries):
        raise ValueError("lockfile must be explicit and contain package hashes")
    document = {
        "schema_version": "1.0",
        "lockfile": lockfile.name,
        "sha256": sha256_file(lockfile),
        "package_entries": len(entries),
    }
    write_json_atomic(manifest_path, document)
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Gene-In's immutable Linux lockfile")
    parser.add_argument("--lockfile", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    try:
        result = record(args.lockfile, args.manifest) if args.record else validate(args.lockfile, args.manifest)
    except ValueError as exc:
        print(f"[FATAL] {exc}")
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
