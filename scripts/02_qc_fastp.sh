#!/usr/bin/env bash
# =============================================================================
# 02_qc_fastp.sh — Controle de qualidade com fastp
# =============================================================================
# Objetivo: Trimagem de adaptadores, filtragem por qualidade e descarte de
# leituras curtas, conforme diretrizes de validação (seção 4.5).
#
# Uso:
#   bash scripts/02_qc_fastp.sh <SAMPLE> [THREADS]
#   R1=/caminho/r1.fastq.gz R2=/caminho/r2.fastq.gz bash scripts/02_qc_fastp.sh SAMPLE
#
# Variáveis de ambiente aceitas:
#   R1, R2          — caminhos dos reads (sobrescrevem busca automática em RAW_DIR)
#   SAMPLE_R1/R2    — idem (alias do pipeline)
#   THREADS         — número de threads (padrão: 4)
#   QC_MIN_LEN      — tamanho mínimo de leitura após trim (padrão: 50)
#   QC_MIN_QUAL     — qualidade mínima de base (padrão: 20)
#   QC_OUT_DIR      — diretório de saída (padrão: data/cleaned)
#
# Saída:
#   data/cleaned/{SAMPLE}_R1.clean.fastq.gz
#   data/cleaned/{SAMPLE}_R2.clean.fastq.gz
#   results/qc/{SAMPLE}_fastp.html
#   results/qc/{SAMPLE}_fastp.json
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="${REPO_ROOT}/config/picornavirus.env"
LEGACY_CONFIG="${REPO_ROOT}/config.env"

if [[ "${PIPELINE_CONFIG_LOADED:-0}" != "1" ]]; then
  if [[ -f "${CONFIG_FILE}" ]]; then
    source "${CONFIG_FILE}"
  elif [[ -f "${LEGACY_CONFIG}" ]]; then
    source "${LEGACY_CONFIG}"
  fi
fi

source "${SCRIPT_DIR}/lib/common.sh"

SAMPLE="${1:?SAMPLE obrigatório}"
THREADS="${2:-${THREADS:-4}}"
SAMPLE="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" sample "$SAMPLE")"

RAW_DIR="$(resolve_path "${RAW_DIR:-data/raw}")"
QC_OUT_DIR="$(resolve_path "${QC_OUT_DIR:-data/cleaned}")"
QC_REPORT_DIR="$(resolve_path "results/qc")"

QC_MIN_LEN="${QC_MIN_LEN:-50}"
QC_MIN_QUAL="${QC_MIN_QUAL:-20}"

# ── Detecção de reads ────────────────────────────────────────────────────────
RAW1="${SAMPLE_R1:-${R1:-${RAW_DIR}/${SAMPLE}_R1.fastq.gz}}"
RAW2="${SAMPLE_R2:-${R2:-${RAW_DIR}/${SAMPLE}_R2.fastq.gz}}"

check_file "$RAW1"
check_file "$RAW2"

# ── Verificar se fastp está disponível ──────────────────────────────────────
if ! command -v fastp >/dev/null 2>&1; then
  log_error $'fastp não encontrado no PATH.\nInstale com: sudo apt install -y fastp\nOu: conda install -c bioconda fastp'
fi

mkdir -p "$QC_OUT_DIR" "$QC_REPORT_DIR"

OUT_R1="${QC_OUT_DIR}/${SAMPLE}_R1.clean.fastq.gz"
OUT_R2="${QC_OUT_DIR}/${SAMPLE}_R2.clean.fastq.gz"
HTML_REPORT="${QC_REPORT_DIR}/${SAMPLE}_fastp.html"
JSON_REPORT="${QC_REPORT_DIR}/${SAMPLE}_fastp.json"

log_info "[fastp] sample=${SAMPLE}  threads=${THREADS}"
log_info "[fastp] entrada: ${RAW1}"
log_info "[fastp]          ${RAW2}"
log_info "[fastp] min_len=${QC_MIN_LEN}  min_qual=${QC_MIN_QUAL}"

fastp \
  --in1  "$RAW1" \
  --in2  "$RAW2" \
  --out1 "$OUT_R1" \
  --out2 "$OUT_R2" \
  --html "$HTML_REPORT" \
  --json "$JSON_REPORT" \
  --thread "$THREADS" \
  --qualified_quality_phred "$QC_MIN_QUAL" \
  --length_required "$QC_MIN_LEN" \
  --detect_adapter_for_pe \
  --correction \
  --overrepresentation_analysis

log_info "[fastp] OK: reads limpos em:"
echo "  ${OUT_R1}"
echo "  ${OUT_R2}"
echo "[QC_R1_CLEAN]=${OUT_R1}"
echo "[QC_R2_CLEAN]=${OUT_R2}"
