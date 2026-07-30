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

SAMPLE="${1:?SAMPLE obrigatório}"
KMER="${2:?KMER obrigatório}"

SAMPLE="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" sample "$SAMPLE")"
DB="$(resolve_path "${BLAST_DB:-blastdb/${DB}}")"
THREADS="${BLAST_THREADS:-4}"

CONTIGS="$(resolve_path "data/assemblies/${SAMPLE}_velvet_k${KMER}/contigs.fa")"
OUTDIR="$(resolve_path "results/blast")"
OUT="${OUTDIR}/${SAMPLE}_k${KMER}_vs_db.tsv"

mkdir -p "$OUTDIR"

check_file "$CONTIGS"
check_blast_database "$DB"

log_info "Rodando blastn contra $DB..."
BLAST_TASK="${BLAST_TASK:-blastn}"
BLAST_WORD_SIZE="${BLAST_WORD_SIZE:-11}"
BLAST_EVALUE="${BLAST_EVALUE:-1e-5}"

log_info "Parâmetros BLAST: task=$BLAST_TASK word_size=$BLAST_WORD_SIZE evalue=$BLAST_EVALUE"

OUT_TMP="${OUT}.tmp.$$"
trap 'rm -f "$OUT_TMP"' EXIT
blastn -task "$BLAST_TASK" -query "$CONTIGS" -db "$DB" \
  -outfmt '6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore qlen slen' \
  -max_target_seqs 10 -evalue "$BLAST_EVALUE" -word_size "$BLAST_WORD_SIZE" -num_threads "$THREADS" > "$OUT_TMP"
mv -f "$OUT_TMP" "$OUT"

# compat legado (alguns scripts antigos podem ler o nome sem kmer)
# Remove qualquer link anterior para evitar problemas de dangling symlinks
rm -f "${OUTDIR}/${SAMPLE}_vs_db.tsv"
# Copia o arquivo diretamente para evitar problemas de symlink vazios em NTFS/WSL2
cp -f "$OUT" "${OUTDIR}/${SAMPLE}_vs_db.tsv"

log_info "Resultado salvo em: $OUT"
