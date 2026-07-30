#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
MANIFEST=""; CONFIG="${REPO_ROOT}/config/evidence_v2.yaml"; THREADS="${THREADS:-4}"
RUN_ID=""; EVIDENCE_ROOT="${REPO_ROOT}/results/evidence"
EVIDENCE_RESERVATION_TOKEN="${EVIDENCE_RESERVATION_TOKEN:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch-manifest) MANIFEST="$2"; shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    --threads) THREADS="$2"; shift 2 ;;
    --run-id) RUN_ID="$2"; shift 2 ;;
    --evidence-root) EVIDENCE_ROOT="$2"; shift 2 ;;
    *) echo "[FATAL] invalid batch option: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$MANIFEST" ]] || { echo "[FATAL] --batch-manifest is required" >&2; exit 2; }
RUN_ID="${RUN_ID:-$(python3 -c 'import uuid; print(uuid.uuid4())')}"
RUN_ID="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" run-id "$RUN_ID")"

STATE_FILE="${EVIDENCE_ROOT}/state/${RUN_ID}.json"
STAGING="${EVIDENCE_ROOT}/.staging/${RUN_ID}"
FINAL="${EVIDENCE_ROOT}/runs/${RUN_ID}"
mkdir -p "${EVIDENCE_ROOT}/state" "${EVIDENCE_ROOT}/.staging" "${EVIDENCE_ROOT}/runs"
VALIDATED_MANIFEST="$(mktemp "${EVIDENCE_ROOT}/.staging/.manifest.${RUN_ID}.XXXXXX")"
trap 'rm -f "$VALIDATED_MANIFEST"' EXIT
python3 "$SCRIPT_DIR/evidence/validate_manifest.py" --manifest "$MANIFEST" --out "$VALIDATED_MANIFEST"
mapfile -t SAMPLES < <(awk -F '\t' 'NR > 1 {print $2}' "$VALIDATED_MANIFEST")
[[ ${#SAMPLES[@]} -gt 0 ]] || { echo "[FATAL] batch has no samples" >&2; exit 2; }
BATCH_ID="$(awk -F '\t' 'NR == 2 {print $1}' "$VALIDATED_MANIFEST")"
BATCH_ID="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" batch-id "$BATCH_ID")"
INIT=(--state "$STATE_FILE" init --run-id "$RUN_ID" --action evidence_batch --batch-id "$BATCH_ID")
for sample in "${SAMPLES[@]}"; do INIT+=(--sample "$sample"); done
if [[ -e "$FINAL" || -e "$STAGING" ]]; then
  echo "[FATAL] run id already has staging or final artifacts: $RUN_ID" >&2
  exit 2
elif [[ -e "$STATE_FILE" ]]; then
  [[ -n "$EVIDENCE_RESERVATION_TOKEN" ]] || { echo "[FATAL] run id already exists: $RUN_ID" >&2; exit 2; }
  ADOPT=(--state "$STATE_FILE" adopt --run-id "$RUN_ID" --action evidence_batch \
    --batch-id "$BATCH_ID" --staging "$STAGING" --final "$FINAL")
  for sample in "${SAMPLES[@]}"; do ADOPT+=(--sample "$sample"); done
  python3 "$SCRIPT_DIR/evidence/run_state.py" "${ADOPT[@]}"
else
  [[ -z "$EVIDENCE_RESERVATION_TOKEN" ]] || { echo "[FATAL] reserved run state is missing: $RUN_ID" >&2; exit 2; }
  python3 "$SCRIPT_DIR/evidence/run_state.py" "${INIT[@]}"
fi
mkdir "$STAGING" || { echo "[FATAL] unable to reserve run staging atomically: $RUN_ID" >&2; exit 2; }
mkdir -p "$STAGING/samples" "$STAGING/work"
NORMALIZED="$STAGING/work/manifest.tsv"
mv "$VALIDATED_MANIFEST" "$NORMALIZED"
trap - EXIT

CURRENT_STAGE="input_validation"
stage() {
  CURRENT_STAGE="$1"
  local args=(--state "$STATE_FILE" stage --id "$1" --status "$2")
  [[ -z "${3:-}" ]] || args+=(--message "$3")
  python3 "$SCRIPT_DIR/evidence/run_state.py" "${args[@]}"
}
fail_batch() {
  local rc=$?
  trap - ERR INT TERM
  python3 "$SCRIPT_DIR/evidence/run_state.py" --state "$STATE_FILE" write-failure-evidence \
    --root "$STAGING" --reason "Batch Evidence V2 failed: $CURRENT_STAGE" 2>/dev/null || true
  python3 "$SCRIPT_DIR/evidence/run_state.py" --state "$STATE_FILE" stage --id "$CURRENT_STAGE" --status failed --message "Lote interrompido; artefatos permaneceram em staging." --failure-type TOOL_FAILURE 2>/dev/null || true
  python3 "$SCRIPT_DIR/evidence/run_state.py" --state "$STATE_FILE" status --value failed --failure-type TOOL_FAILURE --failed-stage "$CURRENT_STAGE" --failure-message "Lote interrompido; artefatos permaneceram em staging." 2>/dev/null || true
  exit "$rc"
}
cancel_batch() {
  trap - ERR INT TERM
  python3 "$SCRIPT_DIR/evidence/run_state.py" --state "$STATE_FILE" stage --id "$CURRENT_STAGE" --status cancelled --message "Lote cancelado; resultados parciais não foram promovidos." 2>/dev/null || true
  python3 "$SCRIPT_DIR/evidence/run_state.py" --state "$STATE_FILE" status --value cancelled --failure-type CANCELLED --failed-stage "$CURRENT_STAGE" --failure-message "Lote cancelado; resultados parciais não foram promovidos." 2>/dev/null || true
  exit 130
}
trap fail_batch ERR
trap cancel_batch INT TERM

stage input_validation "done" "Manifesto e entradas validados."
RUN_MAP="$STAGING/work/run_map.tsv"
printf 'sample_id\trun_id\n' > "$RUN_MAP"
stage quality_control running "Processando amostras do lote em runs isolados."
while IFS=$'\t' read -r batch_id sample_id role library_mode umi_mode r1 r2 expected_target; do
  [[ "$batch_id" == "batch_id" ]] && continue
  child_id="${RUN_ID}-${sample_id}"
  printf '%s\t%s\n' "$sample_id" "$child_id" >> "$RUN_MAP"
  SAMPLE_R1="$r1" SAMPLE_R2="$r2" EVIDENCE_LIBRARY_MODE="$library_mode" EVIDENCE_UMI_MODE="$umi_mode" \
    EVIDENCE_ROLE="$role" EVIDENCE_EXPECTED_TARGET="$expected_target" EVIDENCE_RUN_ID="$child_id" EVIDENCE_BATCH_ID="$batch_id" \
    EVIDENCE_RESERVATION_TOKEN="" \
    "$SCRIPT_DIR/20_run_pipeline.sh" --sample "$sample_id" --threads "$THREADS" --evidence-v2 \
      --evidence-config "$CONFIG" --evidence-root "$EVIDENCE_ROOT"
  cp -a "${EVIDENCE_ROOT}/runs/${child_id}" "$STAGING/samples/${sample_id}"
done < "$NORMALIZED"

for id in quality_control assembly initial_blast hsp_aggregation locus_building competitive_search read_remapping coverage; do
  stage "$id" "done" "Concluído nos runs-filhos transacionais."
done
METRICS="$STAGING/work/metrics.tsv"
python3 "$SCRIPT_DIR/evidence/collect_batch_metrics.py" --manifest "$NORMALIZED" --repo-root "$REPO_ROOT" \
  --evidence-root "$EVIDENCE_ROOT" --run-map "$RUN_MAP" --out "$METRICS"
RATIO="$(python3 "$SCRIPT_DIR/evidence/config_value.py" --config "$CONFIG" --key controls.provisional_sample_to_negative_ratio)"
stage controls running
python3 "$SCRIPT_DIR/evidence/evaluate_controls.py" --manifest "$NORMALIZED" --sample-metrics "$METRICS" \
  --provisional-ratio "$RATIO" --out "$STAGING/control_status.tsv"
python3 "$SCRIPT_DIR/evidence/apply_control_status.py" --statuses "$STAGING/control_status.tsv" \
  --evidence-root "$STAGING" --config "$CONFIG"
stage controls "done" "Estados de controle aplicados somente à cópia transacional do lote."

stage evidence_classification running
python3 "$SCRIPT_DIR/evidence/write_provenance.py" --config "$CONFIG" --out "$STAGING/provenance.json" \
  --artifact "e1_activation_policy=$REPO_ROOT/config/evidence_activation.json" \
  --value "run_id=$RUN_ID" --value "batch_id=$BATCH_ID" --value "shadow_mode=$(python3 "$SCRIPT_DIR/evidence/activation_policy.py" --field shadow_mode)" \
  --value "policy_version=$(python3 "$SCRIPT_DIR/evidence/activation_policy.py" --field policy_version)" \
  --value "activation_record_id=$(python3 "$SCRIPT_DIR/evidence/activation_policy.py" --field activation_record_id)" \
  --value "child_run_count=${#SAMPLES[@]}"
python3 "$SCRIPT_DIR/evidence/summarize_batch.py" --batch-id "$BATCH_ID" --run-id "$RUN_ID" --root "$STAGING" \
  --run-map "$RUN_MAP" --statuses "$STAGING/control_status.tsv" --out "$STAGING/batch_evidence.json" --report "$STAGING/batch_report.md"
stage evidence_classification "done"
stage report_export "done" "Relatório experimental do lote exportado."
python3 "$SCRIPT_DIR/evidence/finalize_batch.py" --state "$STATE_FILE" --staging "$STAGING" --final "$FINAL" --run-map "$RUN_MAP"
trap - ERR INT TERM
echo "[OK] Batch Evidence V2 promoted: $FINAL"
echo "[RUN_ID] $RUN_ID"
