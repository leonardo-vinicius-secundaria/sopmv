#!/usr/bin/env bash
# Gera somente as variantes SOPMV10/20/30 da familia 16pr76_T100.
# Mantem o sorteio aleatorio com seed 202601, sem filtro de viabilidade,
# como nas instancias SOPMV ja congeladas do benchmark.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GENERATOR="$ROOT/scripts/gerar_instancias_sopmv.py"
SOURCE_DIR="$ROOT/data/intancias_grandes/sop"
DEST_ROOT="$ROOT/data/intancias_grandes"

[[ -f "$GENERATOR" ]] || { echo "Gerador ausente: $GENERATOR" >&2; exit 2; }
for profile in p1 p2; do
  [[ -f "$SOURCE_DIR/16pr76_T100_${profile}.sop" ]] || {
    echo "Instancia ausente: $SOURCE_DIR/16pr76_T100_${profile}.sop" >&2
    exit 2
  }
done
for directory in sopmv10 sopmv20 sopmv30; do
  for profile in p1 p2; do
    target="$DEST_ROOT/$directory/16pr76_T100_${profile}.sop"
    [[ ! -e "$target" ]] || { echo "Destino ja existe: $target" >&2; exit 2; }
  done
done

TEMP_SOURCE=$(mktemp -d)
trap 'rm -rf "$TEMP_SOURCE"' EXIT
cp "$SOURCE_DIR/16pr76_T100_p1.sop" "$SOURCE_DIR/16pr76_T100_p2.sop" "$TEMP_SOURCE/"

python3 "$GENERATOR" \
  --origem "$TEMP_SOURCE" \
  --raiz-saida "$DEST_ROOT" \
  --pastas-saida sopmv10 sopmv20 sopmv30 \
  --semente 202601
