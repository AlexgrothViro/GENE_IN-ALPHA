#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .common import read_tsv, write_json_atomic
except ImportError:
    from common import read_tsv, write_json_atomic


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
    statuses = {row["sample_id"]: row for row in read_tsv(args.statuses)}
    samples = []
    for row in read_tsv(args.run_map):
        path = args.root / "samples" / row["sample_id"] / "sample_evidence.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        samples.append({
            "sample_id": row["sample_id"], "child_run_id": row["run_id"],
            "evidence_level": data.get("evidence_level"),
            "specificity_status": data.get("specificity_status"),
            "coverage_status": data.get("coverage_status"),
            "control_status": data.get("control_status"),
            "control_metrics": statuses.get(row["sample_id"], {}),
        })
    value = {"run_id": args.run_id, "batch_id": args.batch_id, "shadow_mode": True, "samples": samples}
    write_json_atomic(args.out, value)
    lines = ["# Evidence V2 — relatório experimental do lote", "", "> Evidence V2 em modo experimental. Não substitui a classificação validada da versão 1.1.", "", "| Amostra | Evidência | Especificidade | Cobertura | Controle |", "|---|---|---|---|---|"]
    for item in samples:
        lines.append(f"| {item['sample_id']} | {item['evidence_level']} | {item['specificity_status']} | {item['coverage_status']} | {item['control_status']} |")
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
