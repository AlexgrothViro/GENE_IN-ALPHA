#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/host_filter.sh"
# Normalize incoming DB if it has an alias
case "${DB:-}" in
  teschovirus_a|teschovirus)   DB="ptv" ;;
  enterovirus_g)               DB="evg" ;;
  sapelovirus_a)               DB="psv" ;;
  senecavirus_a)               DB="svv" ;;
  fmdv|foot_and_mouth)         DB="fmdv" ;;
esac

# Limpar preventivamente variáveis herdadas do ambiente que apontam para caminhos inexistentes
# ou que referenciem o diretório antigo do Gene-In (evitando quebras após clonar/renomear pastas).
for var in REF_FASTA BLAST_DB BOWTIE2_INDEX; do
  val="${!var:-}"
  if [[ -n "$val" ]]; then
    if [[ ! -e "$val" && "$val" == /* ]]; then
      unset "$var"
    fi
  fi
done

# 1. GUARDA AS VARIÁVEIS DO DASHBOARD (Prioridade Máxima)
INCOMING_DB="${DB:-}"
INCOMING_DB_QUERY="${DB_QUERY:-}"
INCOMING_ASSEMBLER="${ASSEMBLER:-}"
INCOMING_HOST_FILTER_ENABLED="${HOST_FILTER_ENABLED:-}"
INCOMING_HOST_NAME="${HOST_NAME:-}"
INCOMING_HOST_ACCESSION="${HOST_ACCESSION:-}"
INCOMING_HOST_INDEX_PREFIX="${HOST_INDEX_PREFIX:-}"
INCOMING_SHORT_FRAGMENT_MODE="${SHORT_FRAGMENT_MODE:-}"
INCOMING_SHORT_FRAGMENT_MIN_LEN="${SHORT_FRAGMENT_MIN_LEN:-}"
INCOMING_SHORT_FRAGMENT_MAX_LEN="${SHORT_FRAGMENT_MAX_LEN:-}"
INCOMING_SHORT_FRAGMENT_DEDUP="${SHORT_FRAGMENT_DEDUP:-}"
INCOMING_SHORT_FRAGMENT_BLAST="${SHORT_FRAGMENT_BLAST:-}"
INCOMING_SHORT_FRAGMENT_WORD_SIZE="${SHORT_FRAGMENT_WORD_SIZE:-}"
INCOMING_SHORT_FRAGMENT_EVALUE="${SHORT_FRAGMENT_EVALUE:-}"
INCOMING_SHORT_FRAGMENT_MIN_PID="${SHORT_FRAGMENT_MIN_PID:-}"
INCOMING_SHORT_FRAGMENT_MIN_QCOV="${SHORT_FRAGMENT_MIN_QCOV:-}"
INCOMING_EVIDENCE_V2="${EVIDENCE_V2:-}"
INCOMING_EVIDENCE_CONFIG="${EVIDENCE_CONFIG:-}"
INCOMING_EVIDENCE_LIBRARY_MODE="${EVIDENCE_LIBRARY_MODE:-}"
INCOMING_EVIDENCE_UMI_MODE="${EVIDENCE_UMI_MODE:-}"
INCOMING_EVIDENCE_ROLE="${EVIDENCE_ROLE:-}"
INCOMING_EVIDENCE_EXPECTED_TARGET="${EVIDENCE_EXPECTED_TARGET:-}"
INCOMING_EVIDENCE_COMPOSITE_DB="${EVIDENCE_COMPOSITE_DB:-}"
INCOMING_EVIDENCE_SUBJECT_LABELS="${EVIDENCE_SUBJECT_LABELS:-}"
INCOMING_EVIDENCE_PANEL_FASTA="${EVIDENCE_PANEL_FASTA:-}"
INCOMING_EVIDENCE_PANEL_INDEX="${EVIDENCE_PANEL_INDEX:-}"
INCOMING_EVIDENCE_RUN_ID="${EVIDENCE_RUN_ID:-}"
INCOMING_EVIDENCE_BATCH_ID="${EVIDENCE_BATCH_ID:-}"
CONFIG_FILE="${REPO_ROOT}/config/picornavirus.env"
LEGACY_CONFIG="${REPO_ROOT}/config.env"
HAS_CONFIG=0
if [[ -f "${CONFIG_FILE}" ]]; then
  source "${CONFIG_FILE}"
  HAS_CONFIG=1
elif [[ -f "${LEGACY_CONFIG}" ]]; then
  source "${LEGACY_CONFIG}"
  HAS_CONFIG=1
fi
# 2. RESTAURA AS VARIÁVEIS (Sobrescrevendo o config.env)
if [[ -n "$INCOMING_DB_QUERY" && ( -z "$INCOMING_DB" || "$INCOMING_DB" == "custom" ) ]]; then
  DB_QUERY="$INCOMING_DB_QUERY"
  DB="custom"
  unset REF_FASTA BLAST_DB BOWTIE2_INDEX
elif [[ -n "$INCOMING_DB" ]]; then
  DB="$INCOMING_DB"
  unset REF_FASTA BLAST_DB BOWTIE2_INDEX DB_QUERY
fi

if [[ -n "$INCOMING_ASSEMBLER" ]]; then
  ASSEMBLER="$INCOMING_ASSEMBLER"
fi

if [[ -n "$INCOMING_HOST_FILTER_ENABLED" ]]; then
  HOST_FILTER_ENABLED="$INCOMING_HOST_FILTER_ENABLED"
fi
if [[ -n "$INCOMING_HOST_NAME" ]]; then
  HOST_NAME="$INCOMING_HOST_NAME"
fi
if [[ -n "$INCOMING_HOST_ACCESSION" ]]; then
  HOST_ACCESSION="$INCOMING_HOST_ACCESSION"
fi
if [[ -n "$INCOMING_HOST_INDEX_PREFIX" ]]; then
  HOST_INDEX_PREFIX="$INCOMING_HOST_INDEX_PREFIX"
fi

if [[ -n "$INCOMING_SHORT_FRAGMENT_MODE" ]]; then
  SHORT_FRAGMENT_MODE="$INCOMING_SHORT_FRAGMENT_MODE"
fi
if [[ -n "$INCOMING_SHORT_FRAGMENT_MIN_LEN" ]]; then
  SHORT_FRAGMENT_MIN_LEN="$INCOMING_SHORT_FRAGMENT_MIN_LEN"
fi
if [[ -n "$INCOMING_SHORT_FRAGMENT_MAX_LEN" ]]; then
  SHORT_FRAGMENT_MAX_LEN="$INCOMING_SHORT_FRAGMENT_MAX_LEN"
fi
if [[ -n "$INCOMING_SHORT_FRAGMENT_DEDUP" ]]; then
  SHORT_FRAGMENT_DEDUP="$INCOMING_SHORT_FRAGMENT_DEDUP"
fi
if [[ -n "$INCOMING_SHORT_FRAGMENT_BLAST" ]]; then
  SHORT_FRAGMENT_BLAST="$INCOMING_SHORT_FRAGMENT_BLAST"
fi
if [[ -n "$INCOMING_SHORT_FRAGMENT_WORD_SIZE" ]]; then
  SHORT_FRAGMENT_WORD_SIZE="$INCOMING_SHORT_FRAGMENT_WORD_SIZE"
fi
if [[ -n "$INCOMING_SHORT_FRAGMENT_EVALUE" ]]; then
  SHORT_FRAGMENT_EVALUE="$INCOMING_SHORT_FRAGMENT_EVALUE"
fi
if [[ -n "$INCOMING_SHORT_FRAGMENT_MIN_PID" ]]; then
  SHORT_FRAGMENT_MIN_PID="$INCOMING_SHORT_FRAGMENT_MIN_PID"
fi
if [[ -n "$INCOMING_SHORT_FRAGMENT_MIN_QCOV" ]]; then
  SHORT_FRAGMENT_MIN_QCOV="$INCOMING_SHORT_FRAGMENT_MIN_QCOV"
fi
EVIDENCE_V2="${INCOMING_EVIDENCE_V2:-${EVIDENCE_V2:-false}}"
EVIDENCE_CONFIG="${INCOMING_EVIDENCE_CONFIG:-${EVIDENCE_CONFIG:-${REPO_ROOT}/config/evidence_v2.yaml}}"
EVIDENCE_LIBRARY_MODE="${INCOMING_EVIDENCE_LIBRARY_MODE:-${EVIDENCE_LIBRARY_MODE:-unknown}}"
EVIDENCE_UMI_MODE="${INCOMING_EVIDENCE_UMI_MODE:-${EVIDENCE_UMI_MODE:-none}}"
EVIDENCE_ROLE="${INCOMING_EVIDENCE_ROLE:-${EVIDENCE_ROLE:-sample}}"
EVIDENCE_EXPECTED_TARGET="${INCOMING_EVIDENCE_EXPECTED_TARGET:-${EVIDENCE_EXPECTED_TARGET:-}}"
EVIDENCE_COMPOSITE_DB="${INCOMING_EVIDENCE_COMPOSITE_DB:-${EVIDENCE_COMPOSITE_DB:-}}"
EVIDENCE_SUBJECT_LABELS="${INCOMING_EVIDENCE_SUBJECT_LABELS:-${EVIDENCE_SUBJECT_LABELS:-}}"
EVIDENCE_PANEL_FASTA="${INCOMING_EVIDENCE_PANEL_FASTA:-${EVIDENCE_PANEL_FASTA:-}}"
EVIDENCE_PANEL_INDEX="${INCOMING_EVIDENCE_PANEL_INDEX:-${EVIDENCE_PANEL_INDEX:-}}"
EVIDENCE_RUN_ID="${INCOMING_EVIDENCE_RUN_ID:-${EVIDENCE_RUN_ID:-}}"
EVIDENCE_BATCH_ID="${INCOMING_EVIDENCE_BATCH_ID:-${EVIDENCE_BATCH_ID:-}}"
usage() {
  cat <<'USAGE'
Uso: scripts/20_run_pipeline.sh [opções]
Opções:
  --install                 instala dependências via apt-get (usa 00_check_env.sh)
  --sample NOME             nome da amostra (padrão: SAMPLE_ID/SAMPLE_NAME/SAMPLE ou 81554_S150)
  --kmer K                  k-mer para Velvet (padrão: VELVET_K ou 31)
  --assembler NOME          montador: velvet, spades ou metaspades
  --threads N               número de threads (padrão: THREADS ou 4)
  --spades-params "PARAMS"  parâmetros extras para SPAdes/metaSPAdes
  --advanced-kmers LISTA    k-mers manuais, impares/crescentes e menores que as reads
  --blast-task NOME         tarefa BLAST: blastn ou blastn-short
  --blast-word-size N       word size do BLAST
  --blast-evalue VALOR      e-value do BLAST
  --contigs ARQUIVO         usa contigs já montados como entrada (ignora montagem)
  --skip-assembly           ignora a etapa de montagem (exige --contigs)
  --skip-host-filter        ignora o filtro do hospedeiro
  --skip-qc                 ignora o controle de qualidade com fastp
  --rescue-mode             força o resgate de reads se a montagem falhar ou contigs forem muito curtos
  --evidence-v2             gera evidencia agregada 2.0 em shadow mode
  --evidence-config ARQ     configuracao YAML estrita da evidencia 2.0
  --batch-manifest TSV      executa um lote por scripts/23_run_batch.sh
  -h, --help                mostra esta ajuda
Prioridade de configuração:
  1. argumentos da linha de comando
  2. variáveis de ambiente / config.env
  3. padrões internos seguros
Obs.: se existir config/picornavirus.env (ou config.env legado), ele será usado como base de configuração.
USAGE
}
resolve_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    echo "$path"
  else
    echo "${REPO_ROOT}/${path}"
  fi
}
require_value() {
  local opt="$1"
  local val="${2:-}"
  if [[ -z "$val" ]]; then
    echo "[ERRO] valor ausente para $opt" >&2
    usage
    exit 1
  fi
}
log() {
  printf '\n== [%s] %s ==\n' "$(date +'%Y-%m-%d %H:%M:%S')" "$1"
}
AUTO_INSTALL=0
SKIP_HOST_FILTER=0
SKIP_QC=0
RESCUE_MODE=0
SAMPLE_OVERRIDE=""
KMER_OVERRIDE=""
ASSEMBLER_OVERRIDE=""
THREADS_OVERRIDE=""
SPADES_PARAMS_OVERRIDE=""
ADVANCED_KMERS_OVERRIDE=""
BLAST_TASK_OVERRIDE=""
BLAST_WORD_SIZE_OVERRIDE=""
BLAST_EVALUE_OVERRIDE=""
CONTIGS_OVERRIDE=""
BATCH_MANIFEST=""
SKIP_ASSEMBLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install)
      AUTO_INSTALL=1
      shift
      ;;
    --sample)
      require_value "$1" "${2:-}"
      SAMPLE_OVERRIDE="$2"
      shift 2
      ;;
    --kmer)
      require_value "$1" "${2:-}"
      KMER_OVERRIDE="$2"
      shift 2
      ;;
    --assembler)
      require_value "$1" "${2:-}"
      ASSEMBLER_OVERRIDE="$2"
      shift 2
      ;;
    --threads)
      require_value "$1" "${2:-}"
      THREADS_OVERRIDE="$2"
      shift 2
      ;;
    --spades-params)
      require_value "$1" "${2:-}"
      SPADES_PARAMS_OVERRIDE="$2"
      shift 2
      ;;
    --blast-task)
      require_value "$1" "${2:-}"
      BLAST_TASK_OVERRIDE="$2"
      shift 2
      ;;
    --advanced-kmers)
      require_value "$1" "${2:-}"
      ADVANCED_KMERS_OVERRIDE="$2"
      shift 2
      ;;
    --blast-word-size)
      require_value "$1" "${2:-}"
      BLAST_WORD_SIZE_OVERRIDE="$2"
      shift 2
      ;;
    --blast-evalue)
      require_value "$1" "${2:-}"
      BLAST_EVALUE_OVERRIDE="$2"
      shift 2
      ;;
    --contigs)
      require_value "$1" "${2:-}"
      CONTIGS_OVERRIDE="$2"
      shift 2
      ;;
    --skip-assembly)
      SKIP_ASSEMBLY=1
      shift
      ;;
    --skip-host-filter)
      SKIP_HOST_FILTER=1
      shift
      ;;
    --skip-qc)
      SKIP_QC=1
      shift
      ;;
    --rescue-mode)
      RESCUE_MODE=1
      shift
      ;;
    --evidence-v2)
      EVIDENCE_V2=true
      shift
      ;;
    --evidence-config)
      require_value "$1" "${2:-}"
      EVIDENCE_CONFIG="$2"
      shift 2
      ;;
    --batch-manifest)
      require_value "$1" "${2:-}"
      BATCH_MANIFEST="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERRO] opção inválida: $1" >&2
      usage
      exit 1
      ;;
  esac
done
if [[ -n "$BATCH_MANIFEST" ]]; then
  exec "$SCRIPT_DIR/23_run_batch.sh" --batch-manifest "$BATCH_MANIFEST" --config "$EVIDENCE_CONFIG" \
    --threads "${THREADS_OVERRIDE:-${THREADS:-4}}"
fi
SAMPLE_NAME="${SAMPLE_OVERRIDE:-${SAMPLE_NAME:-${SAMPLE:-amostra_teste}}}"
SAMPLE_NAME="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" sample "$SAMPLE_NAME")"
mkdir -p "${REPO_ROOT}/tmp"
exec 8>"${REPO_ROOT}/tmp/${SAMPLE_NAME}.pipeline.lock"
if ! flock -n 8; then
  echo "[FATAL] ja existe um pipeline em execucao para a amostra '${SAMPLE_NAME}'" >&2
  exit 1
fi
if [[ -n "$SAMPLE_OVERRIDE" ]]; then
  SAMPLE_ID="$SAMPLE_NAME"
else
  SAMPLE_ID="${SAMPLE_ID:-$SAMPLE_NAME}"
fi
# Path-safe version: espaços trocados por _ para caminhos de diretórios de montagem
SAFE_SAMPLE_NAME="${SAMPLE_NAME// /_}"
VELVET_K="${KMER_OVERRIDE:-${VELVET_K:-31}}"
ASSEMBLER="${ASSEMBLER_OVERRIDE:-${ASSEMBLER:-velvet}}"
THREADS="${THREADS_OVERRIDE:-${THREADS:-4}}"
SPADES_PARAMS="${SPADES_PARAMS_OVERRIDE:-${SPADES_PARAMS:-}}"
ADVANCED_KMERS="${ADVANCED_KMERS_OVERRIDE:-${ADVANCED_KMERS:-}}"
if ! [[ "$THREADS" =~ ^[1-9][0-9]*$ ]] || (( THREADS > 256 )); then
  log_fatal "THREADS invalido: $THREADS"
fi
if ! [[ "$VELVET_K" =~ ^[0-9]+$ ]] || (( VELVET_K < 15 || VELVET_K > 127 )); then
  log_fatal "VELVET_K invalido: $VELVET_K"
fi
: "${HOST_FILTER_ENABLED:=true}"
: "${HOST_NAME:=Sus scrofa}"
: "${HOST_ACCESSION:=GCF_000003025.6}"
: "${HOST_INDEX_PREFIX:=${REPO_ROOT}/ref/host/sus_scrofa_bt2}"
HOST_INDEX_PREFIX="$(resolve_path "$HOST_INDEX_PREFIX")"
export HOST_INDEX_PREFIX HOST_NAME HOST_ACCESSION HOST_FILTER_ENABLED THREADS
DB="${DB:-ptv}"
BLAST_TASK="${BLAST_TASK_OVERRIDE:-${BLAST_TASK:-blastn}}"
BLAST_WORD_SIZE="${BLAST_WORD_SIZE_OVERRIDE:-${BLAST_WORD_SIZE:-11}}"
BLAST_EVALUE="${BLAST_EVALUE_OVERRIDE:-${BLAST_EVALUE:-1e-5}}"
CONTIGS="${CONTIGS_OVERRIDE:-${CONTIGS:-}}"
INPUT_MODE="READS"
# Define e exporta variáveis de contexto de log
export SAMPLE_NAME
export PIPELINE_ETAPA="QC_PREFLIGHT"

if [[ "$ASSEMBLER" != "velvet" && "$ASSEMBLER" != "spades" && "$ASSEMBLER" != "metaspades" ]]; then
  log_fatal "ASSEMBLER invalido: $ASSEMBLER — Use velvet, spades ou metaspades."
fi
if [[ "$BLAST_TASK" != "blastn" && "$BLAST_TASK" != "blastn-short" ]]; then
  log_fatal "BLAST_TASK invalido: $BLAST_TASK — Use blastn ou blastn-short."
fi
if [[ $SKIP_ASSEMBLY -eq 1 && -z "$CONTIGS" ]]; then
  log_fatal "--skip-assembly exige --contigs <arquivo> — Forneca o arquivo de contigs."
fi
BLAST_DB="$(resolve_path "${BLAST_DB:-blastdb/${DB}}")"
RAW_DIR="$(resolve_path "${RAW_DIR:-data/raw}")"
SAMPLE_R1="${SAMPLE_R1:-}"
SAMPLE_R2="${SAMPLE_R2:-}"
SAMPLE_SINGLE="${SAMPLE_SINGLE:-}"
# Contigs sao uma entrada distinta de reads; nao devem passar pelo fluxo FASTQ.
if [[ -n "$CONTIGS" ]]; then
  INPUT_MODE="CONTIGS"
  CONTIGS="$(resolve_path "$CONTIGS")"
  SKIP_HOST_FILTER=1
  SAMPLE_SINGLE=""
  SAMPLE_R1=""
  SAMPLE_R2=""
fi
if [[ -n "$SAMPLE_SINGLE" && ( -n "$SAMPLE_R1" || -n "$SAMPLE_R2" ) ]]; then
  echo "[ERRO] Use SAMPLE_SINGLE ou SAMPLE_R1/SAMPLE_R2, mas não ambos." >&2
  exit 1
fi
if [[ -n "$SAMPLE_SINGLE" ]]; then
  SAMPLE_SINGLE="$(resolve_path "$SAMPLE_SINGLE")"
else
  if [[ -n "$SAMPLE_R1" ]]; then
    SAMPLE_R1="$(resolve_path "$SAMPLE_R1")"
  else
    SAMPLE_R1="${RAW_DIR}/${SAMPLE_NAME}_R1.fastq.gz"
  fi
  if [[ -n "$SAMPLE_R2" ]]; then
    SAMPLE_R2="$(resolve_path "$SAMPLE_R2")"
  else
    SAMPLE_R2="${RAW_DIR}/${SAMPLE_NAME}_R2.fastq.gz"
  fi
fi
SHORT_FRAGMENT_MODE="${SHORT_FRAGMENT_MODE:-false}"
SHORT_FRAGMENT_MIN_LEN="${SHORT_FRAGMENT_MIN_LEN:-20}"
SHORT_FRAGMENT_MAX_LEN="${SHORT_FRAGMENT_MAX_LEN:-100}"
SHORT_FRAGMENT_DEDUP="${SHORT_FRAGMENT_DEDUP:-true}"
SHORT_FRAGMENT_BLAST="${SHORT_FRAGMENT_BLAST:-false}"
SHORT_FRAGMENT_WORD_SIZE="${SHORT_FRAGMENT_WORD_SIZE:-7}"
SHORT_FRAGMENT_EVALUE="${SHORT_FRAGMENT_EVALUE:-1000}"
SHORT_FRAGMENT_MIN_PID="${SHORT_FRAGMENT_MIN_PID:-70}"
SHORT_FRAGMENT_MIN_QCOV="${SHORT_FRAGMENT_MIN_QCOV:-70}"

# ── Log por amostra ──────────────────────────────────────────────────────────
# Grava logs/{SAMPLE_NAME}_pipeline.log conforme documentado no README.
# Usa tee em modo append para preservar execuções anteriores.
# Compatível com pipefail: o processo principal continua sendo o pai.
LOG_DIR="${REPO_ROOT}/logs"
mkdir -p "$LOG_DIR"
PIPELINE_LOG="${LOG_DIR}/${SAMPLE_NAME}_pipeline.log"
exec > >(tee -a "$PIPELINE_LOG") 2>&1
echo "=== Pipeline iniciado em $(date -Iseconds) ==="
echo "    Amostra: ${SAMPLE_NAME}  Assembler: ${ASSEMBLER}  DB: ${DB:-ptv}"
echo "=============================================="

export SAMPLE_ID SAMPLE_NAME SAMPLE_R1 SAMPLE_R2 SAMPLE_SINGLE RAW_DIR INPUT_MODE
export ASSEMBLER THREADS SPADES_PARAMS VELVET_K
export ADVANCED_KMERS
export BLAST_TASK BLAST_WORD_SIZE BLAST_EVALUE
export CONTIGS SKIP_ASSEMBLY SKIP_QC SKIP_HOST_FILTER RESCUE_MODE HOST_INDEX_PREFIX HOST_NAME HOST_ACCESSION HOST_FILTER_ENABLED
export SHORT_FRAGMENT_MODE SHORT_FRAGMENT_MIN_LEN SHORT_FRAGMENT_MAX_LEN SHORT_FRAGMENT_DEDUP
export SHORT_FRAGMENT_BLAST SHORT_FRAGMENT_WORD_SIZE SHORT_FRAGMENT_EVALUE SHORT_FRAGMENT_MIN_PID SHORT_FRAGMENT_MIN_QCOV
export EVIDENCE_V2 EVIDENCE_CONFIG EVIDENCE_LIBRARY_MODE EVIDENCE_UMI_MODE
export PIPELINE_CONFIG_LOADED=1
EVIDENCE_STATE_FILE="${REPO_ROOT}/results/evidence/state/${EVIDENCE_RUN_ID}.json"
evidence_state_status() {
  [[ "${EVIDENCE_V2,,}" =~ ^(true|1|yes)$ && -n "$EVIDENCE_RUN_ID" && -f "$EVIDENCE_STATE_FILE" ]] || return 0
  local args=(--state "$EVIDENCE_STATE_FILE" status --value "$1")
  [[ -z "${2:-}" ]] || args+=(--official-v1-status "$2")
  [[ -z "${3:-}" ]] || args+=(--evidence-v2-status "$3")
  python3 "$SCRIPT_DIR/evidence/run_state.py" "${args[@]}"
}
evidence_state_stage() {
  [[ "${EVIDENCE_V2,,}" =~ ^(true|1|yes)$ && -n "$EVIDENCE_RUN_ID" && -f "$EVIDENCE_STATE_FILE" ]] || return 0
  local args=(--state "$EVIDENCE_STATE_FILE" stage --id "$1" --status "$2")
  [[ -z "${3:-}" ]] || args+=(--message "$3")
  python3 "$SCRIPT_DIR/evidence/run_state.py" "${args[@]}"
}
evidence_state_status running running queued
evidence_state_stage input_validation running "Validando FASTQ/FASTA, configuração e parâmetros."
# --- Preflight: validar a entrada efetiva ---
if [[ "$INPUT_MODE" == "CONTIGS" ]]; then
  python3 "${SCRIPT_DIR}/lib/input_validation.py" fasta "$CONTIGS"
elif [[ -n "$SAMPLE_SINGLE" ]]; then
  if [[ ! -s "$SAMPLE_SINGLE" ]]; then
    log_fatal "Read single nao encontrado ou vazio: $SAMPLE_SINGLE — Verifique o arquivo."
  fi
  if [[ "$SAMPLE_SINGLE" =~ \.gz$ ]]; then
    gzip -t "$SAMPLE_SINGLE" 2>/dev/null || log_fatal "Read single corrompido ou .gz invalido — Verifique o arquivo antes de prosseguir."
  fi
else
  R1="$SAMPLE_R1"
  R2="$SAMPLE_R2"
  if [[ ! -s "$R1" || ! -s "$R2" ]]; then
    echo "[FATAL]      [QC_PREFLIGHT] [${SAMPLE_NAME}] — FASTQs da amostra nao encontrados ou vazios:" >&2
    echo "             $R1" >&2
    echo "             $R2" >&2
    echo "" >&2
    echo "[DICA] Importe uma amostra com:" >&2
    echo "  bash scripts/00_import_sample.sh --sample NOME --r1 CAMINHO --r2 CAMINHO [--copy]" >&2
    echo "[DICA] Amostras detectadas em ${RAW_DIR}:" >&2
    ls -1 "${RAW_DIR}"/*_R1.fastq.gz 2>/dev/null | sed -E 's#.*/##; s/_R1\.fastq\.gz$//' | sort -u | sed 's/^/  - /' >&2 || true
    exit 1
  fi

  if [[ "$R1" =~ \.gz$ ]]; then
    gzip -t "$R1" 2>/dev/null || log_fatal "R1 corrompido ou .gz invalido — Verifique o arquivo antes de prosseguir."
  fi
  if [[ "$R2" =~ \.gz$ ]]; then
    gzip -t "$R2" 2>/dev/null || log_fatal "R2 corrompido ou .gz invalido — Verifique o arquivo antes de prosseguir."
  fi

  log_info "Verificando integridade e pareamento dos FASTQs..."
  if [[ "$R1" =~ \.gz$ ]]; then
    r1_lines=$(gzip -cd "$R1" | wc -l)
  else
    r1_lines=$(wc -l < "$R1")
  fi

  if [[ "$R2" =~ \.gz$ ]]; then
    r2_lines=$(gzip -cd "$R2" | wc -l)
  else
    r2_lines=$(wc -l < "$R2")
  fi

  if (( r1_lines % 4 != 0 || r2_lines % 4 != 0 )); then
    log_fatal "FASTQ com numero de linhas nao multiplo de 4 — Verifique a integridade do arquivo."
  fi

  r1_reads=$((r1_lines / 4))
  r2_reads=$((r2_lines / 4))

  if (( r1_reads != r2_reads )); then
    log_fatal "Pareamento inconsistente: R1=${r1_reads} reads, R2=${r2_reads} reads — Confira se os arquivos pertencem ao mesmo par."
  fi
  log_info "FASTQs pareados com sucesso: ${r1_reads} reads detectadas."
fi
log "Configuração efetiva"
if [[ "$INPUT_MODE" == "READS" ]]; then
  if [[ -n "$SAMPLE_SINGLE" ]]; then
    python3 "${SCRIPT_DIR}/lib/input_validation.py" fastq "$SAMPLE_SINGLE"
  else
    python3 "${SCRIPT_DIR}/lib/input_validation.py" fastq "$SAMPLE_R1" --mate "$SAMPLE_R2"
  fi
fi
if [[ " ${SPADES_PARAMS:-} " =~ [[:space:]]-k([[:space:]]|=) ]]; then
  log_fatal "Use --advanced-kmers para configurar k-mers; -k em --spades-params nao e permitido."
fi
if [[ -n "$ADVANCED_KMERS" ]]; then
  [[ "$INPUT_MODE" == "READS" ]] || log_fatal "--advanced-kmers exige reads FASTQ."
  KMER_FASTQ="${SAMPLE_SINGLE:-$SAMPLE_R1}"
  ADVANCED_KMERS="$(python3 "${SCRIPT_DIR}/evidence/validate_kmers.py" --kmers "$ADVANCED_KMERS" --fastq "$KMER_FASTQ")"
  if [[ "$ASSEMBLER" == "spades" ]]; then
    SPADES_PARAMS="${SPADES_PARAMS} -k ${ADVANCED_KMERS}"
  fi
fi
evidence_state_stage input_validation done "Entrada e parâmetros do pipeline validados."
echo "Amostra: $SAMPLE_NAME"
echo "Assembler: $ASSEMBLER"
echo "Threads: $THREADS"
echo "SPADES_PARAMS: ${SPADES_PARAMS:-<vazio>}"
echo "ADVANCED_KMERS: ${ADVANCED_KMERS:-automatico}"
echo "BLAST_DB: $BLAST_DB"
echo "BLAST: task=$BLAST_TASK word_size=$BLAST_WORD_SIZE evalue=$BLAST_EVALUE"
echo "SHORT_FRAGMENT_MODE: $SHORT_FRAGMENT_MODE (range: $SHORT_FRAGMENT_MIN_LEN - $SHORT_FRAGMENT_MAX_LEN, dedup: $SHORT_FRAGMENT_DEDUP)"
echo "SHORT_FRAGMENT_BLAST: $SHORT_FRAGMENT_BLAST (word_size=$SHORT_FRAGMENT_WORD_SIZE evalue=$SHORT_FRAGMENT_EVALUE min_pid=$SHORT_FRAGMENT_MIN_PID min_qcov=$SHORT_FRAGMENT_MIN_QCOV)"
log "[1/6] Verificando ambiente"
if [[ $AUTO_INSTALL -eq 1 ]]; then
  "$SCRIPT_DIR/00_check_env.sh" --install
else
  "$SCRIPT_DIR/00_check_env.sh"
fi
log "[2/6] Preparando diretórios e bancos"
make -C "$REPO_ROOT" setup_dirs
DB_TARGET="db-blast"
[[ "$DB" == "custom" ]] && DB_TARGET="db"
if [[ -n "${DB_QUERY:-}" && -n "${DB_QUERY//[[:space:]]/}" ]]; then
  make -C "$REPO_ROOT" "$DB_TARGET" DB="$DB" DB_QUERY="$DB_QUERY"
else
  make -C "$REPO_ROOT" "$DB_TARGET" DB="$DB"
fi

if [[ ! -f "${BLAST_DB}.nhr" ]]; then
  log_fatal "Banco BLAST nao encontrado em ${BLAST_DB}.nhr — Verifique se a criacao do banco de dados terminou com sucesso."
fi

# ── Etapa 2.5: QC com fastp (antes da filtragem de hospedeiro e montagem) ────
evidence_state_stage quality_control running "Executando ou avaliando o controle de qualidade do fluxo 1.1."
if [[ $SKIP_QC -eq 0 && -z "$SAMPLE_SINGLE" && -z "$CONTIGS" ]]; then
  if command -v fastp >/dev/null 2>&1; then
    log "[2.5/6] Controle de qualidade (fastp)"
    "$SCRIPT_DIR/02_qc_fastp.sh" "$SAMPLE_NAME" "$THREADS"
    # Reatribuir reads para as versões limpas
    CLEANED_R1="${REPO_ROOT}/data/cleaned/${SAMPLE_NAME}_R1.clean.fastq.gz"
    CLEANED_R2="${REPO_ROOT}/data/cleaned/${SAMPLE_NAME}_R2.clean.fastq.gz"
    if [[ -s "$CLEANED_R1" && -s "$CLEANED_R2" ]]; then
      SAMPLE_R1="$CLEANED_R1"
      SAMPLE_R2="$CLEANED_R2"
      export SAMPLE_R1 SAMPLE_R2
      echo "[INFO] Reads de entrada atualizados para versões limpas pelo fastp."
    else
      echo "[AVISO] fastp não gerou reads limpos válidos; usando reads originais."
    fi
  else
    echo "[AVISO] fastp não encontrado — etapa de QC ignorada."
    echo "        Para ativar: sudo apt install -y fastp"
    echo "        Para suprimir este aviso: use --skip-qc"
  fi
else
  log "[2.5/6] Controle de qualidade (fastp) ignorado"
fi
evidence_state_stage quality_control done "Controle de qualidade concluído ou explicitamente ignorado."

HOST_FILTER_DISABLED=0
case "${HOST_FILTER_ENABLED,,}" in
  false|0|no|nao) HOST_FILTER_DISABLED=1 ;;
esac

if [[ $SKIP_HOST_FILTER -eq 0 && $HOST_FILTER_DISABLED -eq 0 ]]; then
  log "[3/6] Filtrando hospedeiro (opcional)"
  if [[ -n "$SAMPLE_SINGLE" ]]; then
    echo "[AVISO] Filtro do hospedeiro ignora amostras single-end. Use --skip-host-filter para silenciar." >&2
  else
    if resolve_bt2_index "$HOST_INDEX_PREFIX" >/dev/null; then
      "$SCRIPT_DIR/03_filter_host.sh" "$SAMPLE_NAME"
      # Reatribuir reads para as versões com hospedeiro removido
      FILTERED_R1="${REPO_ROOT}/data/host_removed/${SAMPLE_NAME}_R1.host_removed.fastq.gz"
      FILTERED_R2="${REPO_ROOT}/data/host_removed/${SAMPLE_NAME}_R2.host_removed.fastq.gz"
      if [[ -s "$FILTERED_R1" && -s "$FILTERED_R2" ]]; then
        SAMPLE_R1="$FILTERED_R1"
        SAMPLE_R2="$FILTERED_R2"
        export SAMPLE_R1 SAMPLE_R2
        echo "[INFO] Reads de entrada atualizados para versões com hospedeiro removido."
      else
        echo "[AVISO] 03_filter_host.sh não gerou reads válidos; usando reads da etapa anterior."
      fi
    else
      echo "[AVISO] Indice completo do hospedeiro (${HOST_NAME}) nao encontrado no prefixo ${HOST_INDEX_PREFIX} (.bt2 ou .bt2l)"
      echo "        Se quiser rodar o filtro de hospedeiro, execute scripts/11_prepare_host_reference.sh"
      echo "        ou ajuste HOST_INDEX_PREFIX para um indice Bowtie2 valido."
    fi
  fi
else
  log "[3/6] Filtro do hospedeiro ignorado"
  if [[ $HOST_FILTER_DISABLED -eq 1 ]]; then
    echo "[INFO] HOST_FILTER_ENABLED=false; reads seguem sem etapa Bowtie2 de hospedeiro."
  fi
fi
evidence_state_stage assembly running "Montagem em execução; SPAdes usa k-mers automáticos por padrão."
log "[4/6] Montagem de contigs"
ASSEMBLY_CONTIGS=""
ASSEMBLY_FAILED=0
if [[ -n "$CONTIGS" ]]; then
  ASSEMBLY_CONTIGS="$(resolve_path "$CONTIGS")"
  log_info "Contigs fornecidos: $ASSEMBLY_CONTIGS (montagem ignorada)"
  METADATA_FILE="${REPO_ROOT}/data/assemblies/${SAMPLE_NAME}_assembly/assembly_metadata.env"
  mkdir -p "$(dirname "$METADATA_FILE")"
  {
    echo "ASSEMBLER_REQUESTED=\"provided\""
    echo "ASSEMBLER_USED=\"provided\""
    echo "ASSEMBLY_FALLBACK=0"
    echo "ASSEMBLY_FAILURE_TYPE=\"NONE\""
    echo "RESCUE_TRIGGERED=0"
    echo "INPUT_MODE=\"CONTIGS\""
  } > "$METADATA_FILE"
else
  set +e
  "$SCRIPT_DIR/run_assembly_router.sh"
  ASSEMBLY_EXIT_CODE=$?
  set -e
  ASSEMBLY_CONTIGS="${REPO_ROOT}/data/assemblies/${SAMPLE_NAME}_assembly/contigs.fa"

  METADATA_FILE="${REPO_ROOT}/data/assemblies/${SAMPLE_NAME}_assembly/assembly_metadata.env"
  if [[ -f "$METADATA_FILE" ]]; then
    source "$METADATA_FILE"
  fi

  if [[ ! -s "${ASSEMBLY_CONTIGS}" ]]; then
    log_warning "Montagem falhou ou nao produziu contigs viaveis."
    ASSEMBLY_FAILED=1
    mkdir -p "$(dirname "${ASSEMBLY_CONTIGS}")"
    touch "${ASSEMBLY_CONTIGS}"
  fi
fi
evidence_state_stage assembly done "Montagem concluída ou contigs fornecidos validados."

if [[ "${SHORT_FRAGMENT_MODE:-false}" == "true" ]]; then
  log "[4.5/6] Extração de fragmentos curtos"
  SHORT_INPUT="${REPO_ROOT}/data/assemblies/${SAMPLE_NAME}_assembly/all_kmers_contigs.fa"
  if [[ ! -f "$SHORT_INPUT" ]]; then
    SHORT_INPUT="${REPO_ROOT}/data/assemblies/${SAMPLE_NAME}_assembly/contigs.fa"
  fi

  if [[ -f "$SHORT_INPUT" ]]; then
    DEDUP_FLAG=""
    if [[ "${SHORT_FRAGMENT_DEDUP:-false}" == "true" ]]; then
      DEDUP_FLAG="--dedup"
    fi

    python3 "$SCRIPT_DIR/04_extract_short_fragments.py" \
      --input "$SHORT_INPUT" \
      --sample "$SAMPLE_NAME" \
      --min-len "$SHORT_FRAGMENT_MIN_LEN" \
      --max-len "$SHORT_FRAGMENT_MAX_LEN" \
      ${DEDUP_FLAG}
  else
    echo "[AVISO] Nenhum FASTA de contigs encontrado para extração de fragmentos curtos."
  fi
fi

  if [[ "${SHORT_FRAGMENT_BLAST:-false}" == "true" ]]; then
    log "[4.6/6] BLAST sensível dos fragmentos curtos"
    SF_UNIQUE="${REPO_ROOT}/results/short_fragments/${SAMPLE_NAME}_short_fragments_unique.fa"
    SF_RAW="${REPO_ROOT}/results/short_fragments/${SAMPLE_NAME}_short_fragments.fa"
    # Preferir deduplicado; cair no bruto se não existir
    if [[ -f "$SF_UNIQUE" ]]; then
      SF_INPUT="$SF_UNIQUE"
    elif [[ -f "$SF_RAW" ]]; then
      SF_INPUT="$SF_RAW"
    else
      SF_INPUT=""
    fi

    if [[ -n "$SF_INPUT" ]]; then
      "$SCRIPT_DIR/05_blast_short_fragments.sh" \
        --sample "$SAMPLE_NAME" \
        --input  "$SF_INPUT" \
        --db     "$BLAST_DB" \
        --word-size "$SHORT_FRAGMENT_WORD_SIZE" \
        --evalue    "$SHORT_FRAGMENT_EVALUE" \
        --min-pid   "$SHORT_FRAGMENT_MIN_PID" \
        --min-qcov  "$SHORT_FRAGMENT_MIN_QCOV" \
        --threads   "$THREADS"
    else
      echo "[AVISO] Nenhum FASTA de fragmentos curtos encontrado para SHORT_FRAGMENT_BLAST."
      echo "        Ative SHORT_FRAGMENT_MODE=true para gerar os fragmentos antes."
    fi
  fi

evidence_state_stage initial_blast running "Executando BLAST inicial do fluxo preservado."
log_info "[5/6] BLAST dos contigs"
OUTDIR="${REPO_ROOT}/results/blast"
mkdir -p "$OUTDIR"

# ── Lógica de Resgate de Reads (Correção 2) ──
max_contig_len=0
if [[ $ASSEMBLY_FAILED -eq 0 && -s "${ASSEMBLY_CONTIGS}" ]]; then
  max_contig_len=$(awk '/^>/ {if (seqlen > max) max = seqlen; seqlen = 0; next} {seqlen += length($0)} END {if (seqlen > max) max = seqlen; print max}' "${ASSEMBLY_CONTIGS}" 2>/dev/null || echo 0)
  max_contig_len=${max_contig_len:-0}
fi

TRIGGER_RESCUE=0
if [[ "$INPUT_MODE" == "CONTIGS" ]]; then
  if [[ ${RESCUE_MODE:-0} -eq 1 ]]; then
    echo "[AVISO] --rescue-mode ignorado para entrada de contigs sem reads." >&2
  fi
elif [[ ${RESCUE_MODE:-0} -eq 1 ]]; then
  TRIGGER_RESCUE=1
  echo "[INFO] Modo de resgate de reads ativado manualmente (--rescue-mode)."
elif [[ $ASSEMBLY_FAILED -eq 1 || $max_contig_len -lt 200 ]]; then
  TRIGGER_RESCUE=1
  echo "[INFO] Ativando resgate automático: maior contig (${max_contig_len} pb) menor que 200 pb."
fi

if [[ $TRIGGER_RESCUE -eq 1 && "$INPUT_MODE" == "READS" ]]; then
  echo "[INFO] Executando resgate de leituras..."
  RESCUE_FA="${REPO_ROOT}/data/assemblies/${SAMPLE_NAME}_assembly/rescue_reads.fa"
  mkdir -p "$(dirname "${RESCUE_FA}")"
  rm -f "$RESCUE_FA"

  cat_fastq_to_fasta() {
    local infile="$1"
    local outfile="$2"
    local mate_suffix="${3:-}"
    if [[ "$infile" =~ \.gz$ ]]; then
      gzip -dc "$infile" | awk -v mate="$mate_suffix" 'NR%4==1{
        header=$0
        sub(/^@/, "", header)
        split(header, parts, /[[:space:]]+/)
        id=parts[1]
        rest=substr(header, length(id) + 1)
        if (mate != "" && id !~ /(\/[12]|[.][12])$/) id=id "/" mate
        print ">" id rest
      } NR%4==2{print}' >> "$outfile"
    else
      awk -v mate="$mate_suffix" 'NR%4==1{
        header=$0
        sub(/^@/, "", header)
        split(header, parts, /[[:space:]]+/)
        id=parts[1]
        rest=substr(header, length(id) + 1)
        if (mate != "" && id !~ /(\/[12]|[.][12])$/) id=id "/" mate
        print ">" id rest
      } NR%4==2{print}' "$infile" >> "$outfile"
    fi
  }

  assert_unique_fasta_headers() {
    local fasta="$1"
    local total unique
    total="$(grep -c '^>' "$fasta" || true)"
    unique="$(awk '/^>/ {print}' "$fasta" | LC_ALL=C sort -u | wc -l | awk '{print $1}')"
    if [[ "$total" != "$unique" ]]; then
      log_fatal "FASTA de resgate possui headers duplicados (${unique}/${total} unicos). Abortando para evitar BLAST com IDs corrompidos."
    fi
  }

  if [[ -n "${SAMPLE_SINGLE:-}" && -s "$SAMPLE_SINGLE" ]]; then
    cat_fastq_to_fasta "$SAMPLE_SINGLE" "$RESCUE_FA"
  else
    if [[ -n "${SAMPLE_R1:-}" && -s "$SAMPLE_R1" ]]; then
      cat_fastq_to_fasta "$SAMPLE_R1" "$RESCUE_FA" "1"
    fi
    if [[ -n "${SAMPLE_R2:-}" && -s "$SAMPLE_R2" ]]; then
      cat_fastq_to_fasta "$SAMPLE_R2" "$RESCUE_FA" "2"
    fi
  fi

  if [[ -s "$RESCUE_FA" ]]; then
    assert_unique_fasta_headers "$RESCUE_FA"
    RESCUE_RAW_OUT="${REPO_ROOT}/results/blast/${SAMPLE_NAME}_read_level_vs_db_raw.tsv"
    RESCUE_FINAL_OUT="${REPO_ROOT}/results/blast/${SAMPLE_NAME}_read_level_candidates.tsv"
    echo "[INFO] Alinhando reads diretamente contra o banco viral (blastn-short)..."
    RESCUE_RAW_TMP="${RESCUE_RAW_OUT}.tmp.$$"
    blastn -task blastn-short -query "$RESCUE_FA" -db "$BLAST_DB" \
      -outfmt '6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore qlen slen' \
      -max_target_seqs 5 -evalue 1e-5 -num_threads "$THREADS" > "$RESCUE_RAW_TMP"
    mv -f "$RESCUE_RAW_TMP" "$RESCUE_RAW_OUT"

    python3 "${SCRIPT_DIR}/filter_rescue_reads.py" --blast-raw "$RESCUE_RAW_OUT" --out-tsv "$RESCUE_FINAL_OUT"
    rm -f "$RESCUE_RAW_OUT"
    # Atualiza metadados indicando que o resgate foi ativado com sucesso
    if [[ -f "${METADATA_FILE:-}" ]]; then
      sed -i 's/RESCUE_TRIGGERED=0/RESCUE_TRIGGERED=1/' "${METADATA_FILE}" 2>/dev/null || true
    fi
  else
    echo "[AVISO] Nenhuma read de entrada válida encontrada para o resgate."
  fi
fi

case "$ASSEMBLER" in
  velvet)     OUT="${OUTDIR}/${SAMPLE_NAME}_k${VELVET_K}_vs_db.tsv" ;;
  metaspades) OUT="${OUTDIR}/${SAMPLE_NAME}_metaspades_vs_db.tsv" ;;
  *)          OUT="${OUTDIR}/${SAMPLE_NAME}_spades_vs_db.tsv" ;;
esac

if [[ -s "${ASSEMBLY_CONTIGS}" ]]; then
  echo "Parâmetros BLAST de contigs: task=$BLAST_TASK word_size=$BLAST_WORD_SIZE evalue=$BLAST_EVALUE"
  BLAST_TMP="${OUT}.tmp.$$"
  blastn -task "$BLAST_TASK" -query "$ASSEMBLY_CONTIGS" -db "$BLAST_DB" \
    -outfmt '6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore qlen slen' \
    -max_target_seqs 10 -evalue "$BLAST_EVALUE" -word_size "$BLAST_WORD_SIZE" -num_threads "$THREADS" > "$BLAST_TMP"
  mv -f "$BLAST_TMP" "$OUT"
else
  echo "[INFO] Contigs vazios ou montagem ausente. Gerando arquivo BLAST vazio."
  touch "$OUT"
fi
evidence_state_stage initial_blast done "BLAST inicial concluído; resultados V2 continuam experimentais."

# Remove qualquer link anterior para evitar problemas de dangling symlinks
rm -f "${OUTDIR}/${SAMPLE_NAME}_vs_db.tsv"
# Copia o arquivo para criar o link canônico (evita problemas de symlink vazios em NTFS/WSL2)
cp -f "$OUT" "${OUTDIR}/${SAMPLE_NAME}_vs_db.tsv"
echo "Resultado salvo em: $OUT"
REPORT="${REPO_ROOT}/results/reports/${SAMPLE_NAME}_summary.md"
"$SCRIPT_DIR/95_report_minimal.sh" --sample "$SAMPLE_NAME" --contigs "$ASSEMBLY_CONTIGS" --blast "$OUT" --out "$REPORT"
evidence_state_status running done running
case "${EVIDENCE_V2,,}" in
  true|1|yes)
    EVIDENCE_ARGS=(
      --sample "$SAMPLE_NAME" --queries "$ASSEMBLY_CONTIGS"
      --config "$EVIDENCE_CONFIG" --evidence-root "${REPO_ROOT}/results/evidence"
      --library-mode "$EVIDENCE_LIBRARY_MODE" --umi-mode "$EVIDENCE_UMI_MODE" --threads "$THREADS"
    )
    EVIDENCE_ARGS+=(--role "$EVIDENCE_ROLE")
    [[ -z "$EVIDENCE_EXPECTED_TARGET" ]] || EVIDENCE_ARGS+=(--expected-target "$EVIDENCE_EXPECTED_TARGET")
    [[ -z "$EVIDENCE_RUN_ID" ]] || EVIDENCE_ARGS+=(--run-id "$EVIDENCE_RUN_ID")
    [[ -z "$EVIDENCE_BATCH_ID" ]] || EVIDENCE_ARGS+=(--batch-id "$EVIDENCE_BATCH_ID")
    if [[ -n "$EVIDENCE_COMPOSITE_DB" ]]; then
      EVIDENCE_ARGS+=(--composite-db "$EVIDENCE_COMPOSITE_DB")
      [[ -z "$EVIDENCE_SUBJECT_LABELS" ]] || EVIDENCE_ARGS+=(--subject-labels "$EVIDENCE_SUBJECT_LABELS")
      [[ -z "$EVIDENCE_PANEL_FASTA" ]] || EVIDENCE_ARGS+=(--panel-fasta "$EVIDENCE_PANEL_FASTA")
      [[ -z "$EVIDENCE_PANEL_INDEX" ]] || EVIDENCE_ARGS+=(--panel-index "$EVIDENCE_PANEL_INDEX")
      if [[ "$INPUT_MODE" == "READS" && -n "${SAMPLE_R1:-}" && -n "${SAMPLE_R2:-}" ]]; then
        EVIDENCE_ARGS+=(--r1 "$SAMPLE_R1" --r2 "$SAMPLE_R2")
      fi
    else
      EVIDENCE_ARGS+=(--blast "${BLAST_TASK}=${OUT}")
    fi
    if ! "$SCRIPT_DIR/22_run_evidence_v2.sh" "${EVIDENCE_ARGS[@]}"; then
      log_warning "Evidencia 2.0 shadow falhou; a conclusao 1.1 foi preservada."
    fi
    ;;
esac
echo "Resumo salvo em: $REPORT"
log "[6/6] Pipeline concluído"
echo "Amostra: $SAMPLE_NAME"
echo "Assembler: $ASSEMBLER"
echo "Contigs: $ASSEMBLY_CONTIGS"
echo "BLAST: $OUT"
echo "Relatório: $REPORT"
