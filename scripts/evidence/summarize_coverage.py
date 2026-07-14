#!/usr/bin/env python3
from __future__ import annotations

import argparse
import statistics
from collections import defaultdict

try:
    from .common import read_fasta, write_tsv_atomic
except ImportError:
    from common import read_fasta, write_tsv_atomic


FIELDS = [
    "reference", "reference_length", "covered_bases_1x", "covered_bases_3x", "breadth_1x",
    "breadth_3x", "mean_depth_genome", "median_depth_covered", "min_depth_covered",
    "max_window_depth_fraction", "concentration_window_bp", "minimum_mapq", "minimum_base_quality",
]


def concentration_fraction(depths: list[int], window_bp: int) -> float:
    total = sum(depths)
    if total <= 0:
        return 0.0
    width = min(max(window_bp, 1), len(depths))
    current = sum(depths[:width])
    maximum = current
    for idx in range(width, len(depths)):
        current += depths[idx] - depths[idx - width]
        maximum = max(maximum, current)
    return maximum / total


def summarize(depth_by_ref: dict[str, dict[int, int]], lengths: dict[str, int], window_bp: int,
              minimum_mapq: int, minimum_base_quality: int) -> list[dict]:
    rows = []
    for reference, length in sorted(lengths.items()):
        if length <= 0:
            continue
        positions = depth_by_ref.get(reference, {})
        depths = [positions.get(pos, 0) for pos in range(1, length + 1)]
        covered = [value for value in depths if value > 0]
        covered_1x = len(covered)
        covered_3x = sum(value >= 3 for value in depths)
        rows.append({
            "reference": reference, "reference_length": length,
            "covered_bases_1x": covered_1x, "covered_bases_3x": covered_3x,
            "breadth_1x": f"{covered_1x / length:.8f}", "breadth_3x": f"{covered_3x / length:.8f}",
            "mean_depth_genome": f"{sum(depths) / length:.8f}",
            "median_depth_covered": f"{statistics.median(covered) if covered else 0.0:.8f}",
            "min_depth_covered": min(covered) if covered else 0,
            "max_window_depth_fraction": f"{concentration_fraction(depths, window_bp):.8f}",
            "concentration_window_bp": window_bp, "minimum_mapq": minimum_mapq,
            "minimum_base_quality": minimum_base_quality,
        })
    return rows


def parse_depth(path: str) -> dict[str, dict[int, int]]:
    result = defaultdict(dict)
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            cols = raw.rstrip("\n").split("\t")
            if len(cols) < 3:
                raise ValueError(f"depth line {line_number} has fewer than 3 columns")
            reference, position, depth = cols[:3]
            result[reference][int(position)] = int(depth)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize per-base depth without conflating genome and covered positions")
    parser.add_argument("--depth", required=True)
    parser.add_argument("--reference-fasta", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--window-bp", type=int, default=100)
    parser.add_argument("--minimum-mapq", type=int, default=10)
    parser.add_argument("--minimum-base-quality", type=int, default=20)
    args = parser.parse_args()
    lengths = {name: len(seq) for name, seq in read_fasta(args.reference_fasta).items()}
    write_tsv_atomic(args.out, summarize(parse_depth(args.depth), lengths, args.window_bp,
                                         args.minimum_mapq, args.minimum_base_quality), FIELDS)


if __name__ == "__main__":
    main()
