#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .common import read_tsv, write_json_atomic, write_text_atomic
    from .activation_policy import load_activation_policy
    from .evidence_contract import promote_for_public_output, validate_document
except ImportError:
    from common import read_tsv, write_json_atomic, write_text_atomic
    from activation_policy import load_activation_policy
    from evidence_contract import promote_for_public_output, validate_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Create batch-level Evidence V2 summary")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--run-map", required=True)
    parser.add_argument("--statuses", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    policy = load_activation_policy()
    statuses = {row["sample_id"]: row for row in read_tsv(args.statuses)}
    samples = []
    for row in read_tsv(args.run_map):
        path = args.root / "samples" / row["sample_id"] / "sample_evidence.json"
        data = validate_document(json.loads(path.read_text(encoding="utf-8", errors="strict")))
        samples.append({
            "sample_id": row["sample_id"], "child_run_id": row["run_id"],
            "execution_status": data["execution_status"], "analysis_outcome": data["analysis_outcome"],
            "evidence_level": data["evidence_level"],
            "reported_conclusion": data["reported_conclusion"],
            "specificity_status": data["specificity"].get("status", "NOT_EVALUATED"),
            "coverage_status": data["coverage"].get("status", "NOT_EVALUATED"),
            "control_status": data["controls"].get("status", "NOT_EVALUATED"),
            "control_metrics": statuses.get(row["sample_id"], {}),
            "caveats": data["caveats"], "promotion_gates": data["promotion_gates"],
        })
    value = {
        "schema_version": "2.0", "pipeline_version": "2.0.0-alpha.2",
        "run_id": args.run_id, "batch_id": args.batch_id,
        "shadow_mode": policy["shadow_mode"],
        "policy_version": policy["policy_version"],
        "activation_record_id": policy["activation_record_id"],
        "evidence_ceiling": policy["evidence_ceiling"],
        "reported_conclusion": "E1_ONLY", "samples": samples,
    }
    write_json_atomic(args.out, promote_for_public_output(value))
    lines = [
        "# Gene-In 2.0 — relatório de evidência do lote", "",
        "> E1 ATIVO: evidência computacional canônica. Não afirma presença, ausência, identidade ou confirmação viral.", "",
        "| Amostra | Outcome | Evidência | Especificidade | Cobertura | Controle |",
        "|---|---|---|---|---|---|",
    ]
    for item in samples:
        lines.append(
            f"| {item['sample_id']} | {item['analysis_outcome']} | {item['evidence_level']} | "
            f"{item['specificity_status']} | {item['coverage_status']} | {item['control_status']} |"
        )
    write_text_atomic(args.report, "\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
