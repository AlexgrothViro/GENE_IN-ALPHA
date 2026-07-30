#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SAMPLE=""; INDEX=""; REFERENCE=""; R1=""; R2=""; OUTDIR=""; LOCI=""
LIBRARY_MODE="unknown"; UMI_MODE="none"; UMI_SEED=1; MIN_MAPQ=10; MIN_BASEQ=20; WINDOW_BP=100; THREADS=4
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sample) SAMPLE="$2"; shift 2 ;;
    --index) INDEX="$2"; shift 2 ;;
    --reference) REFERENCE="$2"; shift 2 ;;
    --r1) R1="$2"; shift 2 ;;
    --r2) R2="$2"; shift 2 ;;
    --out-dir) OUTDIR="$2"; shift 2 ;;
    --loci) LOCI="$2"; shift 2 ;;
    --library-mode) LIBRARY_MODE="$2"; shift 2 ;;
    --umi-mode) UMI_MODE="$2"; shift 2 ;;
    --umi-seed) UMI_SEED="$2"; shift 2 ;;
    --minimum-mapq) MIN_MAPQ="$2"; shift 2 ;;
    --minimum-base-quality) MIN_BASEQ="$2"; shift 2 ;;
    --window-bp) WINDOW_BP="$2"; shift 2 ;;
    --threads) THREADS="$2"; shift 2 ;;
    *) echo "[FATAL] invalid map_read_support option: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$SAMPLE" && -n "$INDEX" && -n "$REFERENCE" && -n "$R1" && -n "$R2" && -n "$OUTDIR" ]] || {
  echo "[FATAL] --sample --index --reference --r1 --r2 --out-dir are required" >&2; exit 2;
}
for cmd in bowtie2 samtools python3; do command -v "$cmd" >/dev/null 2>&1 || { echo "[FATAL] missing $cmd" >&2; exit 3; }; done
mkdir -p "$OUTDIR"
TMPDIR_RUN="$(mktemp -d "${OUTDIR}/.mapping.XXXXXX")"
trap 'rm -rf "$TMPDIR_RUN"' EXIT

bowtie2 --very-sensitive-local -x "$INDEX" -1 "$R1" -2 "$R2" -p "$THREADS" -S "$TMPDIR_RUN/raw.sam" 2> "$OUTDIR/bowtie2.log"
samtools view -b -F 2304 -q "$MIN_MAPQ" "$TMPDIR_RUN/raw.sam" | samtools sort -n -o "$TMPDIR_RUN/name.bam"
samtools fixmate -m "$TMPDIR_RUN/name.bam" "$TMPDIR_RUN/fixmate.bam"
samtools sort -o "$TMPDIR_RUN/coordinate.bam" "$TMPDIR_RUN/fixmate.bam"

if [[ "$UMI_MODE" == "none" ]]; then
  # Sem UMI não há identidade molecular para remoção segura. A deduplicação fica
  # desativada por padrão em todas as bibliotecas e seu uso futuro exigirá análise
  # de sensibilidade explicitamente versionada.
  cp -f "$TMPDIR_RUN/coordinate.bam" "$TMPDIR_RUN/deduplicated.bam"
else
  if ! command -v umi_tools >/dev/null 2>&1; then
    printf 'sample_id\treference_id\tcategory\tlocus_id\torientation\tquery_ids\tlibrary_mode\tumi_mode\tsupport_status\tunique_templates\tdistinct_starts\tproper_pair_templates\tdiscordant_templates\tminimum_mapq\n' > "$OUTDIR/read_support.tsv.tmp"
    if [[ -n "$LOCI" && -s "$LOCI" ]]; then
      awk -F '\t' -v sample="$SAMPLE" -v library="$LIBRARY_MODE" -v umi="$UMI_MODE" -v mapq="$MIN_MAPQ" '
        BEGIN { OFS="\t" }
        NR == 1 {
          for (i = 1; i <= NF; i++) column[$i] = i
          next
        }
        {
          print sample, $column["sseqid"], $column["category"], $column["locus_id"],
                $column["orientation"], $column["query_ids"], library, umi,
                "UMI_DEDUP_UNAVAILABLE", 0, 0, 0, 0, mapq
        }
      ' "$LOCI" >> "$OUTDIR/read_support.tsv.tmp"
    else
      printf '%s\t\t\t\t\t\t%s\t%s\tUMI_DEDUP_UNAVAILABLE\t0\t0\t0\t0\t%s\n' \
        "$SAMPLE" "$LIBRARY_MODE" "$UMI_MODE" "$MIN_MAPQ" >> "$OUTDIR/read_support.tsv.tmp"
    fi
    mv -f "$OUTDIR/read_support.tsv.tmp" "$OUTDIR/read_support.tsv"
    printf 'reference_id\tcategory\tlocus_id\torientation\tquery_ids\treference_length\tlocus_length\tcovered_bases_1x\tcovered_bases_3x\tbreadth_1x\tbreadth_3x\tmean_depth_locus\tmedian_depth_covered\tmin_depth_covered\tmax_window_depth_fraction\tconcentration_window_bp\tminimum_mapq\tminimum_base_quality\n' > "$OUTDIR/coverage.tsv.tmp"
    mv -f "$OUTDIR/coverage.tsv.tmp" "$OUTDIR/coverage.tsv"
    exit 0
  fi
  UMI_ARGS=(--paired)
  if [[ "$UMI_MODE" == "read_name" ]]; then
    UMI_ARGS+=(--extract-umi-method=read_id)
  else
    UMI_ARGS+=(--extract-umi-method=tag --umi-tag=RX)
  fi
  umi_tools dedup "${UMI_ARGS[@]}" --random-seed "$UMI_SEED" \
    --stdin "$TMPDIR_RUN/coordinate.bam" --stdout "$TMPDIR_RUN/deduplicated.bam"
fi

samtools index "$TMPDIR_RUN/deduplicated.bam"
samtools quickcheck -v "$TMPDIR_RUN/deduplicated.bam"
samtools view -h "$TMPDIR_RUN/deduplicated.bam" > "$TMPDIR_RUN/deduplicated.sam"
LOCI_ARGS=()
[[ -n "$LOCI" ]] && LOCI_ARGS=(--loci "$LOCI")
python3 "$SCRIPT_DIR/summarize_read_support.py" --sam "$TMPDIR_RUN/deduplicated.sam" --sample "$SAMPLE" \
  --library-mode "$LIBRARY_MODE" --umi-mode "$UMI_MODE" --minimum-mapq "$MIN_MAPQ" \
  "${LOCI_ARGS[@]}" --out "$OUTDIR/read_support.tsv"
samtools depth -aa -q "$MIN_BASEQ" -Q "$MIN_MAPQ" "$TMPDIR_RUN/deduplicated.bam" > "$TMPDIR_RUN/depth.tsv"
python3 "$SCRIPT_DIR/summarize_coverage.py" --depth "$TMPDIR_RUN/depth.tsv" --reference-fasta "$REFERENCE" \
  "${LOCI_ARGS[@]}" --window-bp "$WINDOW_BP" --minimum-mapq "$MIN_MAPQ" \
  --minimum-base-quality "$MIN_BASEQ" --out "$OUTDIR/coverage.tsv"
cp -f "$TMPDIR_RUN/deduplicated.bam" "$OUTDIR/read_support.bam.tmp"
cp -f "$TMPDIR_RUN/deduplicated.bam.bai" "$OUTDIR/read_support.bam.bai.tmp"
mv -f "$OUTDIR/read_support.bam.tmp" "$OUTDIR/read_support.bam"
mv -f "$OUTDIR/read_support.bam.bai.tmp" "$OUTDIR/read_support.bam.bai"
