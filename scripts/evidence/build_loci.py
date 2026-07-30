#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from collections import defaultdict

try:
    from .common import as_float, as_int, format_intervals, interval_size, merge_intervals, parse_intervals, read_tsv, write_tsv_atomic
except ImportError:
    from common import as_float, as_int, format_intervals, interval_size, merge_intervals, parse_intervals, read_tsv, write_tsv_atomic


FIELDS = [
    "locus_id", "sseqid", "taxon", "category", "segment", "orientation", "task",
    "query_intervals", "query_covered_bp", "reference_intervals", "reference_start", "reference_end", "covered_reference_bp",
    "reference_length", "reference_breadth", "query_ids", "query_count", "unique_sequence_count",
    "hsp_count", "best_bitscore", "sum_bitscore", "best_adj_identity", "best_evalue",
    "max_query_length", "max_query_covered_bp", "low_complexity_queries",
]


def build_loci(rows: list[dict[str, str]], gap_bp: int = 100, categories: set[str] | None = None) -> list[dict]:
    categories = categories or {"TARGET_VIRUS", "UNLABELED"}
    buckets = defaultdict(list)
    for row in rows:
        if row.get("category", "UNLABELED") not in categories:
            continue
        key = (row["sseqid"], row.get("segment", "unsegmented"), row.get("orientation", "+"), row.get("task", "blastn"))
        for start, end in parse_intervals(row["reference_intervals"]):
            buckets[key].append((start, end, row))

    output = []
    for (sseqid, segment, orientation, task), items in sorted(buckets.items()):
        items.sort(key=lambda item: (item[0], item[1]))
        clusters: list[list] = []
        for item in items:
            if not clusters or item[0] > max(x[1] for x in clusters[-1]) + gap_bp + 1:
                clusters.append([item])
            else:
                clusters[-1].append(item)
        for cluster in clusters:
            intervals = merge_intervals((x[0], x[1]) for x in cluster)
            cluster_rows = list({id(x[2]): x[2] for x in cluster}.values())
            query_intervals_by_id: dict[str, list[tuple[int, int]]] = defaultdict(list)
            for row in cluster_rows:
                query_intervals_by_id[row["qseqid"]].extend(
                    parse_intervals(row.get("query_intervals", ""))
                )
            merged_query_intervals = {
                query_id: merge_intervals(values)
                for query_id, values in query_intervals_by_id.items()
            }
            query_covered_by_id = {
                query_id: interval_size(values)
                for query_id, values in merged_query_intervals.items()
            }
            query_ids = sorted({r["qseqid"] for r in cluster_rows})
            hashes = {r["sequence_sha256"] for r in cluster_rows if r.get("sequence_sha256")}
            covered = interval_size(intervals)
            slen = max((as_int(r.get("slen")) for r in cluster_rows), default=0)
            digest = hashlib.sha256(
                f"{sseqid}|{segment}|{orientation}|{task}|{format_intervals(intervals)}".encode("utf-8")
            ).hexdigest()[:12]
            output.append({
                "locus_id": f"LOCUS_{digest}", "sseqid": sseqid,
                "taxon": cluster_rows[0].get("taxon", ""), "category": cluster_rows[0].get("category", "UNLABELED"),
                "segment": segment, "orientation": orientation, "task": task,
                "reference_intervals": format_intervals(intervals), "reference_start": intervals[0][0],
                "reference_end": intervals[-1][1], "covered_reference_bp": covered,
                "query_intervals": "|".join(
                    f"{query_id}:{format_intervals(merged_query_intervals[query_id])}"
                    for query_id in query_ids
                ),
                "query_covered_bp": sum(query_covered_by_id.values()),
                "reference_length": slen, "reference_breadth": f"{covered / slen if slen else 0.0:.8f}",
                "query_ids": ";".join(query_ids), "query_count": len(query_ids),
                "unique_sequence_count": len(hashes) if hashes else len(query_ids),
                "hsp_count": sum(as_int(r.get("hsp_count"), 1) for r in cluster_rows),
                "best_bitscore": f"{max(as_float(r.get('best_bitscore')) for r in cluster_rows):.6f}",
                "sum_bitscore": f"{sum(as_float(r.get('sum_bitscore'), as_float(r.get('best_bitscore'))) for r in cluster_rows):.6f}",
                "best_adj_identity": f"{max(as_float(r.get('adj_identity')) for r in cluster_rows):.6f}",
                "best_evalue": f"{min(as_float(r.get('best_evalue'), 1.0) for r in cluster_rows):.8g}",
                "max_query_length": max(as_int(r.get("qlen")) for r in cluster_rows),
                "max_query_covered_bp": max(query_covered_by_id.values(), default=0),
                "low_complexity_queries": sum(r.get("low_complexity_status") == "LOW_COMPLEXITY" for r in cluster_rows),
            })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build independent viral loci from aggregated HSPs")
    parser.add_argument("--fragments", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--gap-bp", type=int, default=100)
    parser.add_argument("--categories", default="TARGET_VIRUS,UNLABELED")
    args = parser.parse_args()
    if args.gap_bp < 0:
        parser.error("--gap-bp must be non-negative")
    rows = build_loci(read_tsv(args.fragments), args.gap_bp, set(args.categories.split(",")))
    write_tsv_atomic(args.out, rows, FIELDS)


if __name__ == "__main__":
    main()
