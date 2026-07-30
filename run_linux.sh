#!/usr/bin/env bash
# run_linux.sh — Lançador do Gene-In para Linux nativo
# Uso normal (após ./install_linux.sh):
#   ./run_linux.sh
#
# Abre o dashboard web local. Acesse em: http://localhost:8000
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────
#  Localização do projeto
# ─────────────────────────────────────────────────────────────────────
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$ROOT"

CONFIG_FILE="$ROOT/config/picornavirus.env"
LEGACY_CONFIG="$ROOT/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
elif [[ -f "$LEGACY_CONFIG" ]]; then
    source "$LEGACY_CONFIG"
fi

# ─────────────────────────────────────────────────────────────────────
#  Caminhos do ambiente isolado
# ─────────────────────────────────────────────────────────────────────
BUNDLE_DIR="$ROOT/bundle"
BIN_DIR="$BUNDLE_DIR/bin"
ENV_DIR="$BUNDLE_DIR/env"
MICRO="$BIN_DIR/micromamba"
BIND_HOST="${BIND_HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

# ─────────────────────────────────────────────────────────────────────
#  Verificar que estamos em Linux
# ─────────────────────────────────────────────────────────────────────
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "[ERRO] Este script é para Linux nativo."
    echo "       No Windows, use ABRIR_GENEIN.bat na raiz do projeto."
    exit 1
fi

echo ""
echo "====================================================================="
echo "  Gene-In 1.1 — Abrindo plataforma (Linux)"
echo "====================================================================="
echo ""

# ─────────────────────────────────────────────────────────────────────
#  Verificar se o ambiente foi instalado
# ─────────────────────────────────────────────────────────────────────
if [[ ! -x "$MICRO" ]]; then
    echo "[ERRO] Micromamba não encontrado em: $MICRO"
    echo ""
    echo "  O Gene-In ainda não foi instalado neste computador."
    echo "  Execute primeiro o instalador:"
    echo ""
    echo "    ./install_linux.sh"
    echo ""
    exit 1
fi

if [[ ! -d "$ENV_DIR" ]]; then
    echo "[ERRO] Ambiente Gene-In não encontrado em: $ENV_DIR"
    echo ""
    echo "  O Gene-In ainda não foi instalado neste computador."
    echo "  Execute primeiro o instalador:"
    echo ""
    echo "    ./install_linux.sh"
    echo ""
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────
#  Detectar conda/mamba ativo — avisar, mas não bloquear
# ─────────────────────────────────────────────────────────────────────
if [[ -n "${CONDA_PREFIX:-}" ]] || [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    echo "[AVISO] Ambiente conda ativo detectado no shell."
    echo "        O Gene-In usará exclusivamente o ambiente isolado local:"
    echo "          $ENV_DIR"
    echo "        Seu ambiente conda não será afetado."
    echo ""
fi

# ─────────────────────────────────────────────────────────────────────
#  Verificar que python3 existe no ambiente isolado
# ─────────────────────────────────────────────────────────────────────
if ! "$MICRO" run -p "$ENV_DIR" command -v python > /dev/null 2>&1; then
    echo "[ERRO] Python não encontrado no ambiente isolado."
    echo ""
    echo "  O ambiente pode estar corrompido ou incompleto."
    echo "  Tente reinstalar com:"
    echo ""
    echo "    ./install_linux.sh"
    echo ""
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────
#  Verificar que o script do dashboard existe
# ─────────────────────────────────────────────────────────────────────
DASHBOARD_SCRIPT="$ROOT/scripts/ux_dashboard.py"
if [[ ! -f "$DASHBOARD_SCRIPT" ]]; then
    echo "[ERRO] Script do dashboard não encontrado: $DASHBOARD_SCRIPT"
    echo "       Verifique se a pasta do projeto está íntegra."
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────
#  Desativar influência de conda/mamba global durante a execução
# ─────────────────────────────────────────────────────────────────────
export MAMBA_ROOT_PREFIX="$BUNDLE_DIR/mamba"
unset CONDA_PREFIX      2>/dev/null || true
unset CONDA_DEFAULT_ENV 2>/dev/null || true
unset CONDA_SHLVL       2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────
#  Abrir o dashboard usando o Python do ambiente isolado
# ─────────────────────────────────────────────────────────────────────
echo "[OK] Ambiente verificado: $ENV_DIR"
echo "[OK] Iniciando Gene-In..."
echo ""
echo "  Quando o painel estiver pronto, acesse no navegador:"
if [[ "$BIND_HOST" == "0.0.0.0" ]]; then
    echo "    http://localhost:${PORT}"
    echo "    (escutando em todas as interfaces: ${BIND_HOST}:${PORT})"
else
    echo "    http://${BIND_HOST}:${PORT}"
fi
echo ""
echo "  Para fechar o Gene-In, pressione Ctrl+C nesta janela."
echo ""

exec "$MICRO" run -p "$ENV_DIR" \
    python "$DASHBOARD_SCRIPT" --host "$BIND_HOST" --port "$PORT"
