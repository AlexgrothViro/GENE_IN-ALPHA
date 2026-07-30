#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="${REPO_ROOT}/config/picornavirus.env"
LEGACY_CONFIG="${REPO_ROOT}/config.env"
if [[ -f "${CONFIG_FILE}" ]]; then
  source "${CONFIG_FILE}"
elif [[ -f "${LEGACY_CONFIG}" ]]; then
  source "${LEGACY_CONFIG}"
fi

source "${SCRIPT_DIR}/lib/common.sh"

DB="${DB:-ptv}"
DB_QUERY="${DB_QUERY:-\"Teschovirus\"[Organism]}"
REF_FASTA="${REF_FASTA:-data/ref/${DB}.fa}"
BLAST_DB="${BLAST_DB:-blastdb/${DB}}"
BOWTIE2_INDEX="${BOWTIE2_INDEX:-bowtie2/${DB}}"

echo "== Smoke test do pipeline =="

log_info "Preparando DB (DB=${DB})..."
make -C "$REPO_ROOT" db DB="$DB" DB_QUERY="$DB_QUERY" REF_FASTA="$REF_FASTA" \
  BLAST_DB="$BLAST_DB" BOWTIE2_INDEX="$BOWTIE2_INDEX"

check_file "$REF_FASTA"
log_info "FASTA presente: $REF_FASTA"

missing_db=0
for ext in nhr nin nsq; do
  f="${BLAST_DB}.${ext}"
  if [[ ! -f "$f" ]]; then
    log_warn "arquivo BLAST DB faltando: $f"
    missing_db=1
  fi
done
if [[ $missing_db -ne 0 ]]; then
  log_error "Sugestão: make db DB=${DB}"
fi
log_info "Banco BLAST encontrado em prefixo: $BLAST_DB"

missing_bt2=0
for f in "${BOWTIE2_INDEX}".*.bt2*; do
  if [[ ! -e "$f" ]]; then
    missing_bt2=1
  fi
done
if [[ $missing_bt2 -ne 0 ]]; then
  log_error "índice Bowtie2 ausente para prefixo ${BOWTIE2_INDEX}. Sugestão: make db DB=${DB}"
fi
log_info "Índice Bowtie2 encontrado em prefixo: $BOWTIE2_INDEX"

echo "[Teste rápido] blastn (entrada curta via stdin, sem esperar hits)..."
printf ">q1\nACTGACTGACTG\n" | blastn -query - -db "$BLAST_DB" -outfmt 6 >/dev/null
log_info "blastn executou."

echo "=== Checagem de sintaxe dos scripts críticos ==="
SYNTAX_OK=1
for script in \
  scripts/20_run_pipeline.sh \
  scripts/01_run_spades.sh \
  scripts/01_run_metaspades.sh \
  scripts/01_run_velvet.sh \
  scripts/02_qc_fastp.sh \
  scripts/03_filter_host.sh \
  scripts/95_report_minimal.sh; do
  if [[ -f "${REPO_ROOT}/${script}" ]]; then
    if bash -n "${REPO_ROOT}/${script}" 2>&1; then
      log_info "Sintaxe OK: ${script}"
    else
      log_warn "Sintaxe FALHOU: ${script}"
      SYNTAX_OK=0
    fi
  fi
done
if [[ $SYNTAX_OK -eq 0 ]]; then
  log_error "Um ou mais scripts têm erros de sintaxe. Corrija antes de rodar o pipeline."
fi
log_info "Checagem de sintaxe concluída."

log_info "Smoke test concluído com sucesso."
