#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SOURCE=${VNS_SOURCE:-/home/leo/vns-sop}
DEST=${VNS_ADAPTED_DIR:-"$ROOT/build/vns_sop_adapted"}
[[ -d "$SOURCE/sources" ]] || { echo "VNS_SOURCE invalido: $SOURCE" >&2; exit 2; }
rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$SOURCE/." "$DEST/"
rm -rf "$DEST/.git" "$DEST/results" "$DEST/sources/obj" "$DEST/sources/sop_vns"
for patch_file in "$ROOT"/vns_adapter/patches/*.patch; do
  patch -d "$DEST" -p1 < "$patch_file"
done
make -C "$DEST/sources" sop_vns
echo "VNS adaptado: $DEST/sources/sop_vns"
