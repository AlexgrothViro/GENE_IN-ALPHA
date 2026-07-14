#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .common import as_float, as_int, load_yaml_config, read_tsv, write_json_atomic
except ImportError:
    from common import as_float, as_int, load_yaml_config, read_tsv, write_json_atomic


DEFAULTS = {
    "locus": {"minimum_candidate_bp": 50},
    "support": {"minimum_unique_templates": 3, "minimum_distinct_starts_shotgun": 2},
    "sample_evidence": {"multi_locus_minimum": 2, "multi_locus_total_bp": 150,
                        "genome_breadth_1x": 0.20, "median_covered_depth": 3},
    "controls": {"uncontrolled_maximum": "MULTI_LOCUS_CANDIDATE"},
}


def _section(config: dict, name: str) -> dict:
    merged = dict(DEFAULTS.get(name, {}))
    merged.update(config.get(name, {}))
    return merged


def classify(sample: str, loci: list[dict[str, str]], competitive: list[dict[str, str]],
             read_support: list[dict[str, str]], coverage: list[dict[str, str]],
             control_status: str, library_mode: str, config: dict, shadow: bool = True,
             provenance: dict | None = None) -> dict:
    locus_cfg = _section(config, "locus")
    support_cfg = _section(config, "support")
    evidence_cfg = _section(config, "sample_evidence")
    controls_cfg = _section(config, "controls")
    comp_by_query = {(r["qseqid"], r.get("task", "blastn")): r["specificity_status"] for r in competitive}
    statuses = []
    qualifying_loci = []
    for locus in loci:
        query_statuses = [comp_by_query.get((qid, locus.get("task", "blastn")), "NOT_EVALUATED")
                          for qid in filter(None, locus.get("query_ids", "").split(";"))]
        statuses.extend(query_statuses)
        if "TARGET_SPECIFIC" in query_statuses or (not competitive and locus.get("category") == "UNLABELED"):
            qualifying_loci.append(locus)

    if statuses and all(status == "TARGET_SPECIFIC" for status in statuses):
        specificity = "TARGET_SPECIFIC"
    elif "NON_TARGET_BEST" in statuses and "TARGET_SPECIFIC" not in statuses:
        specificity = "NON_TARGET_BEST"
    elif statuses and any(status in {"AMBIGUOUS", "NON_TARGET_BEST"} for status in statuses):
        specificity = "AMBIGUOUS"
    else:
        specificity = "NOT_EVALUATED"

    support_available = bool(read_support)
    unique_templates = max((as_int(r.get("unique_templates")) for r in read_support), default=0)
    distinct_starts = max((as_int(r.get("distinct_starts")) for r in read_support), default=0)
    proper_pair_templates = max((as_int(r.get("proper_pair_templates")) for r in read_support), default=0)
    support_states = {r.get("support_status", "") for r in read_support}
    support_ok = support_available and unique_templates >= as_int(support_cfg["minimum_unique_templates"])
    if library_mode == "shotgun":
        support_ok = support_ok and distinct_starts >= as_int(support_cfg["minimum_distinct_starts_shotgun"])
        if support_cfg.get("require_proper_pair_shotgun", True):
            support_ok = support_ok and proper_pair_templates >= as_int(support_cfg["minimum_unique_templates"])

    if "UMI_DEDUP_UNAVAILABLE" in support_states:
        coverage_status = "UMI_DEDUP_UNAVAILABLE"
        breadth_1x = median_depth = breadth_3x = concentration = 0.0
    elif coverage:
        coverage_status = "COVERAGE_AVAILABLE" if support_ok else "INSUFFICIENT_SUPPORT"
        breadth_1x = max(as_float(r.get("breadth_1x")) for r in coverage)
        median_depth = max(as_float(r.get("median_depth_covered")) for r in coverage)
        breadth_3x = max(as_float(r.get("breadth_3x")) for r in coverage)
        concentration = max(as_float(r.get("max_window_depth_fraction")) for r in coverage)
    else:
        coverage_status = "COVERAGE_UNAVAILABLE"
        breadth_1x = median_depth = breadth_3x = concentration = 0.0

    locus_bp = [as_int(r.get("covered_reference_bp")) for r in qualifying_loci]
    total_bp = sum(locus_bp)
    max_bp = max(locus_bp, default=0)
    evidence_level = "INCONCLUSIVE"
    if loci and max(as_int(r.get("max_query_length")) for r in loci) < as_int(locus_cfg["minimum_candidate_bp"]):
        evidence_level = "EXPLORATORY_FRAGMENT"
    elif qualifying_loci and max_bp >= as_int(locus_cfg["minimum_candidate_bp"]) and support_ok:
        evidence_level = "LOCUS_CANDIDATE"
        if len(qualifying_loci) >= as_int(evidence_cfg["multi_locus_minimum"]) and total_bp >= as_int(evidence_cfg["multi_locus_total_bp"]):
            evidence_level = "MULTI_LOCUS_CANDIDATE"
            if breadth_1x >= as_float(evidence_cfg["genome_breadth_1x"]) and median_depth >= as_float(evidence_cfg["median_covered_depth"]):
                evidence_level = "GENOME_SUPPORTED"

    # Missing controls reduce the interpretive ceiling but do not create a
    # new combinatorial class or an automatic contamination verdict.
    if control_status == "UNCONTROLLED":
        levels = ["INCONCLUSIVE", "EXPLORATORY_FRAGMENT", "LOCUS_CANDIDATE",
                  "MULTI_LOCUS_CANDIDATE", "GENOME_SUPPORTED"]
        ceiling = controls_cfg.get("uncontrolled_maximum", "MULTI_LOCUS_CANDIDATE")
        if ceiling in levels and levels.index(evidence_level) > levels.index(ceiling):
            evidence_level = ceiling

    return {
        "schema_version": "2.0-alpha", "pipeline_version": "2.0.0-alpha.1", "sample_id": sample,
        "shadow_mode": shadow, "evidence_level": evidence_level, "specificity_status": specificity,
        "coverage_status": coverage_status, "control_status": control_status,
        "reported_conclusion": "SHADOW_ONLY" if shadow else evidence_level,
        "metrics": {
            "qualifying_loci": len(qualifying_loci), "total_nonredundant_reference_bp": total_bp,
            "unique_templates": unique_templates, "distinct_starts": distinct_starts,
            "proper_pair_templates": proper_pair_templates,
            "breadth_1x": breadth_1x, "breadth_3x": breadth_3x,
            "median_depth_covered": median_depth, "max_window_depth_fraction": concentration,
        },
        "provenance": provenance or {},
        "policy_notes": [
            "20-49 bp fragments are exploratory and cannot independently produce a conclusion",
            "thresholds are provisional until benchmark completion",
            "v1.1 conclusions are unchanged while shadow_mode is true",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify evidence dimensions without combinatorial classes")
    parser.add_argument("--sample", required=True)
    parser.add_argument("--loci", required=True)
    parser.add_argument("--competitive", required=True)
    parser.add_argument("--read-support")
    parser.add_argument("--coverage")
    parser.add_argument("--control-status", default="UNCONTROLLED")
    parser.add_argument("--library-mode", choices=["shotgun", "amplicon", "targeted", "unknown"], default="unknown")
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--provenance")
    parser.add_argument("--activate", action="store_true", help="reserved for post-benchmark activation")
    args = parser.parse_args()
    if args.activate:
        parser.error("evidence v2 activation is locked until the benchmark is completed")
    read_support = read_tsv(args.read_support) if args.read_support and Path(args.read_support).stat().st_size else []
    coverage = read_tsv(args.coverage) if args.coverage and Path(args.coverage).stat().st_size else []
    provenance = {}
    if args.provenance:
        with open(args.provenance, "r", encoding="utf-8") as handle:
            provenance = json.load(handle)
    result = classify(args.sample, read_tsv(args.loci), read_tsv(args.competitive), read_support,
                      coverage, args.control_status, args.library_mode, load_yaml_config(args.config), True,
                      provenance)
    write_json_atomic(args.out, result)


if __name__ == "__main__":
    main()
