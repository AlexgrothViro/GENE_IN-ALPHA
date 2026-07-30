#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTDIR="$ROOT/dist"
VERSION="${1:-$(date +%Y%m%d)}"
NAME="picornavirus-wsl-bundle-${VERSION}"
STAGE="$OUTDIR/$NAME"

mkdir -p "$OUTDIR"
rm -rf "$STAGE"
mkdir -p "$STAGE"

echo "[INFO] Staging em: $STAGE"
# Copia projeto sem lixo pesado
rsync -a \
  --exclude '.git' \
  --exclude 'dist' \
  --exclude '.bundle' \
  --exclude 'data' \
  --exclude 'results' \
  --exclude 'blastdb' \
  --exclude 'bowtie2' \
  --exclude 'tmp' \
  --exclude 'logs' \
  --exclude 'run_T1' \
  "$ROOT/" "$STAGE/"

chmod +x "$STAGE/bundle/run.sh" "$STAGE/bundle/install_wsl.sh" || true
chmod +x "$STAGE/scripts/98_build_bundle_wsl.sh" || true

# Empacota tar.gz
TAR="$OUTDIR/${NAME}.tar.gz"
tar -czf "$TAR" -C "$OUTDIR" "$NAME"

# Empacota zip (via python, pra não depender de zip instalado)
ZIP="$OUTDIR/${NAME}.zip"
python3 - <<PY
import os, zipfile
root = r"$STAGE"
zip_path = r"$ZIP"
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for base, dirs, files in os.walk(root):
        for f in files:
            full = os.path.join(base, f)
            rel  = os.path.relpath(full, os.path.dirname(root))
            z.write(full, rel)
print("[OK] ZIP:", zip_path)
PY
echo "[OK] Bundle criado:"
echo " - $TAR"
echo " - $ZIP"
