#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BIN="$ROOT/build/vns_sop_adapted/sources/sop_vns"
OUT="$ROOT/new_experiments/vns_sopmv_contracts_$(date +%Y%m%d_%H%M%S)"
[[ -x "$BIN" ]] || { echo "VNS adaptado nao compilado" >&2; exit 2; }
mkdir -p "$OUT"
for instance in "$ROOT"/data/instancias_pequenas/sopmv_10/11berlin52_T80_p1.sop "$ROOT"/data/instancias_pequenas/sopmv_20/11berlin52_T80_p1.sop; do
  name=$(basename "$instance" .sop); work="$OUT/$name"; mkdir -p "$work"
  "$BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 --output="$work" --results=results.log --save-results=1 --save-info=0 --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 --initial-greedy-solution=1 --use-rvns=0 --seed=202601 --time-only-stop=1 --maximal-calculation-time-sec=2 --num-iterations=2147483647 --num-iterations-unimproved=2147483647 >"$work/stdout.log" 2>&1
  python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$work/results.log" | tee "$work/validation.txt"
done
echo "Contratos SOPMV validados em: $OUT"
