#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
TMP_DIR="$(mktemp -d /tmp/genein-router-regressions.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$TMP_DIR/bin"

python3 - "$TMP_DIR" <<'PY'
from pathlib import Path
import gzip
import sys

out = Path(sys.argv[1])
for mate in (1, 2):
    with gzip.open(out / f"R{mate}.fastq.gz", "wt", encoding="ascii") as handle:
        handle.write(f"@pair/{mate}\n{'A' * 150}\n+\n{'I' * 150}\n")
PY

cat >"$TMP_DIR/bin/spades.py" <<'FAKE_SPADES'
#!/usr/bin/env bash
set -euo pipefail
out=""
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "-o" ]]; then out="$2"; shift 2; else shift; fi
done
[[ -n "$out" ]] || exit 2
[[ "${FAKE_SPADES_RESULT:-success}" == hard ]] && exit 42
mkdir -p "$out"
if [[ "${FAKE_SPADES_RESULT:-success}" == soft ]]; then
  printf '>short\n%s\n' "$(printf 'A%.0s' {1..120})" > "$out/contigs.fasta"
else
  printf '>long\n%s\n' "$(printf 'A%.0s' {1..300})" > "$out/contigs.fasta"
fi
FAKE_SPADES
cat >"$TMP_DIR/bin/velveth" <<'FAKE_VELVETH'
#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$1"
FAKE_VELVETH
cat >"$TMP_DIR/bin/velvetg" <<'FAKE_VELVETG'
#!/usr/bin/env bash
set -euo pipefail
out="$1"
[[ "${FAKE_VELVET_RESULT:-success}" == hard ]] && exit 43
printf '>long\n%s\n' "$(printf 'C%.0s' {1..300})" > "$out/contigs.fa"
FAKE_VELVETG
chmod +x "$TMP_DIR/bin/spades.py" "$TMP_DIR/bin/velveth" "$TMP_DIR/bin/velvetg"

run_router() {
  local assembler="$1" result="$2"
  set +e
  PATH="$TMP_DIR/bin:$PATH" PIPELINE_CONFIG_LOADED=1 SAMPLE_NAME=B3ROUTER SAMPLE_ID=B3ROUTER \
    SAMPLE_R1="$TMP_DIR/R1.fastq.gz" SAMPLE_R2="$TMP_DIR/R2.fastq.gz" \
    ASSEMBLY_DIR="$TMP_DIR/$result" ASSEMBLER="$assembler" THREADS=1 \
    FAKE_SPADES_RESULT="${FAKE_SPADES_RESULT:-success}" FAKE_VELVET_RESULT="${FAKE_VELVET_RESULT:-success}" \
    bash scripts/run_assembly_router.sh >/dev/null 2>&1
  local rc=$?
  set -e
  return "$rc"
}

mkdir -p "$TMP_DIR/stale/B3ROUTER_assembly"
printf '>old\n%s\n' "$(printf 'G%.0s' {1..300})" > "$TMP_DIR/stale/B3ROUTER_assembly/contigs.fa"
FAKE_SPADES_RESULT=hard FAKE_VELVET_RESULT=hard run_router spades stale || true
[[ ! -s "$TMP_DIR/stale/B3ROUTER_assembly/contigs.fa" ]]
[[ -s "$TMP_DIR/stale/B3ROUTER_assembly/contigs.previous.fa" ]]
grep -q 'ASSEMBLY_FAILURE_TYPE="HARD"' "$TMP_DIR/stale/B3ROUTER_assembly/assembly_metadata.env"

FAKE_SPADES_RESULT=soft FAKE_VELVET_RESULT=success run_router spades soft
[[ -s "$TMP_DIR/soft/B3ROUTER_assembly/contigs.fa" ]]
grep -q 'ASSEMBLY_FAILURE_TYPE="SOFT"' "$TMP_DIR/soft/B3ROUTER_assembly/assembly_metadata.env"
grep -q '^>short$' "$TMP_DIR/soft/B3ROUTER_assembly/contigs.fa"

FAKE_SPADES_RESULT=success FAKE_VELVET_RESULT=hard run_router velvet fallback
grep -q 'ASSEMBLER_USED="spades"' "$TMP_DIR/fallback/B3ROUTER_assembly/assembly_metadata.env"
grep -q 'ASSEMBLY_FALLBACK=1' "$TMP_DIR/fallback/B3ROUTER_assembly/assembly_metadata.env"

echo "PASS router stale-output, short-contig and symmetric-fallback regressions"
