#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path

try:
    from .common import sha256_file, validate_artifact_manifest
    from .evidence_contract import PIPELINE_VERSION, validate_document
except ImportError:
    from common import sha256_file, validate_artifact_manifest
    from evidence_contract import PIPELINE_VERSION, validate_document


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
    "read_support.tsv": {"sample_id", "reference_id", "category", "locus_id", "query_ids", "unique_templates", "distinct_starts", "support_status"},
    "coverage.tsv": {"reference_id", "category", "locus_id", "query_ids", "breadth_1x", "breadth_3x", "mean_depth_locus", "median_depth_covered"},
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
        validate_document(value)


def validate_commit_metadata(directory: Path, expected_run_id: str | None = None) -> list[str]:
    errors: list[str] = []
    manifest_path = directory / "artifact_manifest.json"
    success_path = directory / "SUCCESS.json"
    if not manifest_path.is_file():
        errors.append("missing commit artifact: artifact_manifest.json")
    if not success_path.is_file():
        errors.append("missing commit artifact: SUCCESS.json")
    if errors:
        return errors
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
        errors.extend(validate_artifact_manifest(directory, manifest))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid artifact_manifest.json: {exc}")
        return errors
    try:
        success = json.loads(success_path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid SUCCESS.json: {exc}")
        return errors
    if not isinstance(success, dict):
        return errors + ["SUCCESS.json must be an object"]
    if success.get("pipeline_version") != PIPELINE_VERSION:
        errors.append("SUCCESS.json is not an Alpha.2 commit")
    if success.get("shadow_mode") is not True:
        errors.append("SUCCESS.json must preserve shadow_mode=true")
    if success.get("status") not in {"done", "done_with_warning"}:
        errors.append("SUCCESS.json has no successful terminal status")
    if not isinstance(success.get("run_id"), str) or not success["run_id"].strip():
        errors.append("SUCCESS.json run_id is required")
    if expected_run_id is not None and success.get("run_id") != expected_run_id:
        errors.append("SUCCESS.json run_id does not match the requested run")
    files = manifest.get("files", {}) if isinstance(manifest, dict) else {}
    if success.get("artifact_count") != len(files):
        errors.append("SUCCESS.json artifact_count does not match the manifest")
    if success.get("artifact_manifest_sha256") != sha256_file(manifest_path):
        errors.append("SUCCESS.json artifact manifest hash mismatch")
    sample_evidence = directory / "sample_evidence.json"
    if sample_evidence.is_file():
        try:
            evidence = json.loads(sample_evidence.read_text(encoding="utf-8", errors="strict"))
            if evidence.get("run_id") != success.get("run_id"):
                errors.append("sample evidence run_id does not match SUCCESS.json")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"invalid sample_evidence.json during commit verification: {exc}")
    if "sample_evidence_sha256" in success and sample_evidence.is_file():
        if success["sample_evidence_sha256"] != sha256_file(sample_evidence):
            errors.append("SUCCESS.json sample evidence hash mismatch")
    return errors


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
    manifest_exists = (directory / "artifact_manifest.json").exists()
    success_exists = (directory / "SUCCESS.json").exists()
    if manifest_exists or success_exists:
        errors.extend(validate_commit_metadata(directory))
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
