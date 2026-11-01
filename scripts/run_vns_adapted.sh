#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BIN=${VNS_ADAPTED_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
[[ $# -ge 2 ]] || { echo "Uso: $0 INSTANCIA SEED [TEMPO_SEGUNDOS]" >&2; exit 2; }
INSTANCE=$1; SEED=$2; LIMIT=${3:-60}
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/vns_adapted_${STAMP}_seed${SEED}"
mkdir -p "$OUT"
"$BIN" --problem="$INSTANCE" --sop-type=sop --name=no_name --gui=none --nowait=1 \
  --output="$OUT" --results=results.log --save-results=1 --save-info=0 --save-settings=1 \
  --save-visual=0 --save-targets=0 --save-sampled-path=0 --initial-greedy-solution=1 \
  --use-rvns=0 --seed="$SEED" --time-only-stop=1 --maximal-calculation-time-sec="$LIMIT" \
  --num-iterations=2147483647 --num-iterations-unimproved=2147483647 \
  >"$OUT/stdout.log" 2>&1
echo "Resultado: $OUT"
