#!/usr/bin/env bash
# Benchmark reproduzivel ILS (N=40) x VNS adaptado.
# Uso: ./scripts/run_ils_vns_benchmark.sh {small-sop|large-sop|small-sopmv|large-sopmv}
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/config/benchmark_ils_vns.env"
ILS_BIN=${ILS_BIN:-"$ROOT/build/bin/sopmv_ils_new_version"}
VNS_BIN=${VNS_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
STAGE=${1:-}
[[ "$STAGE" =~ ^(small-sop|large-sop|small-sopmv|large-sopmv)$ ]] || {
  echo "Uso: $0 {small-sop|large-sop|small-sopmv|large-sopmv}" >&2; exit 2; }
[[ -x "$ILS_BIN" && -x "$VNS_BIN" ]] || { echo "ILS ou VNS adaptado nao compilado" >&2; exit 2; }

STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/ils_vns_${STAGE}_${STAMP}"
ILS_CSV="$OUT/ils_results.csv"
VNS_CSV="$OUT/vns_results.csv"
MANIFEST="$OUT/manifest.csv"
mkdir -p "$OUT/raw_vns" "$OUT/logs/ils" "$OUT/logs/vns"
printf 'solver,instance,seed,sets,time_limit_seconds,variant\n' > "$MANIFEST"
printf 'instance,seed,sets,time_limit_seconds,reward,distance,iterations,validation\n' > "$VNS_CSV"

case "$STAGE" in
  small-sop)
    mapfile -t INSTANCES < <(find "$ROOT/data/instancias_pequenas/sop" -maxdepth 1 -name '*.sop' -type f | sort)
    ;;
  large-sop)
    INSTANCES=(
      "$ROOT/data/intancias_grandes/sop/212u1060_T80_p1.sop"
      "$ROOT/data/intancias_grandes/sop/217vm1084_T80_p1.sop"
    )
    ;;
  small-sopmv)
    mapfile -t INSTANCES < <(find "$ROOT/data/instancias_pequenas" -mindepth 2 -maxdepth 2 -path '*/sopmv_*/*.sop' -type f | sort)
    ;;
  large-sopmv)
    INSTANCES=()
    for mv in sopmv10 sopmv20 sopmv30; do
      INSTANCES+=("$ROOT/data/intancias_grandes/$mv/212u1060_T80_p1.sop")
      INSTANCES+=("$ROOT/data/intancias_grandes/$mv/217vm1084_T80_p1.sop")
    done
    ;;
esac

[[ ${#INSTANCES[@]} -gt 0 ]] || { echo "Nenhuma instancia selecionada" >&2; exit 2; }
for instance in "${INSTANCES[@]}"; do [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }; done

for instance in "${INSTANCES[@]}"; do
  name=$(basename "$instance" .sop)
  sets=$(awk -F': *' '/^SETS:/ {print $2; exit}' "$instance")
  limit=$(python3 -c "import math; print(max(1, math.ceil($TIME_MULTIPLIER * $sets)))")
  variant=$(basename "$(dirname "$instance")")
  for seed in $SEEDS; do
    printf 'ILS,%s,%s,%s,%s,%s\n' "$name" "$seed" "$sets" "$limit" "$variant" >> "$MANIFEST"
    "$ILS_BIN" --instance "$instance" --ils-iterations 1000000000 --ils-time-limit "$limit" --ils-reset-interval "$ILS_RESET_INTERVAL" --seed "$seed" --csv "$ILS_CSV" >"$OUT/logs/ils/${name}_seed${seed}.log" 2>&1

    work="$OUT/raw_vns/${name}_seed${seed}"; mkdir -p "$work"
    printf 'VNS,%s,%s,%s,%s,%s\n' "$name" "$seed" "$sets" "$limit" "$variant" >> "$MANIFEST"
    "$VNS_BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 --output="$work" --results=results.log --save-results=1 --save-info=0 --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 --initial-greedy-solution=1 --use-rvns=0 --seed="$seed" --time-only-stop=1 --maximal-calculation-time-sec="$limit" --num-iterations=2147483647 --num-iterations-unimproved=2147483647 >"$OUT/logs/vns/${name}_seed${seed}.log" 2>&1
    validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$work/results.log")
    record=$(tail -n 1 "$work/results.log")
    reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record")
    distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record")
    iterations=$(sed -n 's/.*;NUM_ITERS:\([^;]*\);.*/\1/p' <<< "$record")
    printf '%s,%s,%s,%s,%s,%s,%s,"%s"\n' "$name" "$seed" "$sets" "$limit" "$reward" "$distance" "$iterations" "$validation" >> "$VNS_CSV"
  done
done
echo "Concluido: $OUT"
