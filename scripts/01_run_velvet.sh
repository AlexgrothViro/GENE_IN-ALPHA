#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
  cat <<'USAGE' >&2
Uso:
  bash scripts/01_run_velvet.sh SAMPLE [KMER]

Regras:
- SAMPLE passado por argumento SEMPRE vence.
- Procura reads em: data/host_removed -> data/cleaned -> data/raw
USAGE
}

SAMPLE_NAME="${1:-}"
SAMPLE_NAME="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" sample "$SAMPLE_NAME")"
KMER="${2:-${VELVET_K:-31}}"
THREADS="${THREADS:-4}"
MIN_CONTIG_LEN="${MIN_CONTIG_LEN:-50}"
VELVET_EXTRA_OPTS="${3:-}"

[[ -z "$SAMPLE_NAME" ]] && usage && exit 1

pick_reads_paired() {
  local s="$1"
  for d in "data/host_removed" "data/cleaned" "data/raw"; do
    local r1="${REPO_ROOT}/${d}/${s}_R1.fastq.gz"
    local r2="${REPO_ROOT}/${d}/${s}_R2.fastq.gz"
    if [[ -s "$r1" && -s "$r2" ]]; then
      echo "$r1|$r2|$d"
      return 0
    fi
  done
  return 1
}

pick_reads_single() {
  local s="$1"
  for d in "data/host_removed" "data/cleaned" "data/raw"; do
    local se="${REPO_ROOT}/${d}/${s}.fastq.gz"
    if [[ -s "$se" ]]; then
      echo "$se|$d"
      return 0
    fi
  done
  return 1
}

SINGLE_INPUT="${SAMPLE_SINGLE:-}"
R1_INPUT="${R1:-}"
R2_INPUT="${R2:-}"

if [[ -n "$SINGLE_INPUT" ]]; then
  SINGLE_PATH="$SINGLE_INPUT"
  [[ "$SINGLE_PATH" = /* ]] || SINGLE_PATH="${REPO_ROOT}/${SINGLE_PATH}"
  [[ -s "$SINGLE_PATH" ]] || { echo "[ERRO] SAMPLE_SINGLE não encontrado: $SINGLE_PATH" >&2; exit 1; }
  MODE="single"
elif [[ -n "$R1_INPUT" && -n "$R2_INPUT" ]]; then
  R1="$R1_INPUT"; R2="$R2_INPUT"
  [[ "$R1" = /* ]] || R1="${REPO_ROOT}/${R1}"
  [[ "$R2" = /* ]] || R2="${REPO_ROOT}/${R2}"
  [[ -s "$R1" && -s "$R2" ]] || { echo "[ERRO] R1/R2 informados não encontrados." >&2; exit 1; }
  MODE="paired"
elif picked="$(pick_reads_paired "$SAMPLE_NAME")"; then
  R1="${picked%%|*}"; rest="${picked#*|}"
  R2="${rest%%|*}"; SRC_DIR="${rest#*|}"
  MODE="paired"
elif picked_single="$(pick_reads_single "$SAMPLE_NAME")"; then
  SINGLE_PATH="${picked_single%%|*}"; SRC_DIR="${picked_single#*|}"
  MODE="single"
else
  echo "[ERRO] FASTQs não encontrados para SAMPLE='$SAMPLE_NAME'." >&2
  echo "       Procurei em: data/host_removed, data/cleaned, data/raw" >&2
  echo "[DICA] Amostras em data/raw:" >&2
  ls -1 "${REPO_ROOT}/data/raw"/*_R1.fastq.gz 2>/dev/null | sed -E 's#.*/##; s/_R1\.fastq\.gz$//' | sort -u | sed 's/^/  - /' >&2 || true
  exit 1
fi

OUTDIR="${REPO_ROOT}/data/assemblies/${SAMPLE_NAME}_velvet_k${KMER}"
mkdir -p "$OUTDIR"

echo "[INFO] Velvet: SAMPLE=$SAMPLE_NAME KMER=$KMER"
echo "[INFO] Reads: ${SRC_DIR:-custom}"
echo "[INFO] Out: $OUTDIR"

if [[ "$MODE" == "single" ]]; then
  echo "[INFO] Modo single-end: $SINGLE_PATH"
  velveth "$OUTDIR" "$KMER" -short -fastq.gz "$SINGLE_PATH"
else
  velveth "$OUTDIR" "$KMER" -shortPaired -fastq.gz -separate "$R1" "$R2"
fi
READ_TRKG="${READ_TRKG:-yes}"

if velvetg "$OUTDIR" -exp_cov auto -cov_cutoff auto -read_trkg "$READ_TRKG" -min_contig_lgth "$MIN_CONTIG_LEN" ${VELVET_EXTRA_OPTS:-}; then
  :
else
  exit_code=$?
  if [[ $exit_code -eq 139 ]]; then
    echo "[ERRO] Velvet falhou com segmentation fault (exit code 139)." >&2
    echo "       Causas prováveis:" >&2
    echo "       - Limitação estrutural ou bug do Velvet para esse dataset específico." >&2
    echo "       - Lentidão extrema ou erros ao rodar dentro do diretório do Windows (/mnt/c) via WSL." >&2
    echo "       - Falta de memória RAM para a quantidade de reads." >&2
    echo "       - Incompatibilidade com os parâmetros de montagem ou tamanho de k-mer." >&2
    echo "" >&2
    echo "[DICA] Recomendamos trocar o montador:" >&2
    echo "       make pipeline SAMPLE=$SAMPLE_NAME ASSEMBLER=spades" >&2
    echo "       make pipeline SAMPLE=$SAMPLE_NAME ASSEMBLER=metaspades" >&2
  else
    echo "[ERRO] velvetg falhou com exit code $exit_code." >&2
  fi
  exit $exit_code
fi
[[ -s "$OUTDIR/contigs.fa" ]] || { echo "[ERRO] Velvet não gerou contigs.fa em $OUTDIR" >&2; exit 1; }
echo "[OK] Contigs: $OUTDIR/contigs.fa"
