#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-engineering}"

step() {
  local label="$1"
  shift
  printf '\n[TEST:%s] %s\n' "$MODE" "$label"
  "$@"
}

require_commands() {
  local missing=()
  local command_name
  for command_name in "$@"; do
    command -v "$command_name" >/dev/null 2>&1 || missing+=("$command_name")
  done
  if ((${#missing[@]})); then
    printf '[SKIP] ferramentas operacionais ausentes: %s\n' "${missing[*]}" >&2
    return 77
  fi
}

run_engineering() {
  echo "[SCOPE] Engenharia: contratos, fixtures, mocks, concorrência e regressões."
  echo "[LIMIT] Aprovação desta suíte não constitui validação científica ou qualificação de evidência."
  step "Python unittest discovery" \
    python3 -m unittest discover -s scripts/tests -p 'test_*.py'
  step "Roteamento/fallback de montagem com executáveis controlados" \
    bash scripts/tests/test_assembly_router_regressions.sh
  step "Estado explícito sem UMI-tools no remapeamento controlado" \
    bash scripts/tests/evidence/test_map_read_support.sh

  mapfile -d '' shell_files < <(find . -type f -name '*.sh' -print0)
  step "Sintaxe Bash de ${#shell_files[@]} scripts" bash -n "${shell_files[@]}"
  step "Compilação Python" python3 -m compileall -q scripts
  if command -v node >/dev/null 2>&1; then
    step "Sintaxe JavaScript do dashboard" node --check dashboard/app.js
  else
    echo "[SKIP] node ausente; dashboard/app.js não foi verificado nesta execução."
  fi
}

run_operational() {
  echo "[SCOPE] Operacional: ferramentas científicas reais instaladas neste host."
  echo "[LIMIT] As versões locais podem divergir do lock; isto não é validação científica."
  require_commands \
    python3 fastp bowtie2 bowtie2-build samtools \
    blastn blastdbcmd makeblastdb \
    spades.py metaspades.py velveth velvetg || return $?
  step "Integridade do lockfile versionado" \
    python3 scripts/evidence/environment_lock.py \
      --lockfile conda-linux-64.lock \
      --manifest config/environment_lock.json
  step "fastp e filtro de hospedeiro com ferramentas reais" \
    python3 -m unittest scripts.tests.test_host_filter
  step "Evidence V2 com BLAST+ real e painel sintético" \
    bash scripts/tests/evidence/test_blast_e2e_real.sh
  step "Velvet, SPAdes e metaSPAdes reais" \
    bash scripts/tests/test_assembly_tools_smoke.sh
}

case "$MODE" in
  engineering)
    run_engineering
    ;;
  operational)
    run_operational
    ;;
  reproducible)
    echo "[SCOPE] Reprodutibilidade: ambiente Conda ativo idêntico ao lock + testes operacionais."
    echo "[LIMIT] Mesmo esta suíte não substitui benchmark científico congelado e revisão independente."
    step "Qualificação estrita do ambiente ativo" \
      python3 scripts/tests/verify_locked_runtime.py
    run_operational
    ;;
  *)
    echo "Uso: $0 {engineering|operational|reproducible}" >&2
    exit 2
    ;;
esac

printf '\n[PASS] suíte %s concluída dentro do escopo declarado.\n' "$MODE"
