#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import (
        build_artifact_manifest, fsync_directory, sha256_file,
        validate_artifact_manifest, write_json_atomic,
    )
    from .validate_run_artifacts import validate
except ImportError:
    from common import (
        build_artifact_manifest, fsync_directory, sha256_file,
        validate_artifact_manifest, write_json_atomic,
    )
    from validate_run_artifacts import validate


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and atomically promote an Evidence V2 run")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--final", required=True, type=Path)
    args = parser.parse_args()
    if args.final.exists():
        raise FileExistsError(f"final run directory already exists: {args.final}")
    errors = validate(args.staging)
    if errors:
        raise ValueError("; ".join(errors))
    with args.state.open("r", encoding="utf-8") as handle:
        state = json.load(handle)
    status = "done_with_warning" if state.get("warnings") else "done"
    final_state = dict(state)
    with (args.staging / "sample_evidence.json").open("r", encoding="utf-8", errors="strict") as handle:
        evidence = json.load(handle)
    final_state.update({
        "status": status,
        "evidence_v2_status": status,
        "execution_status": evidence["execution_status"],
        "analysis_outcome": evidence["analysis_outcome"],
        "evidence_level": evidence["evidence_level"],
        "current_stage": None,
        "finished_at": now(),
    })
    write_json_atomic(args.staging / "run_state.json", final_state)
    manifest = build_artifact_manifest(args.staging)
    write_json_atomic(args.staging / "artifact_manifest.json", manifest)
    manifest_errors = validate_artifact_manifest(args.staging, manifest)
    if manifest_errors:
        raise ValueError("; ".join(manifest_errors))
    success = {
        "run_id": state["run_id"], "pipeline_version": state["pipeline_version"],
        "policy_version": state["policy_version"], "shadow_mode": True,
        "status": status, "validated_at": final_state["finished_at"],
        "artifact_count": len(manifest["files"]),
        "artifact_manifest_sha256": sha256_file(args.staging / "artifact_manifest.json"),
        "sample_evidence_sha256": sha256_file(args.staging / "sample_evidence.json"),
    }
    # SUCCESS is deliberately the final write inside staging.
    write_json_atomic(args.staging / "SUCCESS.json", success)
    fsync_directory(args.staging)
    try:
        args.final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(args.staging, args.final)
    except Exception:
        # A commit marker is valid only as part of a promoted run directory.
        (args.staging / "SUCCESS.json").unlink(missing_ok=True)
        fsync_directory(args.staging)
        raise
    fsync_directory(args.final.parent)
    write_json_atomic(args.state, final_state)
    print(args.final)


if __name__ == "__main__":
    main()
