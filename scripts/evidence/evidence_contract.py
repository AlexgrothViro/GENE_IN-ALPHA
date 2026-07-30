#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from copy import deepcopy

try:
    from .activation_policy import conclusion_for, load_activation_policy
except ImportError:
    from activation_policy import conclusion_for, load_activation_policy


SCHEMA_VERSION = "2.0"
PIPELINE_VERSION = "2.0.0-alpha.2"
EVIDENCE_LEVELS = {"E1", "E2", "E3", "NOT_EVALUABLE"}
ANALYSIS_OUTCOMES = {"EVIDENCE_RECOVERED", "NO_EVIDENCE_RECOVERED", "NOT_EVALUABLE"}
EXECUTION_STATUSES = {"queued", "running", "done", "warning", "blocked", "failed", "cancelled"}
CONTROL_PASS = {"CONTROL_BELOW_SAMPLE", "CONTROL_NOT_DETECTED", "CONTROL_NOT_APPLICABLE"}
TERMINAL_EXECUTION_STATUSES = {"done", "warning", "blocked", "failed", "cancelled"}
FAILED_EXECUTION_STATUSES = {"blocked", "failed", "cancelled"}


def _validate_public_state(execution_status: object, analysis_outcome: object,
                           evidence_level: object, *, context: str = "") -> None:
    prefix = f"{context} " if context else ""
    if execution_status not in EXECUTION_STATUSES:
        raise ValueError(f"invalid {prefix}execution_status")
    if execution_status not in TERMINAL_EXECUTION_STATUSES:
        raise ValueError(f"{prefix}evidence document requires a terminal execution_status")
    if analysis_outcome not in ANALYSIS_OUTCOMES:
        raise ValueError(f"invalid {prefix}analysis_outcome")
    if evidence_level not in EVIDENCE_LEVELS:
        raise ValueError(f"invalid {prefix}evidence_level")
    if evidence_level in {"E2", "E3"}:
        raise ValueError("E2/E3 are structurally unreachable in alpha.2")
    if execution_status in FAILED_EXECUTION_STATUSES and analysis_outcome != "NOT_EVALUABLE":
        raise ValueError(
            f"{prefix}failed, blocked, or cancelled execution requires NOT_EVALUABLE"
        )
    if analysis_outcome == "NOT_EVALUABLE" and evidence_level != "NOT_EVALUABLE":
        raise ValueError("NOT_EVALUABLE outcome requires NOT_EVALUABLE evidence level")
    if analysis_outcome != "NOT_EVALUABLE" and evidence_level == "NOT_EVALUABLE":
        raise ValueError("NOT_EVALUABLE evidence level requires NOT_EVALUABLE outcome")


def validate_document(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("evidence document must be an object")
    required = {
        "schema_version", "pipeline_version", "sample_id", "run_id", "execution_status",
        "analysis_outcome", "evidence_level", "shadow_mode", "reported_conclusion",
        "candidates", "caveats", "promotion_gates", "specificity", "coverage", "controls",
        "provenance",
    }
    missing = required - set(value)
    if missing:
        raise ValueError("evidence document missing fields: " + ", ".join(sorted(missing)))
    if value["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported evidence schema: {value['schema_version']}")
    if value["pipeline_version"] != PIPELINE_VERSION:
        raise ValueError(f"unsupported evidence pipeline: {value['pipeline_version']}")
    for name in ("sample_id", "run_id"):
        if not isinstance(value[name], str) or not value[name].strip():
            raise ValueError(f"{name} is required")
    _validate_public_state(
        value["execution_status"], value["analysis_outcome"], value["evidence_level"],
    )
    if not isinstance(value["shadow_mode"], bool):
        raise ValueError("shadow_mode must be boolean")
    if value["shadow_mode"]:
        if value["reported_conclusion"] != "SHADOW_ONLY":
            raise ValueError("shadow evidence requires reported_conclusion=SHADOW_ONLY")
    else:
        policy = load_activation_policy()
        required_active = {"policy_version", "activation_record_id", "evidence_ceiling"}
        missing_active = required_active - set(value)
        if missing_active:
            raise ValueError(
                "active E1 evidence missing fields: " + ", ".join(sorted(missing_active))
            )
        if value["policy_version"] != policy["policy_version"]:
            raise ValueError("active evidence policy_version does not match activation record")
        if value["activation_record_id"] != policy["activation_record_id"]:
            raise ValueError("active evidence activation_record_id does not match activation record")
        if value["evidence_ceiling"] != "E1":
            raise ValueError("active evidence ceiling must remain E1")
        expected_conclusion = conclusion_for(policy, value["analysis_outcome"])
        if value["reported_conclusion"] != expected_conclusion:
            raise ValueError(
                f"active evidence conclusion must be {expected_conclusion}"
            )
    for name in ("candidates", "caveats", "promotion_gates"):
        if not isinstance(value[name], list):
            raise ValueError(f"{name} must be a list")
    if not value["caveats"] or not value["promotion_gates"]:
        raise ValueError("caveats and promotion_gates must be non-empty")
    for name in ("specificity", "coverage", "controls", "provenance"):
        if not isinstance(value[name], dict):
            raise ValueError(f"{name} must be an object")
    for name in ("specificity", "coverage", "controls"):
        if not isinstance(value[name].get("status"), str) or not value[name]["status"]:
            raise ValueError(f"{name}.status is required")
    if "by_candidate" not in value["coverage"] or not isinstance(value["coverage"]["by_candidate"], list):
        raise ValueError("coverage.by_candidate must be a list")
    for candidate in value["candidates"]:
        if not isinstance(candidate, dict):
            raise ValueError("candidate must be an object")
        missing_candidate = {
            "candidate_id", "reference_id", "category", "locus_id", "query_ids",
            "orientation", "candidate_class", "promotion_status", "blocking_reasons",
        } - set(candidate)
        if missing_candidate:
            raise ValueError("candidate missing fields: " + ", ".join(sorted(missing_candidate)))
        for name in ("candidate_id", "reference_id", "category", "locus_id"):
            if not isinstance(candidate[name], str) or not candidate[name].strip():
                raise ValueError(f"candidate.{name} is required")
        if candidate["orientation"] not in {"+", "-", "UNKNOWN"}:
            raise ValueError("candidate.orientation must be +, -, or UNKNOWN")
        if not isinstance(candidate["query_ids"], list):
            raise ValueError("candidate.query_ids must be a list")
        if candidate["candidate_class"] not in {
            "EXPLORATORY_FRAGMENT", "LOCUS_CANDIDATE", "LEGACY_INCOMPATIBLE",
        }:
            raise ValueError("invalid candidate.candidate_class")
        if candidate["promotion_status"] not in {"ELIGIBLE", "BLOCKED"}:
            raise ValueError("invalid candidate.promotion_status")
        if not isinstance(candidate["blocking_reasons"], list):
            raise ValueError("candidate.blocking_reasons must be a list")
        if candidate["promotion_status"] == "ELIGIBLE" and candidate["blocking_reasons"]:
            raise ValueError("eligible candidate cannot have blocking reasons")
        if candidate["promotion_status"] == "BLOCKED" and not candidate["blocking_reasons"]:
            raise ValueError("blocked candidate requires blocking reasons")
        if (
            candidate["candidate_class"] == "EXPLORATORY_FRAGMENT"
            and candidate["promotion_status"] != "BLOCKED"
        ):
            raise ValueError("exploratory fragment cannot be promotion eligible")
    if value["analysis_outcome"] == "NO_EVIDENCE_RECOVERED" and value["candidates"]:
        raise ValueError("NO_EVIDENCE_RECOVERED requires an empty candidate list")
    if value["analysis_outcome"] == "EVIDENCE_RECOVERED" and not value["candidates"]:
        raise ValueError("EVIDENCE_RECOVERED requires at least one candidate")
    return value


def adapt_legacy_document(value: dict, *, adaptation_id: str | None = None) -> dict:
    """Explicit, traceable migration helper; never used by public read paths."""
    if value.get("schema_version") == SCHEMA_VERSION and value.get("pipeline_version") == PIPELINE_VERSION:
        return validate_document(deepcopy(value))
    if not isinstance(adaptation_id, str) or not adaptation_id.strip():
        raise ValueError("legacy adaptation requires an explicit adaptation_id")
    source_sha256 = hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    sample_id = str(value.get("sample_id") or value.get("sample") or "UNKNOWN")
    old_level = str(value.get("evidence_level") or value.get("evidence_class") or "REVIEW")
    has_signal = old_level not in {"", "INCONCLUSIVE", "NO_VIRAL_HITS", "NONE"}
    candidates = []
    if has_signal:
        candidates.append({
            "candidate_id": "legacy-candidate",
            "reference_id": "LEGACY_UNKNOWN",
            "category": "UNLABELED",
            "locus_id": "LEGACY_UNSCOPED",
            "query_ids": [],
            "orientation": "UNKNOWN",
            "legacy_label": old_level,
            "candidate_class": "LEGACY_INCOMPATIBLE",
            "promotion_status": "BLOCKED",
            "blocking_reasons": ["LEGACY_REEXECUTION_REQUIRED"],
            "specificity_status": str(value.get("specificity_status", "NOT_EVALUATED")),
        })
    document = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "sample_id": sample_id,
        "run_id": str(value.get("run_id") or f"legacy-{sample_id}"),
        "execution_status": "done",
        "analysis_outcome": "NOT_EVALUABLE",
        "evidence_level": "NOT_EVALUABLE",
        "shadow_mode": True,
        "reported_conclusion": "SHADOW_ONLY",
        "candidates": candidates,
        "caveats": [
            "Resultado legado adaptado explicitamente para auditoria; nenhum nível E1 é atribuído automaticamente.",
            "Limiares científicos permanecem em calibração.",
        ],
        "promotion_gates": [{
            "gate_id": "legacy_compatibility", "status": "BLOCKED",
            "reason": "Artefatos legados permanecem NOT_EVALUABLE até reexecução canônica.",
        }],
        "specificity": {"status": str(value.get("specificity_status", "NOT_EVALUATED"))},
        "coverage": {"status": str(value.get("coverage_status", "NOT_EVALUATED")), "by_candidate": []},
        "controls": {"status": str(value.get("control_status", "UNCONTROLLED")), "metrics": {}},
        "provenance": {
            **deepcopy(value.get("provenance") or {}),
            "legacy_adaptation": {
                "mode": "EXPLICIT",
                "adaptation_id": adaptation_id.strip(),
                "source_sha256": source_sha256,
                "source_schema_version": value.get("schema_version"),
            },
        },
        "legacy": deepcopy(value),
    }
    return validate_document(document)


def promote_for_public_output(value: object) -> dict:
    """Validate the public evidence representation without adapting legacy input."""
    if not isinstance(value, dict):
        raise ValueError("evidence output must be an object")
    if isinstance(value.get("samples"), list):
        required = {
            "schema_version", "pipeline_version", "run_id", "batch_id",
            "shadow_mode", "reported_conclusion", "samples",
        }
        missing = required - set(value)
        if missing:
            raise ValueError("batch evidence missing fields: " + ", ".join(sorted(missing)))
        if value["schema_version"] != SCHEMA_VERSION or value["pipeline_version"] != PIPELINE_VERSION:
            raise ValueError("batch evidence contract version is incompatible")
        if not isinstance(value["shadow_mode"], bool):
            raise ValueError("batch shadow_mode must be boolean")
        if value["shadow_mode"]:
            if value["reported_conclusion"] != "SHADOW_ONLY":
                raise ValueError("shadow batch conclusion must remain SHADOW_ONLY")
        else:
            policy = load_activation_policy()
            if value.get("policy_version") != policy["policy_version"]:
                raise ValueError("active batch policy_version does not match activation record")
            if value.get("activation_record_id") != policy["activation_record_id"]:
                raise ValueError("active batch activation_record_id does not match activation record")
            if value.get("evidence_ceiling") != "E1":
                raise ValueError("active batch evidence ceiling must remain E1")
            if value["reported_conclusion"] != "E1_ONLY":
                raise ValueError("active batch reported_conclusion must be E1_ONLY")
        if not isinstance(value["run_id"], str) or not value["run_id"].strip():
            raise ValueError("batch run_id is required")
        if not isinstance(value["batch_id"], str) or not value["batch_id"].strip():
            raise ValueError("batch batch_id is required")
        output = deepcopy(value)
        for sample in output["samples"]:
            if not isinstance(sample, dict):
                raise ValueError("batch sample must be an object")
            required_sample = {
                "sample_id", "execution_status", "analysis_outcome", "evidence_level",
                "reported_conclusion", "caveats", "promotion_gates",
            }
            if required_sample - set(sample):
                raise ValueError("batch sample missing public evidence fields")
            expected_sample_conclusion = (
                "SHADOW_ONLY"
                if value["shadow_mode"]
                else conclusion_for(policy, sample["analysis_outcome"])
            )
            if sample["reported_conclusion"] != expected_sample_conclusion:
                raise ValueError("batch sample reported_conclusion conflicts with policy")
            _validate_public_state(
                sample["execution_status"], sample["analysis_outcome"],
                sample["evidence_level"], context="batch sample",
            )
        return output
    return validate_document(deepcopy(value))


def not_evaluable_document(
    sample_id: str,
    run_id: str,
    reason: str,
    provenance: dict | None = None,
    policy: dict | None = None,
) -> dict:
    active_policy = policy or load_activation_policy()
    document = {
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "sample_id": sample_id,
        "run_id": run_id,
        "execution_status": "failed",
        "analysis_outcome": "NOT_EVALUABLE",
        "evidence_level": "NOT_EVALUABLE",
        "shadow_mode": active_policy["shadow_mode"],
        "reported_conclusion": conclusion_for(active_policy, "NOT_EVALUABLE"),
        "candidates": [],
        "caveats": [reason],
        "promotion_gates": [{"gate_id": "scientific_execution", "status": "BLOCKED", "reason": reason}],
        "specificity": {"status": "NOT_EVALUATED"},
        "coverage": {"status": "NOT_EVALUATED", "by_candidate": []},
        "controls": {"status": "NOT_EVALUATED", "metrics": {}},
        "provenance": provenance or {},
    }
    if not active_policy["shadow_mode"]:
        document.update({
            "policy_version": active_policy["policy_version"],
            "activation_record_id": active_policy["activation_record_id"],
            "evidence_ceiling": active_policy["evidence_ceiling"],
        })
    return validate_document(document)
