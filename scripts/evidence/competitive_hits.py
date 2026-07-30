#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict

try:
    from .common import as_float, read_tsv, write_tsv_atomic
except ImportError:
    from common import as_float, read_tsv, write_tsv_atomic


FIELDS = [
    "qseqid", "task", "target_sseqid", "target_taxon", "target_bitscore", "target_qcov",
    "competitor_sseqid", "competitor_taxon", "competitor_category", "competitor_bitscore",
    "competitor_qcov", "delta_bitscore", "delta_bitscore_fraction", "qcov_difference_pp",
    "qcov_difference_abs_pp",
    "specificity_status", "specificity_flags",
]


def evaluate(
    rows: list[dict[str, str]],
    min_delta: float = 10.0,
    max_qcov_difference_pp: float = 5.0,
    search_complete: bool = True,
) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["qseqid"], row.get("task", "blastn"))].append(row)
    output = []
    for (qseqid, task), hits in sorted(grouped.items()):
        targets = [h for h in hits if h.get("category") == "TARGET_VIRUS"]
        competitors = [h for h in hits if h.get("category") not in {"TARGET_VIRUS", "UNLABELED"}]
        unlabeled = [h for h in hits if h.get("category", "UNLABELED") == "UNLABELED"]
        target = max(targets, key=lambda h: as_float(h.get("best_bitscore")), default=None)
        known_competitor = max(
            competitors, key=lambda h: as_float(h.get("best_bitscore")), default=None
        )
        unknown_blocker = max(
            unlabeled, key=lambda h: as_float(h.get("best_bitscore")), default=None
        )
        competitor = known_competitor
        flags = []
        if not search_complete:
            flags.append("SEARCH_SPACE_UNVERIFIED")
        if unknown_blocker is not None:
            flags.append("UNLABELED_HIT_PRESENT")
        if target is None:
            if known_competitor is not None:
                status = "NON_TARGET_BEST"
            else:
                status = "NOT_EVALUATED"
                competitor = unknown_blocker
            target_score = target_qcov = 0.0
        else:
            target_score = as_float(target.get("best_bitscore"))
            target_qcov = as_float(target.get("query_coverage"))
            if target.get("low_complexity_status") == "LOW_COMPLEXITY":
                flags.append("LOW_COMPLEXITY_QUERY")
            if unknown_blocker is not None and (
                known_competitor is None
                or as_float(unknown_blocker.get("best_bitscore"))
                > as_float(known_competitor.get("best_bitscore"))
            ):
                competitor = unknown_blocker
        competitor_score = as_float(competitor.get("best_bitscore")) if competitor else 0.0
        competitor_qcov = as_float(competitor.get("query_coverage")) if competitor else 0.0
        delta = target_score - competitor_score
        fraction = delta / target_score if target_score else 0.0
        # The configured criterion is a maximum absolute difference.  Using
        # only the signed difference would incorrectly accept a competitor
        # covering substantially more of the query than the target.
        qcov_diff_pp = (target_qcov - competitor_qcov) * 100.0
        qcov_difference_abs_pp = abs(qcov_diff_pp)
        if target is not None and known_competitor is None and unknown_blocker is None:
            status = "NOT_EVALUATED"
            flags.append("NO_NON_TARGET_COMPETITOR")
        elif target is not None:
            known_score = (
                as_float(known_competitor.get("best_bitscore"))
                if known_competitor else 0.0
            )
            if known_competitor is not None and known_score > target_score:
                status = "NON_TARGET_BEST"
                competitor = known_competitor
                competitor_score = known_score
                competitor_qcov = as_float(known_competitor.get("query_coverage"))
                delta = target_score - competitor_score
                fraction = delta / target_score if target_score else 0.0
                qcov_diff_pp = (target_qcov - competitor_qcov) * 100.0
                qcov_difference_abs_pp = abs(qcov_diff_pp)
            elif unknown_blocker is not None:
                status = "AMBIGUOUS"
            elif (
                delta >= min_delta
                and qcov_difference_abs_pp <= max_qcov_difference_pp
                and not flags
            ):
                status = "TARGET_SPECIFIC"
            else:
                status = "AMBIGUOUS"
        if not search_complete and status == "TARGET_SPECIFIC":
            status = "NOT_EVALUATED"
        output.append({
            "qseqid": qseqid, "task": task,
            "target_sseqid": target.get("sseqid", "") if target else "",
            "target_taxon": target.get("taxon", "") if target else "",
            "target_bitscore": f"{target_score:.6f}", "target_qcov": f"{target_qcov:.6f}",
            "competitor_sseqid": competitor.get("sseqid", "") if competitor else "",
            "competitor_taxon": competitor.get("taxon", "") if competitor else "",
            "competitor_category": competitor.get("category", "") if competitor else "",
            "competitor_bitscore": f"{competitor_score:.6f}", "competitor_qcov": f"{competitor_qcov:.6f}",
            "delta_bitscore": f"{delta:.6f}", "delta_bitscore_fraction": f"{fraction:.6f}",
            "qcov_difference_pp": f"{qcov_diff_pp:.6f}",
            "qcov_difference_abs_pp": f"{qcov_difference_abs_pp:.6f}",
            "specificity_status": status,
            "specificity_flags": ";".join(flags) or "OK",
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare target and non-target hits from the same BLAST task/database")
    parser.add_argument("--fragments", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--minimum-delta-bitscore", type=float, default=10.0)
    parser.add_argument("--maximum-qcov-difference-pp", type=float, default=5.0)
    parser.add_argument(
        "--search-complete",
        action="store_true",
        help="confirm that the BLAST report limit covered every subject in the competitive DB",
    )
    args = parser.parse_args()
    write_tsv_atomic(
        args.out,
        evaluate(
            read_tsv(args.fragments),
            args.minimum_delta_bitscore,
            args.maximum_qcov_difference_pp,
            args.search_complete,
        ),
        FIELDS,
    )


if __name__ == "__main__":
    main()
