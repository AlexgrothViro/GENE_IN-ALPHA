#!/usr/bin/env python3
from __future__ import annotations

import argparse

try:
    from .common import load_yaml_config, read_fasta, read_tsv, sequence_metrics, write_json_atomic
except ImportError:
    from common import load_yaml_config, read_fasta, read_tsv, sequence_metrics, write_json_atomic


def informative_sites(sequences: list[str]) -> int:
    if not sequences:
        return 0
    width = max(map(len, sequences))
    result = 0
    for index in range(width):
        counts: dict[str, int] = {}
        for sequence in sequences:
            state = sequence[index].upper() if index < len(sequence) else "-"
            if state in "ACGT":
                counts[state] = counts.get(state, 0) + 1
        if sum(count >= 2 for count in counts.values()) >= 2:
            result += 1
    return result


def evaluate(alignment_path: str, query_path: str, reference_path: str, config: dict,
             metadata_path: str | None = None, competitive_path: str | None = None,
             iqtree_available: bool = True) -> dict:
    alignment = read_fasta(alignment_path)
    queries = read_fasta(query_path)
    references = read_fasta(reference_path)
    phy = config["phylogeny"]
    flags: list[str] = []
    aligned_queries = [alignment[name] for name in queries if name in alignment]
    aligned_bp = max((sum(base.upper() in "ACGT" for base in seq) for seq in aligned_queries), default=0)
    characters = sum(len(seq) for seq in aligned_queries)
    n_fraction = sum(seq.upper().count("N") for seq in aligned_queries) / characters if characters else 1.0
    gap_fraction = sum(seq.count("-") for seq in aligned_queries) / characters if characters else 1.0
    low_complexity = any(sequence_metrics(seq.replace("-", ""))["entropy"] < 1.2 for seq in aligned_queries)
    informative = informative_sites(list(alignment.values()))
    if aligned_bp < int(phy["minimum_aligned_bp"]): flags.append("INSUFFICIENT_ALIGNED_BP")
    if informative < int(phy["minimum_informative_sites"]): flags.append("INSUFFICIENT_INFORMATIVE_SITES")
    if len(references) < int(phy["minimum_references"]): flags.append("INSUFFICIENT_REFERENCES")
    if n_fraction > float(phy["maximum_n_fraction"]): flags.append("EXCESSIVE_N_FRACTION")
    if gap_fraction > float(phy["maximum_gap_fraction"]): flags.append("EXCESSIVE_GAP_FRACTION")
    if low_complexity: flags.append("LOW_COMPLEXITY")
    if not iqtree_available: flags.append("IQTREE_UNAVAILABLE")

    taxon_groups: set[str] = set()
    outgroup_present = False
    metadata_ids: set[str] = set()
    if metadata_path:
        rows = read_tsv(metadata_path)
        required = {"sseqid", "taxon_group", "is_outgroup"}
        if rows and not required.issubset(rows[0]):
            flags.append("INVALID_REFERENCE_METADATA")
        for row in rows:
            metadata_ids.add(row.get("sseqid", ""))
            if row.get("taxon_group"):
                taxon_groups.add(row["taxon_group"])
            outgroup_present = outgroup_present or row.get("is_outgroup", "").strip().lower() in {"1", "true", "yes"}
        if not set(references).issubset(metadata_ids) or len(taxon_groups) < 2 or not outgroup_present:
            flags.append("UNBALANCED_REFERENCE_PANEL")
    else:
        flags.append("REFERENCE_PANEL_METADATA_MISSING")

    chimera = False
    if competitive_path:
        taxa_by_query: dict[str, set[str]] = {}
        for row in read_tsv(competitive_path):
            if row.get("specificity_status") in {"AMBIGUOUS", "NON_TARGET_BEST"}:
                chimera = True
            taxon = row.get("target_taxon", "")
            if taxon:
                taxa_by_query.setdefault(row["qseqid"], set()).add(taxon)
        chimera = chimera or any(len(taxa) > 1 for taxa in taxa_by_query.values())
    if chimera:
        flags.append("CHIMERA_SUSPECTED")

    flags = list(dict.fromkeys(flags))
    return {
        "gate_status": "PASS" if not flags else "BLOCKED",
        "flags": flags,
        "metrics": {
            "aligned_bp": aligned_bp,
            "informative_sites": informative,
            "reference_count": len(references),
            "n_fraction": n_fraction,
            "gap_fraction": gap_fraction,
            "taxon_groups": len(taxon_groups),
            "outgroup_present": outgroup_present,
        },
        "note": "Limiares operacionais provisórios até a conclusão do benchmark.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply operational phylogeny gates")
    parser.add_argument("--alignment", required=True)
    parser.add_argument("--queries", required=True)
    parser.add_argument("--references", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--reference-metadata")
    parser.add_argument("--competitive")
    parser.add_argument("--iqtree-available", choices=["true", "false"], default="true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = evaluate(args.alignment, args.queries, args.references, load_yaml_config(args.config),
                      args.reference_metadata, args.competitive, args.iqtree_available == "true")
    write_json_atomic(args.out, result)
    raise SystemExit(0 if result["gate_status"] == "PASS" else 3)


if __name__ == "__main__":
    main()
