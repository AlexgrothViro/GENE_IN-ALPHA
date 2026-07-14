#!/usr/bin/env bash
# =============================================================================
# 01_run_metaspades.sh — Montagem metagenômica com metaSPAdes
# =============================================================================
# Objetivo: Recuperação de fragmentos genômicos virais curtos/ultra-curtos
# em dados metagenômicos. Usa spades.py --meta com k-mers otimizados para
# fragmentos pequenos (foco do mestrado: detecção de vírus em amostras
# metagenômicas fragmentadas e de baixa cobertura).
#
# Uso:
#   bash scripts/01_run_metaspades.sh <SAMPLE> [THREADS] [EXTRA_PARAMS]
#   R1=reads_R1.fastq.gz R2=reads_R2.fastq.gz bash scripts/01_run_metaspades.sh AMOSTRA
#
# Variáveis de ambiente aceitas:
#   R1, R2           — caminhos absolutos dos reads paired-end
#   SAMPLE_SINGLE    — caminho para single-end (alternativa a R1/R2)
#   THREADS          — número de threads (padrão: 4)
#   VELVET_K         — k-mer base (usado para definir escala dos k-mers)
#   SPADES_PARAMS    — flags extras para spades.py
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="${REPO_ROOT}/config/picornavirus.env"
LEGACY_CONFIG="${REPO_ROOT}/config.env"

# Se chamado pelo pipeline principal, não recarregar config.env.
if [[ "${PIPELINE_CONFIG_LOADED:-0}" != "1" ]]; then
  if [[ -f "${CONFIG_FILE}" ]]; then
    source "${CONFIG_FILE}"
  elif [[ -f "${LEGACY_CONFIG}" ]]; then
    source "${LEGACY_CONFIG}"
  fi
fi

source "${SCRIPT_DIR}/lib/common.sh"

SAMPLE="${1:?SAMPLE obrigatório}"
THREADS="${2:-${THREADS:-4}}"
SAMPLE="$(python3 "${SCRIPT_DIR}/lib/input_validation.py" sample "$SAMPLE")"
SPADES_PARAMS="${3:-${SPADES_PARAMS:-}}"

# Forçar offset 33 para dados sintéticos do pipeline para evitar falhas do auto-detector
if [[ "$SAMPLE" == "DEMO" || "$SAMPLE" == "nohits" ]]; then
  if [[ " ${SPADES_PARAMS} " != *" --phred-offset "* ]]; then
    SPADES_PARAMS="${SPADES_PARAMS} --phred-offset 33"
  fi
fi

RAW_DIR="$(resolve_path "${RAW_DIR:-data/raw}")"
ASSEMBLY_DIR="$(resolve_path "${ASSEMBLY_DIR:-data/assemblies}")"

# SPAdes 4.x falha quando o caminho de output contém espaços
# (erro: "conversion of data to type 'std::filesystem::path' failed")
# Soluição: sanitizar o nome da amostra no diretório, trocando espaços por _
SAFE_SAMPLE="${SAMPLE// /_}"
OUTDIR="${ASSEMBLY_DIR}/${SAFE_SAMPLE}_metaspades"

# Diretório com o nome original (para compat com o restante do pipeline)
ORIG_OUTDIR="${ASSEMBLY_DIR}/${SAMPLE}_metaspades"

# ─────────────────────────────────────────────────
# K-mers otimizados para fragmentos curtos/ultra-curtos
# Foco do trabalho: recuperar genomas virais fragmentados
# K-mers menores (21, 33) capturam fragmentos ultrashort
# ─────────────────────────────────────────────────
KMERS="${ADVANCED_KMERS:-auto}"
KMER_ARGS=()
if [[ -n "${ADVANCED_KMERS:-}" ]]; then
  KMER_ARGS=(-k "$ADVANCED_KMERS")
fi

# ─────────────────────────────────────────────────
# Detecção de reads
# ─────────────────────────────────────────────────
pick_first() { printf '%s\n' "$@" 2>/dev/null | sed '/^$/d' | sort | head -n1; }
find_read() {
  local sample="$1" raw_dir="$2" which="$3"
  local -a cands=()
  shopt -s nullglob
  if [[ "$which" == "R1" ]]; then
    cands=(
      "$raw_dir/${sample}_R1"*.fastq.gz "$raw_dir/${sample}_R1"*.fq.gz
      "$raw_dir/${sample}_R1"*.fastq    "$raw_dir/${sample}_R1"*.fq
      "$raw_dir/${sample}"*"_R1"*".fastq.gz" "$raw_dir/${sample}"*"_R1"*".fq.gz"
      "$raw_dir/${sample}_1"*.fastq.gz "$raw_dir/${sample}_1"*.fq.gz
    )
  else
    cands=(
      "$raw_dir/${sample}_R2"*.fastq.gz "$raw_dir/${sample}_R2"*.fq.gz
      "$raw_dir/${sample}_R2"*.fastq    "$raw_dir/${sample}_R2"*.fq
      "$raw_dir/${sample}"*"_R2"*".fastq.gz" "$raw_dir/${sample}"*"_R2"*".fq.gz"
      "$raw_dir/${sample}_2"*.fastq.gz "$raw_dir/${sample}_2"*.fq.gz
    )
  fi
  shopt -u nullglob
  pick_first "${cands[@]}"
}

RAW_SINGLE="${SAMPLE_SINGLE:-${SINGLE:-${FASTQ_SINGLE:-}}}"
RAW1="${R1:-${READ1:-${FASTQ_R1:-}}}"
RAW2="${R2:-${READ2:-${FASTQ_R2:-}}}"

if [[ -z "${RAW_SINGLE}" ]]; then
  if [[ -z "${RAW1}" || -z "${RAW2}" ]]; then
    RAW1="$(find_read "$SAMPLE" "$RAW_DIR" "R1")"
    RAW2="$(find_read "$SAMPLE" "$RAW_DIR" "R2")"
  fi
  if [[ -z "${RAW1}" || -z "${RAW2}" ]]; then
    log_error "FASTQs não encontrados para sample='$SAMPLE'.
Procurei em: $RAW_DIR
Alternativas aceitas:
  ${SAMPLE}_R1*.fastq(.gz) / ${SAMPLE}_R2*.fastq(.gz)
  ${SAMPLE}_1*.fq(.gz)     / ${SAMPLE}_2*.fq(.gz)
Defina explicitamente:
  R1=/caminho/r1.fastq.gz R2=/caminho/r2.fastq.gz bash $0 $SAMPLE"
  fi
fi

# ─────────────────────────────────────────────────
# Verificações de pré-requisito
# ─────────────────────────────────────────────────
command -v spades.py >/dev/null 2>&1 || log_error $'spades.py não encontrado no PATH.\nInstale com: sudo apt install -y spades\nOu use o bundle: bash bundle/install_wsl.sh'

if [[ -n "${RAW_SINGLE}" ]]; then
  check_file "$RAW_SINGLE"
else
  check_file "$RAW1"
  check_file "$RAW2"
fi

# ─────────────────────────────────────────────────
# Execução
# ─────────────────────────────────────────────────
mkdir -p "$OUTDIR"

log_info "[metaSPAdes] sample=$SAMPLE"
if [[ "$SAFE_SAMPLE" != "$SAMPLE" ]]; then
  log_info "[metaSPAdes] AVISO: espaço no nome da amostra detectado. Diretório sanitizado: $OUTDIR"
fi
log_info "[metaSPAdes] output=$OUTDIR"
log_info "[metaSPAdes] k-mers=$KMERS  threads=$THREADS"
if [[ -n "${RAW_SINGLE}" ]]; then
  log_info "[metaSPAdes] SINGLE=$RAW_SINGLE"
else
  log_info "[metaSPAdes] R1=$RAW1"
  log_info "[metaSPAdes] R2=$RAW2"
fi
[[ -n "$SPADES_PARAMS" ]] && log_info "[metaSPAdes] extra params='$SPADES_PARAMS'"

# Nota: --meta é o modo correto do metaSPAdes — habilita o assembler metagenômico
# Flags incompatíveis com --meta são filtrados do SPADES_PARAMS para evitar conflitos.
# Filtrar: --rnaviral, --rna, --plasmid, --metaviral, --metaplasmid, -k <vals>
SAFE_PARAMS=""
if [[ -n "${SPADES_PARAMS}" ]]; then
  # Lê token a token; descarta flags incompatíveis e seus argumentos
  skip_next=0
  for tok in ${SPADES_PARAMS}; do
    if [[ $skip_next -eq 1 ]]; then
      skip_next=0
      continue
    fi
    case "$tok" in
      --rnaviral|--rna|--plasmid|--metaviral|--metaplasmid|--meta)
        log_info "[metaSPAdes] AVISO: '$tok' removido de SPADES_PARAMS (incompatível com --meta)"
        ;;
      -k)
        log_info "[metaSPAdes] AVISO: '-k' de SPADES_PARAMS ignorado — usando k-mers otimizados: $KMERS"
        skip_next=1
        ;;
      -k,*|-k[0-9]*)
        log_info "[metaSPAdes] AVISO: '$tok' de SPADES_PARAMS ignorado — usando k-mers otimizados: $KMERS"
        ;;
      *)
        SAFE_PARAMS="${SAFE_PARAMS} ${tok}"
        ;;
    esac
  done
  SAFE_PARAMS="${SAFE_PARAMS# }"  # remove espaço inicial
fi
[[ -n "$SAFE_PARAMS" ]] && log_info "[metaSPAdes] params extras aplicados: '$SAFE_PARAMS'"

# Criar ambiente temporário curto livre de espaços/parênteses para evitar bugs do spades.py
SPADES_TMP_DIR="/tmp/spades_tmp_$(date +%s)_$$"
mkdir -p "$SPADES_TMP_DIR"
SPADES_TMP_OUT="$SPADES_TMP_DIR/out"

# Links simbólicos de entrada curtos
if [[ -n "${RAW_SINGLE}" ]]; then
  ln -sf "$RAW_SINGLE" "$SPADES_TMP_DIR/s.fastq.gz"
  log_info "[metaSPAdes] Executando montagem via link curto: $SPADES_TMP_DIR/s.fastq.gz"
  spades.py \
    --meta \
    "${KMER_ARGS[@]}" \
    -s "$SPADES_TMP_DIR/s.fastq.gz" \
    -o "$SPADES_TMP_OUT" \
    -t "$THREADS" \
    --only-assembler \
    ${SAFE_PARAMS}
else
  ln -sf "$RAW1" "$SPADES_TMP_DIR/r1.fastq.gz"
  ln -sf "$RAW2" "$SPADES_TMP_DIR/r2.fastq.gz"
  log_info "[metaSPAdes] Executando montagem via links curtos em $SPADES_TMP_DIR"
  spades.py \
    --meta \
    "${KMER_ARGS[@]}" \
    -1 "$SPADES_TMP_DIR/r1.fastq.gz" \
    -2 "$SPADES_TMP_DIR/r2.fastq.gz" \
    -o "$SPADES_TMP_OUT" \
    -t "$THREADS" \
    --only-assembler \
    ${SAFE_PARAMS}
fi

# Copiar os resultados de volta para a pasta real do Gene-In
if [[ -f "$SPADES_TMP_OUT/contigs.fasta" ]]; then
  mkdir -p "$OUTDIR"
  cp -f "$SPADES_TMP_OUT/contigs.fasta" "$OUTDIR/contigs.fasta"
  # Copiar outros arquivos úteis se existirem
  [[ -f "$SPADES_TMP_OUT/scaffolds.fasta" ]] && cp -f "$SPADES_TMP_OUT/scaffolds.fasta" "$OUTDIR/scaffolds.fasta" 2>/dev/null || true
  [[ -f "$SPADES_TMP_OUT/spades.log" ]] && cp -f "$SPADES_TMP_OUT/spades.log" "$OUTDIR/spades.log" 2>/dev/null || true
fi

# Limpar arquivos temporários curtos
rm -rf "$SPADES_TMP_DIR"

check_file "$OUTDIR/contigs.fasta"

# Se o nome da amostra foi sanitizado, criar symlink para o nome original
# (para que o router encontre em ${SAMPLE}_metaspades/contigs.fasta)
if [[ "$SAFE_SAMPLE" != "$SAMPLE" && ! -e "$ORIG_OUTDIR" ]]; then
  if ! ln -sf "$OUTDIR" "$ORIG_OUTDIR" 2>/dev/null; then
    # ln falha em NTFS: copiar os contigs diretamente
    mkdir -p "$ORIG_OUTDIR"
    rm -f "$ORIG_OUTDIR/contigs.fasta"
    cp -f "$OUTDIR/contigs.fasta" "$ORIG_OUTDIR/contigs.fasta"
    log_info "[metaSPAdes] cp fallback: contigs copiados para $ORIG_OUTDIR"
  fi
fi

log_info "[metaSPAdes] OK: $OUTDIR/contigs.fasta"
