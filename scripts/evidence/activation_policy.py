#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ALLOWED_LEVELS = {"E1", "NOT_EVALUABLE"}
ACTIVE_CONCLUSIONS = {
    "EVIDENCE_RECOVERED": "E1_COMPUTATIONAL_EVIDENCE",
    "NO_EVIDENCE_RECOVERED": "NO_EVIDENCE_RECOVERED",
    "NOT_EVALUABLE": "NOT_EVALUABLE",
}


def default_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "evidence_activation.json"


def load_activation_policy(path: str | Path | None = None) -> dict:
    source = Path(path) if path else default_path()
    with source.open("r", encoding="utf-8", errors="strict") as handle:
        value = json.load(handle)
    if not isinstance(value, dict) or value.get("schema_version") != "1.0":
        raise ValueError("activation policy requires schema_version 1.0")
    required = {
        "activation_record_id", "policy_version", "status", "effective_at",
        "shadow_mode", "evidence_ceiling", "approval", "validation_basis", "invariants",
    }
    missing = required - set(value)
    if missing:
        raise ValueError("activation policy missing fields: " + ", ".join(sorted(missing)))
    for key in ("activation_record_id", "policy_version", "effective_at"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError(f"activation policy {key} is required")
    if value["status"] != "ACTIVE":
        raise ValueError("activation policy is not ACTIVE")
    if value["shadow_mode"] is not False:
        raise ValueError("active E1 policy requires shadow_mode=false")
    if value["evidence_ceiling"] != "E1":
        raise ValueError("active policy evidence ceiling must remain E1")
    if not isinstance(value["approval"], dict) or not value["approval"].get("authority"):
        raise ValueError("activation policy requires documented approval authority")
    if not isinstance(value["validation_basis"], dict):
        raise ValueError("activation policy validation_basis must be an object")
    invariants = value["invariants"]
    if not isinstance(invariants, dict):
        raise ValueError("activation policy invariants must be an object")
    if set(invariants.get("allowed_evidence_levels", [])) != ALLOWED_LEVELS:
        raise ValueError("activation policy must allow only E1 and NOT_EVALUABLE")
    if invariants.get("exploratory_fragment_max_bp") != 49:
        raise ValueError("activation policy must preserve the 20-49 bp exploratory ceiling")
    if invariants.get("exploratory_fragments_never_promote_alone") is not True:
        raise ValueError("activation policy must block isolated exploratory-fragment promotion")
    if invariants.get("diagnostic_language_allowed") is not False:
        raise ValueError("activation policy must prohibit diagnostic language")
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        **value,
        "source": str(source.resolve()),
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def conclusion_for(policy: dict, analysis_outcome: str) -> str:
    if policy.get("shadow_mode") is True:
        return "SHADOW_ONLY"
    try:
        return ACTIVE_CONCLUSIONS[analysis_outcome]
    except KeyError as exc:
        raise ValueError(f"unsupported analysis outcome: {analysis_outcome}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and inspect the Evidence V2 activation policy")
    parser.add_argument("--policy", type=Path, default=default_path())
    parser.add_argument(
        "--field",
        choices=[
            "activation_record_id", "policy_version", "shadow_mode",
            "evidence_ceiling", "source", "sha256",
        ],
    )
    args = parser.parse_args()
    value = load_activation_policy(args.policy)
    if args.field:
        field = value[args.field]
        print(str(field).lower() if isinstance(field, bool) else field)
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
