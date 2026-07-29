#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .common import as_float, as_int, load_yaml_config, read_tsv, write_json_atomic
    from .evidence_contract import CONTROL_PASS, PIPELINE_VERSION, SCHEMA_VERSION, validate_document
except ImportError:
    from common import as_float, as_int, load_yaml_config, read_tsv, write_json_atomic
    from evidence_contract import CONTROL_PASS, PIPELINE_VERSION, SCHEMA_VERSION, validate_document


DEFAULTS = {
    "locus": {"minimum_candidate_bp": 50},
    "support": {
        "minimum_unique_templates": 3,
        "minimum_distinct_starts_shotgun": 2,
        "require_proper_pair_shotgun": True,
    },
    "sample_evidence": {
        "multi_locus_minimum": 2,
        "multi_locus_total_bp": 150,
        "genome_breadth_1x": 0.20,
        "median_covered_depth": 3,
    },
}


def _section(config: dict, name: str) -> dict:
    """Retain safe defaults for direct API callers; CLI config is schema-validated."""
    merged = dict(DEFAULTS[name])
    merged.update(config.get(name, {}))
    return merged


def _metric_key(row: dict) -> tuple[str, str, str]:
    return (
        str(row.get("reference_id") or row.get("reference") or ""),
        str(row.get("category") or ""),
        str(row.get("locus_id") or ""),
    )


def _index_scoped_metrics(rows: list[dict], name: str) -> tuple[dict[tuple[str, str, str], dict], list[str]]:
    result: dict[tuple[str, str, str], dict] = {}
    caveats: list[str] = []
    for row_number, row in enumerate(rows, 2):
        key = _metric_key(row)
        if not all(key):
            caveats.append(f"{name} sem reference/category/locus na linha {row_number}; métrica ignorada.")
            continue
        if key in result:
            raise ValueError(f"duplicate {name} metric key: {key}")
        result[key] = row
    return result, caveats


def _candidate_key(locus: dict) -> tuple[str, str, str]:
    return (
        str(locus.get("sseqid") or locus.get("reference_id") or ""),
        str(locus.get("category") or "UNLABELED"),
        str(locus.get("locus_id") or ""),
    )


def classify(sample: str, loci: list[dict[str, str]], competitive: list[dict[str, str]],
             read_support: list[dict[str, str]], coverage: list[dict[str, str]],
             control_status: str, library_mode: str, config: dict, shadow: bool = True,
             provenance: dict | None = None, run_id: str | None = None) -> dict:
    if shadow is not True:
        raise ValueError("shadow_mode activation is locked until benchmark approval")

    provenance = provenance or {}
    locus_cfg = _section(config, "locus")
    support_cfg = _section(config, "support")
    evidence_cfg = _section(config, "sample_evidence")
    parameters = provenance.get("parameters", {}) if isinstance(provenance, dict) else {}
    resolved_run_id = str(run_id or parameters.get("run_id") or provenance.get("run_id") or f"untracked-{sample}")
    comp_by_query = {
        (row["qseqid"], row.get("task", "blastn")): row.get("specificity_status", "NOT_EVALUATED")
        for row in competitive
    }
    support_by_key, support_caveats = _index_scoped_metrics(read_support, "read_support")
    coverage_by_key, coverage_caveats = _index_scoped_metrics(coverage, "coverage")

    evaluated_candidates = []
    all_specificity: list[str] = []
    for locus in loci:
        category = locus.get("category", "UNLABELED")
        if category not in {"TARGET_VIRUS", "UNLABELED"}:
            continue
        query_ids = list(filter(None, locus.get("query_ids", "").split(";")))
        query_statuses = [
            comp_by_query.get((query_id, locus.get("task", "blastn")), "NOT_EVALUATED")
            for query_id in query_ids
        ]
        all_specificity.extend(query_statuses)
        specificity_status = (
            "TARGET_SPECIFIC" if query_statuses and all(item == "TARGET_SPECIFIC" for item in query_statuses)
            else "NON_TARGET_BEST" if "NON_TARGET_BEST" in query_statuses and "TARGET_SPECIFIC" not in query_statuses
            else "AMBIGUOUS" if any(item in {"AMBIGUOUS", "NON_TARGET_BEST"} for item in query_statuses)
            else "NOT_EVALUATED"
        )
        key = _candidate_key(locus)
        support = support_by_key.get(key)
        covered = coverage_by_key.get(key)
        query_length = as_int(locus.get("max_query_length"))
        # Older canonical locus tables did not carry max_query_length.  In
        # that case the nonredundant reference span is the only validated
        # length available for applying the same minimum-candidate policy.
        candidate_bp = query_length or as_int(locus.get("covered_reference_bp"))
        evaluated_candidates.append({
            "candidate_id": locus.get("locus_id") or f"{key[0]}:{locus.get('reference_start', '')}-{locus.get('reference_end', '')}",
            "reference_id": key[0],
            "category": key[1],
            "locus_id": key[2],
            "query_ids": query_ids,
            "orientation": locus.get("orientation", ""),
            "segment": locus.get("segment", "unsegmented"),
            "reference_intervals": locus.get("reference_intervals", ""),
            "specificity_status": specificity_status,
            "covered_reference_bp": as_int(locus.get("covered_reference_bp")),
            "candidate_bp": candidate_bp,
            "support": {
                "status": support.get("support_status", "NOT_EVALUATED") if support else "NOT_EVALUATED",
                "unique_templates": as_int(support.get("unique_templates")) if support else 0,
                "distinct_starts": as_int(support.get("distinct_starts")) if support else 0,
                "proper_pair_templates": as_int(support.get("proper_pair_templates")) if support else 0,
            },
            "coverage": {
                "status": "AVAILABLE" if covered else "NOT_EVALUATED",
                "breadth_1x": as_float(covered.get("breadth_1x")) if covered else 0.0,
                "breadth_3x": as_float(covered.get("breadth_3x")) if covered else 0.0,
                "median_depth_covered": as_float(covered.get("median_depth_covered")) if covered else 0.0,
                "max_window_depth_fraction": as_float(covered.get("max_window_depth_fraction")) if covered else 0.0,
            },
        })

    if all_specificity and all(item == "TARGET_SPECIFIC" for item in all_specificity):
        specificity_status = "TARGET_SPECIFIC"
    elif "NON_TARGET_BEST" in all_specificity and "TARGET_SPECIFIC" not in all_specificity:
        specificity_status = "NON_TARGET_BEST"
    elif any(item in {"AMBIGUOUS", "NON_TARGET_BEST"} for item in all_specificity):
        specificity_status = "AMBIGUOUS"
    else:
        specificity_status = "NOT_EVALUATED"

    def is_specific(candidate: dict) -> bool:
        return candidate["specificity_status"] == "TARGET_SPECIFIC" or (
            not competitive and candidate["category"] == "UNLABELED"
        )

    def support_passes(candidate: dict) -> bool:
        support = candidate["support"]
        if support["status"] != "SUPPORT_AVAILABLE":
            return False
        if support["unique_templates"] < as_int(support_cfg["minimum_unique_templates"]):
            return False
        if library_mode == "shotgun":
            if support["distinct_starts"] < as_int(support_cfg["minimum_distinct_starts_shotgun"]):
                return False
            if (support_cfg["require_proper_pair_shotgun"]
                    and support["proper_pair_templates"] < as_int(support_cfg["minimum_unique_templates"])):
                return False
        return True

    locus_eligible = [
        item for item in evaluated_candidates
        if is_specific(item) and item["candidate_bp"] >= as_int(locus_cfg["minimum_candidate_bp"])
    ]
    candidates = [item for item in locus_eligible if support_passes(item)]
    aggregate_candidates_by_interval = {}
    for candidate in candidates:
        interval_key = (
            candidate["reference_id"],
            candidate["segment"],
            candidate["orientation"],
            candidate["reference_intervals"],
        )
        aggregate_candidates_by_interval.setdefault(interval_key, candidate)
    aggregate_candidates = list(aggregate_candidates_by_interval.values())
    matched_support = [item["support"] for item in candidates]
    matched_coverage = [item["coverage"] for item in candidates if item["coverage"]["status"] == "AVAILABLE"]
    coverage_passes = [
        item for item in matched_coverage
        if item["breadth_1x"] >= as_float(evidence_cfg["genome_breadth_1x"])
        and item["median_depth_covered"] >= as_float(evidence_cfg["median_covered_depth"])
    ]
    if any(item["support"]["status"] == "UMI_DEDUP_UNAVAILABLE" for item in evaluated_candidates):
        coverage_status = "UMI_DEDUP_UNAVAILABLE"
    elif matched_coverage:
        coverage_status = "COVERAGE_AVAILABLE" if coverage_passes else "INSUFFICIENT_COVERAGE"
    elif locus_eligible:
        coverage_status = "INSUFFICIENT_SUPPORT" if not candidates else "COVERAGE_UNAVAILABLE"
    else:
        coverage_status = "COVERAGE_UNAVAILABLE"
    multi_locus_passes = (
        len(aggregate_candidates) >= as_int(evidence_cfg["multi_locus_minimum"])
        and sum(item["covered_reference_bp"] for item in aggregate_candidates) >= as_int(evidence_cfg["multi_locus_total_bp"])
    )
    analysis_outcome = "EVIDENCE_RECOVERED" if candidates else "NO_EVIDENCE_RECOVERED"
    caveats = [
        "Evidence 2.0 alpha.2 opera em shadow mode; E2 e E3 permanecem estruturalmente bloqueados.",
        "E1 autoriza relatar apenas evidência computacional exploratória, não presença ou identidade viral.",
        *support_caveats,
        *coverage_caveats,
    ]
    if not candidates:
        caveats.append("Nenhuma evidência recuperada sob os limiares configurados; isso não demonstra ausência viral.")
    if control_status not in CONTROL_PASS:
        caveats.append(f"Controles não autorizam promoção: {control_status}.")

    gates = [
        {
            "gate_id": "candidate_evidence", "status": "PASS" if locus_eligible else "BLOCKED",
            "reason": (
                "Candidato específico atende locus.minimum_candidate_bp."
                if locus_eligible else "Nenhum locus específico atende locus.minimum_candidate_bp."
            ),
        },
        {
            "gate_id": "competitive_specificity",
            "status": "PASS" if specificity_status == "TARGET_SPECIFIC" else "BLOCKED",
            "reason": specificity_status,
        },
        {
            "gate_id": "reference_scoped_support",
            "status": "PASS" if matched_support else "BLOCKED",
            "reason": (
                "Suporte candidato-específico atende os limiares configurados."
                if matched_support else "Nenhum suporte candidato-específico atende os limiares configurados."
            ),
        },
        {
            "gate_id": "multi_locus_evidence",
            "status": "PASS" if multi_locus_passes else "BLOCKED",
            "reason": (
                "Candidatos atendem sample_evidence.multi_locus_minimum e multi_locus_total_bp."
                if multi_locus_passes else "Candidatos não atendem os limiares multi-locus configurados."
            ),
        },
        {
            "gate_id": "reference_scoped_coverage",
            "status": "PASS" if coverage_passes else "BLOCKED",
            "reason": (
                "Cobertura candidato-específica atende genome_breadth_1x e median_covered_depth."
                if coverage_passes else "Nenhuma cobertura candidato-específica atende os limiares configurados."
            ),
        },
        {
            "gate_id": "controls",
            "status": "PASS" if control_status in CONTROL_PASS else "BLOCKED",
            "reason": control_status,
        },
        {
            "gate_id": "alpha_shadow_ceiling", "status": "BLOCKED",
            "reason": "A política alpha.2 mantém o teto em E1 até benchmark aprovado.",
        },
    ]

    metrics = {
        "candidate_count": len(aggregate_candidates),
        "qualifying_loci": len(aggregate_candidates),
        "total_nonredundant_reference_bp": sum(item["covered_reference_bp"] for item in aggregate_candidates),
        "unique_templates": max((item["unique_templates"] for item in matched_support), default=0),
        "distinct_starts": max((item["distinct_starts"] for item in matched_support), default=0),
        "proper_pair_templates": max((item["proper_pair_templates"] for item in matched_support), default=0),
        "breadth_1x": max((item["breadth_1x"] for item in matched_coverage), default=0.0),
        "breadth_3x": max((item["breadth_3x"] for item in matched_coverage), default=0.0),
        "median_depth_covered": max((item["median_depth_covered"] for item in matched_coverage), default=0.0),
        "max_window_depth_fraction": max((item["max_window_depth_fraction"] for item in matched_coverage), default=0.0),
    }

    document = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "sample_id": sample,
        "run_id": resolved_run_id,
        "execution_status": "done",
        "analysis_outcome": analysis_outcome,
        "evidence_level": "E1",
        "shadow_mode": True,
        "reported_conclusion": "SHADOW_ONLY",
        "candidates": candidates,
        "caveats": list(dict.fromkeys(caveats)),
        "promotion_gates": gates,
        "specificity": {"status": specificity_status},
        "coverage": {"status": coverage_status, "by_candidate": [item["coverage"] | {"candidate_id": item["candidate_id"]} for item in candidates]},
        "controls": {"status": control_status, "metrics": {}},
        "provenance": provenance,
        "library_mode": library_mode,
        "metrics": metrics,
        # Read-only compatibility aliases for the existing dashboard/API.
        "specificity_status": specificity_status,
        "coverage_status": coverage_status,
        "control_status": control_status,
    }
    return validate_document(document)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create conservative alpha.2 evidence documents")
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
    parser.add_argument("--run-id")
    parser.add_argument("--activate", action="store_true", help="reserved for post-benchmark activation")
    args = parser.parse_args()
    if args.activate:
        parser.error("evidence activation is locked until the benchmark is completed")
    read_support = read_tsv(args.read_support) if args.read_support and Path(args.read_support).stat().st_size else []
    coverage = read_tsv(args.coverage) if args.coverage and Path(args.coverage).stat().st_size else []
    provenance = {}
    if args.provenance:
        with open(args.provenance, "r", encoding="utf-8", errors="strict") as handle:
            provenance = json.load(handle)
    result = classify(
        args.sample, read_tsv(args.loci), read_tsv(args.competitive), read_support, coverage,
        args.control_status, args.library_mode, load_yaml_config(args.config), True, provenance, args.run_id,
    )
    write_json_atomic(args.out, result)


if __name__ == "__main__":
    main()
