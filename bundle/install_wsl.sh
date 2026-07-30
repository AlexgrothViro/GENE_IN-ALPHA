#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="$HOME/.gene-in-bundle"
BIN_DIR="$BUNDLE_DIR/bin"
ENV_DIR="$BUNDLE_DIR/env"
MAMBA_ROOT="$BUNDLE_DIR/mamba"
MICRO="$BIN_DIR/micromamba"

export MAMBA_ROOT_PREFIX="$MAMBA_ROOT"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

LOCAL_MAMBA_CANDIDATES=(
  "$ROOT/bundle/cache/micromamba.tar.bz2"
  "$ROOT/bundle/cache/micromamba-linux-64.tar.bz2"
  "$ROOT/bundle/micromamba.tar.bz2"
)

resolve_local_mamba() {
  local file
  for file in "${LOCAL_MAMBA_CANDIDATES[@]}"; do
    if [[ -f "$file" ]]; then
      echo "$file"
      return 0
    fi
  done
  return 1
}

echo "[INFO] Root: $ROOT"
mkdir -p "$BIN_DIR" "$MAMBA_ROOT"

# Pré-requisitos mínimos (se faltar, tenta instalar via apt com sudo)
if ! need_cmd curl; then
  echo "[WARN] curl não encontrado. Tentando instalar via apt (sudo)..."
  sudo apt-get update && sudo apt-get install -y curl ca-certificates
fi
if ! need_cmd tar; then
  echo "[WARN] tar não encontrado. Tentando instalar via apt (sudo)..."
  sudo apt-get update && sudo apt-get install -y tar
fi
if ! need_cmd bzip2; then
  echo "[WARN] bzip2 não encontrado. Tentando instalar via apt (sudo)..."
  sudo apt-get update && sudo apt-get install -y bzip2
fi

# Instala micromamba (preferindo bundle/cache local em modo offline)
if [[ ! -x "$MICRO" ]]; then
  tmp="$(mktemp -d)"
  if local_bundle="$(resolve_local_mamba)"; then
    echo "[INFO] Usando micromamba local: $local_bundle"
    tar -xvjf "$local_bundle" -C "$tmp" bin/micromamba
  else
    echo "[INFO] Bundle local não encontrado. Baixando micromamba..."
    ( cd "$tmp" && curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba )
  fi
  install -m 0755 "$tmp/bin/micromamba" "$MICRO"
  rm -rf "$tmp"
else
  echo "[INFO] micromamba já existe: $MICRO"
fi

# Cria/atualiza o ambiente local a partir do environment.yml do projeto
if [[ ! -f "$ROOT/environment.yml" ]]; then
  echo "[ERROR] environment.yml não encontrado em $ROOT"
  exit 1
fi
if [[ ! -d "$ENV_DIR" ]]; then
  echo "[INFO] Criando ambiente em: $ENV_DIR"
  "$MICRO" create -y -p "$ENV_DIR" -f "$ROOT/environment.yml"
else
  echo "[INFO] Atualizando ambiente existente em: $ENV_DIR"
  "$MICRO" install -y -p "$ENV_DIR" -f "$ROOT/environment.yml"
fi

echo "[INFO] Verificando ferramentas dentro do env..."
"$MICRO" run -p "$ENV_DIR" python -V || true
"$MICRO" run -p "$ENV_DIR" blastn -version 2>/dev/null | head -n 1 || true
"$MICRO" run -p "$ENV_DIR" bowtie2 --version 2>/dev/null | head -n 1 || true
"$MICRO" run -p "$ENV_DIR" spades.py --version 2>/dev/null || true
"$MICRO" run -p "$ENV_DIR" mafft --version 2>&1 | head -n 1 || true
"$MICRO" run -p "$ENV_DIR" iqtree2 -version 2>&1 | head -n 1 || true
if ! "$MICRO" run -p "$ENV_DIR" python -c 'import yaml' >/dev/null 2>&1; then
  echo "[ERROR] PyYAML não está disponível no ambiente instalado." >&2
  echo "        Reexecute a atualização do ambiente antes de usar Evidence V2." >&2
  exit 1
fi
"$MICRO" run -p "$ENV_DIR" python -c 'import yaml; print("[OK] PyYAML", getattr(yaml, "__version__", "unknown"))'

echo "[OK] Ambiente pronto. Use: bash bundle/run.sh smoke-test"
