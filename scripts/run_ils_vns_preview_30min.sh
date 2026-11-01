#!/usr/bin/env bash
# Pilotos de no maximo 30 min, com o orcamento completo de 1,5 x SETS.
# Uso: ./scripts/run_ils_vns_preview_30min.sh {small-sop|large-sop|small-sopmv|large-sopmv}
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/config/benchmark_ils_vns.env"
ILS_BIN=${ILS_BIN:-"$ROOT/build/bin/sopmv_ils_new_version"}
VNS_BIN=${VNS_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
STAGE=${1:-large-sop}
[[ "$STAGE" =~ ^(small-sop|large-sop|small-sopmv|large-sopmv)$ ]] || {
  echo "Uso: $0 {small-sop|large-sop|small-sopmv|large-sopmv}" >&2; exit 2; }
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$ROOT/new_experiments/ils_vns_preview_30min_${STAGE}_${STAMP}"
[[ -x "$ILS_BIN" && -x "$VNS_BIN" ]] || { echo "ILS ou VNS adaptado nao compilado" >&2; exit 2; }
[[ ! -e "$OUT" ]] || { echo "Diretorio ja existe: $OUT" >&2; exit 2; }
mkdir -p "$OUT/raw_vns" "$OUT/logs/ils" "$OUT/logs/vns"
printf 'solver,instance,seed,sets,time_limit_seconds,variant\n' > "$OUT/manifest.csv"
printf 'instance,seed,sets,time_limit_seconds,reward,distance,iterations,validation\n' > "$OUT/vns_results.csv"

case "$STAGE" in
  small-sop)
    mapfile -t INSTANCES < <(find "$ROOT/data/instancias_pequenas/sop" -maxdepth 1 -type f -name '*.sop' | sort)
    PREVIEW_SEEDS="202601 202602"
    ;;
  large-sop)
    INSTANCES=("$ROOT/data/intancias_grandes/sop/212u1060_T80_p1.sop" "$ROOT/data/intancias_grandes/sop/217vm1084_T80_p1.sop")
    PREVIEW_SEEDS="202601"
    ;;
  small-sopmv)
    INSTANCES=()
    for group in sopmv_10 sopmv_20 sopmv_30; do
      mapfile -t selected < <(find "$ROOT/data/instancias_pequenas/$group" -maxdepth 1 -type f -name '*.sop' | sort | head -n 7)
      INSTANCES+=("${selected[@]}")
    done
    PREVIEW_SEEDS="202601 202602"
    ;;
  large-sopmv)
    # Dois extremos de MV; o MV20 entra na campanha completa posterior.
    INSTANCES=("$ROOT/data/intancias_grandes/sopmv10/212u1060_T80_p1.sop" "$ROOT/data/intancias_grandes/sopmv30/217vm1084_T80_p1.sop")
    PREVIEW_SEEDS="202601"
    ;;
esac

for instance in "${INSTANCES[@]}"; do
  [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
done

for instance in "${INSTANCES[@]}"; do
  name=$(basename "$instance" .sop)
  sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  limit=$(python3 -c "import math; print(math.ceil($TIME_MULTIPLIER * $sets))")
  for SEED in $PREVIEW_SEEDS; do
    printf 'ILS,%s,%s,%s,%s,%s\n' "$name" "$SEED" "$sets" "$limit" "$STAGE" >> "$OUT/manifest.csv"
    "$ILS_BIN" --instance "$instance" --ils-iterations 1000000000 --ils-time-limit "$limit" --ils-reset-interval "$ILS_RESET_INTERVAL" --seed "$SEED" --csv "$OUT/ils_results.csv" >"$OUT/logs/ils/${name}_seed${SEED}.log" 2>&1
    work="$OUT/raw_vns/${name}_seed${SEED}"; mkdir -p "$work"
    printf 'VNS,%s,%s,%s,%s,%s\n' "$name" "$SEED" "$sets" "$limit" "$STAGE" >> "$OUT/manifest.csv"
    "$VNS_BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 --output="$work" --results=results.log --save-results=1 --save-info=0 --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 --initial-greedy-solution=1 --use-rvns=0 --seed="$SEED" --time-only-stop=1 --maximal-calculation-time-sec="$limit" --num-iterations=2147483647 --num-iterations-unimproved=2147483647 >"$OUT/logs/vns/${name}_seed${SEED}.log" 2>&1
    validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$work/results.log")
    record=$(tail -n 1 "$work/results.log")
    reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record")
    distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record")
    iterations=$(sed -n 's/.*;NUM_ITERS:\([^;]*\);.*/\1/p' <<< "$record")
    printf '%s,%s,%s,%s,%s,%s,%s,"%s"\n' "$name" "$SEED" "$sets" "$limit" "$reward" "$distance" "$iterations" "$validation" >> "$OUT/vns_results.csv"
  done
done
echo "Concluido: $OUT"
