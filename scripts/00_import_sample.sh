#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<EOF2
Uso:
  bash scripts/00_import_sample.sh --sample NOME --r1 CAMINHO --r2 CAMINHO [--copy]

Importa para:
  data/raw/NOME_R1.fastq.gz
  data/raw/NOME_R2.fastq.gz
EOF2
}

SAMPLE=""
R1=""
R2=""
MODE="link"

normalize_windows_path() {
  local raw="$1"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%$'\r'}"

  if [[ "$raw" =~ ^[A-Za-z]:\\ ]]; then
    if command -v wslpath >/dev/null 2>&1; then
      wslpath -u -- "$raw"
      return
    fi
  fi

  printf '%s\n' "$raw"
}


resolve_existing_file() {
  local raw="$1"
  # se já existe como caminho (abs/rel), retorna
  if [[ -f "$raw" ]]; then
    printf '%s\n' "$raw"
    return 0
  fi

  # tenta basename em diretórios comuns
  local base
  base="$(basename "$raw")"

  local candidates=(
    "$PWD/$base"
    "$PWD/data/raw/$base"
    "$PWD/data/$base"
    "$HOME/Downloads/$base"
    "$HOME/Área de Trabalho/$base"
    "$HOME/Desktop/$base"
  )

  for c in "${candidates[@]}"; do
    if [[ -f "$c" ]]; then
      printf '%s\n' "$c"
      return 0
    fi
  done

  # tenta busca rápida no diretório atual (1 nível)
  local found
  found="$(find "$PWD" -maxdepth 2 -type f -name "$base" 2>/dev/null | head -n 1 || true)"
  if [[ -n "$found" && -f "$found" ]]; then
    printf '%s\n' "$found"
    return 0
  fi

  # não achou
  echo "[ERRO] Arquivo não encontrado: $raw" >&2
  echo "[DICA] Você pode passar caminho absoluto/relativo, ou apenas o nome do arquivo se ele estiver em:" >&2
  echo "       - pasta atual" >&2
  echo "       - data/raw/" >&2
  echo "       - ~/Downloads/" >&2
  echo "[DICA] Procurando por '$base' (até 2 níveis abaixo do diretório atual):" >&2
  find "$PWD" -maxdepth 2 -type f -name "$base" 2>/dev/null | sed 's/^/  - /' >&2 || true
  return 1
}

sanitize_sample() {
  python3 "$SCRIPT_DIR/lib/input_validation.py" sample "$1"
  return
  local raw="$1"
  raw="${raw%\"}"
  raw="${raw#\"}"
  raw="${raw%$'\r'}"
  raw="${raw// /_}"
  raw="$(printf '%s' "$raw" | LC_ALL=C tr -cs 'A-Za-z0-9_.-' '_')"
  raw="${raw#_}"; raw="${raw%_}"
  raw="${raw:0:80}"
  printf '%s\n' "$raw"
}

check_ext() {
  local file="$1"
  [[ "$file" =~ \.fastq$ || "$file" =~ \.fastq\.gz$ ]] || {
    echo "[ERRO] extensão inválida (use .fastq ou .fastq.gz): $file"
    exit 1
  }
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sample) SAMPLE="${2:-}"; shift 2;;
    --r1) R1="${2:-}"; shift 2;;
    --r2) R2="${2:-}"; shift 2;;
    --copy) MODE="copy"; shift 1;;
    -h|--help) usage; exit 0;;
    *) echo "[ERRO] argumento inválido: $1"; usage; exit 2;;
  esac
done

[[ -n "$SAMPLE" && -n "$R1" && -n "$R2" ]] || { echo "[ERRO] faltou --sample/--r1/--r2"; usage; exit 2; }

SAMPLE_RAW="$SAMPLE"
SAMPLE="$(sanitize_sample "$SAMPLE_RAW")"
if [[ -z "$SAMPLE" ]]; then
  echo "[ERRO] sample inválido após sanitização: $SAMPLE_RAW" >&2
  exit 2
fi
if [[ "$SAMPLE" != "$SAMPLE_RAW" ]]; then
  echo "[INFO] sample sanitizado: '$SAMPLE_RAW' -> '$SAMPLE'"
fi


R1="$(normalize_windows_path "$R1")"
R2="$(normalize_windows_path "$R2")"

R1="$(resolve_existing_file "$R1")"
R2="$(resolve_existing_file "$R2")"

if [[ ! -s "$R1" ]]; then
  echo "[ERRO] arquivo vazio: $R1"
  exit 1
fi
if [[ ! -s "$R2" ]]; then
  echo "[ERRO] arquivo vazio: $R2"
  exit 1
fi

check_ext "$R1"
check_ext "$R2"
python3 "$SCRIPT_DIR/lib/input_validation.py" fastq "$R1" --mate "$R2"

if [[ "$R1" != *"R1"* ]]; then
  echo "[AVISO] arquivo R1 não contém marcador R1 no nome: $R1"
fi
if [[ "$R2" != *"R2"* ]]; then
  echo "[AVISO] arquivo R2 não contém marcador R2 no nome: $R2"
fi

mkdir -p data/raw
out1="data/raw/${SAMPLE}_R1.fastq.gz"
out2="data/raw/${SAMPLE}_R2.fastq.gz"

place_fastq() {
  local src="$1" dst="$2"
  local tmp="${dst}.tmp.$$"
  rm -f "$tmp"
  if [[ "$src" == *.fastq.gz ]]; then
    if [[ "$MODE" == "copy" ]]; then
      cp -f "$src" "$tmp"
    else
      ln -sf "$(realpath "$src")" "$tmp"
    fi
  else
    gzip -c "$src" > "$tmp"
  fi
  mv -f "$tmp" "$dst"
}

place_fastq "$R1" "$out1"
place_fastq "$R2" "$out2"

echo "[OK] Amostra importada: $SAMPLE"
echo "  $out1"
echo "  $out2"
