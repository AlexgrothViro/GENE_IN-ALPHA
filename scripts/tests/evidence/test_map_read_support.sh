#!/usr/bin/env bash
set -euo pipefail
PATH="/usr/bin:/bin:${PATH:-}"

SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/out"

cat > "$TMP/bin/bowtie2" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "-S" ]]; then out="$2"; shift 2; else shift; fi
done
printf '@HD\tVN:1.6\tSO:unknown\n' > "$out"
EOF

cat > "$TMP/bin/samtools" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cmd="$1"; shift
case "$cmd" in
  view) cat "${@: -1}" ;;
  sort)
    out=""; source=""
    while [[ $# -gt 0 ]]; do
      case "$1" in -o) out="$2"; shift 2 ;; -n) shift ;; *) source="$1"; shift ;; esac
    done
    if [[ -n "$source" && -f "$source" ]]; then cp "$source" "$out"; else cat > "$out"; fi
    ;;
  fixmate) cp "${@: -2:1}" "${@: -1}" ;;
  *) exit 99 ;;
esac
EOF

cat > "$TMP/bin/python3" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$TMP/bin/bowtie2" "$TMP/bin/samtools" "$TMP/bin/python3"
printf '>ref\nACGT\n' > "$TMP/ref.fa"
printf '@r/1\nACGT\n+\nIIII\n' > "$TMP/r1.fastq"
printf '@r/2\nACGT\n+\nIIII\n' > "$TMP/r2.fastq"

PATH="$TMP/bin:/usr/bin:/bin" "$REPO_ROOT/scripts/evidence/map_read_support.sh" \
  --sample synthetic --index "$TMP/index" --reference "$TMP/ref.fa" \
  --r1 "$TMP/r1.fastq" --r2 "$TMP/r2.fastq" --out-dir "$TMP/out" \
  --library-mode shotgun --umi-mode tag

grep -q 'UMI_DEDUP_UNAVAILABLE' "$TMP/out/read_support.tsv"
grep -q 'breadth_1x' "$TMP/out/coverage.tsv"
[[ ! -e "$TMP/out/read_support.bam" ]]
echo "[OK] ausência de UMI-tools gera estado explícito e conjunto TSV completo"
