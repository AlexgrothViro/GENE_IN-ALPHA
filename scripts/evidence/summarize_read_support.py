#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re

try:
    from .common import write_tsv_atomic
except ImportError:
    from common import write_tsv_atomic


FIELDS = [
    "sample_id", "library_mode", "umi_mode", "support_status", "unique_templates",
    "distinct_starts", "proper_pair_templates", "discordant_templates", "minimum_mapq",
]
CIGAR_RE = re.compile(r"(\d+)([MIDNSHP=X])")


def five_prime(position: int, cigar: str, reverse: bool) -> int:
    operations = [(int(size), op) for size, op in CIGAR_RE.findall(cigar)]
    if not operations:
        return position
    if not reverse:
        leading_clip = operations[0][0] if operations[0][1] in {"S", "H"} else 0
        return position - leading_clip
    reference_span = sum(size for size, op in operations if op in {"M", "D", "N", "=", "X"})
    trailing_clip = operations[-1][0] if operations[-1][1] in {"S", "H"} else 0
    return position + reference_span + trailing_clip - 1


def summarize_sam(path: str, sample: str, library_mode: str, umi_mode: str, minimum_mapq: int) -> list[dict]:
    templates = {}
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if not raw.strip() or raw.startswith("@"):
                continue
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 11:
                continue
            qname, flag_text, reference, position_text, mapq_text, cigar = cols[:6]
            flag, position, mapq = int(flag_text), int(position_text), int(mapq_text)
            if flag & 0x4 or flag & 0x100 or flag & 0x800 or mapq < minimum_mapq:
                continue
            reverse = bool(flag & 0x10)
            start = five_prime(position, cigar, reverse)
            record = templates.setdefault(qname, {"starts": [], "proper": False, "discordant": False})
            record["starts"].append((reference, start, "-" if reverse else "+"))
            record["proper"] = record["proper"] or bool(flag & 0x2)
            record["discordant"] = record["discordant"] or (bool(flag & 0x1) and not bool(flag & 0x2))
    template_keys = set()
    starts = set()
    proper = discordant = 0
    for qname, record in templates.items():
        ordered = tuple(sorted(record["starts"]))
        template_keys.add(ordered)
        starts.update(record["starts"])
        proper += bool(record["proper"])
        discordant += bool(record["discordant"])
    return [{
        "sample_id": sample, "library_mode": library_mode, "umi_mode": umi_mode,
        "support_status": "COVERAGE_AVAILABLE", "unique_templates": len(template_keys),
        "distinct_starts": len(starts), "proper_pair_templates": proper,
        "discordant_templates": discordant, "minimum_mapq": minimum_mapq,
    }]


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize template-level read support from primary SAM alignments")
    parser.add_argument("--sam", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--library-mode", required=True, choices=["shotgun", "amplicon", "targeted", "unknown"])
    parser.add_argument("--umi-mode", default="none", choices=["none", "read_name", "tag"])
    parser.add_argument("--minimum-mapq", type=int, default=10)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    write_tsv_atomic(args.out, summarize_sam(args.sam, args.sample, args.library_mode, args.umi_mode, args.minimum_mapq), FIELDS)


if __name__ == "__main__":
    main()
