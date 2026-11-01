#!/usr/bin/env bash
# Valida a viabilidade do VNS adaptado em SOPMV10/20/30.
# Executa todas as 60 instancias pequenas e vm1084 grande em cada nivel.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BIN=${VNS_ADAPTED_BIN:-"$ROOT/build/vns_sop_adapted/sources/sop_vns"}
SEED=${1:-202601}
[[ "$SEED" =~ ^[0-9]+$ ]] || { echo "Seed deve ser numerica" >&2; exit 2; }
[[ -x "$BIN" ]] || { echo "VNS adaptado nao compilado: $BIN" >&2; exit 2; }

OUT="$ROOT/new_experiments/vns_sopmv_validation_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT/raw_vns" "$OUT/logs"
printf 'instance,group,size,seed,sets,time_limit_seconds,reward,distance,iterations,validation\n' > "$OUT/results.csv"

INSTANCES=()
for group in sopmv_10 sopmv_20 sopmv_30; do
  while IFS= read -r instance; do INSTANCES+=("$group:small:$instance"); done < <(
    find "$ROOT/data/instancias_pequenas/$group" -maxdepth 1 -type f -name '*.sop' | sort
  )
done
INSTANCES+=(
  "sopmv10:large:$ROOT/data/intancias_grandes/sopmv10/217vm1084_T80_p1.sop"
  "sopmv20:large:$ROOT/data/intancias_grandes/sopmv20/217vm1084_T80_p1.sop"
  "sopmv30:large:$ROOT/data/intancias_grandes/sopmv30/217vm1084_T80_p1.sop"
)

for item in "${INSTANCES[@]}"; do
  IFS=: read -r group size instance <<< "$item"
  [[ -f "$instance" ]] || { echo "Instancia ausente: $instance" >&2; exit 2; }
  name=$(basename "$instance" .sop)
  sets=$(sed -n 's/^SETS:[[:space:]]*//p' "$instance" | head -n 1)
  limit=$(( (3 * sets + 1) / 2 )) # ceil(1.5 * SETS)
  work="$OUT/raw_vns/${group}_${size}_${name}"
  mkdir -p "$work"

  "$BIN" --problem="$instance" --sop-type=sop --name=no_name --gui=none --nowait=1 \
    --output="$work" --results=results.log --save-results=1 --save-info=0 \
    --save-settings=0 --save-visual=0 --save-targets=0 --save-sampled-path=0 \
    --initial-greedy-solution=1 --use-rvns=0 --seed="$SEED" --time-only-stop=1 \
    --maximal-calculation-time-sec="$limit" --num-iterations=2147483647 \
    --num-iterations-unimproved=2147483647 \
    >"$OUT/logs/${group}_${size}_${name}.log" 2>&1

  validation=$(python3 "$ROOT/scripts/validate_vns_solution.py" --instance "$instance" --results-log "$work/results.log")
  record=$(tail -n 1 "$work/results.log")
  reward=$(sed -n 's/.*;REWARDS:\([^;]*\);.*/\1/p' <<< "$record")
  distance=$(sed -n 's/.*;LENGTH:\([^;]*\);.*/\1/p' <<< "$record")
  iterations=$(sed -n 's/.*;NUM_ITERS:\([^;]*\);.*/\1/p' <<< "$record")
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,"%s"\n' \
    "$name" "$group" "$size" "$SEED" "$sets" "$limit" "$reward" "$distance" "$iterations" "$validation" \
    >> "$OUT/results.csv"
done

echo "Validadas ${#INSTANCES[@]} solucoes SOPMV: $OUT"
