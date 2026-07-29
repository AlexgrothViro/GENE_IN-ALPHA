#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import (
        build_artifact_manifest, fsync_directory, read_tsv, sha256_file,
        validate_artifact_manifest, write_json_atomic,
    )
    from .evidence_contract import PIPELINE_VERSION, validate_document
    from .run_state import read_state
    from .validate_run_artifacts import validate
except ImportError:
    from common import (
        build_artifact_manifest, fsync_directory, read_tsv, sha256_file,
        validate_artifact_manifest, write_json_atomic,
    )
    from evidence_contract import PIPELINE_VERSION, validate_document
    from run_state import read_state
    from validate_run_artifacts import validate


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_sample_commit(sample_dir: Path, row: dict[str, str], parent_run_id: str) -> None:
    source_success_path = sample_dir / "SUCCESS.json"
    if not source_success_path.is_file():
        raise ValueError(f"resultado incompleto da amostra {row['sample_id']}")
    source_success = json.loads(source_success_path.read_text(encoding="utf-8", errors="strict"))
    if source_success.get("status") not in {"done", "done_with_warning"}:
        raise ValueError(f"execução filha não concluída da amostra {row['sample_id']}")
    write_json_atomic(sample_dir / "SOURCE_SUCCESS.json", source_success)
    source_success_path.unlink()
    old_manifest = sample_dir / "artifact_manifest.json"
    if old_manifest.exists():
        old_manifest.unlink()
    errors = validate(sample_dir)
    if errors:
        raise ValueError(f"amostra {row['sample_id']}: {'; '.join(errors)}")
    with (sample_dir / "sample_evidence.json").open("r", encoding="utf-8", errors="strict") as handle:
        validate_document(json.load(handle))
    manifest = build_artifact_manifest(sample_dir)
    write_json_atomic(sample_dir / "artifact_manifest.json", manifest)
    manifest_errors = validate_artifact_manifest(sample_dir, manifest)
    if manifest_errors:
        raise ValueError(f"amostra {row['sample_id']}: {'; '.join(manifest_errors)}")
    write_json_atomic(sample_dir / "SUCCESS.json", {
        "run_id": row["run_id"], "parent_run_id": parent_run_id,
        "pipeline_version": PIPELINE_VERSION,
        "status": source_success.get("status", "done"), "completed_at": now(),
        "shadow_mode": True, "artifact_count": len(manifest["files"]),
        "artifact_manifest_sha256": sha256_file(sample_dir / "artifact_manifest.json"),
        "sample_evidence_sha256": sha256_file(sample_dir / "sample_evidence.json"),
    })
    fsync_directory(sample_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and atomically promote an Evidence V2 batch")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--final", required=True, type=Path)
    parser.add_argument("--run-map", required=True, type=Path)
    args = parser.parse_args()
    if args.final.exists():
        raise FileExistsError(f"diretório final já existe: {args.final}")
    state = read_state(args.state)
    rows = read_tsv(args.run_map)
    required = ["batch_evidence.json", "control_status.tsv", "batch_report.md", "provenance.json"]
    missing = [name for name in required if not (args.staging / name).is_file()]
    if missing:
        raise ValueError("artefatos de lote ausentes: " + ", ".join(missing))
    for row in rows:
        write_sample_commit(args.staging / "samples" / row["sample_id"], row, state["run_id"])

    shutil.rmtree(args.staging / "work", ignore_errors=True)
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
    manifest = build_artifact_manifest(args.staging)
    write_json_atomic(args.staging / "artifact_manifest.json", manifest)
    manifest_errors = validate_artifact_manifest(args.staging, manifest)
    if manifest_errors:
        raise ValueError("; ".join(manifest_errors))
    # SUCCESS is deliberately the final batch write.
    write_json_atomic(args.staging / "SUCCESS.json", {
        "run_id": state["run_id"], "pipeline_version": PIPELINE_VERSION,
        "status": state["status"], "completed_at": now(),
        "batch_evidence_sha256": sha256_file(args.staging / "batch_evidence.json"),
        "artifact_manifest_sha256": sha256_file(args.staging / "artifact_manifest.json"),
        "artifact_count": len(manifest["files"]), "sample_count": len(rows), "shadow_mode": True,
    })
    fsync_directory(args.staging)
    try:
        args.final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(args.staging, args.final)
    except Exception:
        (args.staging / "SUCCESS.json").unlink(missing_ok=True)
        fsync_directory(args.staging)
        raise
    fsync_directory(args.final.parent)
    write_json_atomic(args.state, state)
    print(args.final)


if __name__ == "__main__":
    main()
