#!/usr/bin/env bash
set -euo pipefail

# ── Funções padronizadas de log ──────────────────────────────────────────────
# Formato: [NÍVEL] [ETAPA] [AMOSTRA] — descrição — ação sugerida
#
# Identificadores de etapa (sem acento):
#   QC_PREFLIGHT, QC_FASTP, HOST_FILTER, ASSEMBLY, RESCUE_READS,
#   BLAST, CLASSIFICACAO, REPORT, DASHBOARD
#
# Níveis: FATAL (interrompe), RECUPERADO (fallback), AVISO (não fatal), INFO

log_fatal()     { echo "[FATAL]      [${PIPELINE_ETAPA:-?}] [${SAMPLE_NAME:-?}] — $*" >&2; exit 1; }
log_recovered() { echo "[RECUPERADO] [${PIPELINE_ETAPA:-?}] [${SAMPLE_NAME:-?}] — $*"; }
log_warning()   { echo "[AVISO]      [${PIPELINE_ETAPA:-?}] [${SAMPLE_NAME:-?}] — $*" >&2; }
log_info()      { echo "[INFO]       [${PIPELINE_ETAPA:-?}] [${SAMPLE_NAME:-?}] — $*"; }

# Aliases para compatibilidade com código existente (run_assembly_router.sh, etc.)
log_error() { echo "[FATAL]      [${PIPELINE_ETAPA:-?}] [${SAMPLE_NAME:-?}] — $*" >&2; exit 1; }
log_warn()  { echo "[AVISO]      [${PIPELINE_ETAPA:-?}] [${SAMPLE_NAME:-?}] — $*" >&2; }

resolve_path() {
  local path="$1"
  if [[ "$path" == /* ]]; then
    echo "$path"
  else
    echo "${REPO_ROOT}/${path}"
  fi
}

check_file() {
  if [[ ! -s "$1" ]]; then
    log_error "Arquivo não encontrado ou vazio: $1"
  fi
}
