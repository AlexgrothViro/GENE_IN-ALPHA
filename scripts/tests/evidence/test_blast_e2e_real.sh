#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
for command_name in python3 blastn blastdbcmd makeblastdb; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "SKIP: $command_name is not installed"
    exit 77
  }
done

WORK="$(mktemp -d /tmp/genein-b4-e2e.XXXXXX)"
cleanup() {
  case "$WORK" in
    /tmp/genein-b4-e2e.*) rm -rf -- "$WORK" ;;
    *) echo "Refusing to remove unexpected test path: $WORK" >&2 ;;
  esac
}
trap cleanup EXIT

QUERY_SEQUENCE="ACGTCAGTGCATGACCTGACTAGCATCGTACGATGCTAGCTGACGTACGTCAGTGCATG"
HOST_SEQUENCE="ACGTCAGTGCATGACCTGACTAGCATCGTACGATGCTAGCTGACGTACGTCAGAAAAAA"
printf '>query_b4\n%s\n' "$QUERY_SEQUENCE" > "$WORK/query.fa"
printf '>target_ref\n%sTGCATCGATCGT\n>host_ref\n%sTGCATCGATCGT\n' \
  "$QUERY_SEQUENCE" "$HOST_SEQUENCE" > "$WORK/panel.fa"
printf 'sseqid\tcategory\ttaxon\tsegment\n' > "$WORK/labels.tsv"
printf 'target_ref\tTARGET_VIRUS\tsynthetic_target\tunsegmented\n' >> "$WORK/labels.tsv"
printf 'host_ref\tHOST\tsynthetic_host\tunsegmented\n' >> "$WORK/labels.tsv"

makeblastdb -in "$WORK/panel.fa" -dbtype nucl -parse_seqids \
  -out "$WORK/panel" >/dev/null

bash "$ROOT/scripts/22_run_evidence_v2.sh" \
  --sample b4synthetic \
  --queries "$WORK/query.fa" \
  --config "$ROOT/config/evidence_v2.yaml" \
  --evidence-root "$WORK/evidence" \
  --run-id b4-test-run-0001 \
  --composite-db "$WORK/panel" \
  --subject-labels "$WORK/labels.tsv" \
  --threads 1 >/dev/null

FINAL="$WORK/evidence/runs/b4-test-run-0001"
python3 - "$FINAL" <<'PY'
import csv
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
if not (root / "SUCCESS.json").is_file():
    raise SystemExit("SUCCESS.json was not promoted")
with (root / "provenance.json").open(encoding="utf-8") as handle:
    provenance = json.load(handle)
with (root / "sample_evidence.json").open(encoding="utf-8") as handle:
    evidence = json.load(handle)
with (root / "competitive_hits.tsv").open(encoding="utf-8", newline="") as handle:
    competitive = list(csv.DictReader(handle, delimiter="\t"))
if provenance["parameters"]["blast_search_complete"] != "true":
    raise SystemExit("BLAST search was not recorded as complete")
if provenance["parameters"]["blast_database_sequence_count"] != "2":
    raise SystemExit("BLAST database sequence count is incorrect")
if not competitive or competitive[0]["specificity_status"] != "TARGET_SPECIFIC":
    raise SystemExit("complete synthetic panel did not produce TARGET_SPECIFIC")
if evidence["analysis_outcome"] != "EVIDENCE_RECOVERED" or not evidence["candidates"]:
    raise SystemExit("real BLAST candidate was lost from canonical evidence")
candidate = evidence["candidates"][0]
if candidate["candidate_class"] != "LOCUS_CANDIDATE":
    raise SystemExit("real BLAST candidate has an unexpected candidate class")
if candidate["promotion_status"] != "BLOCKED" or "SUPPORT_NOT_PASSED" not in candidate["blocking_reasons"]:
    raise SystemExit("candidate without read support was promoted or lacks an explicit block")
print("PASS: real BLAST B4 end-to-end")
PY
