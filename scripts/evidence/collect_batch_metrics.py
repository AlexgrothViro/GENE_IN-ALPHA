#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path

try:
    from .common import read_tsv, write_tsv_atomic
except ImportError:
    from common import read_tsv, write_tsv_atomic


FIELDS = ["batch_id", "sample_id", "target", "expected_target", "rpm_post_qc", "rpm_nonhost", "sequence_hashes", "evidence_level", "analysis_outcome"]


def fastq_reads(path: Path) -> int | None:
    if not path.is_file():
        return None
    opener = gzip.open if path.suffix == ".gz" else open
    lines = 0
    with opener(path, "rt", encoding="utf-8", errors="strict") as handle:
        for lines, _ in enumerate(handle, 1):
            pass
    return lines // 4


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect normalized batch metrics from shadow evidence outputs")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--evidence-root")
    parser.add_argument("--run-map", help="TSV with sample_id and run_id")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.repo_root)
    evidence_root = Path(args.evidence_root) if args.evidence_root else root / "results" / "evidence"
    run_ids = {}
    if args.run_map:
        run_ids = {row["sample_id"]: row["run_id"] for row in read_tsv(args.run_map)}
    output = []
    manifest_rows = read_tsv(args.manifest)
    positive_targets = {}
    for row in manifest_rows:
        if row.get("role") == "positive" and row.get("expected_target"):
            positive_targets.setdefault(row["batch_id"], set()).add(row["expected_target"])
    for item in manifest_rows:
        sample = item["sample_id"]
        if sample not in run_ids:
            raise ValueError(f"run_id ausente para amostra {sample}")
        evidence_dir = evidence_root / "runs" / run_ids[sample]
        if not (evidence_dir / "SUCCESS.json").is_file():
            raise ValueError(f"execução incompleta para amostra {sample}")
        with (evidence_dir / "sample_evidence.json").open("r", encoding="utf-8") as handle:
            evidence = json.load(handle)
        hashes = []
        fragment_path = evidence_dir / "fragment_evidence.tsv"
        if fragment_path.is_file():
            hashes = sorted({r["sequence_sha256"] for r in read_tsv(fragment_path) if r.get("sequence_sha256")})
        templates = float(evidence.get("metrics", {}).get("unique_templates", 0))
        post_qc_reads = None
        fastp_json = root / "results" / "qc" / f"{sample}_fastp.json"
        if fastp_json.is_file():
            with fastp_json.open("r", encoding="utf-8") as handle:
                post_qc_reads = json.load(handle).get("summary", {}).get("after_filtering", {}).get("total_reads")
        nonhost_reads = fastq_reads(root / "data" / "host_removed" / f"{sample}_R1.host_removed.fastq.gz")
        rpm_post = templates * 1_000_000 / post_qc_reads if post_qc_reads else 0.0
        rpm_nonhost = templates * 1_000_000 / nonhost_reads if nonhost_reads else None
        batch_targets = positive_targets.get(item["batch_id"], set())
        fallback_target = next(iter(batch_targets)) if len(batch_targets) == 1 else "UNSPECIFIED"
        output.append({
            "batch_id": item["batch_id"], "sample_id": sample,
            "target": item.get("expected_target", "") or fallback_target,
            "expected_target": item.get("expected_target", ""), "rpm_post_qc": f"{rpm_post:.8f}",
            "rpm_nonhost": f"{rpm_nonhost:.8f}" if rpm_nonhost is not None else "NA",
            "sequence_hashes": ";".join(hashes), "evidence_level": evidence.get("evidence_level", "INCONCLUSIVE"),
            "analysis_outcome": evidence.get("analysis_outcome", "NOT_EVALUABLE"),
        })
    write_tsv_atomic(args.out, output, FIELDS)


if __name__ == "__main__":
    main()
