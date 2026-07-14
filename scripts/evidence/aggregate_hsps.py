#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

try:
    from .common import (
        format_intervals, interval_size, merge_intervals, read_fasta, read_tsv,
        sequence_metrics, sha256_text, write_tsv_atomic,
    )
except ImportError:
    from common import (
        format_intervals, interval_size, merge_intervals, read_fasta, read_tsv,
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
    ordered = sorted(hsps, key=lambda h: (min(h["qstart"], h["qend"]),
                                           max(h["qstart"], h["qend"]),
                                           -h["bitscore"]))
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
    rows = read_tsv(path)
    required = {"sseqid", "category"}
    if not rows and Path(path).stat().st_size:
        return {}
    if rows and not required.issubset(rows[0]):
        raise ValueError("subject labels require sseqid and category columns")
    return {row["sseqid"]: row for row in rows}


def parse_blast(path: str | Path, task: str) -> list[dict]:
    result = []
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 14:
                raise ValueError(f"{path}:{line_number}: expected BLAST outfmt 6 with 14 columns")
            try:
                qstart, qend, sstart, send = map(int, cols[6:10])
                result.append({
                    "qseqid": cols[0], "sseqid": cols[1], "pident": float(cols[2]),
                    "length": int(float(cols[3])), "qstart": qstart, "qend": qend,
                    "sstart": sstart, "send": send, "evalue": float(cols[10]),
                    "bitscore": float(cols[11]), "qlen": int(float(cols[12])),
                    "slen": int(float(cols[13])), "task": task,
                })
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: invalid numeric BLAST field") from exc
    return result


def aggregate(records: list[dict], sequences: dict[str, str], labels: dict[str, dict[str, str]]) -> list[dict]:
    grouped = defaultdict(list)
    for hit in records:
        orientation = "+" if (hit["qend"] - hit["qstart"]) * (hit["send"] - hit["sstart"]) >= 0 else "-"
        label = labels.get(hit["sseqid"], {})
        segment = label.get("segment", "unsegmented") or "unsegmented"
        key = (hit["qseqid"], hit["sseqid"], hit["task"], segment, orientation)
        grouped[key].append(hit)

    rows = []
    for (qseqid, sseqid, task, segment, orientation), hsps in sorted(grouped.items()):
        q_intervals = merge_intervals((h["qstart"], h["qend"]) for h in hsps)
        s_intervals = merge_intervals((h["sstart"], h["send"]) for h in hsps)
        q_covered = interval_size(q_intervals)
        s_covered = interval_size(s_intervals)
        qlen = max(h["qlen"] for h in hsps)
        slen = max(h["slen"] for h in hsps)
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
