#!/usr/bin/env bash
# =============================================================================
# 05_blast_short_fragments.sh — BLAST sensível para fragmentos curtos
# =============================================================================
# Realiza blastn-short contra banco viral para fragmentos curtos extraídos
# pela etapa SHORT_FRAGMENT_MODE. Aplica filtros de identidade e cobertura
# de query. Gera resultados em results/blast/:
#   <sample>_short_fragments_blast.tsv    (hits brutos)
#   <sample>_short_fragments_filtered.tsv (após filtros pident/qcov)
#
# Uso direto:
#   bash scripts/05_blast_short_fragments.sh \
#     --sample NOME --input FASTA --db CAMINHO_BLAST_DB \
#     [--word-size 7] [--evalue 1000] [--min-pid 70] [--min-qcov 70] \
#     [--threads 4]
#
# Ou via variáveis de ambiente exportadas pelo pipeline principal.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# Defaults (sobrescritos por variáveis de ambiente ou argumentos CLI)
# ---------------------------------------------------------------------------
SAMPLE=""
INPUT_FASTA=""
BLAST_DB_PATH=""
WORD_SIZE="${SHORT_FRAGMENT_WORD_SIZE:-7}"
EVALUE="${SHORT_FRAGMENT_EVALUE:-1000}"
MIN_PID="${SHORT_FRAGMENT_MIN_PID:-70}"
MIN_QCOV="${SHORT_FRAGMENT_MIN_QCOV:-70}"
THREADS="${THREADS:-4}"

# ---------------------------------------------------------------------------
# Parsing de argumentos
# ---------------------------------------------------------------------------
usage() {
  cat <<'USAGE'
Uso: scripts/05_blast_short_fragments.sh [opções]
Opções:
  --sample   NOME         nome da amostra (obrigatório)
  --input    FASTA        FASTA de fragmentos curtos (obrigatório)
  --db       CAMINHO      caminho base do banco BLAST (sem extensão, obrigatório)
  --word-size N           word size do blastn-short (padrão: 7)
  --evalue   VALOR        e-value do BLAST (padrão: 1000)
  --min-pid  N            identidade mínima % para filtro (padrão: 70)
  --min-qcov N            cobertura mínima de query % para filtro (padrão: 70)
  --threads  N            threads (padrão: 4)
  -h, --help              mostra esta ajuda
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sample)    SAMPLE="$2";       shift 2 ;;
    --input)     INPUT_FASTA="$2";  shift 2 ;;
    --db)        BLAST_DB_PATH="$2"; shift 2 ;;
    --word-size) WORD_SIZE="$2";    shift 2 ;;
    --evalue)    EVALUE="$2";       shift 2 ;;
    --min-pid)   MIN_PID="$2";      shift 2 ;;
    --min-qcov)  MIN_QCOV="$2";     shift 2 ;;
    --threads)   THREADS="$2";      shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *) echo "[ERRO] opção inválida: $1" >&2; usage; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# Validações
# ---------------------------------------------------------------------------
if [[ -z "$SAMPLE" ]]; then
  echo "[ERRO] --sample é obrigatório." >&2; exit 1
fi
if [[ -z "$INPUT_FASTA" ]]; then
  echo "[ERRO] --input é obrigatório." >&2; exit 1
fi
if [[ -z "$BLAST_DB_PATH" ]]; then
  echo "[ERRO] --db é obrigatório." >&2; exit 1
fi

if [[ ! -f "$INPUT_FASTA" ]]; then
  echo "[AVISO] FASTA de fragmentos curtos não encontrado: $INPUT_FASTA"
  echo "        Etapa SHORT_FRAGMENT_BLAST ignorada."
  exit 0
fi

# Verifica se o FASTA tem alguma sequência
SEQ_COUNT=$(grep -c '^>' "$INPUT_FASTA" 2>/dev/null || true)
if [[ "${SEQ_COUNT:-0}" -eq 0 ]]; then
  echo "[AVISO] FASTA vazio (sem sequências): $INPUT_FASTA"
  echo "        Etapa SHORT_FRAGMENT_BLAST ignorada."
  exit 0
fi

if [[ ! -f "${BLAST_DB_PATH}.nhr" ]]; then
  echo "[ERRO] Banco BLAST não encontrado em ${BLAST_DB_PATH}.nhr" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Diretório de saída
# ---------------------------------------------------------------------------
OUTDIR="${REPO_ROOT}/results/blast"
mkdir -p "$OUTDIR"

BLAST_RAW="${OUTDIR}/${SAMPLE}_short_fragments_blast.tsv"
BLAST_FILTERED="${OUTDIR}/${SAMPLE}_short_fragments_filtered.tsv"

echo "[05] BLAST sensível para fragmentos curtos"
echo "     Amostra : $SAMPLE"
echo "     Input   : $INPUT_FASTA ($SEQ_COUNT sequências)"
echo "     DB      : $BLAST_DB_PATH"
echo "     Params  : task=blastn-short word_size=$WORD_SIZE evalue=$EVALUE threads=$THREADS"
echo "     Filtros : pident>=${MIN_PID}% qcov>=${MIN_QCOV}%"

# ---------------------------------------------------------------------------
# Executar BLAST
# Formato de saída: qseqid sseqid pident length mismatch gapopen
#                   qstart qend sstart send evalue bitscore qlen slen
# ---------------------------------------------------------------------------
blastn \
  -task blastn-short \
  -query "$INPUT_FASTA" \
  -db "$BLAST_DB_PATH" \
  -outfmt '6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore qlen slen' \
  -max_target_seqs 10 \
  -evalue "$EVALUE" \
  -word_size "$WORD_SIZE" \
  -num_threads "$THREADS" \
  > "$BLAST_RAW"

RAW_HITS=$(wc -l < "$BLAST_RAW" 2>/dev/null || echo 0)
echo "     Hits brutos: $RAW_HITS"

# ---------------------------------------------------------------------------
# Filtrar por identidade e cobertura de query
# Cobertura de query = (qend - qstart + 1) / qlen * 100
# Colunas: 1=qseqid 2=sseqid 3=pident 4=length 5=mismatch 6=gapopen
#          7=qstart 8=qend 9=sstart 10=send 11=evalue 12=bitscore 13=qlen 14=slen
# ---------------------------------------------------------------------------

# Cabeçalho para o filtered TSV
printf 'qseqid\tsseqid\tpident\tlength\tmismatch\tgapopen\tqstart\tqend\tsstart\tsend\tevalue\tbitscore\tqlen\tslen\tqcov\n' \
  > "$BLAST_FILTERED"

awk -v min_pid="$MIN_PID" -v min_qcov="$MIN_QCOV" '
BEGIN { OFS="\t" }
{
  qseqid=$1; sseqid=$2; pident=$3; length=$4; mismatch=$5; gapopen=$6
  qstart=$7; qend=$8; sstart=$9; send=$10; evalue=$11; bitscore=$12
  qlen=$13; slen=$14

  # Calcular cobertura de query (proteção contra qlen=0)
  if (qlen > 0) {
    aln_len = (qend > qstart) ? (qend - qstart + 1) : (qstart - qend + 1)
    qcov = aln_len / qlen * 100.0
  } else {
    qcov = 0
  }

  if (pident >= min_pid && qcov >= min_qcov) {
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%.2f\n", \
      qseqid, sseqid, pident, length, mismatch, gapopen, \
      qstart, qend, sstart, send, evalue, bitscore, qlen, slen, qcov
  }
}
' "$BLAST_RAW" >> "$BLAST_FILTERED"

FILTERED_HITS=$(( $(wc -l < "$BLAST_FILTERED") - 1 ))  # descontar cabeçalho
echo "     Hits filtrados (pident>=${MIN_PID}% qcov>=${MIN_QCOV}%): $FILTERED_HITS"
echo "     Resultado bruto   : $BLAST_RAW"
echo "     Resultado filtrado: $BLAST_FILTERED"

if [[ "$FILTERED_HITS" -eq 0 ]]; then
  echo "[AVISO] Nenhum hit passou os filtros de identidade e cobertura."
  echo "        Considere relaxar SHORT_FRAGMENT_MIN_PID ou SHORT_FRAGMENT_MIN_QCOV."
fi
