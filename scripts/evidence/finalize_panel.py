#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import read_fasta, read_tsv, write_json_atomic
except ImportError:
    from common import read_fasta, read_tsv, write_json_atomic


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and promote a competitive panel as one transaction")
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
        "panel_id": args.panel_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sequence_count": len(sequences),
        "index_kind": index_files[0].suffix.lstrip("."),
        "files": {str(path.relative_to(args.staging)): {"size": path.stat().st_size, "sha256": digest(path)} for path in files},
    }
    write_json_atomic(args.staging / "panel_manifest.json", manifest)
    write_json_atomic(args.staging / "SUCCESS.json", {"panel_id": args.panel_id, "status": "done", "manifest": "panel_manifest.json"})
    args.final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(args.staging, args.final)
    print(args.final)


if __name__ == "__main__":
    main()
