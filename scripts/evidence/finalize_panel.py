#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import fsync_directory, read_fasta, read_tsv, sha256_file, write_json_atomic
except ImportError:
    from common import fsync_directory, read_fasta, read_tsv, sha256_file, write_json_atomic


REQUIRED_CATEGORIES = {
    "TARGET_VIRUS", "NEAR_NON_TARGET_VIRUS", "HOST", "VECTOR_ADAPTER",
    "KNOWN_CONTAMINANT", "SYNTHETIC_SEQUENCE",
}


def tool_version(command: str) -> dict[str, str]:
    executable = shutil.which(command)
    if not executable:
        return {"executable": "UNAVAILABLE", "version": "UNAVAILABLE", "sha256": "UNAVAILABLE"}
    result = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
    text = (result.stdout or result.stderr).splitlines()
    return {
        "executable": str(Path(executable).resolve()), "version": text[0] if text else "UNKNOWN",
        "sha256": sha256_file(executable),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and atomically promote a complete competitive panel")
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--final", required=True, type=Path)
    parser.add_argument("--panel-id", required=True)
    args = parser.parse_args()
    if args.final.exists():
        raise FileExistsError(f"panel already exists: {args.final}")
    fasta = args.staging / "panel.fa"
    labels = args.staging / "labels.tsv"
    sequences = read_fasta(fasta)
    label_rows = read_tsv(labels)
    if not label_rows or {row.get("sseqid") for row in label_rows} != set(sequences):
        raise ValueError("panel labels do not match FASTA identifiers")
    categories = {row.get("category") for row in label_rows}
    missing_categories = REQUIRED_CATEGORIES - categories
    if missing_categories:
        raise ValueError("competitive panel missing categories: " + ", ".join(sorted(missing_categories)))
    blast_files = [args.staging / "blast" / f"panel.{ext}" for ext in ("nhr", "nin", "nsq")]
    if any(not path.is_file() or path.stat().st_size == 0 for path in blast_files):
        raise ValueError("incomplete BLAST database")
    bt2 = [args.staging / "bowtie2" / f"panel.{ext}.bt2" for ext in ("1", "2", "3", "4", "rev.1", "rev.2")]
    bt2l = [args.staging / "bowtie2" / f"panel.{ext}.bt2l" for ext in ("1", "2", "3", "4", "rev.1", "rev.2")]
    index_files = bt2 if all(path.is_file() and path.stat().st_size for path in bt2) else bt2l
    if not all(path.is_file() and path.stat().st_size for path in index_files):
        raise ValueError("incomplete Bowtie2 index")
    files = [fasta, labels, *blast_files, *index_files]
    manifest = {
        "schema_version": "2.0", "panel_id": args.panel_id,
        "created_at": datetime.now(timezone.utc).isoformat(), "sequence_count": len(sequences),
        "categories": sorted(categories), "index_kind": index_files[0].suffix.lstrip("."),
        "constructors": {"makeblastdb": tool_version("makeblastdb"), "bowtie2-build": tool_version("bowtie2-build")},
        "files": {
            str(path.relative_to(args.staging)): {"size": path.stat().st_size, "sha256": sha256_file(path)}
            for path in files
        },
    }
    write_json_atomic(args.staging / "panel_manifest.json", manifest)
    # SUCCESS is intentionally the last write before atomic promotion.
    write_json_atomic(args.staging / "SUCCESS.json", {
        "panel_id": args.panel_id, "status": "done", "shadow_mode": True,
        "manifest": "panel_manifest.json", "manifest_sha256": sha256_file(args.staging / "panel_manifest.json"),
    })
    fsync_directory(args.staging)
    args.final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(args.staging, args.final)
    fsync_directory(args.final.parent)
    print(args.final)


if __name__ == "__main__":
    main()
