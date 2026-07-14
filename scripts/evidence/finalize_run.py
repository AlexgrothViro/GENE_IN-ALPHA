#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    from .common import write_json_atomic
    from .validate_run_artifacts import validate
except ImportError:
    from common import write_json_atomic
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
    final_state.update({
        "status": status,
        "evidence_v2_status": status,
        "current_stage": None,
        "finished_at": now(),
    })
    success = {
        "run_id": state["run_id"], "pipeline_version": state["pipeline_version"],
        "policy_version": state["policy_version"], "shadow_mode": True,
        "status": status, "validated_at": final_state["finished_at"],
    }
    write_json_atomic(args.staging / "run_state.json", final_state)
    write_json_atomic(args.staging / "SUCCESS.json", success)
    args.final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(args.staging, args.final)
    write_json_atomic(args.state, final_state)
    print(args.final)


if __name__ == "__main__":
    main()
