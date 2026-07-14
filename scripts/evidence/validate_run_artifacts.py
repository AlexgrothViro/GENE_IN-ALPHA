#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path


REQUIRED_TSV = {
    "fragment_evidence.tsv",
    "locus_evidence.tsv",
    "competitive_hits.tsv",
    "read_support.tsv",
    "coverage.tsv",
}
REQUIRED_JSON = {"sample_evidence.json", "provenance.json", "runtime_preflight.json"}
REQUIRED_TEXT = {"evidence_report.md"}
REQUIRED_HEADERS = {
    "fragment_evidence.tsv": {"qseqid", "sseqid", "task", "query_covered_bp", "reference_covered_bp", "adj_identity"},
    "locus_evidence.tsv": {"locus_id", "sseqid", "segment", "orientation", "covered_reference_bp", "query_ids"},
    "competitive_hits.tsv": {"qseqid", "task", "target_bitscore", "competitor_bitscore", "delta_bitscore", "specificity_status"},
    "read_support.tsv": {"sample_id", "unique_templates", "distinct_starts", "support_status"},
    "coverage.tsv": {"reference", "breadth_1x", "breadth_3x", "mean_depth_genome", "median_depth_covered"},
}


def validate_tsv(path: Path) -> None:
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader, None)
        if not header or any(not value for value in header):
            raise ValueError(f"invalid TSV header: {path.name}")
        if len(header) != len(set(header)):
            raise ValueError(f"duplicate TSV columns: {path.name}")
        required = REQUIRED_HEADERS.get(path.name, set())
        missing = sorted(required - set(header))
        if missing:
            raise ValueError(f"missing required TSV columns: {', '.join(missing)}")
        for line_number, row in enumerate(reader, 2):
            if len(row) != len(header):
                raise ValueError(f"{path.name}:{line_number}: column count mismatch")


def validate_json(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if path.name == "runtime_preflight.json":
        if not isinstance(value, dict) or value.get("valid") is not True:
            raise ValueError("runtime preflight is not valid")
    elif path.name == "sample_evidence.json":
        required = {"sample_id", "evidence_level", "specificity_status", "coverage_status", "control_status"}
        if not isinstance(value, dict) or not required.issubset(value):
            raise ValueError("sample evidence schema is incomplete")


def validate(directory: Path) -> list[str]:
    errors = []
    for name in sorted(REQUIRED_TSV | REQUIRED_JSON | REQUIRED_TEXT):
        path = directory / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty artifact: {name}")
            continue
        try:
            if name.endswith(".tsv"):
                validate_tsv(path)
            elif name.endswith(".json"):
                validate_json(path)
        except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
            errors.append(f"invalid artifact {name}: {exc}")
    partials = [p.name for p in directory.rglob("*") if p.is_file() and (p.name.endswith(".tmp") or p.name.startswith("."))]
    if partials:
        errors.append("temporary artifacts remain: " + ", ".join(sorted(partials)))
    bam = directory / "read_support.bam"
    bai = directory / "read_support.bam.bai"
    if bam.exists():
        if not bai.is_file() or bai.stat().st_size == 0:
            errors.append("BAM exists without a valid BAI")
        samtools = shutil.which("samtools")
        if not samtools:
            errors.append("samtools unavailable for BAM quickcheck")
        else:
            result = subprocess.run([samtools, "quickcheck", "-v", str(bam)], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                errors.append("samtools quickcheck failed: " + (result.stderr.strip() or result.stdout.strip()))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a complete Evidence V2 staging directory")
    parser.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args()
    errors = validate(args.dir)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        raise SystemExit(1)
    print("[OK] Evidence V2 artifact set is complete and internally readable")


if __name__ == "__main__":
    main()
