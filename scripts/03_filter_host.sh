#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

INCOMING_HOST_FILTER_ENABLED="${HOST_FILTER_ENABLED:-}"
INCOMING_HOST_NAME="${HOST_NAME:-}"
INCOMING_HOST_INDEX_PREFIX="${HOST_INDEX_PREFIX:-}"
INCOMING_HOST_REMOVED_DIR="${HOST_REMOVED_DIR:-}"
INCOMING_RAW_DIR="${RAW_DIR:-}"

CONFIG_FILE="${REPO_ROOT}/config/picornavirus.env"
LEGACY_CONFIG="${REPO_ROOT}/config.env"
if [[ -f "${CONFIG_FILE}" ]]; then
  source "${CONFIG_FILE}"
elif [[ -f "${LEGACY_CONFIG}" ]]; then
  source "${LEGACY_CONFIG}"
fi

if [[ -n "$INCOMING_HOST_FILTER_ENABLED" ]]; then
  HOST_FILTER_ENABLED="$INCOMING_HOST_FILTER_ENABLED"
fi
if [[ -n "$INCOMING_HOST_NAME" ]]; then
  HOST_NAME="$INCOMING_HOST_NAME"
fi
if [[ -n "$INCOMING_HOST_INDEX_PREFIX" ]]; then
  HOST_INDEX_PREFIX="$INCOMING_HOST_INDEX_PREFIX"
fi
if [[ -n "$INCOMING_HOST_REMOVED_DIR" ]]; then
  HOST_REMOVED_DIR="$INCOMING_HOST_REMOVED_DIR"
fi
if [[ -n "$INCOMING_RAW_DIR" ]]; then
  RAW_DIR="$INCOMING_RAW_DIR"
fi

source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/host_filter.sh"

if [[ $# -lt 1 ]]; then
  log_error "Uso: $0 NOME_AMOSTRA"
fi

SAMPLE="$1"
SAMPLE="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" sample "$SAMPLE")"
SAMPLE_NAME="$SAMPLE"
THREADS="${THREADS:-$(nproc --all 2>/dev/null || echo 4)}"
HOST_MIN_ALIGNMENT_RATE="${HOST_MIN_ALIGNMENT_RATE:-50}"
HOST_FILTER_ENABLED="${HOST_FILTER_ENABLED:-true}"
HOST_NAME="${HOST_NAME:-Sus scrofa}"

RAW_DIR="$(resolve_path "${RAW_DIR:-data/raw}")"
HOST_REMOVED_DIR="$(resolve_path "${HOST_REMOVED_DIR:-data/host_removed}")"
HOST_INDEX_PREFIX="$(resolve_path "${HOST_INDEX_PREFIX:-ref/host/sus_scrofa_bt2}")"

if [[ -n "${SAMPLE_SINGLE:-}" ]]; then
  log_error "Filtro do hospedeiro requer leituras pareadas. Use SAMPLE_R1/SAMPLE_R2."
fi

if [[ -n "${SAMPLE_R1:-}" ]]; then
  R1="$(resolve_path "${SAMPLE_R1}")"
else
  R1="${RAW_DIR}/${SAMPLE}_R1.fastq.gz"
fi

if [[ -n "${SAMPLE_R2:-}" ]]; then
  R2="$(resolve_path "${SAMPLE_R2}")"
else
  R2="${RAW_DIR}/${SAMPLE}_R2.fastq.gz"
fi

check_file "$R1"
check_file "$R2"

if [[ ! -d "$HOST_REMOVED_DIR" ]]; then
  mkdir -p "$HOST_REMOVED_DIR"
fi

OUT_R1="${HOST_REMOVED_DIR}/${SAMPLE}_R1.host_removed.fastq.gz"
OUT_R2="${HOST_REMOVED_DIR}/${SAMPLE}_R2.host_removed.fastq.gz"
WORK_DIR="$(mktemp -d "${HOST_REMOVED_DIR}/.${SAMPLE}.host-filter.XXXXXX")"
cleanup() {
  rm -rf -- "$WORK_DIR"
}
trap cleanup EXIT

copy_read_to_gz() {
  local src="$1"
  local dst="$2"
  if [[ "$src" == *.gz ]]; then
    cp -f "$src" "$dst"
  else
    gzip -c "$src" > "$dst"
  fi
}

validate_staged_pair() {
  local staged_r1="$1"
  local staged_r2="$2"
  if [[ ! -f "$staged_r1" || ! -f "$staged_r2" ]]; then
    log_error "Filtro de hospedeiro nao produziu o par de FASTQs esperado."
  fi
  if ! gzip -t "$staged_r1" "$staged_r2"; then
    log_error "FASTQs produzidos pelo filtro de hospedeiro estao corrompidos."
  fi
}

promote_staged_pair() {
  local staged_r1="$1"
  local staged_r2="$2"
  local previous_r1="${WORK_DIR}/previous_R1.fastq.gz"
  local previous_r2="${WORK_DIR}/previous_R2.fastq.gz"
  local had_previous_r1=0
  local had_previous_r2=0

  validate_staged_pair "$staged_r1" "$staged_r2"

  if [[ -e "$OUT_R1" ]]; then
    mv "$OUT_R1" "$previous_r1"
    had_previous_r1=1
  fi
  if [[ -e "$OUT_R2" ]]; then
    if ! mv "$OUT_R2" "$previous_r2"; then
      if [[ $had_previous_r1 -eq 1 ]]; then
        mv "$previous_r1" "$OUT_R1"
      fi
      log_error "Nao foi possivel iniciar a promocao transacional dos FASTQs filtrados."
    fi
    had_previous_r2=1
  fi

  if mv "$staged_r1" "$OUT_R1" && mv "$staged_r2" "$OUT_R2"; then
    return 0
  fi

  rm -f -- "$OUT_R1" "$OUT_R2"
  if [[ $had_previous_r1 -eq 1 ]]; then
    mv "$previous_r1" "$OUT_R1"
  fi
  if [[ $had_previous_r2 -eq 1 ]]; then
    mv "$previous_r2" "$OUT_R2"
  fi
  log_error "Falha ao promover FASTQs filtrados; o par anterior foi restaurado."
}

case "${HOST_FILTER_ENABLED,,}" in
  false|0|no|nao)
    log_info "Filtro de hospedeiro desabilitado (HOST_FILTER_ENABLED=false); reads copiadas sem Bowtie2."
    copy_read_to_gz "$R1" "${WORK_DIR}/R1.fastq.gz"
    copy_read_to_gz "$R2" "${WORK_DIR}/R2.fastq.gz"
    promote_staged_pair "${WORK_DIR}/R1.fastq.gz" "${WORK_DIR}/R2.fastq.gz"
    echo "  ${OUT_R1}"
    echo "  ${OUT_R2}"
    exit 0
    ;;
esac

if ! INDEX_KIND="$(validate_bt2_index "$HOST_INDEX_PREFIX")"; then
  log_error "Falha na validacao do indice do hospedeiro '${HOST_NAME}' em ${HOST_INDEX_PREFIX}."
fi

TMP_PREFIX="${WORK_DIR}/host_removed"
BT2_LOG="${HOST_REMOVED_DIR}/${SAMPLE}_host_filter_bowtie2.log"

log_info "Filtrando leituras do hospedeiro (${HOST_NAME}) para amostra ${SAMPLE} usando indice ${INDEX_KIND} e ${THREADS} thread(s)..."

if ! bowtie2 \
  -x "$HOST_INDEX_PREFIX" \
  -1 "$R1" \
  -2 "$R2" \
  --very-sensitive \
  -p "$THREADS" \
  --un-conc-gz "${TMP_PREFIX}.fastq.gz" \
  -S /dev/null \
  2> "$BT2_LOG"; then
  log_error "Bowtie2 falhou durante filtro do hospedeiro. Veja o log: ${BT2_LOG}"
fi

alignment_rate="$(awk '/overall alignment rate/ {gsub("%", "", $1); print $1}' "$BT2_LOG" | tail -n 1)"
if [[ -n "$alignment_rate" ]]; then
  low_rate="$(awk -v rate="$alignment_rate" -v min="$HOST_MIN_ALIGNMENT_RATE" 'BEGIN {print (rate < min) ? 1 : 0}')"
  if [[ "$low_rate" == "1" ]]; then
    log_error "Taxa de alinhamento ao hospedeiro baixa (${alignment_rate}%; minimo ${HOST_MIN_ALIGNMENT_RATE}%). Possivel referencia incompleta ou indice incorreto: ${HOST_INDEX_PREFIX}"
  fi
else
  log_warning "Nao foi possivel ler a taxa de alinhamento do Bowtie2 em ${BT2_LOG}."
fi

# Bowtie2 com --un-conc-gz gera dois arquivos:
#   ${TMP_PREFIX}.fastq.1.gz  e  ${TMP_PREFIX}.fastq.2.gz
promote_staged_pair "${TMP_PREFIX}.fastq.1.gz" "${TMP_PREFIX}.fastq.2.gz"

log_info "Leituras não alinhadas ao hospedeiro salvas em:"
echo "  ${OUT_R1}"
echo "  ${OUT_R2}"
