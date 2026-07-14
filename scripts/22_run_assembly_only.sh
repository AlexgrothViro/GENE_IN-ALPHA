#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"

# ---------------------------------------------------------------------------
# Uso
# ---------------------------------------------------------------------------
usage() {
  cat <<'USAGE' >&2
Uso:
  bash scripts/22_run_assembly_only.sh --sample <id> --assembler <velvet|spades|metaspades> [--kmer <k>] [--spades-params <params>]

Opções:
  --sample        ID da amostra (obrigatório)
  --assembler     Montador a usar: velvet, spades, metaspades (padrão: velvet)
  --kmer          Tamanho do k-mer (padrão: 31)
  --spades-params Parâmetros extras para SPAdes/metaSPAdes (opcional)
  -h, --help      Exibe esta ajuda

Saídas:
  data/assemblies/<sample>_assembly/contigs.fa   — contigs padronizados
  results/assemblies/<sample>/assembly_only_summary.md — resumo simples

Nota:
  Não executa preparação de banco, BLAST, filtros ou relatórios.
USAGE
}

# ---------------------------------------------------------------------------
# Parsear argumentos
# ---------------------------------------------------------------------------
SAMPLE_NAME=""
ASSEMBLER="velvet"
KMER="31"
SPADES_PARAMS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sample)        SAMPLE_NAME="$2";    shift 2 ;;
    --assembler)     ASSEMBLER="$2";      shift 2 ;;
    --kmer)          KMER="$2";           shift 2 ;;
    --spades-params) SPADES_PARAMS="$2";  shift 2 ;;
    -h|--help)       usage; exit 0 ;;
    *) log_error "Argumento desconhecido: $1" ;;
  esac
done

if [[ -z "$SAMPLE_NAME" ]]; then
  usage
  log_error "Argumento obrigatório ausente: --sample"
fi

ASSEMBLER="${ASSEMBLER,,}"   # lowercase
THREADS="${THREADS:-4}"
RAW_DIR="${REPO_ROOT}/data/raw"
ASSEMBLY_DIR="${REPO_ROOT}/data/assemblies"
SUMMARY_DIR="${REPO_ROOT}/results/assemblies/${SAMPLE_NAME}"

# ---------------------------------------------------------------------------
# Validação do assembler
# ---------------------------------------------------------------------------
case "$ASSEMBLER" in
  velvet|spades|metaspades) ;;
  *) log_error "Assembler inválido: '$ASSEMBLER'. Use velvet, spades ou metaspades." ;;
esac

# ---------------------------------------------------------------------------
# Validação dos FASTQs de entrada
# ---------------------------------------------------------------------------
pick_reads() {
  for d in "data/host_removed" "data/cleaned" "data/raw"; do
    local r1="${REPO_ROOT}/${d}/${SAMPLE_NAME}_R1.fastq.gz"
    local r2="${REPO_ROOT}/${d}/${SAMPLE_NAME}_R2.fastq.gz"
    if [[ -s "$r1" && -s "$r2" ]]; then
      echo "$r1|$r2"
      return 0
    fi
  done
  return 1
}

if ! READS="$(pick_reads)"; then
  log_error "FASTQs não encontrados para amostra '${SAMPLE_NAME}'. Procurado em data/host_removed/, data/cleaned/ e data/raw/."
fi

RAW1="${READS%%|*}"
RAW2="${READS##*|}"
log_info "[ASSEMBLY_ONLY] Amostra: $SAMPLE_NAME"
log_info "[ASSEMBLY_ONLY] Assembler: $ASSEMBLER  k-mer: $KMER"
log_info "[ASSEMBLY_ONLY] Input R1: $RAW1"
log_info "[ASSEMBLY_ONLY] Input R2: $RAW2"

# ---------------------------------------------------------------------------
# Criar diretórios
# ---------------------------------------------------------------------------
SAFE_SAMPLE="${SAMPLE_NAME// /_}"
STD_ASM_DIR="${ASSEMBLY_DIR}/${SAMPLE_NAME}_assembly"
mkdir -p "$STD_ASM_DIR" "$SUMMARY_DIR"

# ---------------------------------------------------------------------------
# Helper: copiar contigs para o local padronizado
# ---------------------------------------------------------------------------
copy_contigs() {
  local src="$1" dst="$2"
  if [[ ! -f "$src" ]]; then
    log_error "[ASSEMBLY_ONLY] Contigs não gerados em: $src"
  fi
  rm -f "$dst"
  cp -f "$src" "$dst"
  log_info "[ASSEMBLY_ONLY] Contigs copiados: $src → $dst"
}

START_TIME="$(date '+%Y-%m-%dT%H:%M:%S')"

# ---------------------------------------------------------------------------
# Executar montagem
# ---------------------------------------------------------------------------
case "$ASSEMBLER" in
  velvet)
    R1="$RAW1" R2="$RAW2" \
      "${SCRIPT_DIR}/01_run_velvet.sh" "$SAFE_SAMPLE" "$KMER" "${VELVET_OPTS:-}"
    CONTIGS_SRC="${ASSEMBLY_DIR}/${SAFE_SAMPLE}_velvet_k${KMER}/contigs.fa"
    copy_contigs "$CONTIGS_SRC" "${STD_ASM_DIR}/contigs.fa"
    ;;

  spades)
    R1="$RAW1" R2="$RAW2" \
      "${SCRIPT_DIR}/01_run_spades.sh" "$SAFE_SAMPLE" "$THREADS" "$SPADES_PARAMS" "spades"
    CONTIGS_SRC="${ASSEMBLY_DIR}/${SAFE_SAMPLE}_spades/contigs.fasta"
    copy_contigs "$CONTIGS_SRC" "${STD_ASM_DIR}/contigs.fa"
    ;;

  metaspades)
    R1="$RAW1" R2="$RAW2" \
      "${SCRIPT_DIR}/01_run_metaspades.sh" "$SAFE_SAMPLE" "$THREADS" "$SPADES_PARAMS"
    CONTIGS_SRC="${ASSEMBLY_DIR}/${SAFE_SAMPLE}_metaspades/contigs.fasta"
    copy_contigs "$CONTIGS_SRC" "${STD_ASM_DIR}/contigs.fa"
    ;;
esac

FINAL_CONTIGS="${STD_ASM_DIR}/contigs.fa"
if [[ ! -s "$FINAL_CONTIGS" ]]; then
  log_error "[ASSEMBLY_ONLY] Arquivo de contigs vazio ou ausente: $FINAL_CONTIGS"
fi

# ---------------------------------------------------------------------------
# Gerar resumo simples
# ---------------------------------------------------------------------------
N_CONTIGS=0
MAX_LEN=0
if command -v python3 &>/dev/null; then
  SUMMARY_JSON="$(python3 - <<'PYEOF' "$FINAL_CONTIGS"
import sys
fasta = sys.argv[1]
n, maxlen = 0, 0
with open(fasta) as f:
    cur = 0
    for line in f:
        line = line.rstrip()
        if line.startswith(">"):
            if cur > maxlen:
                maxlen = cur
            n += 1
            cur = 0
        else:
            cur += len(line)
    if cur > maxlen:
        maxlen = cur
print(f"{n}:{maxlen}")
PYEOF
)"
  N_CONTIGS="${SUMMARY_JSON%%:*}"
  MAX_LEN="${SUMMARY_JSON##*:}"
fi

SUMMARY_FILE="${SUMMARY_DIR}/assembly_only_summary.md"
cat >"$SUMMARY_FILE" <<SUMMARY_EOF
# Resumo de Montagem — ${SAMPLE_NAME}

| Campo            | Valor                                        |
|------------------|----------------------------------------------|
| Amostra          | ${SAMPLE_NAME}                               |
| Assembler        | ${ASSEMBLER}                                 |
| k-mer            | ${KMER}                                      |
| Threads          | ${THREADS}                                   |
| Data/hora        | ${START_TIME}                                |
| Contigs gerados  | ${N_CONTIGS}                                 |
| Maior contig (bp)| ${MAX_LEN}                                   |
| Arquivo contigs  | data/assemblies/${SAMPLE_NAME}_assembly/contigs.fa |

> Este resumo foi gerado pela ação **Montar contigs apenas** do Gene-In.
> Nenhum banco viral, BLAST ou validação foi executado nesta etapa.
SUMMARY_EOF

log_info "[ASSEMBLY_ONLY] Resumo salvo em: $SUMMARY_FILE"

# ---------------------------------------------------------------------------
# Resultado final
# ---------------------------------------------------------------------------
log_info "[ASSEMBLY_ONLY] ==========================="
log_info "[ASSEMBLY_ONLY] Montagem concluída com sucesso."
log_info "[ASSEMBLY_ONLY] Contigs: ${FINAL_CONTIGS}"
log_info "[ASSEMBLY_ONLY] Contigs gerados: ${N_CONTIGS}"
log_info "[ASSEMBLY_ONLY] Maior contig: ${MAX_LEN} bp"
log_info "[ASSEMBLY_ONLY] Resumo: ${SUMMARY_FILE}"
log_info "[ASSEMBLY_ONLY] ==========================="
