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
    from .run_state import read_state, state_lock
    from .validate_run_artifacts import validate
except ImportError:
    from common import (
        build_artifact_manifest, fsync_directory, sha256_file,
        validate_artifact_manifest, write_json_atomic,
    )
    from run_state import read_state, state_lock
    from validate_run_artifacts import validate


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def remove_commit_metadata(directory: Path) -> None:
    (directory / "SUCCESS.json").unlink(missing_ok=True)
    (directory / "artifact_manifest.json").unlink(missing_ok=True)
    fsync_directory(directory)


def promote_directory(staging: Path, final: Path) -> None:
    os.replace(staging, final)


def validate_identity(state: dict, evidence: dict, staging: Path, final: Path) -> None:
    run_id = state.get("run_id")
    if state.get("action") != "evidence_single":
        raise ValueError("single-run finalizer requires evidence_single state")
    if evidence.get("run_id") != run_id:
        raise ValueError("sample evidence run_id does not match run state")
    if state.get("sample_ids") != [evidence.get("sample_id")]:
        raise ValueError("sample evidence sample_id does not match run state")
    if state.get("shadow_mode") is not evidence.get("shadow_mode"):
        # Keep checked-in Alpha.2 fixtures and explicitly generated historical
        # shadow runs readable after E1 activation.  A shadow document without
        # activation metadata is unambiguously a legacy artifact; promote it
        # as shadow and strip active-policy fields from the committed state.
        if evidence.get("shadow_mode") is True and not evidence.get("policy_version"):
            state["shadow_mode"] = True
            state["policy_version"] = "2.0-alpha"
            state.pop("activation_record_id", None)
            state.pop("activation_record_sha256", None)
            state.pop("evidence_ceiling", None)
        else:
            raise ValueError("sample evidence shadow_mode does not match run state")
    if not evidence.get("shadow_mode"):
        for field in ("policy_version", "activation_record_id", "evidence_ceiling"):
            if state.get(field) != evidence.get(field):
                raise ValueError(f"sample evidence {field} does not match run state")
    if staging.name != run_id or final.name != run_id:
        raise ValueError("staging and final directories must match run_id")
    if state.get("status") in {"done", "done_with_warning", "blocked", "failed", "cancelled"}:
        raise ValueError(f"run state is already terminal: {state.get('status')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and atomically promote an Evidence V2 run")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--final", required=True, type=Path)
    args = parser.parse_args()
    if args.final.exists():
        raise FileExistsError(f"final run directory already exists: {args.final}")
    args.final.parent.mkdir(parents=True, exist_ok=True)
    if args.staging.stat().st_dev != args.final.parent.stat().st_dev:
        raise ValueError("run staging and final directory must share a filesystem")
    if (args.staging / "SUCCESS.json").exists():
        raise ValueError("staging contains an invalid pre-existing SUCCESS.json")
    if (args.staging / "artifact_manifest.json").is_file() and not (args.staging / "SUCCESS.json").exists():
        # Recover a staging directory left after a failed promotion attempt.
        (args.staging / "artifact_manifest.json").unlink()
    errors = validate(args.staging)
    if errors:
        raise ValueError("; ".join(errors))
    with (args.staging / "sample_evidence.json").open("r", encoding="utf-8", errors="strict") as handle:
        evidence = json.load(handle)
    with state_lock(args.state):
        state = read_state(args.state)
        validate_identity(state, evidence, args.staging, args.final)
        status = "done_with_warning" if state.get("warnings") else "done"
        final_state = dict(state)
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
            remove_commit_metadata(args.staging)
            raise ValueError("; ".join(manifest_errors))
        success = {
            "run_id": state["run_id"], "pipeline_version": state["pipeline_version"],
            "policy_version": state.get("policy_version"),
            "shadow_mode": state["shadow_mode"],
            "status": status, "validated_at": final_state["finished_at"],
            "artifact_count": len(manifest["files"]),
            "artifact_manifest_sha256": sha256_file(args.staging / "artifact_manifest.json"),
            "sample_evidence_sha256": sha256_file(args.staging / "sample_evidence.json"),
        }
        if not state["shadow_mode"]:
            success.update({
                "policy_version": state["policy_version"],
                "activation_record_id": state.get("activation_record_id"),
                "activation_record_sha256": state.get("activation_record_sha256"),
                "evidence_ceiling": state.get("evidence_ceiling"),
            })
        fsync_directory(args.staging)
        try:
            promote_directory(args.staging, args.final)
        except Exception:
            remove_commit_metadata(args.staging)
            raise
        fsync_directory(args.final.parent)
        try:
            # The promoted directory remains invalid until this final commit write.
            write_json_atomic(args.final / "SUCCESS.json", success)
            fsync_directory(args.final)
            write_json_atomic(args.state, final_state)
        except Exception:
            # Never leave a valid committed run paired with stale external state.
            (args.final / "SUCCESS.json").unlink(missing_ok=True)
            fsync_directory(args.final)
            try:
                os.replace(args.final, args.staging)
                remove_commit_metadata(args.staging)
                fsync_directory(args.final.parent)
            except Exception:
                # The final directory remains invalid because SUCCESS was removed.
                pass
            raise
    print(args.final)


if __name__ == "__main__":
    main()
