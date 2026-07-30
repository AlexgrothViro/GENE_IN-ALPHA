#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

try:
    from .common import (
        format_intervals, interval_size, merge_intervals, read_fasta,
        sequence_metrics, sha256_text, write_tsv_atomic,
    )
except ImportError:
    from common import (
        format_intervals, interval_size, merge_intervals, read_fasta,
        sequence_metrics, sha256_text, write_tsv_atomic,
    )


FIELDS = [
    "qseqid", "sseqid", "task", "category", "taxon", "segment", "orientation",
    "qlen", "slen", "hsp_count", "query_intervals", "reference_intervals",
    "query_covered_bp", "reference_covered_bp", "query_coverage", "weighted_pident",
    "identity_covered_bp",
    "best_evalue", "best_bitscore", "sum_bitscore", "adj_identity_raw", "adj_identity",
    "integrity_flags", "sequence_sha256", "sequence_entropy", "n_fraction",
    "max_homopolymer_fraction", "low_complexity_status",
]
LABEL_CATEGORIES = {
    "TARGET_VIRUS", "NEAR_NON_TARGET_VIRUS", "HOST", "VECTOR_ADAPTER",
    "KNOWN_CONTAMINANT", "SYNTHETIC_SEQUENCE", "UNLABELED",
}


def union_weighted_identity(hsps: list[dict]) -> tuple[float, int]:
    """Estimate identity over non-redundant query positions only.

    BLAST can emit overlapping HSPs for the same query.  Sorting by query
    interval and then preferring the stronger HSP makes the assignment
    deterministic while ensuring an overlap contributes once to the
    aggregate identity.
    """
    covered: list[tuple[int, int]] = []
    weighted = 0.0
    unique_bp = 0
    ordered = sorted(
        hsps,
        key=lambda h: (
            -h["bitscore"], h["evalue"], -h["pident"],
            min(h["qstart"], h["qend"]), max(h["qstart"], h["qend"]),
            min(h["sstart"], h["send"]), max(h["sstart"], h["send"]),
        ),
    )
    for hsp in ordered:
        start, end = sorted((hsp["qstart"], hsp["qend"]))
        if start > end:
            continue
        novel = end - start + 1
        for old_start, old_end in covered:
            overlap_start = max(start, old_start)
            overlap_end = min(end, old_end)
            if overlap_start <= overlap_end:
                novel -= overlap_end - overlap_start + 1
        novel = max(novel, 0)
        if novel:
            weighted += hsp["pident"] * novel
            unique_bp += novel
            covered = merge_intervals([*covered, (start, end)])
    return (weighted / unique_bp if unique_bp else 0.0, unique_bp)


def load_labels(path: str | None) -> dict[str, dict[str, str]]:
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"sseqid", "category"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("subject labels require sseqid and category columns")
        labels: dict[str, dict[str, str]] = {}
        for line_number, row in enumerate(reader, 2):
            subject = row.get("sseqid", "")
            category = row.get("category", "")
            if not subject:
                raise ValueError(f"{path}:{line_number}: empty subject label")
            if category not in LABEL_CATEGORIES:
                raise ValueError(
                    f"{path}:{line_number}: invalid subject category: {category!r}"
                )
            if subject in labels:
                raise ValueError(f"{path}:{line_number}: duplicate subject label: {subject}")
            labels[subject] = row
    return labels


def _finite_number(value: str, field: str, path: str | Path, line_number: int) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{path}:{line_number}: invalid numeric BLAST field {field}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{path}:{line_number}: non-finite BLAST field {field}")
    return number


def parse_blast(path: str | Path, task: str) -> list[dict]:
    result = []
    with Path(path).open("r", encoding="utf-8", errors="strict") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            cols = raw.rstrip("\n").split("\t")
            if len(cols) != 14:
                raise ValueError(f"{path}:{line_number}: expected the canonical 14-column BLAST outfmt")
            try:
                qstart, qend, sstart, send = map(int, cols[6:10])
                length = int(cols[3])
                mismatch = int(cols[4])
                gapopen = int(cols[5])
                qlen = int(cols[12])
                slen = int(cols[13])
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: invalid numeric BLAST field") from exc
            pident = _finite_number(cols[2], "pident", path, line_number)
            evalue = _finite_number(cols[10], "evalue", path, line_number)
            bitscore = _finite_number(cols[11], "bitscore", path, line_number)
            if not cols[0] or not cols[1]:
                raise ValueError(f"{path}:{line_number}: empty BLAST sequence identifier")
            if not 0.0 <= pident <= 100.0:
                raise ValueError(f"{path}:{line_number}: pident is outside 0..100")
            if length < 1 or mismatch < 0 or gapopen < 0 or qlen < 1 or slen < 1:
                raise ValueError(f"{path}:{line_number}: invalid BLAST lengths or counts")
            if evalue < 0.0 or bitscore < 0.0:
                raise ValueError(f"{path}:{line_number}: negative BLAST score")
            if min(qstart, qend, sstart, send) < 1:
                raise ValueError(f"{path}:{line_number}: BLAST coordinates must be positive")
            if max(qstart, qend) > qlen or max(sstart, send) > slen:
                raise ValueError(f"{path}:{line_number}: BLAST coordinates exceed sequence length")
            result.append({
                "qseqid": cols[0], "sseqid": cols[1], "pident": pident,
                "length": length, "mismatch": mismatch, "gapopen": gapopen,
                "qstart": qstart, "qend": qend, "sstart": sstart, "send": send,
                "evalue": evalue, "bitscore": bitscore, "qlen": qlen,
                "slen": slen, "task": task,
            })
    return result


def split_reference_clusters(hsps: list[dict]) -> list[list[dict]]:
    """Keep disconnected subject regions separate until locus construction."""
    ordered = sorted(
        hsps,
        key=lambda h: (
            min(h["sstart"], h["send"]), max(h["sstart"], h["send"]),
            min(h["qstart"], h["qend"]), max(h["qstart"], h["qend"]),
        ),
    )
    clusters: list[list[dict]] = []
    cluster_end = 0
    for hsp in ordered:
        start, end = sorted((hsp["sstart"], hsp["send"]))
        if not clusters or start > cluster_end + 1:
            clusters.append([hsp])
            cluster_end = end
        else:
            clusters[-1].append(hsp)
            cluster_end = max(cluster_end, end)
    return clusters


def aggregate(records: list[dict], sequences: dict[str, str], labels: dict[str, dict[str, str]]) -> list[dict]:
    grouped = defaultdict(list)
    for hit in records:
        if sequences:
            if hit["qseqid"] not in sequences:
                raise ValueError(f"BLAST query is absent from query FASTA: {hit['qseqid']}")
            if len(sequences[hit["qseqid"]]) != hit["qlen"]:
                raise ValueError(
                    f"BLAST qlen disagrees with query FASTA for {hit['qseqid']}"
                )
        orientation = "+" if (hit["qend"] - hit["qstart"]) * (hit["send"] - hit["sstart"]) >= 0 else "-"
        label = labels.get(hit["sseqid"], {})
        segment = label.get("segment", "unsegmented") or "unsegmented"
        key = (hit["qseqid"], hit["sseqid"], hit["task"], segment, orientation)
        grouped[key].append(hit)

    rows = []
    for (qseqid, sseqid, task, segment, orientation), grouped_hsps in sorted(grouped.items()):
        qlens = {h["qlen"] for h in grouped_hsps}
        slens = {h["slen"] for h in grouped_hsps}
        if len(qlens) != 1:
            raise ValueError(f"inconsistent qlen values for {qseqid}")
        if len(slens) != 1:
            raise ValueError(f"inconsistent slen values for {sseqid}")
        qlen = next(iter(qlens))
        slen = next(iter(slens))
        for hsps in split_reference_clusters(grouped_hsps):
            q_intervals = merge_intervals((h["qstart"], h["qend"]) for h in hsps)
            s_intervals = merge_intervals((h["sstart"], h["send"]) for h in hsps)
            q_covered = interval_size(q_intervals)
            s_covered = interval_size(s_intervals)
            weighted_pident, identity_covered_bp = union_weighted_identity(hsps)
            qcov = q_covered / qlen if qlen else 0.0
            raw_adj = weighted_pident * qcov
            flags = []
            if raw_adj > 100.0:
                flags.append("ADJ_IDENTITY_CLAMPED")
            if q_covered > qlen > 0:
                flags.append("QUERY_UNION_EXCEEDS_QLEN")
            sequence = sequences.get(qseqid, "")
            metrics = sequence_metrics(sequence)
            low_complexity = metrics["entropy"] < 1.2 or metrics["max_homopolymer_fraction"] > 0.60
            label = labels.get(sseqid, {})
            rows.append({
                "qseqid": qseqid, "sseqid": sseqid, "task": task,
                "category": label.get("category", "UNLABELED"), "taxon": label.get("taxon", ""),
                "segment": segment, "orientation": orientation, "qlen": qlen, "slen": slen,
                "hsp_count": len(hsps), "query_intervals": format_intervals(q_intervals),
                "reference_intervals": format_intervals(s_intervals), "query_covered_bp": q_covered,
                "reference_covered_bp": s_covered, "query_coverage": f"{qcov:.6f}",
                "weighted_pident": f"{weighted_pident:.6f}",
                "identity_covered_bp": identity_covered_bp,
                "best_evalue": f"{min(h['evalue'] for h in hsps):.8g}",
                "best_bitscore": f"{max(h['bitscore'] for h in hsps):.6f}",
                "sum_bitscore": f"{sum(h['bitscore'] for h in hsps):.6f}",
                "adj_identity_raw": f"{raw_adj:.6f}", "adj_identity": f"{min(raw_adj, 100.0):.6f}",
                "integrity_flags": ";".join(flags) or "OK",
                "sequence_sha256": sha256_text(sequence) if sequence else "",
                "sequence_entropy": f"{metrics['entropy']:.6f}", "n_fraction": f"{metrics['n_fraction']:.6f}",
                "max_homopolymer_fraction": f"{metrics['max_homopolymer_fraction']:.6f}",
                "low_complexity_status": "LOW_COMPLEXITY" if low_complexity else "ACCEPTABLE",
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate overlapping BLAST HSPs without inflating evidence")
    parser.add_argument("--blast", action="append", required=True, metavar="TASK=PATH")
    parser.add_argument("--query-fasta")
    parser.add_argument("--subject-labels")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    records = []
    for spec in args.blast:
        if "=" not in spec:
            parser.error("--blast must use TASK=PATH")
        task, path = spec.split("=", 1)
        if task not in {"blastn", "blastn-short"}:
            parser.error(f"unsupported BLAST task: {task}")
        records.extend(parse_blast(path, task))
    sequences = read_fasta(args.query_fasta) if args.query_fasta else {}
    write_tsv_atomic(args.out, aggregate(records, sequences, load_labels(args.subject_labels)), FIELDS)


if __name__ == "__main__":
    main()
