#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
EVIDENCE_DIR="${SCRIPT_DIR}/evidence"

SAMPLE=""; QUERIES=""; CONFIG="${REPO_ROOT}/config/evidence_v2.yaml"
SUBJECT_LABELS=""; COMPOSITE_DB=""; PANEL_FASTA=""; PANEL_INDEX=""; R1=""; R2=""
LIBRARY_MODE="unknown"; UMI_MODE="none"; ROLE="sample"; EXPECTED_TARGET=""; THREADS="${THREADS:-4}"; BATCH_ID=""
EVIDENCE_ROOT="${REPO_ROOT}/results/evidence"; RUN_ID=""; LEGACY_OUTDIR=""
EVIDENCE_RESERVATION_TOKEN="${EVIDENCE_RESERVATION_TOKEN:-}"
BLAST_SPECS=()
BLAST_PARAM_SOURCE="external_input"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sample) SAMPLE="$2"; shift 2 ;;
    --queries) QUERIES="$2"; shift 2 ;;
    --blast) BLAST_SPECS+=("$2"); shift 2 ;;
    --config) CONFIG="$2"; shift 2 ;;
    --evidence-root) EVIDENCE_ROOT="$2"; shift 2 ;;
    --out-dir) LEGACY_OUTDIR="$2"; shift 2 ;;
    --run-id) RUN_ID="$2"; shift 2 ;;
    --batch-id) BATCH_ID="$2"; shift 2 ;;
    --subject-labels) SUBJECT_LABELS="$2"; shift 2 ;;
    --composite-db) COMPOSITE_DB="$2"; shift 2 ;;
    --panel-fasta) PANEL_FASTA="$2"; shift 2 ;;
    --panel-index) PANEL_INDEX="$2"; shift 2 ;;
    --r1) R1="$2"; shift 2 ;;
    --r2) R2="$2"; shift 2 ;;
    --library-mode) LIBRARY_MODE="$2"; shift 2 ;;
    --umi-mode) UMI_MODE="$2"; shift 2 ;;
    --role) ROLE="$2"; shift 2 ;;
    --expected-target) EXPECTED_TARGET="$2"; shift 2 ;;
    --threads) THREADS="$2"; shift 2 ;;
    *) echo "[FATAL] invalid evidence-v2 option: $1" >&2; exit 2 ;;
  esac
done

if [[ -n "$LEGACY_OUTDIR" ]]; then
  EVIDENCE_ROOT="$LEGACY_OUTDIR"
fi
[[ -n "$SAMPLE" && -n "$QUERIES" ]] || { echo "[FATAL] --sample and --queries are required" >&2; exit 2; }
[[ "$ROLE" =~ ^(sample|negative_extraction|negative_library|negative_sequencing|positive)$ ]] || { echo "[FATAL] invalid role" >&2; exit 2; }
[[ "$ROLE" != "positive" || -n "$EXPECTED_TARGET" ]] || { echo "[FATAL] positive control requires expected target" >&2; exit 2; }
SAMPLE="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" sample "$SAMPLE")"
RUN_ID="${RUN_ID:-$(python3 -c 'import uuid; print(uuid.uuid4())')}"
[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$ ]] || { echo "[FATAL] invalid run id" >&2; exit 2; }

STATE_DIR="${EVIDENCE_ROOT}/state"; STAGING_ROOT="${EVIDENCE_ROOT}/.staging"; RUNS_ROOT="${EVIDENCE_ROOT}/runs"
STATE_FILE="${STATE_DIR}/${RUN_ID}.json"; OUTDIR="${STAGING_ROOT}/${RUN_ID}"; FINAL_DIR="${RUNS_ROOT}/${RUN_ID}"
mkdir -p "$STATE_DIR" "$STAGING_ROOT" "$RUNS_ROOT"
INIT_ARGS=(--state "$STATE_FILE" init --run-id "$RUN_ID" --action evidence_single --sample "$SAMPLE")
[[ -z "$BATCH_ID" ]] || INIT_ARGS+=(--batch-id "$BATCH_ID")
if [[ -e "$FINAL_DIR" || -e "$OUTDIR" ]]; then
  echo "[FATAL] run id already has staging or final artifacts: $RUN_ID" >&2
  exit 2
elif [[ -e "$STATE_FILE" ]]; then
  [[ -n "$EVIDENCE_RESERVATION_TOKEN" ]] || { echo "[FATAL] run id already exists: $RUN_ID" >&2; exit 2; }
  ADOPT_ARGS=(--state "$STATE_FILE" adopt --run-id "$RUN_ID" --action evidence_single \
    --sample "$SAMPLE" --staging "$OUTDIR" --final "$FINAL_DIR")
  [[ -z "$BATCH_ID" ]] || ADOPT_ARGS+=(--batch-id "$BATCH_ID")
  python3 "$EVIDENCE_DIR/run_state.py" "${ADOPT_ARGS[@]}"
else
  [[ -z "$EVIDENCE_RESERVATION_TOKEN" ]] || { echo "[FATAL] reserved run state is missing: $RUN_ID" >&2; exit 2; }
  python3 "$EVIDENCE_DIR/run_state.py" "${INIT_ARGS[@]}"
fi
mkdir "$OUTDIR" || {
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" status --value failed \
    --failure-type TOOL_FAILURE --failure-message "Unable to create isolated staging directory" 2>/dev/null || true
  echo "[FATAL] unable to reserve run staging atomically: $RUN_ID" >&2
  exit 2
}
python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" status --value running --evidence-v2-status running

CURRENT_STAGE="input_validation"
EVIDENCE_FAILURE_TYPE="UNKNOWN"
state_stage() {
  CURRENT_STAGE="$1"
  local args=(--state "$STATE_FILE" stage --id "$1" --status "$2")
  [[ -z "${3:-}" ]] || args+=(--message "$3")
  python3 "$EVIDENCE_DIR/run_state.py" "${args[@]}"
}
fail_run() {
  local rc=$?
  trap - ERR INT TERM
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" stage --id "$CURRENT_STAGE" --status failed --message "Etapa interrompida; consulte o log." 2>/dev/null || true
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" status --value failed 2>/dev/null || true
  exit "$rc"
}
cancel_run() {
  trap - ERR INT TERM
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" stage --id "$CURRENT_STAGE" --status cancelled --message "Execução cancelada." 2>/dev/null || true
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" status --value cancelled 2>/dev/null || true
  exit 130
}
fail_run_v2() {
  local rc=$?
  trap - ERR INT TERM
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" write-failure-evidence \
    --root "$OUTDIR" --reason "Evidence V2 stage failed: $CURRENT_STAGE" 2>/dev/null || true
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" stage --id "$CURRENT_STAGE" \
    --status failed --message "Evidence V2 stage failed" --failure-type "${EVIDENCE_FAILURE_TYPE:-TOOL_FAILURE}" \
    --failed-command "${BASH_COMMAND:-}" 2>/dev/null || true
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" status --value failed \
    --failure-type "${EVIDENCE_FAILURE_TYPE:-TOOL_FAILURE}" --failed-stage "$CURRENT_STAGE" \
    --failure-message "Evidence V2 stage failed" --failed-command "${BASH_COMMAND:-}" 2>/dev/null || true
  exit "$rc"
}
cancel_run_v2() {
  trap - ERR INT TERM
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" stage --id "$CURRENT_STAGE" \
    --status cancelled --message "Evidence V2 execution cancelled" --failure-type CANCELLED 2>/dev/null || true
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" status --value cancelled \
    --failure-type CANCELLED --failed-stage "$CURRENT_STAGE" \
    --failure-message "Evidence V2 execution cancelled" 2>/dev/null || true
  exit 130
}
trap fail_run_v2 ERR
trap cancel_run_v2 INT TERM

state_stage input_validation running
if [[ ! -s "$QUERIES" || ! -s "$CONFIG" ]]; then
  EVIDENCE_FAILURE_TYPE="INPUT_INVALID"
  echo "[FATAL] query FASTA or evidence config is missing" >&2
  false
fi
TMPDIR_RUN="$(mktemp -d "${OUTDIR}/work.XXXXXX")"
PREFLIGHT_ARGS=(--config "$CONFIG" --assembler none \
  --umi-mode "$UMI_MODE" --json-out "$OUTDIR/runtime_preflight.json" \
  --lockfile "$REPO_ROOT/conda-linux-64.lock" \
  --lock-manifest "$REPO_ROOT/config/environment_lock.json")
if [[ -n "$COMPOSITE_DB" ]]; then
  BLAST_PARAM_SOURCE="internal_composite_pipeline"
  PREFLIGHT_ARGS+=(--require-command blastn)
fi
if [[ -n "$PANEL_INDEX" || -n "$PANEL_FASTA" || -n "$R1" || -n "$R2" ]]; then
  PREFLIGHT_ARGS+=(--require-command bowtie2 --require-command samtools)
fi
if ! python3 "$EVIDENCE_DIR/runtime_preflight.py" "${PREFLIGHT_ARGS[@]}"; then
  if python3 -c 'import json,sys; data=json.load(open(sys.argv[1], encoding="utf-8")); print("DEPENDENCY_MISSING" if any("PyYAML" in e or "depend" in e for e in data.get("errors", [])) else "CONFIG_INVALID")' "$OUTDIR/runtime_preflight.json" > "$OUTDIR/.failure_type.tmp"; then
    EVIDENCE_FAILURE_TYPE="$(tr -d '\r\n' < "$OUTDIR/.failure_type.tmp")"
  fi
  rm -f "$OUTDIR/.failure_type.tmp"
  echo "[FATAL] Evidence V2 runtime preflight failed; V1.1 remains preserved." >&2
  false
fi
python3 "$EVIDENCE_DIR/config_value.py" --config "$CONFIG" --key schema_version >/dev/null
python3 "${SCRIPT_DIR}/lib/input_validation.py" fasta "$QUERIES" >/dev/null
state_stage input_validation "done" "Entradas e configuração validadas."
state_stage quality_control "done" "Executado pelo fluxo 1.1 ou fornecido como entrada validada."
state_stage assembly "done" "Contigs fornecidos pelo fluxo 1.1; conclusão oficial preservada."

cfg() { python3 "$EVIDENCE_DIR/config_value.py" --config "$CONFIG" --key "$1"; }
GAP_BP="$(cfg locus.gap_bp)"; MIN_DELTA="$(cfg specificity.minimum_delta_bitscore)"
MAX_QCOV_DIFF="$(cfg specificity.maximum_qcov_difference_pp)"; MIN_MAPQ="$(cfg support.minimum_mapq)"
MIN_BASEQ="$(cfg support.minimum_base_quality)"; WINDOW_BP="$(cfg sample_evidence.concentration_window_bp)"
DUST_CONFIG="$(cfg blast.explicit_dust)"; SOFT_MASKING="$(cfg blast.soft_masking)"
DUST="no"; [[ "$DUST_CONFIG" == "true" ]] && DUST="yes"
state_stage initial_blast running
if [[ -n "$COMPOSITE_DB" ]]; then
  [[ -n "$SUBJECT_LABELS" && -s "$SUBJECT_LABELS" ]] || { echo "[FATAL] composite DB requires --subject-labels" >&2; false; }
  command -v blastn >/dev/null 2>&1 || { echo "[FATAL] blastn not found" >&2; false; }
  SHORT_RAW="$TMPDIR_RUN/blastn-short.tsv"; BLASTN_RAW="$TMPDIR_RUN/blastn.tsv"
  python3 "$EVIDENCE_DIR/blast_router.py" --query "$QUERIES" --db "$COMPOSITE_DB" --config "$CONFIG" \
    --threads "$THREADS" --out-short "$SHORT_RAW" --out-conventional "$BLASTN_RAW" \
    --provenance "$OUTDIR/blast_routing.json"
  BLAST_SPECS=("blastn-short=$SHORT_RAW" "blastn=$BLASTN_RAW")
fi
[[ ${#BLAST_SPECS[@]} -gt 0 ]] || { echo "[FATAL] provide --blast TASK=PATH or --composite-db" >&2; false; }
state_stage initial_blast "done" "Resultados BLAST disponíveis para agregação."

AGG_ARGS=(); for spec in "${BLAST_SPECS[@]}"; do AGG_ARGS+=(--blast "$spec"); done
[[ -z "$SUBJECT_LABELS" ]] || AGG_ARGS+=(--subject-labels "$SUBJECT_LABELS")
state_stage hsp_aggregation running
python3 "$EVIDENCE_DIR/aggregate_hsps.py" "${AGG_ARGS[@]}" --query-fasta "$QUERIES" --out "$OUTDIR/fragment_evidence.tsv"
state_stage hsp_aggregation "done"
state_stage locus_building running
python3 "$EVIDENCE_DIR/build_loci.py" --fragments "$OUTDIR/fragment_evidence.tsv" --gap-bp "$GAP_BP" --out "$OUTDIR/locus_evidence.tsv"
state_stage locus_building "done"
state_stage competitive_search running
python3 "$EVIDENCE_DIR/competitive_hits.py" --fragments "$OUTDIR/fragment_evidence.tsv" \
  --minimum-delta-bitscore "$MIN_DELTA" --maximum-qcov-difference-pp "$MAX_QCOV_DIFF" --out "$OUTDIR/competitive_hits.tsv"
state_stage competitive_search "done"

READ_SUPPORT="$OUTDIR/read_support.tsv"; COVERAGE="$OUTDIR/coverage.tsv"
state_stage read_remapping running
if [[ -n "$PANEL_INDEX" && -n "$PANEL_FASTA" && -n "$R1" && -n "$R2" ]]; then
  "$EVIDENCE_DIR/map_read_support.sh" --sample "$SAMPLE" --index "$PANEL_INDEX" --reference "$PANEL_FASTA" \
    --r1 "$R1" --r2 "$R2" --out-dir "$OUTDIR" --library-mode "$LIBRARY_MODE" --umi-mode "$UMI_MODE" \
    --loci "$OUTDIR/locus_evidence.tsv" --umi-seed 1 --minimum-mapq "$MIN_MAPQ" \
    --minimum-base-quality "$MIN_BASEQ" --window-bp "$WINDOW_BP" --threads "$THREADS"
  state_stage read_remapping "done"
  state_stage coverage "done" "Cobertura calculada sobre o painel competitivo."
else
  printf 'sample_id\treference_id\tcategory\tlocus_id\torientation\tquery_ids\tlibrary_mode\tumi_mode\tsupport_status\tunique_templates\tdistinct_starts\tproper_pair_templates\tdiscordant_templates\tminimum_mapq\n' > "$READ_SUPPORT.tmp"
  mv -f "$READ_SUPPORT.tmp" "$READ_SUPPORT"
  printf 'reference_id\tcategory\tlocus_id\torientation\tquery_ids\treference_length\tlocus_length\tcovered_bases_1x\tcovered_bases_3x\tbreadth_1x\tbreadth_3x\tmean_depth_locus\tmedian_depth_covered\tmin_depth_covered\tmax_window_depth_fraction\tconcentration_window_bp\tminimum_mapq\tminimum_base_quality\n' > "$COVERAGE.tmp"
  mv -f "$COVERAGE.tmp" "$COVERAGE"
  state_stage read_remapping warning "Painel de remapeamento ou reads não fornecidos; suporte indisponível."
  state_stage coverage warning "Cobertura indisponível; a dimensão correspondente permanece limitada."
fi

state_stage controls warning "Execução individual sem avaliação de controles de lote."
PROVENANCE_ARTIFACTS=(--artifact "queries=$QUERIES")
[[ -z "$SUBJECT_LABELS" ]] || PROVENANCE_ARTIFACTS+=(--artifact "subject_labels=$SUBJECT_LABELS")
[[ -z "$PANEL_FASTA" ]] || PROVENANCE_ARTIFACTS+=(--artifact "competitive_panel=$PANEL_FASTA")
for spec in "${BLAST_SPECS[@]}"; do
  task="${spec%%=*}"; path="${spec#*=}"
  PROVENANCE_ARTIFACTS+=(--artifact "blast_${task}_$(basename "$path")=$path")
done
python3 "$EVIDENCE_DIR/write_provenance.py" --config "$CONFIG" --out "$OUTDIR/provenance.json" \
  "${PROVENANCE_ARTIFACTS[@]}" --artifact "environment_lock=$REPO_ROOT/conda-linux-64.lock" \
  --value "run_id=$RUN_ID" --value "sample_id=$SAMPLE" --value "shadow_mode=true" --value "dust=$DUST" \
  --value "role=$ROLE" --value "expected_target=$EXPECTED_TARGET" \
  --value "soft_masking=$SOFT_MASKING" --value "minimum_mapq=$MIN_MAPQ" \
  --value "minimum_base_quality=$MIN_BASEQ" --value "locus_gap_bp=$GAP_BP" \
  --value "bowtie2_mode=--very-sensitive-local" --value "samtools_view_filter=-F 2304 -q $MIN_MAPQ" \
  --value "samtools_depth_filter=-aa -q $MIN_BASEQ -Q $MIN_MAPQ" \
  --value "umi_random_seed=1" --value "dedup_without_umi=disabled" \
  --value "require_proper_pair_shotgun=$(cfg support.require_proper_pair_shotgun)" \
  --value "blast_parameter_source=$BLAST_PARAM_SOURCE" \
  --value "blast_tasks=$(IFS=,; echo "${BLAST_SPECS[*]}")" \
  --value "blastn-short_word_size=7" --value "blastn-short_reward=1" --value "blastn-short_penalty=-3" \
  --value "blastn_word_size=11" --value "blastn_reward=2" --value "blastn_penalty=-3" \
  --value "blast_gapopen=5" --value "blast_gapextend=2" --value "blast_evalue=1000" \
  --value "blast_max_target_seqs=50"
python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" provenance --json "$OUTDIR/provenance.json"

state_stage evidence_classification running
python3 "$EVIDENCE_DIR/classify_sample.py" --sample "$SAMPLE" --loci "$OUTDIR/locus_evidence.tsv" \
  --competitive "$OUTDIR/competitive_hits.tsv" --read-support "$READ_SUPPORT" --coverage "$COVERAGE" \
  --control-status UNCONTROLLED --library-mode "$LIBRARY_MODE" --config "$CONFIG" \
  --provenance "$OUTDIR/provenance.json" --run-id "$RUN_ID" --out "$OUTDIR/sample_evidence.json"
state_stage evidence_classification "done"
state_stage report_export running
python3 "$EVIDENCE_DIR/export_evidence.py" --json "$OUTDIR/sample_evidence.json" --out "$OUTDIR/evidence_report.md"
rm -rf "$TMPDIR_RUN"

for artifact in fragment_evidence locus_evidence competitive_hits read_support coverage sample_evidence provenance evidence_report runtime_preflight blast_routing; do
  case "$artifact" in
    sample_evidence|provenance|runtime_preflight|blast_routing) extension=json ;;
    evidence_report) extension=md ;;
    *) extension=tsv ;;
  esac
  [[ -f "$OUTDIR/${artifact}.${extension}" ]] || continue
  python3 "$EVIDENCE_DIR/run_state.py" --state "$STATE_FILE" artifact --name "$artifact" --path "runs/${RUN_ID}/${artifact}.${extension}"
done
python3 "$EVIDENCE_DIR/validate_run_artifacts.py" --dir "$OUTDIR"
state_stage report_export "done" "Artefatos validados antes da promoção transacional."
FINAL_PATH="$(python3 "$EVIDENCE_DIR/finalize_run.py" --state "$STATE_FILE" --staging "$OUTDIR" --final "$FINAL_DIR")"
trap - ERR INT TERM
echo "[OK] Gene-In 2.0 shadow evidence: $FINAL_PATH"
echo "[RUN_ID] $RUN_ID"
