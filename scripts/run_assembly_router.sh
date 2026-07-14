#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="${REPO_ROOT}/config/picornavirus.env"
LEGACY_CONFIG="${REPO_ROOT}/config.env"

# Se este script foi chamado pelo pipeline principal,
# não recarregar config.env para não sobrescrever argumentos da CLI.
if [[ "${PIPELINE_CONFIG_LOADED:-0}" != "1" ]]; then
  if [[ -f "${CONFIG_FILE}" ]]; then
    source "${CONFIG_FILE}"
  elif [[ -f "${LEGACY_CONFIG}" ]]; then
    source "${LEGACY_CONFIG}"
  fi
fi

source "${SCRIPT_DIR}/lib/common.sh"
set +e

if [[ "${PIPELINE_CONFIG_LOADED:-0}" != "1" ]]; then
  if [[ ! -f "${CONFIG_FILE}" && ! -f "${LEGACY_CONFIG}" ]]; then
    log_error "config/picornavirus.env não existe. Crie com: cp config/picornavirus.env.example config/picornavirus.env"
  fi
fi

RAW_DIR="$(resolve_path "${RAW_DIR:-data/raw}")"
ASSEMBLY_DIR="$(resolve_path "${ASSEMBLY_DIR:-data/assemblies}")"

SAMPLE_NAME="${SAMPLE_NAME:-${SAMPLE:-amostra_teste}}"
SAMPLE_ID="${SAMPLE_ID:-$SAMPLE_NAME}"
SAMPLE_KEY="$SAMPLE_ID"

# Sanitiza espaços do SAMPLE_KEY para uso em paths de diretório de montagem
# (SPAdes 4.x falha com espaços nos caminhos dos configs internos)
SAFE_SAMPLE_KEY="${SAMPLE_KEY// /_}"

ASSEMBLER="${ASSEMBLER:-velvet}"
THREADS="${THREADS:-4}"
SPADES_PARAMS="${SPADES_PARAMS:-}"
VELVET_K="${VELVET_K:-31}"

USE_SINGLE=0
RAW_SINGLE=""

if [[ -n "${SAMPLE_SINGLE:-}" ]]; then
  USE_SINGLE=1
  RAW_SINGLE="$(resolve_path "${SAMPLE_SINGLE}")"
  check_file "$RAW_SINGLE"
else
  if [[ -n "${SAMPLE_R1:-}" ]]; then
    RAW1="$(resolve_path "${SAMPLE_R1}")"
  else
    RAW1="${RAW_DIR}/${SAMPLE_KEY}_R1.fastq.gz"
  fi

  if [[ -n "${SAMPLE_R2:-}" ]]; then
    RAW2="$(resolve_path "${SAMPLE_R2}")"
  else
    RAW2="${RAW_DIR}/${SAMPLE_KEY}_R2.fastq.gz"
  fi

  check_file "$RAW1"
  check_file "$RAW2"
fi

log_info "[PIPELINE] Sample: $SAMPLE_NAME"
log_info "[PIPELINE] Sample key: $SAMPLE_KEY  (safe: $SAFE_SAMPLE_KEY)"
log_info "[PIPELINE] Assembler: $ASSEMBLER"
if [[ $USE_SINGLE -eq 1 ]]; then
  log_info "[PIPELINE] Input single-end: $RAW_SINGLE"
else
  log_info "[PIPELINE] Input paired-end: $RAW1 / $RAW2"
fi

# Diretório padronizado de saída (usa nome original do sample para compatibilidade)
STD_ASM_DIR="${ASSEMBLY_DIR}/${SAMPLE_KEY}_assembly"
mkdir -p "$STD_ASM_DIR"

export PIPELINE_ETAPA="ASSEMBLY"

STD_ASM_DIR="${ASSEMBLY_DIR}/${SAMPLE_KEY}_assembly"
mkdir -p "$STD_ASM_DIR"

copy_contigs() {
  local src="$1" dst="$2"
  if [[ ! -f "$src" ]]; then
    log_error "Contigs não encontrados em: $src"
  fi
  rm -f "$dst"
  cp -f "$src" "$dst"
  log_info "[PIPELINE] Contigs copiados com sucesso: $src → $dst"
}

# Variáveis globais para armazenar os caminhos
LAST_CONTIGS_SRC=""

run_single_assembler() {
  local asm="$1"
  local rc=0
  local asm_log_dir="${REPO_ROOT}/logs/assembly"
  local stdout_log="${asm_log_dir}/${SAFE_SAMPLE_KEY}_${asm}.stdout.log"
  local stderr_log="${asm_log_dir}/${SAFE_SAMPLE_KEY}_${asm}.stderr.log"
  mkdir -p "$asm_log_dir"
  rm -f "$stdout_log" "$stderr_log"

  log_info "Tentando montar com: $asm"

  if [[ "$asm" == "metaspades" ]]; then
    rm -rf "${ASSEMBLY_DIR}/${SAFE_SAMPLE_KEY}_metaspades"
    if [[ $USE_SINGLE -eq 1 ]]; then
      SAMPLE_SINGLE="$RAW_SINGLE" \
        "${SCRIPT_DIR}/01_run_metaspades.sh" "$SAFE_SAMPLE_KEY" "$THREADS" "$SPADES_PARAMS" > "$stdout_log" 2> "$stderr_log"
    else
      R1="$RAW1" R2="$RAW2" \
        "${SCRIPT_DIR}/01_run_metaspades.sh" "$SAFE_SAMPLE_KEY" "$THREADS" "$SPADES_PARAMS" > "$stdout_log" 2> "$stderr_log"
    fi
    rc=$?
    local contigs_src="${ASSEMBLY_DIR}/${SAFE_SAMPLE_KEY}_metaspades/contigs.fasta"

  elif [[ "$asm" == "spades" ]]; then
    rm -rf "${ASSEMBLY_DIR}/${SAFE_SAMPLE_KEY}_spades"
    if [[ $USE_SINGLE -eq 1 ]]; then
      SAMPLE_SINGLE="$RAW_SINGLE" \
        "${SCRIPT_DIR}/01_run_spades.sh" "$SAFE_SAMPLE_KEY" "$THREADS" "$SPADES_PARAMS" "spades" > "$stdout_log" 2> "$stderr_log"
    else
      R1="$RAW1" R2="$RAW2" \
        "${SCRIPT_DIR}/01_run_spades.sh" "$SAFE_SAMPLE_KEY" "$THREADS" "$SPADES_PARAMS" "spades" > "$stdout_log" 2> "$stderr_log"
    fi
    rc=$?
    local contigs_src="${ASSEMBLY_DIR}/${SAFE_SAMPLE_KEY}_spades/contigs.fasta"

  elif [[ "$asm" == "velvet" ]]; then
    rm -rf "${ASSEMBLY_DIR}/${SAFE_SAMPLE_KEY}_velvet_k${VELVET_K}"
    if [[ $USE_SINGLE -eq 1 ]]; then
      SAMPLE_SINGLE="$RAW_SINGLE" \
        "${SCRIPT_DIR}/01_run_velvet.sh" "$SAFE_SAMPLE_KEY" "$VELVET_K" "${VELVET_OPTS:-}" > "$stdout_log" 2> "$stderr_log"
    else
      R1="$RAW1" R2="$RAW2" \
        "${SCRIPT_DIR}/01_run_velvet.sh" "$SAFE_SAMPLE_KEY" "$VELVET_K" "${VELVET_OPTS:-}" > "$stdout_log" 2> "$stderr_log"
    fi
    rc=$?
    local contigs_src="${ASSEMBLY_DIR}/${SAFE_SAMPLE_KEY}_velvet_k${VELVET_K}/contigs.fa"
  fi

  if [[ $rc -ne 0 ]]; then
    log_warning "Montador $asm falhou com exit code: $rc (Falha Dura). Logs: stdout=${stdout_log}; stderr=${stderr_log}"
    return 1 # Falha dura
  fi

  if [[ ! -s "$contigs_src" ]]; then
    log_warning "Montador $asm nao gerou contigs ou arquivo esta vazio (Falha Branda)"
    return 2 # Falha branda
  fi

  # Calcula tamanho do maior contig
  local max_contig_len=0
  max_contig_len=$(awk '/^>/ {if (seqlen > max) max = seqlen; seqlen = 0; next} {seqlen += length($0)} END {if (seqlen > max) max = seqlen; print max}' "$contigs_src" 2>/dev/null || echo 0)
  max_contig_len=${max_contig_len:-0}

  if [[ $max_contig_len -lt 200 ]]; then
    log_warning "Maior contig gerado por $asm (${max_contig_len} pb) menor que 200 pb (Falha Branda)"
    return 2 # Falha branda
  fi

  log_info "Montador $asm concluido com sucesso. Maior contig: ${max_contig_len} pb."
  LAST_CONTIGS_SRC="$contigs_src"
  return 0
}

ASSEMBLER_REQUESTED="$ASSEMBLER"
ASSEMBLER_USED="$ASSEMBLER"
ASSEMBLY_FALLBACK=0
ASSEMBLY_FAILURE_TYPE="NONE"

# Executa montador inicial
run_single_assembler "$ASSEMBLER"
ASM_STATUS=$?

if [[ $ASM_STATUS -eq 0 ]]; then
  copy_contigs "$LAST_CONTIGS_SRC" "$STD_ASM_DIR/contigs.fa"
elif [[ $ASM_STATUS -eq 2 ]]; then
  # Falha branda: não cascateia por padrão, apenas reporta
  log_info "Montador inicial $ASSEMBLER reportou Falha Branda. Nao havera cascateamento automatico."
  ASSEMBLY_FAILURE_TYPE="SOFT"
  # Toca arquivo contigs.fa vazio para a etapa de resgate
  touch "$STD_ASM_DIR/contigs.fa"
else
  # Falha dura: executa cadeia de fallback
  log_recovered "Montador inicial $ASSEMBLER reportou Falha Dura. Iniciando cadeia de fallback..."
  ASSEMBLY_FALLBACK=1

  FALLBACK_RESOLVED=0
  if [[ "$ASSEMBLER" == "spades" ]]; then
    run_single_assembler "metaspades"
    FB_STATUS=$?
    if [[ $FB_STATUS -eq 0 ]]; then
      ASSEMBLER_USED="metaspades"
      copy_contigs "$LAST_CONTIGS_SRC" "$STD_ASM_DIR/contigs.fa"
      FALLBACK_RESOLVED=1
    elif [[ $FB_STATUS -eq 2 ]]; then
      ASSEMBLER_USED="metaspades"
      ASSEMBLY_FAILURE_TYPE="SOFT"
      touch "$STD_ASM_DIR/contigs.fa"
      FALLBACK_RESOLVED=1
    else
      # Tentativa Velvet
      run_single_assembler "velvet"
      FB2_STATUS=$?
      if [[ $FB2_STATUS -eq 0 ]]; then
        ASSEMBLER_USED="velvet"
        copy_contigs "$LAST_CONTIGS_SRC" "$STD_ASM_DIR/contigs.fa"
        FALLBACK_RESOLVED=1
      elif [[ $FB2_STATUS -eq 2 ]]; then
        ASSEMBLER_USED="velvet"
        ASSEMBLY_FAILURE_TYPE="SOFT"
        touch "$STD_ASM_DIR/contigs.fa"
        FALLBACK_RESOLVED=1
      fi
    fi
  elif [[ "$ASSEMBLER" == "metaspades" ]]; then
    run_single_assembler "spades"
    FB_STATUS=$?
    if [[ $FB_STATUS -eq 0 ]]; then
      ASSEMBLER_USED="spades"
      copy_contigs "$LAST_CONTIGS_SRC" "$STD_ASM_DIR/contigs.fa"
      FALLBACK_RESOLVED=1
    elif [[ $FB_STATUS -eq 2 ]]; then
      ASSEMBLER_USED="spades"
      ASSEMBLY_FAILURE_TYPE="SOFT"
      touch "$STD_ASM_DIR/contigs.fa"
      FALLBACK_RESOLVED=1
    else
      # Tentativa Velvet
      run_single_assembler "velvet"
      FB2_STATUS=$?
      if [[ $FB2_STATUS -eq 0 ]]; then
        ASSEMBLER_USED="velvet"
        copy_contigs "$LAST_CONTIGS_SRC" "$STD_ASM_DIR/contigs.fa"
        FALLBACK_RESOLVED=1
      elif [[ $FB2_STATUS -eq 2 ]]; then
        ASSEMBLER_USED="velvet"
        ASSEMBLY_FAILURE_TYPE="SOFT"
        touch "$STD_ASM_DIR/contigs.fa"
        FALLBACK_RESOLVED=1
      fi
    fi
  fi

  if [[ $FALLBACK_RESOLVED -eq 0 ]]; then
    log_warning "Todos os montadores da cadeia de fallback falharam."
    ASSEMBLY_FAILURE_TYPE="HARD"
    touch "$STD_ASM_DIR/contigs.fa"
  else
    log_recovered "Cadeia de fallback resolvida. Montador utilizado: $ASSEMBLER_USED (Tipo de Falha: $ASSEMBLY_FAILURE_TYPE)"
  fi
fi

# Grava metadados da montagem
METADATA_FILE="${STD_ASM_DIR}/assembly_metadata.env"
{
  echo "ASSEMBLER_REQUESTED=\"${ASSEMBLER_REQUESTED}\""
  echo "ASSEMBLER_USED=\"${ASSEMBLER_USED}\""
  echo "ASSEMBLY_FALLBACK=${ASSEMBLY_FALLBACK}"
  echo "ASSEMBLY_FAILURE_TYPE=\"${ASSEMBLY_FAILURE_TYPE}\""
  echo "RESCUE_TRIGGERED=0"
  echo "INPUT_MODE=READS"
} > "$METADATA_FILE"

log_info "Metadados de montagem salvos em ${METADATA_FILE}"
