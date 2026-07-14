#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import write_json_atomic
except ImportError:
    from common import write_json_atomic


PIPELINE_VERSION = "2.0.0-alpha.1"
POLICY_VERSION = "2.0-alpha"
RUN_STATUSES = {"queued", "running", "done", "done_with_warning", "blocked", "failed", "cancelled"}
STAGE_STATUSES = {"pending", "running", "done", "warning", "blocked", "failed", "cancelled"}
FAILURE_TYPES = {
    "DEPENDENCY_MISSING", "CONFIG_INVALID", "INPUT_INVALID", "TOOL_FAILURE",
    "ARTIFACT_INVALID", "CANCELLED", "UNKNOWN",
}
STAGES = [
    ("input_validation", "Validação da entrada"),
    ("quality_control", "Controle de qualidade"),
    ("assembly", "Montagem"),
    ("initial_blast", "BLAST inicial"),
    ("hsp_aggregation", "Agregação de HSPs"),
    ("locus_building", "Construção de loci"),
    ("competitive_search", "Busca competitiva"),
    ("read_remapping", "Remapeamento das reads"),
    ("coverage", "Cálculo de cobertura"),
    ("controls", "Avaliação de controles"),
    ("evidence_classification", "Geração de evidências"),
    ("report_export", "Exportação do relatório"),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initial_state(run_id: str, action: str, samples: list[str], batch_id: str | None) -> dict:
    return {
        "run_id": run_id,
        "pipeline_version": PIPELINE_VERSION,
        "policy_version": POLICY_VERSION,
        "shadow_mode": True,
        "action": action,
        "sample_ids": samples,
        "batch_id": batch_id or None,
        "status": "queued",
        "official_v1_status": "not_started",
        "evidence_v2_status": "queued",
        "current_stage": None,
        "created_at": now(),
        "started_at": None,
        "finished_at": None,
        "stages": [
            {"id": stage_id, "label": label, "status": "pending", "started_at": None,
             "finished_at": None, "message": None}
            for stage_id, label in STAGES
        ],
        "warnings": [],
        "failed_stage": None,
        "failure_type": None,
        "failure_message": None,
        "failed_command": None,
        "artifacts": {},
        "provenance": {},
    }


def read_state(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        state = json.load(handle)
    if state.get("run_id") is None or not isinstance(state.get("stages"), list):
        raise ValueError(f"invalid run state: {path}")
    return state


def set_stage(state: dict, stage_id: str, status: str, message: str | None) -> None:
    if status not in STAGE_STATUSES:
        raise ValueError(f"invalid stage status: {status}")
    stage = next((item for item in state["stages"] if item["id"] == stage_id), None)
    if stage is None:
        raise ValueError(f"unknown stage: {stage_id}")
    terminal = {"done", "warning", "blocked", "failed", "cancelled"}
    if stage["status"] in terminal:
        if status == stage["status"]:
            if message is not None:
                stage["message"] = message
            return
        if status == "running":
            # A pipeline handoff may replay already completed V1.1 stages.
            # Treat that request as an idempotent no-op; never regress state.
            return
        raise ValueError(
            f"stage {stage_id} already terminal ({stage['status']}); refusing transition to {status}"
        )
    if status == "running" and not stage["started_at"]:
        stage["started_at"] = now()
    if status == "running":
        stage["finished_at"] = None
    if status in {"done", "warning", "blocked", "failed", "cancelled"}:
        stage["started_at"] = stage["started_at"] or now()
        stage["finished_at"] = now()
    stage["status"] = status
    if message is not None:
        stage["message"] = message
    state["current_stage"] = stage_id if status == "running" else None
    if status == "warning" and message and message not in state["warnings"]:
        state["warnings"].append(message)


def set_failure(state: dict, failure_type: str, stage_id: str | None,
                message: str | None, command: str | None) -> None:
    if failure_type not in FAILURE_TYPES:
        raise ValueError(f"invalid failure type: {failure_type}")
    state["failure_type"] = failure_type
    state["failed_stage"] = stage_id or state.get("current_stage")
    state["failure_message"] = message
    state["failed_command"] = command


def main() -> None:
    parser = argparse.ArgumentParser(description="Atomically maintain Evidence V2 structured run state")
    parser.add_argument("--state", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--run-id", required=True)
    init.add_argument("--action", choices=["evidence_single", "evidence_batch"], required=True)
    init.add_argument("--sample", action="append", required=True)
    init.add_argument("--batch-id")
    stage = sub.add_parser("stage")
    stage.add_argument("--id", required=True)
    stage.add_argument("--status", choices=sorted(STAGE_STATUSES), required=True)
    stage.add_argument("--message")
    stage.add_argument("--failure-type", choices=sorted(FAILURE_TYPES))
    stage.add_argument("--failed-command")
    status = sub.add_parser("status")
    status.add_argument("--value", choices=sorted(RUN_STATUSES), required=True)
    status.add_argument("--warning", action="append", default=[])
    status.add_argument("--official-v1-status", choices=["not_started", "running", "done", "failed", "cancelled"])
    status.add_argument("--evidence-v2-status", choices=sorted(RUN_STATUSES))
    status.add_argument("--failure-type", choices=sorted(FAILURE_TYPES))
    status.add_argument("--failed-stage")
    status.add_argument("--failure-message")
    status.add_argument("--failed-command")
    artifact = sub.add_parser("artifact")
    artifact.add_argument("--name", required=True)
    artifact.add_argument("--path", required=True)
    provenance = sub.add_parser("provenance")
    provenance.add_argument("--json", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "init":
        write_json_atomic(args.state, initial_state(args.run_id, args.action, args.sample, args.batch_id))
        return
    state = read_state(args.state)
    if args.command == "stage":
        set_stage(state, args.id, args.status, args.message)
        if args.failure_type:
            set_failure(state, args.failure_type, args.id, args.message, args.failed_command)
        if args.status == "running":
            state["status"] = "running"
            state["started_at"] = state["started_at"] or now()
    elif args.command == "status":
        state["status"] = args.value
        state["evidence_v2_status"] = args.evidence_v2_status or args.value
        if args.official_v1_status:
            state["official_v1_status"] = args.official_v1_status
        if args.failure_type:
            set_failure(state, args.failure_type, args.failed_stage, args.failure_message, args.failed_command)
        for warning in args.warning:
            if warning not in state["warnings"]:
                state["warnings"].append(warning)
        if args.value == "running":
            state["started_at"] = state["started_at"] or now()
        if args.value in {"done", "done_with_warning", "blocked", "failed", "cancelled"}:
            state["finished_at"] = now()
            state["current_stage"] = None
    elif args.command == "artifact":
        state["artifacts"][args.name] = args.path
    elif args.command == "provenance":
        with args.json.open("r", encoding="utf-8") as handle:
            state["provenance"] = json.load(handle)
    write_json_atomic(args.state, state)


if __name__ == "__main__":
    main()
