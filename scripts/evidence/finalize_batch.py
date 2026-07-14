#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import read_tsv, write_json_atomic
    from .run_state import read_state
except ImportError:
    from common import read_tsv, write_json_atomic
    from run_state import read_state


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and atomically promote an Evidence V2 batch")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--final", required=True, type=Path)
    parser.add_argument("--run-map", required=True, type=Path)
    args = parser.parse_args()
    state = read_state(args.state)
    rows = read_tsv(args.run_map)
    required = ["batch_evidence.json", "control_status.tsv", "batch_report.md", "provenance.json"]
    missing = [name for name in required if not (args.staging / name).is_file()]
    if missing:
        raise ValueError("artefatos de lote ausentes: " + ", ".join(missing))
    for row in rows:
        sample_dir = args.staging / "samples" / row["sample_id"]
        if not (sample_dir / "SUCCESS.json").is_file() or not (sample_dir / "sample_evidence.json").is_file():
            raise ValueError(f"resultado incompleto da amostra {row['sample_id']}")
        sample_evidence = json.loads((sample_dir / "sample_evidence.json").read_text(encoding="utf-8"))
        required = {"sample_id", "evidence_level", "specificity_status", "coverage_status", "control_status"}
        if not isinstance(sample_evidence, dict) or not required.issubset(sample_evidence):
            raise ValueError(f"sample_evidence inválido da amostra {row['sample_id']}")
        source_success = json.loads((sample_dir / "SUCCESS.json").read_text(encoding="utf-8"))
        if source_success.get("status") not in {"done", "done_with_warning"}:
            raise ValueError(f"execução filha não concluída da amostra {row['sample_id']}")
        write_json_atomic(sample_dir / "SOURCE_SUCCESS.json", source_success)
        write_json_atomic(sample_dir / "SUCCESS.json", {
            "run_id": row["run_id"], "parent_run_id": state["run_id"], "status": source_success.get("status", "done"),
            "completed_at": now(), "shadow_mode": True,
            "sample_evidence_sha256": hashlib.sha256((sample_dir / "sample_evidence.json").read_bytes()).hexdigest(),
        })
    state["status"] = "done_with_warning" if state.get("warnings") else "done"
    state["evidence_v2_status"] = state["status"]
    state["current_stage"] = None
    state["finished_at"] = now()
    state["artifacts"].update({
        "batch_evidence": f"runs/{state['run_id']}/batch_evidence.json",
        "control_status": f"runs/{state['run_id']}/control_status.tsv",
        "report": f"runs/{state['run_id']}/batch_report.md",
    })
    write_json_atomic(args.staging / "run_state.json", state)
    digest = hashlib.sha256((args.staging / "batch_evidence.json").read_bytes()).hexdigest()
    write_json_atomic(args.staging / "SUCCESS.json", {
        "run_id": state["run_id"], "status": state["status"], "completed_at": now(),
        "batch_evidence_sha256": digest, "sample_count": len(rows), "shadow_mode": True,
    })
    shutil.rmtree(args.staging / "work", ignore_errors=True)
    if args.final.exists():
        raise FileExistsError(f"diretório final já existe: {args.final}")
    args.final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(args.staging, args.final)
    write_json_atomic(args.state, state)
    print(args.final)


if __name__ == "__main__":
    main()
