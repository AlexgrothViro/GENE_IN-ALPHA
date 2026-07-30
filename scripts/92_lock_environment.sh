#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT="${REPO_ROOT}/conda-linux-64.lock"
MANIFEST="${REPO_ROOT}/config/environment_lock.json"
TMP="${OUTPUT}.tmp.$$"
command -v micromamba >/dev/null 2>&1 || { echo "[FATAL] micromamba não encontrado" >&2; exit 2; }
[[ "$(uname -s)" == "Linux" ]] || { echo "[FATAL] o lock validado deve ser gerado em Linux/WSL" >&2; exit 2; }
trap 'rm -f "$TMP"' EXIT
micromamba list --name gene-in --explicit > "$TMP"
grep -Eq '^https?://.*#[0-9a-fA-F]{32,64}$' "$TMP" || { echo "[FATAL] lock explícito sem URLs/hashes" >&2; exit 2; }
mv -f "$TMP" "$OUTPUT"
python3 "${SCRIPT_DIR}/evidence/environment_lock.py" --record --lockfile "$OUTPUT" --manifest "$MANIFEST"
trap - EXIT
echo "[OK] lock gerado: $OUTPUT"
