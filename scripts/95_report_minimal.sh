#!/usr/bin/env bash
set -euo pipefail

SAMPLE=""; CONTIGS=""; BLAST=""; OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sample) SAMPLE="${2:-}"; shift 2 ;;
    --contigs) CONTIGS="${2:-}"; shift 2 ;;
    --blast) BLAST="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    *) echo "[ERRO] arg inválido: $1" >&2; exit 1 ;;
  esac
done
[[ -z "$SAMPLE" || -z "$CONTIGS" || -z "$BLAST" || -z "$OUT" ]] && { echo "[ERRO] uso: --sample --contigs --blast --out" >&2; exit 1; }

METADATA_FILE="$(dirname "$CONTIGS")/assembly_metadata.env"
if [[ -f "$METADATA_FILE" ]]; then
  source "$METADATA_FILE"
fi

mkdir -p "$(dirname "$OUT")"
OUT_TMP="${OUT}.tmp.$$"
trap 'rm -f "$OUT_TMP"' EXIT
contig_count=0
max_len=0
if [[ -s "$CONTIGS" ]]; then
  contig_count="$(grep -c '^>' "$CONTIGS" 2>/dev/null || echo 0)"
  max_len="$(awk '
    /^>/ { if (seqlen>max) max=seqlen; seqlen=0; next }
    { seqlen += length($0) }
    END { if (seqlen>max) max=seqlen; print (max+0) }
  ' "$CONTIGS" 2>/dev/null || echo 0)"
fi
hit_count=0
if [[ -s "$BLAST" ]]; then
  hit_count="$(wc -l < "$BLAST" 2>/dev/null || echo 0)"
fi

BLAST_OUTDIR="$(dirname "$OUT")/../blast"
mkdir -p "$BLAST_OUTDIR"
ADJ_TSV="${BLAST_OUTDIR}/${SAMPLE}_adj_identity.tsv"
python3 "$(dirname "$0")/adj_identity.py" --blast "$BLAST" --contigs "$CONTIGS" --out "$ADJ_TSV"
LABELED_TSV="${BLAST_OUTDIR}/${SAMPLE}_labeled_hits.tsv"
python3 "$(dirname "$0")/label_hits.py" "$ADJ_TSV" --out "$LABELED_TSV" > /dev/null
LEGACY_EVIDENCE_JSON="${BLAST_OUTDIR}/${SAMPLE}_legacy_evidence.json"
ADAPTATION_RUN_ID="${EVIDENCE_RUN_ID:-}"
if [[ -z "$ADAPTATION_RUN_ID" ]]; then
  ADAPTATION_RUN_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
fi
ADAPTATION_ID="report-1.1-${SAMPLE}-${ADAPTATION_RUN_ID}"
python3 "$(dirname "$0")/evidence/adapt_legacy_evidence.py" --sample "$SAMPLE" --labeled "$LABELED_TSV" \
  --run-id "legacy-${SAMPLE}-${ADAPTATION_RUN_ID}" --adaptation-id "$ADAPTATION_ID" --out "$LEGACY_EVIDENCE_JSON"
python3 "$(dirname "$0")/evidence/export_evidence.py" --json "$LEGACY_EVIDENCE_JSON" \
  --out "${BLAST_OUTDIR}/${SAMPLE}_legacy_evidence_report.md"
top_adj_summary=""
if [[ -s "$ADJ_TSV" ]]; then
  top_adj_summary="$(python3 "$(dirname "$0")/select_best_adjusted_hit.py" "$ADJ_TSV")"
fi

# ---------------------------------------------------------------------------
# Exportação FASTA dos contigs com hit viral
# ---------------------------------------------------------------------------
HIT_CONTIGS_FA="${BLAST_OUTDIR}/${SAMPLE}_hit_contigs.fa"
HIT_CONTIGS_SUMMARY="${BLAST_OUTDIR}/${SAMPLE}_hit_contigs_summary.tsv"

# Captura a saída do script para extrair as variáveis de estatística
# O script nunca retorna código != 0 em caso de "sem hits" — apenas cria arquivos vazios
export_output=""
export_output="$(python3 "$(dirname "$0")/06_export_hit_contigs.py" \
  --labeled  "$LABELED_TSV" \
  --contigs  "$CONTIGS" \
  --sample   "$SAMPLE" \
  --out-dir  "$BLAST_OUTDIR" \
  --classes  ALL \
  --min-len  0 2>/dev/null)" || true

# Parse das variáveis de estatística emitidas pelo script Python
_ec_count=0;   _ec_strong=0; _ec_moderate=0
_ec_strong=0;  _ec_strong_div=0; _ec_moderate=0
_ec_weak=0;    _ec_review=0;     _ec_refs=0
_ec_min=0;     _ec_median=0;     _ec_max=0; _ec_n50=0
_ec_missing=0

while IFS= read -r line; do
  case "$line" in
    EXPORT_HIT_CONTIGS_COUNT=*)            _ec_count="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_STRONG=*)           _ec_strong="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_STRONG_DIVERGENT=*) _ec_strong_div="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_MODERATE=*)         _ec_moderate="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_WEAK=*)             _ec_weak="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_REVIEW=*)           _ec_review="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_REFS=*)             _ec_refs="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_MIN=*)              _ec_min="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_MEDIAN=*)           _ec_median="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_MAX=*)              _ec_max="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_N50=*)              _ec_n50="${line#*=}" ;;
    EXPORT_HIT_CONTIGS_MISSING_IN_FASTA=*) _ec_missing="${line#*=}" ;;
  esac
done <<< "$export_output"

# ---------------------------------------------------------------------------
# Geração do relatório Markdown
# ---------------------------------------------------------------------------
{
  echo "# Summary – $SAMPLE"
  echo
  echo "> **Triagem E1 — compatibilidade:** classes históricas abaixo são preservadas somente como \`legacy_label\`."
  echo "> Elas não afirmam presença, ausência, identidade, confirmação, variante ou linhagem viral."
  echo

  # Identificação de controle negativo/background
  is_negative=0
  if [[ -n "${grupo_final:-}" ]]; then
    gf_lower=$(echo "$grupo_final" | tr '[:upper:]' '[:lower:]')
    if [[ "$gf_lower" == *"negativo"* || "$gf_lower" == *"background"* || "$gf_lower" == *"mock"* ]]; then
      is_negative=1
    fi
  elif [[ -n "${GRUPO_FINAL:-}" ]]; then
    gf_lower=$(echo "$GRUPO_FINAL" | tr '[:upper:]' '[:lower:]')
    if [[ "$gf_lower" == *"negativo"* || "$gf_lower" == *"background"* || "$gf_lower" == *"mock"* ]]; then
      is_negative=1
    fi
  fi
  sample_lower=$(echo "$SAMPLE" | tr '[:upper:]' '[:lower:]')
  if [[ "$sample_lower" == *"neg_"* || "$sample_lower" == *"mock"* || "$sample_lower" == *"nohits"* || "$sample_lower" == *"control"* || "$sample_lower" == *"background"* ]]; then
    is_negative=1
  fi

  if [[ $is_negative -eq 1 ]]; then
    n_candidates=0
    n_candidates=$((_ec_strong + _ec_strong_div + _ec_moderate))
    if [[ $n_candidates -gt 0 ]]; then
      echo "> [!WARNING]"
      echo "> **ALERTA:** amostra identificada como controle negativo/background produziu ${n_candidates} candidato(s) MODERATE/STRONG/STRONG_DIVERGENT com o montador ${ASSEMBLER_USED:-desconhecido}. Revisão manual obrigatória antes de qualquer interpretação."
      echo
    fi
  fi

  echo "## Assembly"
  echo "- Montador requisitado: ${ASSEMBLER_REQUESTED:-desconhecido}"
  echo "- Montador utilizado: ${ASSEMBLER_USED:-desconhecido}"
  echo "- Fallback ativado: $([[ ${ASSEMBLY_FALLBACK:-0} -eq 1 ]] && echo "Sim" || echo "Não")"
  echo "- Tipo de falha de montagem: ${ASSEMBLY_FAILURE_TYPE:-Nenhuma}"
  echo "- Contigs gerados: ${contig_count}"
  echo "- Maior contig (bp): ${max_len}"
  echo "- Resgate de leituras (Read-level) acionado: $([[ ${RESCUE_TRIGGERED:-0} -eq 1 ]] && echo "Sim" || echo "Não")"
  echo
  echo "## BLAST (vs banco viral selecionado)"
  echo "- Hits (linhas TSV): ${hit_count}"
  if [[ -n "$top_adj_summary" ]]; then
    echo "- Melhor identidade ajustada: ${top_adj_summary}"
  fi
  echo
  echo "### Top 5 hits (por adj_identity)"
  if [[ -s "$BLAST" ]]; then
    echo
    echo "|qseqid|sseqid|pident|length|qlen|aln_cov|adj_identity|evidence_class|risk_note|evalue|bitscore|"
    echo "|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|"
    # Replace | inside sseqid field with / to avoid breaking Markdown table columns
    mapfile -t _top5 < <(tail -n +2 "$LABELED_TSV" | sort -t$'\t' -k9,9gr)
    if [[ ${#_top5[@]} -gt 0 ]]; then
      printf '%s\n' "${_top5[@]:0:5}" | awk -F'\t' '{
        gsub(/\|/, "/", $2)
        printf "|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n",$1,$2,$3,$4,$7,$8,$9,$10,$11,$5,$6
      }'
    fi
  else
    echo "_Sem hits (arquivo BLAST vazio)_"
  fi
  echo

  # -----------------------------------------------------------------------
  # Nova seção: Contigs com Hit Viral (FASTA exportado)
  # -----------------------------------------------------------------------
  echo "## Contigs com Hit Viral – Exportação FASTA"
  echo
  if [[ "${_ec_count}" -gt 0 ]] 2>/dev/null; then
    echo "- **Arquivo FASTA:** \`${HIT_CONTIGS_FA}\`"
    echo "- **Summary TSV:** \`${HIT_CONTIGS_SUMMARY}\`"
    echo "- **Total de contigs exportados:** ${_ec_count}"
    echo "- **Referências virais distintas atingidas:** ${_ec_refs}"
    echo
    echo "### Distribuição por legacy_label (teto público E1)"
    echo
    echo "| Classe | Contigs |"
    echo "|---|---:|"
    [[ "${_ec_strong}"       -gt 0 ]] 2>/dev/null && echo "| STRONG           | ${_ec_strong}   |"
    [[ "${_ec_strong_div}"   -gt 0 ]] 2>/dev/null && echo "| STRONG_DIVERGENT | ${_ec_strong_div} |"
    [[ "${_ec_moderate}"     -gt 0 ]] 2>/dev/null && echo "| MODERATE         | ${_ec_moderate} |"
    [[ "${_ec_weak}"         -gt 0 ]] 2>/dev/null && echo "| WEAK_RECOVERABLE | ${_ec_weak}     |"
    [[ "${_ec_review}"       -gt 0 ]] 2>/dev/null && echo "| REVIEW           | ${_ec_review}   |"
    echo
    echo "### Tamanho dos contigs exportados (bp)"
    echo
    echo "| Mínimo | Mediana | Máximo | N50 |"
    echo "|---:|---:|---:|---:|"
    echo "| ${_ec_min} | ${_ec_median} | ${_ec_max} | ${_ec_n50} |"
    if [[ "${_ec_missing}" -gt 0 ]] 2>/dev/null; then
      echo
      echo "> **Atenção:** ${_ec_missing} contig(s) presentes no labeled_hits.tsv não foram"
      echo "> localizados no contigs.fa e foram omitidos do FASTA. Verifique se o assembly"
      echo "> e o resultado BLAST correspondem à mesma execução."
    fi
    echo
    echo "> **Nota interpretativa:** O arquivo FASTA acima contém contigs candidatos"
    echo "> com similaridade detectada ao banco viral selecionado. Esses resultados"
    echo "> refletem correspondências computacionais e **não representam confirmação"
    echo "> diagnóstica isolada**. A classificação final deve considerar o contexto"
    echo "> epidemiológico, a qualidade da montagem e validação experimental complementar."
  else
    echo "_Nenhum contig com hit viral foi exportado para esta amostra._"
    if [[ -f "$HIT_CONTIGS_FA" ]]; then
      echo
      echo "_(Arquivo FASTA vazio gerado em: \`${HIT_CONTIGS_FA}\`)_"
    fi
  fi
  RESCUE_TSV="${BLAST_OUTDIR}/${SAMPLE}_read_level_candidates.tsv"
  if [[ -s "$RESCUE_TSV" ]]; then
    n_reads=$(tail -n +2 "$RESCUE_TSV" | wc -l | tr -d ' ')
    if [[ $n_reads -gt 0 ]]; then
      echo "## Resgate de Leituras (Read-level Signal)"
      echo
      echo "> [!NOTE]"
      echo "> Sinais de homologia viral foram detectados diretamente a nível de reads individuais de sequenciamento."
      echo "> Esta evidência é **mais fraca que qualquer classe baseada em contig** (não há confirmação estrutural/de contiguidade),"
      echo "> e registra somente candidatos de homologia em triagem E1, sem afirmar presença física do alvo."
      echo
      echo "- **Total de reads resgatadas:** ${n_reads}"
      echo "- **Arquivo de candidatos:** \`${RESCUE_TSV}\`"
      echo
      echo "### Top 5 reads candidatas resgatadas (ordenadas por bitscore)"
      echo
      echo "|qseqid|sseqid|pident|length|qlen|aln_cov|adj_identity|evidence_class|evalue|bitscore|"
      echo "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|"
      mapfile -t _rescue_top5 < <(tail -n +2 "$RESCUE_TSV" | sort -t$'\t' -k6,6nr)
      if [[ ${#_rescue_top5[@]} -gt 0 ]]; then
        printf '%s\n' "${_rescue_top5[@]:0:5}" | awk -F'\t' '{
          gsub(/\|/, "/", $2)
          printf "|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\n",$1,$2,$3,$4,$7,$8,$9,$10,$5,$6
        }'
      fi
      echo
    fi
  fi

  echo "_Arquivos intermediários: \`${ADJ_TSV}\`, \`${LABELED_TSV}\`_"
} > "$OUT_TMP"
mv -f "$OUT_TMP" "$OUT"

echo "[OK] Relatório: $OUT"
echo "[OK] TSVs intermediários: $ADJ_TSV | $LABELED_TSV"
echo "[OK] FASTA de hits: $HIT_CONTIGS_FA (${_ec_count} contig(s))"
