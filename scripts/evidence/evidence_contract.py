#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from copy import deepcopy


SCHEMA_VERSION = "2.0"
PIPELINE_VERSION = "2.0.0-alpha.2"
EVIDENCE_LEVELS = {"E1", "E2", "E3", "NOT_EVALUABLE"}
ANALYSIS_OUTCOMES = {"EVIDENCE_RECOVERED", "NO_EVIDENCE_RECOVERED", "NOT_EVALUABLE"}
EXECUTION_STATUSES = {"queued", "running", "done", "warning", "blocked", "failed", "cancelled"}
CONTROL_PASS = {"CONTROL_BELOW_SAMPLE", "CONTROL_NOT_DETECTED", "CONTROL_NOT_APPLICABLE"}


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
    if value["execution_status"] not in EXECUTION_STATUSES:
        raise ValueError("invalid execution_status")
    if value["analysis_outcome"] not in ANALYSIS_OUTCOMES:
        raise ValueError("invalid analysis_outcome")
    if value["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError("invalid evidence_level")
    if value["evidence_level"] in {"E2", "E3"}:
        raise ValueError("E2/E3 are structurally unreachable in alpha.2")
    if value["shadow_mode"] is not True:
        raise ValueError("shadow_mode must remain true until benchmark approval")
    if value["reported_conclusion"] != "SHADOW_ONLY":
        raise ValueError("reported_conclusion must remain SHADOW_ONLY")
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
        missing_candidate = {"candidate_id", "reference_id", "category", "locus_id", "query_ids", "orientation"} - set(candidate)
        if missing_candidate:
            raise ValueError("candidate missing fields: " + ", ".join(sorted(missing_candidate)))
        for name in ("candidate_id", "reference_id", "category", "locus_id"):
            if not isinstance(candidate[name], str) or not candidate[name].strip():
                raise ValueError(f"candidate.{name} is required")
        if not isinstance(candidate["orientation"], str):
            raise ValueError("candidate.orientation must be a string")
        if not isinstance(candidate["query_ids"], list):
            raise ValueError("candidate.query_ids must be a list")
    if value["analysis_outcome"] == "NO_EVIDENCE_RECOVERED" and value["candidates"]:
        raise ValueError("NO_EVIDENCE_RECOVERED requires an empty candidate list")
    if value["analysis_outcome"] == "EVIDENCE_RECOVERED" and not value["candidates"]:
        raise ValueError("EVIDENCE_RECOVERED requires at least one candidate")
    if value["analysis_outcome"] == "NOT_EVALUABLE" and value["evidence_level"] != "NOT_EVALUABLE":
        raise ValueError("NOT_EVALUABLE outcome requires NOT_EVALUABLE evidence level")
    if value["analysis_outcome"] != "NOT_EVALUABLE" and value["evidence_level"] == "NOT_EVALUABLE":
        raise ValueError("NOT_EVALUABLE evidence level requires NOT_EVALUABLE outcome")
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
        required = {"schema_version", "pipeline_version", "run_id", "batch_id", "shadow_mode", "samples"}
        missing = required - set(value)
        if missing:
            raise ValueError("batch evidence missing fields: " + ", ".join(sorted(missing)))
        if (
            value["schema_version"] != SCHEMA_VERSION
            or value["pipeline_version"] != PIPELINE_VERSION
            or value["shadow_mode"] is not True
        ):
            raise ValueError("batch evidence is not an alpha.2 shadow artifact")
        if not isinstance(value["run_id"], str) or not value["run_id"].strip():
            raise ValueError("batch run_id is required")
        if not isinstance(value["batch_id"], str) or not value["batch_id"].strip():
            raise ValueError("batch batch_id is required")
        output = deepcopy(value)
        for sample in output["samples"]:
            if not isinstance(sample, dict):
                raise ValueError("batch sample must be an object")
            required_sample = {"sample_id", "execution_status", "analysis_outcome", "evidence_level", "caveats", "promotion_gates"}
            if required_sample - set(sample):
                raise ValueError("batch sample missing public evidence fields")
            if sample["evidence_level"] not in EVIDENCE_LEVELS or sample["analysis_outcome"] not in ANALYSIS_OUTCOMES:
                raise ValueError("batch sample has invalid public evidence state")
            if sample["evidence_level"] in {"E2", "E3"}:
                raise ValueError("E2/E3 are structurally unreachable in alpha.2")
            if (sample["analysis_outcome"] == "NOT_EVALUABLE") != (sample["evidence_level"] == "NOT_EVALUABLE"):
                raise ValueError("batch sample has inconsistent NOT_EVALUABLE state")
        return output
    return validate_document(deepcopy(value))


def not_evaluable_document(sample_id: str, run_id: str, reason: str, provenance: dict | None = None) -> dict:
    return validate_document({
        "schema_version": SCHEMA_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "sample_id": sample_id,
        "run_id": run_id,
        "execution_status": "failed",
        "analysis_outcome": "NOT_EVALUABLE",
        "evidence_level": "NOT_EVALUABLE",
        "shadow_mode": True,
        "reported_conclusion": "SHADOW_ONLY",
        "candidates": [],
        "caveats": [reason],
        "promotion_gates": [{"gate_id": "scientific_execution", "status": "BLOCKED", "reason": reason}],
        "specificity": {"status": "NOT_EVALUATED"},
        "coverage": {"status": "NOT_EVALUATED", "by_candidate": []},
        "controls": {"status": "NOT_EVALUATED", "metrics": {}},
        "provenance": provenance or {},
    })
